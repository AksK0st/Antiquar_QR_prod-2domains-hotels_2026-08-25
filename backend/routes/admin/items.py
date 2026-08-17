from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from config import settings
from db import get_db
from models.admin_user import AdminUser
from models.collection import Collection
from models.item import Item
from models.item_image import ItemImage
from schemas.item import AdminItemResponse, ItemCreate, ItemUpdate
from security.dependencies import get_current_admin
from services.audit import add_audit_log
from services.db_errors import integrity_sqlstate
from services.qr import generate_item_qr_png
from services.storage_cleanup import delete_object_or_enqueue


logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/items",
    tags=["admin-items"],
    dependencies=[Depends(get_current_admin)],
)


async def _ensure_collection_exists(db: AsyncSession, collection_id: int | None) -> None:
    if collection_id is None:
        return
    if await db.get(Collection, collection_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Collection not found",
        )


def _raise_integrity_error(exc: IntegrityError, *, entity: str) -> None:
    sqlstate = integrity_sqlstate(exc)
    if sqlstate == "23505":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{entity} with this slug already exists",
        ) from exc
    if sqlstate in {"23502", "23503", "23514"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {entity.lower()} data",
        ) from exc
    logger.exception("Unexpected database integrity error")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database operation failed",
    ) from exc


@router.get("/{item_id}/qr", response_class=Response)
async def get_item_qr(item_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    png_data = await run_in_threadpool(
        generate_item_qr_png,
        public_id=item.public_id,
        name=item.name,
        base_url=settings.public_base_url,
    )
    return Response(
        content=png_data,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="{item.slug}-qr.png"',
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/", response_model=AdminItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    data: ItemCreate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_collection_exists(db, data.collection_id)
    item = Item(**data.model_dump())
    db.add(item)
    try:
        await db.flush()
        await add_audit_log(
            db,
            request=request,
            action="item.create",
            admin=admin,
            entity_type="item",
            entity_id=item.id,
            details={"slug": item.slug},
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        _raise_integrity_error(exc, entity="Item")

    await db.refresh(item)
    return item


@router.get("/", response_model=list[AdminItemResponse])
async def get_items(
    q: str | None = Query(default=None, max_length=100),
    collection_id: int | None = Query(default=None, ge=1),
    is_active: bool | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    statement = select(Item)
    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.where(or_(Item.name.ilike(pattern), Item.slug.ilike(pattern)))
    if collection_id is not None:
        statement = statement.where(Item.collection_id == collection_id)
    if is_active is not None:
        statement = statement.where(Item.is_active.is_(is_active))

    result = await db.execute(
        statement.order_by(Item.sort_order, Item.id).limit(limit).offset(offset)
    )
    return result.scalars().all()


@router.get("/by-slug/{slug}", response_model=AdminItemResponse)
async def get_item_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item).where(Item.slug == slug))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.get("/{item_id}", response_model=AdminItemResponse)
async def get_item(item_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.patch("/{item_id}", response_model=AdminItemResponse)
async def update_item(
    item_id: int,
    data: ItemUpdate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    if data.expected_version != item.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item was modified by another session. Reload and try again.",
        )

    update_data = data.model_dump(exclude_unset=True, exclude={"expected_version"})
    await _ensure_collection_exists(db, update_data.get("collection_id", item.collection_id))

    merged_period_from = update_data.get("period_from", item.period_from)
    merged_period_to = update_data.get("period_to", item.period_to)
    if (
        merged_period_from is not None
        and merged_period_to is not None
        and merged_period_from > merged_period_to
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="period_from must be less than or equal to period_to",
        )

    changed_fields: list[str] = []
    for field, value in update_data.items():
        if getattr(item, field) != value:
            setattr(item, field, value)
            changed_fields.append(field)

    if changed_fields:
        item.version += 1
        await add_audit_log(
            db,
            request=request,
            action="item.update",
            admin=admin,
            entity_type="item",
            entity_id=item.id,
            details={"fields": changed_fields},
        )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        _raise_integrity_error(exc, entity="Item")

    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    image_result = await db.execute(
        select(ItemImage.object_name).where(ItemImage.item_id == item_id)
    )
    object_names = list(image_result.scalars().all())
    slug = item.slug

    await add_audit_log(
        db,
        request=request,
        action="item.delete",
        admin=admin,
        entity_type="item",
        entity_id=item.id,
        details={"slug": slug, "images": len(object_names)},
    )
    await db.delete(item)
    await db.commit()

    for object_name in object_names:
        await delete_object_or_enqueue(db, object_name)

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.admin_user import AdminUser
from models.collection import Collection
from models.item import Item
from schemas.collection import CollectionCreate, CollectionRead, CollectionUpdate
from security.dependencies import get_current_admin
from services.audit import add_audit_log
from services.db_errors import integrity_sqlstate


logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/collections",
    tags=["admin-collections"],
    dependencies=[Depends(get_current_admin)],
)


def _raise_integrity_error(exc: IntegrityError) -> None:
    sqlstate = integrity_sqlstate(exc)
    if sqlstate == "23505":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Collection with this slug already exists",
        ) from exc
    if sqlstate in {"23502", "23514"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid collection data",
        ) from exc
    logger.exception("Unexpected collection integrity error")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database operation failed",
    ) from exc


@router.post("/", response_model=CollectionRead, status_code=status.HTTP_201_CREATED)
async def create_collection(
    data: CollectionCreate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    collection = Collection(**data.model_dump())
    db.add(collection)
    try:
        await db.flush()
        await add_audit_log(
            db,
            request=request,
            action="collection.create",
            admin=admin,
            entity_type="collection",
            entity_id=collection.id,
            details={"slug": collection.slug},
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        _raise_integrity_error(exc)

    await db.refresh(collection)
    return collection


@router.get("/", response_model=list[CollectionRead])
async def get_collections(
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    statement = select(Collection)
    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.where(
            or_(Collection.name.ilike(pattern), Collection.slug.ilike(pattern))
        )
    result = await db.execute(statement.order_by(Collection.id).limit(limit).offset(offset))
    return result.scalars().all()


@router.get("/{collection_id}", response_model=CollectionRead)
async def get_collection(collection_id: int, db: AsyncSession = Depends(get_db)):
    collection = await db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.patch("/{collection_id}", response_model=CollectionRead)
async def update_collection(
    collection_id: int,
    data: CollectionUpdate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    collection = (
        await db.execute(
            select(Collection).where(Collection.id == collection_id).with_for_update()
        )
    ).scalar_one_or_none()
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    if data.expected_version != collection.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Collection was modified by another session. Reload and try again.",
        )

    update_data = data.model_dump(exclude_unset=True, exclude={"expected_version"})
    changed_fields: list[str] = []
    for field, value in update_data.items():
        if getattr(collection, field) != value:
            setattr(collection, field, value)
            changed_fields.append(field)

    if changed_fields:
        collection.version += 1
        await add_audit_log(
            db,
            request=request,
            action="collection.update",
            admin=admin,
            entity_type="collection",
            entity_id=collection.id,
            details={"fields": changed_fields},
        )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        _raise_integrity_error(exc)

    await db.refresh(collection)
    return collection


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    collection = (
        await db.execute(
            select(Collection).where(Collection.id == collection_id).with_for_update()
        )
    ).scalar_one_or_none()
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")

    item_result = await db.execute(
        select(Item.id).where(Item.collection_id == collection_id).limit(1)
    )
    if item_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Collection contains items",
        )

    await add_audit_log(
        db,
        request=request,
        action="collection.delete",
        admin=admin,
        entity_type="collection",
        entity_id=collection.id,
        details={"slug": collection.slug},
    )
    await db.delete(collection)
    await db.commit()

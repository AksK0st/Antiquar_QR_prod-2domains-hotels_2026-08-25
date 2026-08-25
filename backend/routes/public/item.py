from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db
from models.item import Item
from schemas.item import ItemRead, ItemSummary
from services.site import hotel_name_for_request


router = APIRouter(prefix="/items", tags=["public-items"])


@router.get("/", response_model=list[ItemSummary])
async def get_items(
    request: Request,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    hotel_name = hotel_name_for_request(request)
    result = await db.execute(
        select(Item)
        .where(Item.is_active.is_(True), Item.hotel_name == hotel_name)
        .options(selectinload(Item.images))
        .order_by(Item.sort_order, Item.id)
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def _load_active_item(statement, db: AsyncSession) -> Item:
    item = (await db.execute(statement.options(selectinload(Item.images)))).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    if not item.is_active:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Item is temporarily unavailable",
        )
    return item


@router.get("/by-public-id/{public_id}", response_model=ItemRead)
async def get_item_by_public_id(
    public_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    hotel_name = hotel_name_for_request(request)
    return await _load_active_item(
        select(Item).where(Item.public_id == public_id, Item.hotel_name == hotel_name), db
    )


@router.get("/{slug}", response_model=ItemRead)
async def get_item_by_slug(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    hotel_name = hotel_name_for_request(request)
    return await _load_active_item(
        select(Item).where(Item.slug == slug, Item.hotel_name == hotel_name), db
    )

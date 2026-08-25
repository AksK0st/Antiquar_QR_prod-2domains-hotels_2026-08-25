from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.collection import Collection
from schemas.collection import PublicCollectionRead
from services.site import hotel_name_for_request


router = APIRouter(prefix="/collections", tags=["public-collections"])


@router.get("/", response_model=list[PublicCollectionRead])
async def get_collections(
    request: Request,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    hotel_name = hotel_name_for_request(request)
    result = await db.execute(
        select(Collection)
        .where(Collection.hotel_name == hotel_name)
        .order_by(Collection.id)
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/{collection_id}", response_model=PublicCollectionRead)
async def get_collection(
    collection_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    hotel_name = hotel_name_for_request(request)
    collection = (
        await db.execute(
            select(Collection).where(
                Collection.id == collection_id,
                Collection.hotel_name == hotel_name,
            )
        )
    ).scalar_one_or_none()
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    return collection

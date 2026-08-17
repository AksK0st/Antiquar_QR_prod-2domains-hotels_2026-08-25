from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.collection import Collection
from schemas.collection import PublicCollectionRead


router = APIRouter(prefix="/collections", tags=["public-collections"])


@router.get("/", response_model=list[PublicCollectionRead])
async def get_collections(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Collection).order_by(Collection.id).limit(limit).offset(offset)
    )
    return result.scalars().all()


@router.get("/{collection_id}", response_model=PublicCollectionRead)
async def get_collection(collection_id: int, db: AsyncSession = Depends(get_db)):
    collection = await db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    return collection

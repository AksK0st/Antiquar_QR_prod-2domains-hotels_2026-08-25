from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse
from minio.error import S3Error
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from db import get_db
from minio_client import MINIO_BUCKET, minio_client
from models.item import Item
from models.item_image import ItemImage
from services.site import hotel_name_for_request


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/images", tags=["public-images"])


def _storage_error(exc: S3Error, object_name: str) -> HTTPException:
    logger.exception("Public image storage failure for %s", object_name)
    if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
        return HTTPException(status_code=404, detail="Image not found")
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Image storage temporarily unavailable",
    )


async def _stream_image(image: ItemImage, request: Request, *, immutable: bool):
    etag = f'"image-{image.id}-v{image.content_version}-{image.size or 0}"'
    cache_control = (
        "public, max-age=31536000, immutable"
        if immutable
        else "public, max-age=300, stale-while-revalidate=60"
    )
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": cache_control})

    try:
        response = await run_in_threadpool(
            lambda: minio_client.get_object(MINIO_BUCKET, image.object_name)
        )
    except S3Error as exc:
        raise _storage_error(exc, image.object_name) from exc
    except OSError as exc:
        logger.exception("Public image storage connection failure for %s", image.object_name)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image storage temporarily unavailable",
        ) from exc

    def close_response():
        response.close()
        response.release_conn()

    headers = {
        "Cache-Control": cache_control,
        "ETag": etag,
    }
    if image.size is not None:
        headers["Content-Length"] = str(image.size)

    return StreamingResponse(
        response.stream(32 * 1024),
        media_type=image.content_type or "application/octet-stream",
        background=BackgroundTask(close_response),
        headers=headers,
    )


@router.get("/by-id/{image_id}/v/{content_version}")
async def get_image_by_stable_id(
    image_id: int,
    content_version: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    hotel_name = hotel_name_for_request(request)
    image = (
        await db.execute(
            select(ItemImage)
            .join(Item)
            .where(
                Item.is_active.is_(True),
                Item.hotel_name == hotel_name,
                ItemImage.id == image_id,
                ItemImage.content_version == content_version,
            )
        )
    ).scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return await _stream_image(image, request, immutable=True)


@router.get("/{item_slug}")
async def get_image_by_slug(
    item_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    hotel_name = hotel_name_for_request(request)
    image = (
        await db.execute(
            select(ItemImage)
            .join(Item)
            .where(
                Item.slug == item_slug,
                Item.hotel_name == hotel_name,
                Item.is_active.is_(True),
            )
            .order_by(ItemImage.is_primary.desc(), ItemImage.sort_order, ItemImage.id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return await _stream_image(image, request, immutable=False)


@router.get("/{item_slug}/{image_id}")
async def get_image_by_id(
    item_slug: str,
    image_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    hotel_name = hotel_name_for_request(request)
    image = (
        await db.execute(
            select(ItemImage)
            .join(Item)
            .where(
                Item.slug == item_slug,
                Item.hotel_name == hotel_name,
                Item.is_active.is_(True),
                ItemImage.id == image_id,
            )
        )
    ).scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return await _stream_image(image, request, immutable=True)

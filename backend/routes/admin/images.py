from __future__ import annotations

import logging
from io import BytesIO
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from minio.error import S3Error
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from config import settings
from db import get_db
from minio_client import MINIO_BUCKET, minio_client
from models.admin_user import AdminUser
from models.item import Item
from models.item_image import ItemImage
from schemas.admin_image import AdminItemImageOrderRequest, AdminItemImageResponse
from security.dependencies import get_current_admin
from services.audit import add_audit_log
from services.image_processing import (
    ALLOWED_IMAGE_TYPES,
    ImageTooLargeError,
    InvalidImageError,
    process_image,
)
from services.storage_cleanup import delete_object_or_enqueue


logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/items/{item_id}/images",
    tags=["admin-images"],
    dependencies=[Depends(get_current_admin)],
)


def stream_minio_object(response):
    try:
        for chunk in response.stream(32 * 1024):
            yield chunk
    finally:
        response.close()
        response.release_conn()


def _storage_http_error(exc: S3Error, *, action: str) -> HTTPException:
    if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
        return HTTPException(status_code=404, detail="Stored image not found")
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Object storage {action} failed",
    )


@router.post("/", response_model=AdminItemImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_item_image(
    item_id: int,
    file: UploadFile,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminItemImageResponse:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        await file.close()
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG and WebP images are allowed",
        )

    raw_data = await file.read(settings.admin_image_max_bytes + 1)
    if not raw_data:
        await file.close()
        raise HTTPException(status_code=400, detail="Empty image file")
    if len(raw_data) > settings.admin_image_max_bytes:
        await file.close()
        raise HTTPException(status_code=413, detail="Image file is too large")

    try:
        processed = await run_in_threadpool(
            process_image,
            raw_data,
            file.content_type,
            settings.admin_image_max_pixels,
        )
    except ImageTooLargeError as exc:
        await file.close()
        raise HTTPException(status_code=413, detail="Image resolution is too large") from exc
    except InvalidImageError as exc:
        await file.close()
        raise HTTPException(status_code=415, detail="Invalid image file") from exc

    # Re-encoding may produce a larger payload than the uploaded source. Limit
    # the actual object that will be persisted, not only the incoming request.
    if processed.size > settings.admin_image_max_bytes:
        await file.close()
        raise HTTPException(status_code=413, detail="Processed image file is too large")

    original_filename = (file.filename or "image").replace("\\", "/").split("/")[-1][:255]
    object_name = f"items/{item_id}/{uuid4().hex}{processed.extension}"

    try:
        await run_in_threadpool(
            lambda: minio_client.put_object(
                bucket_name=MINIO_BUCKET,
                object_name=object_name,
                data=BytesIO(processed.data),
                length=processed.size,
                content_type=processed.content_type,
            )
        )
    except (S3Error, OSError) as exc:
        logger.exception("MinIO upload failed for item %s", item_id)
        await file.close()
        if isinstance(exc, S3Error):
            raise _storage_http_error(exc, action="upload") from exc
        raise HTTPException(status_code=503, detail="Object storage upload failed") from exc

    try:
        # Serialize image metadata changes for the same item. This prevents two
        # concurrent first uploads from both becoming primary.
        item_result = await db.execute(
            select(Item).where(Item.id == item_id).with_for_update()
        )
        item = item_result.scalar_one_or_none()
        if item is None:
            await db.rollback()
            await delete_object_or_enqueue(db, object_name)
            raise HTTPException(status_code=404, detail="Item not found")

        images_result = await db.execute(
            select(func.count(ItemImage.id), func.max(ItemImage.sort_order)).where(
                ItemImage.item_id == item_id
            )
        )
        image_count, max_sort_order = images_result.one()
        image = ItemImage(
            item_id=item_id,
            object_name=object_name,
            original_filename=original_filename,
            content_type=processed.content_type,
            size=processed.size,
            width=processed.width,
            height=processed.height,
            sort_order=0 if max_sort_order is None else max_sort_order + 1,
            is_primary=(image_count == 0),
        )
        db.add(image)
        await db.flush()
        await add_audit_log(
            db,
            request=request,
            action="image.upload",
            admin=admin,
            entity_type="item_image",
            entity_id=image.id,
            details={"item_id": item_id, "size": processed.size},
        )
        await db.commit()
        await db.refresh(image)
        return image
    except HTTPException:
        raise
    except (IntegrityError, SQLAlchemyError) as exc:
        await db.rollback()
        logger.exception("Failed to save image metadata for %s", object_name)
        await delete_object_or_enqueue(db, object_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save image metadata",
        ) from exc
    finally:
        await file.close()


@router.get("/", response_model=list[AdminItemImageResponse])
async def get_item_images(item_id: int, db: AsyncSession = Depends(get_db)):
    if await db.get(Item, item_id) is None:
        raise HTTPException(status_code=404, detail="Item not found")
    result = await db.execute(
        select(ItemImage)
        .where(ItemImage.item_id == item_id)
        .order_by(ItemImage.sort_order, ItemImage.id)
    )
    return list(result.scalars().all())


@router.patch("/{image_id}/primary", response_model=AdminItemImageResponse)
async def set_primary_image(
    item_id: int,
    image_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    # Lock the item to serialize primary/reorder/delete mutations for its images.
    item = (
        await db.execute(select(Item).where(Item.id == item_id).with_for_update())
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    image = (
        await db.execute(
            select(ItemImage).where(
                ItemImage.id == image_id,
                ItemImage.item_id == item_id,
            )
        )
    ).scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    await db.execute(
        update(ItemImage).where(ItemImage.item_id == item_id).values(is_primary=False)
    )
    image.is_primary = True
    await add_audit_log(
        db,
        request=request,
        action="image.set_primary",
        admin=admin,
        entity_type="item_image",
        entity_id=image.id,
        details={"item_id": item_id},
    )
    await db.commit()
    await db.refresh(image)
    return image


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item_image(
    item_id: int,
    image_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    item = (
        await db.execute(select(Item).where(Item.id == item_id).with_for_update())
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    image = (
        await db.execute(
            select(ItemImage).where(
                ItemImage.id == image_id,
                ItemImage.item_id == item_id,
            )
        )
    ).scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    object_name = image.object_name
    if image.is_primary:
        image.is_primary = False
        await db.flush()
        replacement = (
            await db.execute(
                select(ItemImage)
                .where(ItemImage.item_id == item_id, ItemImage.id != image_id)
                .order_by(ItemImage.sort_order, ItemImage.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if replacement is not None:
            replacement.is_primary = True
            await db.flush()

    await add_audit_log(
        db,
        request=request,
        action="image.delete",
        admin=admin,
        entity_type="item_image",
        entity_id=image.id,
        details={"item_id": item_id},
    )
    await db.delete(image)
    await db.commit()
    await delete_object_or_enqueue(db, object_name)


@router.patch("/order", response_model=list[AdminItemImageResponse])
async def reorder_item_images(
    item_id: int,
    payload: AdminItemImageOrderRequest,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    item = (
        await db.execute(select(Item).where(Item.id == item_id).with_for_update())
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    result = await db.execute(select(ItemImage).where(ItemImage.item_id == item_id))
    images = list(result.scalars().all())
    existing_ids = {image.id for image in images}
    requested_ids = payload.image_ids

    if len(requested_ids) != len(set(requested_ids)):
        raise HTTPException(status_code=400, detail="Duplicate image IDs are not allowed")
    if set(requested_ids) != existing_ids:
        raise HTTPException(
            status_code=400,
            detail="Image IDs must contain all item images exactly once",
        )

    images_by_id = {image.id: image for image in images}
    for sort_order, image_id in enumerate(requested_ids):
        images_by_id[image_id].sort_order = sort_order

    await add_audit_log(
        db,
        request=request,
        action="image.reorder",
        admin=admin,
        entity_type="item",
        entity_id=item_id,
        details={"image_ids": requested_ids},
    )
    await db.commit()
    return [images_by_id[image_id] for image_id in requested_ids]


@router.get("/{image_id}/content")
async def get_item_image_content(
    item_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_db),
):
    image = (
        await db.execute(
            select(ItemImage).where(
                ItemImage.id == image_id,
                ItemImage.item_id == item_id,
            )
        )
    ).scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        minio_response = await run_in_threadpool(
            lambda: minio_client.get_object(
                bucket_name=MINIO_BUCKET,
                object_name=image.object_name,
            )
        )
    except S3Error as exc:
        logger.exception("Failed to read MinIO object %s", image.object_name)
        raise _storage_http_error(exc, action="read") from exc
    except OSError as exc:
        logger.exception("Object storage connection failed for %s", image.object_name)
        raise HTTPException(status_code=503, detail="Object storage read failed") from exc

    return StreamingResponse(
        stream_minio_object(minio_response),
        media_type=image.content_type or "application/octet-stream",
        headers={"Cache-Control": "private, no-store"},
    )

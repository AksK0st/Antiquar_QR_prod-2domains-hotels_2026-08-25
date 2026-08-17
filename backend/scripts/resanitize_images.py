"""Re-encode image objects created before upload sanitization was fixed.

Dry-run by default. Use ``--apply`` only after taking a backup. The script
normalizes EXIF orientation, strips metadata by re-encoding the image, and
updates image dimensions/content metadata in PostgreSQL.
"""
from __future__ import annotations

import argparse
import asyncio
from io import BytesIO

from minio.error import S3Error
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from config import settings
from db import SessionLocal
from minio_client import MINIO_BUCKET, minio_client
from models.item_image import ItemImage
from services.image_processing import InvalidImageError, ImageTooLargeError, process_image


async def _read_object(object_name: str, limit: int) -> bytes:
    def read() -> bytes:
        response = minio_client.get_object(MINIO_BUCKET, object_name)
        try:
            data = response.read(limit + 1)
        finally:
            response.close()
            response.release_conn()
        if len(data) > limit:
            raise ImageTooLargeError(f"stored object exceeds {limit} bytes")
        return data

    return await run_in_threadpool(read)


async def run(apply: bool) -> int:
    changed = 0
    failed = 0
    async with SessionLocal() as db:
        images = (await db.execute(select(ItemImage).order_by(ItemImage.id))).scalars().all()
        for image in images:
            if not image.content_type:
                print(f"[SKIP] id={image.id} {image.object_name}: missing content_type")
                failed += 1
                continue
            try:
                raw = await _read_object(image.object_name, settings.admin_image_max_bytes)
                processed = process_image(
                    raw,
                    declared_content_type=image.content_type,
                    max_pixels=settings.admin_image_max_pixels,
                )
                if processed.size > settings.admin_image_max_bytes:
                    raise ImageTooLargeError(
                        f"sanitized object exceeds {settings.admin_image_max_bytes} bytes"
                    )
            except (S3Error, OSError, InvalidImageError, ImageTooLargeError) as exc:
                print(f"[ERROR] id={image.id} {image.object_name}: {exc}")
                failed += 1
                continue

            metadata_changed = (
                image.size != processed.size
                or image.width != processed.width
                or image.height != processed.height
                or image.content_type != processed.content_type
            )
            bytes_changed = raw != processed.data
            if not bytes_changed and not metadata_changed and not apply:
                print(f"[OK] id={image.id} {image.object_name}")
                continue

            if bytes_changed or metadata_changed:
                changed += 1
                print(
                    f"[{'APPLY' if apply else 'DRY-RUN'}] id={image.id} {image.object_name}: "
                    f"bytes={len(raw)}->{processed.size}, "
                    f"dimensions={image.width}x{image.height}->{processed.width}x{processed.height}"
                )

            if apply:
                if bytes_changed:
                    await run_in_threadpool(
                        lambda p=processed, n=image.object_name: minio_client.put_object(
                            bucket_name=MINIO_BUCKET,
                            object_name=n,
                            data=BytesIO(p.data),
                            length=p.size,
                            content_type=p.content_type,
                        )
                    )
                image.size = processed.size
                image.width = processed.width
                image.height = processed.height
                image.content_type = processed.content_type
                # Always advance the public cache key in apply mode. If an earlier
                # run managed to overwrite MinIO but failed before the DB commit,
                # rerunning --apply still invalidates any long-lived browser cache.
                image.content_version += 1

        if apply:
            await db.commit()
        else:
            await db.rollback()

    print(f"Done: changed={changed}, failed={failed}, mode={'apply' if apply else 'dry-run'}")
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="overwrite objects and update DB metadata (default is dry-run)",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.apply)))


if __name__ == "__main__":
    main()

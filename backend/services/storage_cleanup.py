from __future__ import annotations

import logging

from minio.error import S3Error
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from minio_client import MINIO_BUCKET, minio_client
from models.storage_cleanup_job import StorageCleanupJob


logger = logging.getLogger(__name__)


async def enqueue_cleanup(db: AsyncSession, object_name: str, error: Exception | str) -> None:
    # PostgreSQL upsert makes enqueue idempotent and safe when multiple requests
    # fail to delete the same object concurrently.
    message = str(error)[:4000]
    stmt = (
        insert(StorageCleanupJob)
        .values(object_name=object_name, attempts=1, last_error=message)
        .on_conflict_do_update(
            index_elements=[StorageCleanupJob.object_name],
            set_={
                "attempts": StorageCleanupJob.attempts + 1,
                "last_error": message,
                "updated_at": func.now(),
            },
        )
    )
    await db.execute(stmt)
    await db.commit()


async def delete_object_or_enqueue(db: AsyncSession, object_name: str) -> bool:
    try:
        await run_in_threadpool(
            lambda: minio_client.remove_object(
                bucket_name=MINIO_BUCKET,
                object_name=object_name,
            )
        )
        return True
    except (S3Error, OSError) as exc:
        logger.exception("Object cleanup failed: %s", object_name)
        await enqueue_cleanup(db, object_name, exc)
        return False

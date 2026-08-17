from __future__ import annotations

import asyncio
import logging

from minio.error import S3Error
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from db import SessionLocal
from minio_client import MINIO_BUCKET, minio_client
from models.storage_cleanup_job import StorageCleanupJob

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("storage_cleanup")


async def main() -> int:
    failures = 0
    async with SessionLocal() as db:
        jobs = (
            await db.execute(select(StorageCleanupJob).order_by(StorageCleanupJob.id).limit(500))
        ).scalars().all()
        for job in jobs:
            try:
                await run_in_threadpool(
                    lambda name=job.object_name: minio_client.remove_object(MINIO_BUCKET, name)
                )
            except (S3Error, OSError) as exc:
                failures += 1
                job.attempts += 1
                job.last_error = str(exc)[:4000]
                logger.warning("retry failed object=%s attempts=%s", job.object_name, job.attempts)
            else:
                await db.delete(job)
                logger.info("deleted object=%s", job.object_name)
        await db.commit()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

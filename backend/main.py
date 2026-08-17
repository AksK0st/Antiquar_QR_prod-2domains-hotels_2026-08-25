from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import fastapi
from fastapi.middleware.cors import CORSMiddleware
from minio.error import S3Error
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from config import settings
from db import SessionLocal, engine
from logging_config import configure_logging
from middleware.http import ApplicationHttpMiddleware
from minio_client import MINIO_BUCKET, minio_client
from routes import router


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: fastapi.FastAPI):
    revision = "unknown"
    try:
        async with SessionLocal() as db:
            result = await db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            revision = result.scalar_one_or_none() or "none"
    except Exception:
        logger.exception("Failed to read migration revision during startup")

    logger.info("application_started", extra={"event": "application_started"})
    logger.info("database_migration_revision=%s", revision, extra={"event": "migration_revision"})
    yield
    await engine.dispose()


app = fastapi.FastAPI(
    title="Antiquar QR API",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(ApplicationHttpMiddleware)

if not settings.is_production and settings.allowed_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )

app.include_router(router)


@app.get("/health/live", include_in_schema=False)
async def health_live():
    return {"status": "ok"}


@app.get("/health/ready", include_in_schema=False)
async def health_ready():
    errors: list[str] = []

    try:
        async with SessionLocal() as db:
            await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=3)
    except Exception:
        logger.exception("Database readiness check failed")
        errors.append("database")

    try:
        bucket_exists = await asyncio.wait_for(
            run_in_threadpool(minio_client.bucket_exists, MINIO_BUCKET),
            timeout=max(settings.minio_connect_timeout_seconds + 1, 3),
        )
        if not bucket_exists:
            errors.append("object_storage_bucket")
    except (S3Error, OSError, TimeoutError, asyncio.TimeoutError):
        logger.exception("Object storage readiness check failed")
        errors.append("object_storage")
    except Exception:
        logger.exception("Unexpected object storage readiness failure")
        errors.append("object_storage")

    if errors:
        raise fastapi.HTTPException(
            status_code=503,
            detail={"status": "not_ready", "dependencies": errors},
        )

    return {"status": "ready"}


@app.get("/health", include_in_schema=False)
async def health_compat():
    return await health_live()

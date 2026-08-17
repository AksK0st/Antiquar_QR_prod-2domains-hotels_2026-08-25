from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from minio.error import S3Error
from sqlalchemy import select

from db import SessionLocal
from minio_client import MINIO_BUCKET, minio_client
from models.item_image import ItemImage


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete-orphans", action="store_true")
    parser.add_argument("--grace-hours", type=int, default=24)
    args = parser.parse_args()

    async with SessionLocal() as db:
        db_objects = set((await db.execute(select(ItemImage.object_name))).scalars().all())

    storage = {}
    try:
        for obj in minio_client.list_objects(MINIO_BUCKET, recursive=True):
            storage[obj.object_name] = obj
    except S3Error as exc:
        print(f"ERROR: could not list object storage: {exc}")
        return 2

    missing = sorted(db_objects - storage.keys())
    orphans = sorted(storage.keys() - db_objects)
    print(f"DB objects: {len(db_objects)}; storage objects: {len(storage)}")
    print(f"Missing in storage: {len(missing)}")
    for name in missing:
        print(f"  MISSING {name}")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(args.grace_hours, 0))
    deletable = []
    for name in orphans:
        modified = storage[name].last_modified
        status = "ORPHAN"
        if modified and modified <= cutoff:
            deletable.append(name)
            status = "ORPHAN_OLD"
        print(f"  {status} {name}")

    if args.delete_orphans:
        for name in deletable:
            minio_client.remove_object(MINIO_BUCKET, name)
            print(f"  DELETED {name}")

    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

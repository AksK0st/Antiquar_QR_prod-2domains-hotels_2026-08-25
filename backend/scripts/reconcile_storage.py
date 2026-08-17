from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
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
        rows = (
            await db.execute(
                select(
                    ItemImage.item_id,
                    ItemImage.object_name,
                    ItemImage.is_primary,
                )
            )
        ).all()

    db_objects = {row.object_name for row in rows}
    images_by_item: dict[int, list[bool]] = defaultdict(list)
    for row in rows:
        images_by_item[row.item_id].append(row.is_primary)

    primary_anomalies: list[tuple[int, int, int]] = []
    for item_id, primary_flags in images_by_item.items():
        primary_count = sum(primary_flags)
        if primary_count != 1:
            primary_anomalies.append((item_id, len(primary_flags), primary_count))

    storage = {}
    try:
        for obj in minio_client.list_objects(MINIO_BUCKET, recursive=True):
            storage[obj.object_name] = obj
    except (S3Error, OSError) as exc:
        print(f"ERROR: could not list object storage: {exc}")
        return 2

    missing = sorted(db_objects - storage.keys())
    orphans = sorted(storage.keys() - db_objects)
    print(f"DB objects: {len(db_objects)}; storage objects: {len(storage)}")
    print(f"Missing in storage: {len(missing)}")
    for name in missing:
        print(f"  MISSING {name}")

    print(f"Primary-image anomalies: {len(primary_anomalies)}")
    for item_id, image_count, primary_count in primary_anomalies:
        print(
            f"  PRIMARY item_id={item_id} images={image_count} primary_count={primary_count}"
        )

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
            try:
                minio_client.remove_object(MINIO_BUCKET, name)
            except (S3Error, OSError) as exc:
                print(f"  DELETE_FAILED {name}: {exc}")
                return 2
            print(f"  DELETED {name}")

    return 1 if missing or primary_anomalies else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

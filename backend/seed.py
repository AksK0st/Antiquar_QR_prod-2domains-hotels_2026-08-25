import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import SessionLocal
from models.collection import Collection
from models.item import Item


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def load_json(filename: str) -> list[dict]:
    path = DATA_DIR / filename

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


async def seed_collections(
    db: AsyncSession,
) -> None:
    collections = load_json("collections.json")

    for raw_data in collections:
        data = raw_data.copy()
        data.setdefault("hotel_name", "Галерея")
        result = await db.execute(
            select(Collection).where(
                Collection.slug == data["slug"],
                Collection.hotel_name == data["hotel_name"],
            )
        )

        existing = result.scalar_one_or_none()

        if existing is not None:
            print(
                f"[SKIP] Collection: {data['slug']}"
            )
            continue

        collection = Collection(**data)

        db.add(collection)

        print(
            f"[CREATE] Collection: {data['slug']}"
        )

    await db.commit()


async def seed_items(
    db: AsyncSession,
) -> None:
    items = load_json("items.json")

    for raw_data in items:
        data = raw_data.copy()
        data.setdefault("hotel_name", "Галерея")

        result = await db.execute(
            select(Item).where(
                Item.slug == data["slug"],
                Item.hotel_name == data["hotel_name"],
            )
        )

        existing = result.scalar_one_or_none()

        if existing is not None:
            print(
                f"[SKIP] Item: {data['slug']}"
            )
            continue

        collection_slug = data.pop(
            "collection_slug",
            None,
        )

        collection_id = None

        if collection_slug is not None:
            result = await db.execute(
                select(Collection).where(
                    Collection.slug == collection_slug,
                    Collection.hotel_name == data["hotel_name"],
                )
            )

            collection = (
                result.scalar_one_or_none()
            )

            if collection is None:
                raise RuntimeError(
                    "Collection "
                    f"'{collection_slug}' "
                    "not found for item "
                    f"'{data['slug']}'"
                )

            collection_id = collection.id

        item = Item(
            **data,
            collection_id=collection_id,
        )

        db.add(item)

        print(
            f"[CREATE] Item: {data['slug']}"
        )

    await db.commit()


async def main() -> None:
    print("Starting database seed...")

    async with SessionLocal() as db:
        await seed_collections(db)
        await seed_items(db)

    print("Seed completed.")


if __name__ == "__main__":
    asyncio.run(main())
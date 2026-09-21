import asyncio
from pathlib import Path

import qrcode
from sqlalchemy import select

from config import settings
from db import SessionLocal
from models.collection import Collection


OUTPUT_DIR = Path("/backend/qr_codes_collections")


def safe_name(value: str) -> str:
    return (
        value.strip()
        .replace("/", "-")
        .replace("\\", "-")
    )


def build_collection_url(hotel_name: str, collection_slug: str) -> str:
    base_url = settings.public_base_url_for_hotel(hotel_name).rstrip("/")
    return f"{base_url}/c/{collection_slug}"


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with SessionLocal() as db:
        result = await db.execute(
            select(Collection)
            .order_by(
                Collection.hotel_name,
                Collection.name,
            )
        )

        collections = result.scalars().all()

    print(f"Найдено коллекций: {len(collections)}")

    for collection in collections:
        url = build_collection_url(
            hotel_name=collection.hotel_name,
            collection_slug=collection.slug,
        )

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=12,
            border=4,
        )

        qr.add_data(url)
        qr.make(fit=True)

        image = qr.make_image(
            fill_color="black",
            back_color="white",
        )

        hotel_dir = OUTPUT_DIR / safe_name(collection.hotel_name)
        hotel_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{collection.slug}.png"
        output_path = hotel_dir / filename

        image.save(output_path)

        print(
            f"[OK] {collection.name}\n"
            f"     {url}\n"
            f"     -> {output_path}"
        )


if __name__ == "__main__":
    asyncio.run(main())
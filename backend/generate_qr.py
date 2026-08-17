import asyncio
from pathlib import Path

from sqlalchemy import select

from config import settings
from db import SessionLocal
from models.item import Item
from services.qr import build_item_public_url, generate_item_qr_png


OUTPUT_DIR = Path("/backend/qr_codes")


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with SessionLocal() as db:
        result = await db.execute(
            select(Item)
            .where(Item.is_active.is_(True))
            .order_by(Item.sort_order, Item.id)
        )
        items = result.scalars().all()

    print(f"Generating {len(items)} QR codes...\n")

    for item in items:
        png_data = generate_item_qr_png(
            public_id=item.public_id,
            name=item.name,
            base_url=settings.public_base_url,
        )
        output_path = OUTPUT_DIR / f"{item.slug}-{item.public_id}.png"
        output_path.write_bytes(png_data)

        url = build_item_public_url(
            base_url=settings.public_base_url,
            public_id=item.public_id,
        )
        print(f"[QR] {item.name}\n     {url}\n     -> {output_path}")

    print(f"\nDone. Generated {len(items)} QR codes.")


if __name__ == "__main__":
    asyncio.run(main())

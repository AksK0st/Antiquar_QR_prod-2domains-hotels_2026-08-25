import asyncio
import json
from io import BytesIO
from pathlib import Path

from minio.error import S3Error
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db import SessionLocal
from minio_client import minio_client, MINIO_BUCKET
from models.item import Item
from models.item_image import ItemImage
from services.image_processing import (
    ALLOWED_IMAGE_TYPES,
    InvalidImageError,
    ImageTooLargeError,
    process_image,
)


BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIRS = [
    BASE_DIR / "data" / "gallery" / "media",
    BASE_DIR / "data" / "mozart" / "media",
]


def load_manifests() -> list[tuple[Path, dict]]:
    result = []

    for media_dir in MEDIA_DIRS:
        manifest_path = media_dir / "media.json"

        if not manifest_path.exists():
            continue

        with manifest_path.open("r", encoding="utf-8") as file:
            manifest = json.load(file)

        for item_data in manifest:
            result.append((media_dir, item_data))

    return result


def ensure_bucket() -> None:
    if minio_client.bucket_exists(MINIO_BUCKET):
        print(f"[OK] Bucket: {MINIO_BUCKET}")
        return
    minio_client.make_bucket(MINIO_BUCKET)
    print(f"[CREATE] Bucket: {MINIO_BUCKET}")


def object_exists(object_name: str) -> bool:
    try:
        minio_client.stat_object(MINIO_BUCKET, object_name)
        return True
    except S3Error as error:
        if error.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
            return False
        raise


def _content_type_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    mapping = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    content_type = mapping.get(suffix)
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise RuntimeError(f"Unsupported seed media type: {path.name}")
    return content_type


def ensure_minio_object(
    media_dir: Path,
    relative_path: str,
    hotel_name: str,
) -> tuple[str, str, int, int, int]:

    file_path = media_dir / relative_path

    if not file_path.exists():
        raise FileNotFoundError(f"Media file not found: {file_path}")

    content_type = _content_type_for_path(file_path)

    try:
        processed = process_image(
            file_path.read_bytes(),
            declared_content_type=content_type,
            max_pixels=settings.admin_image_max_pixels,
        )
    except (InvalidImageError, ImageTooLargeError) as exc:
        raise RuntimeError(f"Invalid seed media {file_path}: {exc}") from exc

    if processed.size > settings.admin_image_max_bytes:
        raise RuntimeError(
            f"Sanitized seed media exceeds "
            f"{settings.admin_image_max_bytes} bytes: {file_path}"
        )

    # Отдельный namespace в MinIO для каждой гостиницы.
    hotel_prefix = (
        "mozart"
        if hotel_name == "Моцарт"
        else "gallery"
    )

    object_name = (
        f"{hotel_prefix}/"
        f"{relative_path.replace(chr(92), '/')}"
    )

    existed = object_exists(object_name)

    minio_client.put_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_name,
        data=BytesIO(processed.data),
        length=processed.size,
        content_type=processed.content_type,
    )

    print(
        f"[MINIO {'UPDATE' if existed else 'UPLOAD'}] "
        f"{object_name}"
    )

    return (
        object_name,
        processed.content_type,
        processed.size,
        processed.width,
        processed.height,
    )


async def get_item(
    db: AsyncSession,
    item_slug: str,
    hotel_name: str,
) -> Item:
    result = await db.execute(
        select(Item).where(
            Item.slug == item_slug,
            Item.hotel_name == hotel_name,
        )
    )

    item = result.scalar_one_or_none()

    if item is None:
        raise RuntimeError(
            f"Item '{item_slug}' not found for hotel '{hotel_name}'. "
            "Run seed.py before minio_seed.py."
        )

    return item


async def ensure_image_record(
    db: AsyncSession,
    item: Item,
    object_name: str,
    original_filename: str,
    content_type: str,
    size: int,
    width: int,
    height: int,
    sort_order: int,
    is_primary: bool,
) -> None:
    result = await db.execute(
        select(ItemImage).where(ItemImage.object_name == object_name)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        existing.item_id = item.id
        existing.original_filename = original_filename
        existing.content_type = content_type
        existing.size = size
        existing.width = width
        existing.height = height
        existing.sort_order = sort_order
        existing.is_primary = is_primary
        existing.content_version = (existing.content_version or 0) + 1

        print(f"[DB UPDATE] {object_name}")
        return

    image = ItemImage(
        item_id=item.id,
        object_name=object_name,
        original_filename=original_filename,
        content_type=content_type,
        size=size,
        width=width,
        height=height,
        sort_order=sort_order,
        is_primary=is_primary,
    )
    db.add(image)
    print(f"[DB LINK] {item.slug} -> {object_name}")


async def seed_media(db: AsyncSession) -> None:
    manifests = load_manifests()

    for media_dir, item_data in manifests:
        hotel_name = item_data.get("hotel_name", "Галерея")

        item = await get_item(
            db,
            item_data["item_slug"],
            hotel_name,
        )

        for image_data in item_data["images"]:
            relative_path = image_data["file"]

            (
                object_name,
                content_type,
                size,
                width,
                height,
            ) = ensure_minio_object(
                media_dir,
                relative_path,
                hotel_name,
            )

            file_path = media_dir / relative_path

            await ensure_image_record(
                db=db,
                item=item,
                object_name=object_name,
                original_filename=file_path.name,
                content_type=content_type,
                size=size,
                width=width,
                height=height,
                sort_order=image_data.get("sort_order", 0),
                is_primary=image_data.get("is_primary", False),
            )

        # Коммитим каждый предмет отдельно.
        # Ошибка в Mozart больше не откатит уже обработанную Gallery.
        await db.commit()


async def main() -> None:
    print("Starting media seed...")
    ensure_bucket()
    async with SessionLocal() as db:
        await seed_media(db)
    print("Media seed completed.")


if __name__ == "__main__":
    asyncio.run(main())

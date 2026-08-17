from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError


ALLOWED_IMAGE_TYPES = {
    "image/jpeg": {
        "format": "JPEG",
        "extension": ".jpg",
    },
    "image/png": {
        "format": "PNG",
        "extension": ".png",
    },
    "image/webp": {
        "format": "WEBP",
        "extension": ".webp",
    },
}


class InvalidImageError(ValueError):
    pass


class ImageTooLargeError(ValueError):
    pass


@dataclass(frozen=True)
class ProcessedImage:
    data: bytes
    content_type: str
    extension: str
    width: int
    height: int

    @property
    def size(self) -> int:
        return len(self.data)


def _has_expected_signature(
    data: bytes,
    content_type: str,
) -> bool:
    if content_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")

    if content_type == "image/png":
        return data.startswith(
            b"\x89PNG\r\n\x1a\n"
        )

    if content_type == "image/webp":
        return (
            len(data) >= 12
            and data[:4] == b"RIFF"
            and data[8:12] == b"WEBP"
        )

    return False


def process_image(
    data: bytes,
    declared_content_type: str,
    max_pixels: int,
) -> ProcessedImage:
    image_config = ALLOWED_IMAGE_TYPES.get(
        declared_content_type
    )

    if image_config is None:
        raise InvalidImageError(
            "Unsupported image type"
        )

    if not _has_expected_signature(
        data,
        declared_content_type,
    ):
        raise InvalidImageError(
            "Image signature does not match content type"
        )

    expected_format = image_config["format"]

    try:
        with Image.open(
            BytesIO(data),
            formats=[expected_format],
        ) as image:
            if image.format != expected_format:
                raise InvalidImageError(
                    "Image format does not match content type"
                )

            if getattr(image, "n_frames", 1) != 1:
                raise InvalidImageError(
                    "Animated images are not allowed"
                )

            width, height = image.size

            if width <= 0 or height <= 0:
                raise InvalidImageError(
                    "Invalid image dimensions"
                )

            if width * height > max_pixels:
                raise ImageTooLargeError(
                    "Image resolution is too large"
                )

            # Полностью декодируем изображение.
            image.load()

            # Применяем ориентацию камеры до удаления EXIF.
            normalized = ImageOps.exif_transpose(image)

            output = BytesIO()

            if expected_format == "JPEG":
                normalized = normalized.convert("RGB")

                normalized.save(
                    output,
                    format="JPEG",
                    quality=90,
                    optimize=True,
                )

            elif expected_format == "PNG":
                if "A" in normalized.getbands():
                    normalized = normalized.convert("RGBA")
                else:
                    normalized = normalized.convert("RGB")

                normalized.save(
                    output,
                    format="PNG",
                    optimize=True,
                )

            elif expected_format == "WEBP":
                if "A" in normalized.getbands():
                    normalized = normalized.convert("RGBA")
                else:
                    normalized = normalized.convert("RGB")

                normalized.save(
                    output,
                    format="WEBP",
                    quality=90,
                )

            return ProcessedImage(
                data=output.getvalue(),
                content_type=declared_content_type,
                extension=image_config["extension"],
                width=normalized.width,
                height=normalized.height,
            )

    except ImageTooLargeError:
        raise

    except InvalidImageError:
        raise

    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        ValueError,
    ) as exc:
        raise InvalidImageError(
            "Invalid or corrupted image"
        ) from exc
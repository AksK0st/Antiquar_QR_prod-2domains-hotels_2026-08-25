from io import BytesIO

import pytest
from PIL import Image

from services.image_processing import (
    ImageTooLargeError,
    InvalidImageError,
    process_image,
)


def make_jpeg(*, width: int = 10, height: int = 20, orientation: int | None = None) -> bytes:
    image = Image.new("RGB", (width, height), "white")
    exif = Image.Exif()
    exif[0x010E] = "private metadata"
    if orientation is not None:
        exif[274] = orientation
    output = BytesIO()
    image.save(output, format="JPEG", exif=exif)
    return output.getvalue()


def test_jpeg_is_reencoded_without_exif_and_orientation_is_applied() -> None:
    result = process_image(make_jpeg(orientation=6), "image/jpeg", max_pixels=10_000)
    assert result.content_type == "image/jpeg"
    assert (result.width, result.height) == (20, 10)

    with Image.open(BytesIO(result.data)) as processed:
        assert len(processed.getexif()) == 0
        assert processed.size == (20, 10)


def test_signature_must_match_declared_type() -> None:
    with pytest.raises(InvalidImageError):
        process_image(b"not-a-png", "image/png", max_pixels=10_000)


def test_pixel_limit_is_enforced() -> None:
    with pytest.raises(ImageTooLargeError):
        process_image(make_jpeg(width=20, height=20), "image/jpeg", max_pixels=399)

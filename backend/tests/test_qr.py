from uuid import UUID

from PIL import Image, ImageDraw, ImageFont

from services.qr import build_item_public_url, generate_item_qr_png, wrap_text


def test_qr_target_uses_immutable_public_id() -> None:
    public_id = UUID("12345678-1234-5678-1234-567812345678")
    assert build_item_public_url(base_url="https://example.com/", public_id=public_id) == (
        "https://example.com/i/12345678-1234-5678-1234-567812345678"
    )


def test_long_unbroken_word_is_split_to_width() -> None:
    font = ImageFont.load_default()
    draw = ImageDraw.Draw(Image.new("RGB", (1000, 100)))
    lines = wrap_text("x" * 200, font, draw, max_width=40)
    assert len(lines) > 1
    assert all(draw.textbbox((0, 0), line, font=font)[2] <= 40 for line in lines)


def test_qr_renderer_outputs_png() -> None:
    data = generate_item_qr_png(
        public_id="12345678-1234-5678-1234-567812345678",
        name="Очень длинное название экспоната " + "безпробелов" * 10,
        base_url="https://example.com",
    )
    assert data.startswith(b"\x89PNG\r\n\x1a\n")

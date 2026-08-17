from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import UUID

import qrcode
from PIL import Image, ImageDraw, ImageFont


QR_BOX_SIZE = 12
QR_BORDER = 4
TEXT_FONT_SIZE = 26
CARD_SIDE_PADDING = 30
TEXT_TOP_PADDING = 22
TEXT_BOTTOM_PADDING = 26
MAX_TEXT_WIDTH = 520
LINE_SPACING = 8
FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")


def _text_width(text: str, font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _split_long_word(
    word: str,
    font: ImageFont.FreeTypeFont,
    draw: ImageDraw.ImageDraw,
    max_width: int,
) -> list[str]:
    if _text_width(word, font, draw) <= max_width:
        return [word]

    chunks: list[str] = []
    current = ""
    for char in word:
        candidate = current + char
        if current and _text_width(candidate, font, draw) > max_width:
            chunks.append(current)
            current = char
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def wrap_text(
    text: str,
    font: ImageFont.FreeTypeFont,
    draw: ImageDraw.ImageDraw,
    max_width: int,
) -> list[str]:
    raw_words = text.split()
    if not raw_words:
        return []

    words: list[str] = []
    for word in raw_words:
        words.extend(_split_long_word(word, font, draw, max_width))

    lines: list[str] = []
    current_line = words[0]
    for word in words[1:]:
        test_line = f"{current_line} {word}"
        if _text_width(test_line, font, draw) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    return lines


def build_item_public_url(*, base_url: str, public_id: UUID | str) -> str:
    normalized_base_url = base_url.rstrip("/")
    return f"{normalized_base_url}/i/{public_id}"


def generate_item_qr_png(
    *,
    public_id: UUID | str,
    name: str,
    base_url: str,
) -> bytes:
    url = build_item_public_url(base_url=base_url, public_id=public_id)

    if not FONT_PATH.is_file():
        raise RuntimeError(f"QR font not found: {FONT_PATH}")

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=QR_BOX_SIZE,
        border=QR_BORDER,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    font = ImageFont.truetype(str(FONT_PATH), TEXT_FONT_SIZE)
    temp_image = Image.new("RGB", (qr_image.width, 200), "white")
    temp_draw = ImageDraw.Draw(temp_image)
    max_text_width = min(MAX_TEXT_WIDTH, qr_image.width - CARD_SIDE_PADDING * 2)
    lines = wrap_text(name, font, temp_draw, max_text_width)

    line_heights: list[int] = []
    for line in lines:
        bbox = temp_draw.textbbox((0, 0), line, font=font)
        line_heights.append(bbox[3] - bbox[1])

    text_block_height = sum(line_heights) + LINE_SPACING * max(0, len(lines) - 1)
    canvas = Image.new(
        "RGB",
        (
            qr_image.width,
            qr_image.height + TEXT_TOP_PADDING + text_block_height + TEXT_BOTTOM_PADDING,
        ),
        "white",
    )
    canvas.paste(qr_image, (0, 0))
    draw = ImageDraw.Draw(canvas)
    current_y = qr_image.height + TEXT_TOP_PADDING

    for index, line in enumerate(lines):
        text_width = _text_width(line, font, draw)
        draw.text(
            ((canvas.width - text_width) // 2, current_y),
            line,
            font=font,
            fill="black",
        )
        current_y += line_heights[index] + LINE_SPACING

    output = BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    return output.getvalue()

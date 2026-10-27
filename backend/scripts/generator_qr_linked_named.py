
import csv
import re
import math
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ================= НАСТРОЙКИ =================

QR_DIR = Path("qr_codes/mozart")
CSV_FILE = Path("item_names.csv")
OUTPUT_FILE = Path("mozart_qr_strips_named.pdf")

# Размеры в миллиметрах
STRIP_LENGTH = 1000
STRIP_HEIGHT = 40

QR_SIZE = 20
QR_GAP = 20

# Отступы текста
TEXT_GAP = 3
TEXT_PADDING = 5

# Ширина текстового блока: 30 мм
TEXT_BLOCK_WIDTH = QR_SIZE + QR_GAP - 2 * TEXT_PADDING

FONT_SIZE = 8
MIN_FONT_SIZE = 5
MAX_TEXT_LINES = 3

# Шрифт Windows с поддержкой кириллицы
FONT_PATH = Path("C:/Windows/Fonts/arial.ttf")
FONT_NAME = "Arial"

UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-"
    r"[0-9a-f]{4}-"
    r"[0-9a-f]{4}-"
    r"[0-9a-f]{4}-"
    r"[0-9a-f]{12}",
    re.IGNORECASE,
)


# ================= CSV =================

def load_names():
    names = {}

    with CSV_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            public_id = row["public_id"].strip().lower()
            name = row["name"].strip()

            if public_id and name:
                names[public_id] = name

    return names


def get_uuid(filename):
    match = UUID_PATTERN.search(filename)

    if match:
        return match.group(0).lower()

    return None


# ================= ТЕКСТ =================

def split_long_word(word, font_size, max_width):
    """Разбивает слово, если оно шире текстового блока."""

    parts = []
    current = ""

    for char in word:
        candidate = current + char

        if (
            pdfmetrics.stringWidth(
                candidate, FONT_NAME, font_size
            ) <= max_width
        ):
            current = candidate
        else:
            if current:
                parts.append(current)
            current = char

    if current:
        parts.append(current)

    return parts


def wrap_text(text, font_size, max_width):
    """Переносит текст с учётом реальной ширины шрифта."""

    lines = []
    current = ""

    for word in text.split():
        if pdfmetrics.stringWidth(
            word, FONT_NAME, font_size
        ) > max_width:
            parts = split_long_word(
                word, font_size, max_width
            )
        else:
            parts = [word]

        for part in parts:
            candidate = f"{current} {part}".strip()

            if pdfmetrics.stringWidth(
                candidate, FONT_NAME, font_size
            ) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = part

    if current:
        lines.append(current)

    return lines


def fit_text(name, max_width):
    """
    Подбирает размер шрифта, чтобы название
    помещалось максимум в 3 строки.
    """

    font_size = FONT_SIZE

    while font_size >= MIN_FONT_SIZE:
        lines = wrap_text(
            name,
            font_size,
            max_width,
        )

        if len(lines) <= MAX_TEXT_LINES:
            return lines, font_size

        font_size -= 0.5

    # Если название всё равно слишком длинное,
    # обрезаем с многоточием.
    font_size = MIN_FONT_SIZE
    lines = wrap_text(name, font_size, max_width)

    if len(lines) > MAX_TEXT_LINES:
        lines = lines[:MAX_TEXT_LINES]

        last = lines[-1]
        ellipsis = "..."

        while (
            last and
            pdfmetrics.stringWidth(
                last + ellipsis,
                FONT_NAME,
                font_size,
            ) > max_width
        ):
            last = last[:-1]

        lines[-1] = last.rstrip() + ellipsis

    return lines, font_size


# ================= ОТРИСОВКА =================

def draw_item(pdf, image_path, name, x):
    """Рисует QR и подпись с фиксированным padding."""

    qr_x = x

    # QR находится в верхней части полосы
    qr_y = (STRIP_HEIGHT - QR_SIZE) * mm

    pdf.drawImage(
        str(image_path),
        qr_x,
        qr_y,
        width=QR_SIZE * mm,
        height=QR_SIZE * mm,
        preserveAspectRatio=True,
        mask="auto",
    )

    # Центр QR
    text_center_x = qr_x + QR_SIZE * mm / 2

    # Доступная ширина текста
    max_width = TEXT_BLOCK_WIDTH * mm

    lines, font_size = fit_text(
        name,
        max_width,
    )

    line_height = font_size * 1.25

    # Отступ от QR до первой строки
    text_y = (
        qr_y
        - TEXT_GAP * mm
        - font_size
    )

    pdf.setFont(FONT_NAME, font_size)

    for line in lines:
        pdf.drawCentredString(
            text_center_x,
            text_y,
            line,
        )

        text_y -= line_height


# ================= ГЕНЕРАЦИЯ PDF =================

def main():
    if not QR_DIR.exists():
        raise FileNotFoundError(
            f"Папка QR не найдена: {QR_DIR}"
        )

    if not CSV_FILE.exists():
        raise FileNotFoundError(
            f"CSV не найден: {CSV_FILE}"
        )

    if not FONT_PATH.exists():
        raise FileNotFoundError(
            f"Шрифт не найден: {FONT_PATH}"
        )

    pdfmetrics.registerFont(
        TTFont(FONT_NAME, str(FONT_PATH))
    )

    names = load_names()

    images = sorted(QR_DIR.glob("*.png"))

    if not images:
        raise RuntimeError("QR-коды не найдены")

    items = []

    for image_path in images:
        public_id = get_uuid(image_path.name)

        if not public_id:
            print(f"[SKIP] Нет UUID: {image_path.name}")
            continue

        name = names.get(public_id)

        if not name:
            print(f"[SKIP] Нет названия: {public_id}")
            continue

        items.append((image_path, name))

    if not items:
        raise RuntimeError(
            "Нет QR-кодов с подходящими названиями"
        )

    # Сколько QR помещается на одну полосу
    per_strip = (
        (STRIP_LENGTH + QR_GAP)
        // (QR_SIZE + QR_GAP)
    )

    pdf = canvas.Canvas(
        str(OUTPUT_FILE),
        pagesize=(
            STRIP_LENGTH * mm,
            STRIP_HEIGHT * mm,
        ),
        pageCompression=1,
    )

    pdf.setTitle("Mozart QR Codes")

    for index, (image_path, name) in enumerate(items):
        position = index % per_strip

        if index > 0 and position == 0:
            pdf.showPage()

        x = position * (QR_SIZE + QR_GAP) * mm

        draw_item(
            pdf,
            image_path,
            name,
            x,
        )

        print(
            f"[OK] {index + 1}/{len(items)}: {name}"
        )

    pdf.save()

    total_strips = math.ceil(
        len(items) / per_strip
    )

    print("\nГотово!")
    print(f"QR-кодов: {len(items)}")
    print(f"QR на полосу: {per_strip}")
    print(f"Полос: {total_strips}")
    print(f"Размер полосы: {STRIP_LENGTH}x{STRIP_HEIGHT} мм")
    print(f"PDF: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()

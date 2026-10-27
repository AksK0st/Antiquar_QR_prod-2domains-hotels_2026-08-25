from pathlib import Path
from urllib.parse import urlparse
import math

import qrcode
from PIL import Image

LINKS_FILE = Path("links_moz.txt")
OUTPUT_DIR = Path("qr_codes/mozart")

DPI = 300
SIZE_MM = 20
SIZE_PX = round(SIZE_MM / 25.4 * DPI)


def generate_qr(url: str, output_path: Path):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=1,
        border=4,
    )

    qr.add_data(url)
    qr.make(fit=True)

    modules = qr.get_matrix()
    count = len(modules)

    # Рисуем QR с целыми размерами модулей
    # и центрируем на холсте 20x20 мм
    box_size = SIZE_PX // count

    if box_size < 2:
        raise ValueError(
            f"QR слишком плотный для 20 мм: {url}"
        )

    actual_size = count * box_size
    offset = (SIZE_PX - actual_size) // 2

    image = Image.new(
        "RGB",
        (SIZE_PX, SIZE_PX),
        "white",
    )

    pixels = image.load()

    for y, row in enumerate(modules):
        for x, is_black in enumerate(row):
            if is_black:
                for dy in range(box_size):
                    for dx in range(box_size):
                        pixels[
                            offset + x * box_size + dx,
                            offset + y * box_size + dy,
                        ] = (0, 0, 0)

    image.save(output_path, dpi=(DPI, DPI))


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    links = [
        line.strip()
        for line in LINKS_FILE.read_text(
            encoding="utf-8-sig"
        ).splitlines()
        if line.strip()
    ]

    links = list(dict.fromkeys(links))

    print(f"Найдено ссылок: {len(links)}")

    for index, url in enumerate(links, start=1):
        public_id = urlparse(url).path.rstrip("/").split("/")[-1]

        filename = f"{index:03d}_{public_id}.png"
        output_path = OUTPUT_DIR / filename

        generate_qr(url, output_path)

        print(f"[{index}/{len(links)}] {filename}")

    print(f"\nГотово! QR-коды в {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
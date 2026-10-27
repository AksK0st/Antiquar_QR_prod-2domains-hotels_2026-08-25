"""Create 1000 x 20 mm print-ready PDF strips from existing QR PNG files."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from PIL import Image

INPUT_DIR = Path('qr_codes/mozart')
OUTPUT_FILE = Path('mozart_qr_strips.pdf')
STRIP_LENGTH_MM = 1000
QR_MM = 20
GAP_MM = 20
PER_STRIP = (STRIP_LENGTH_MM + GAP_MM) // (QR_MM + GAP_MM)  # 25


def main():
    files = sorted(INPUT_DIR.glob('*.png'))
    if not files:
        raise SystemExit(f'Не найдены PNG в {INPUT_DIR.resolve()}')

    page_width = STRIP_LENGTH_MM * mm
    page_height = QR_MM * mm
    c = canvas.Canvas(str(OUTPUT_FILE), pagesize=(page_width, page_height), pageCompression=1)
    c.setTitle('QR-коды Mozart — метровые полосы 20 мм')

    for start in range(0, len(files), PER_STRIP):
        batch = files[start:start + PER_STRIP]
        occupied = len(batch) * QR_MM + (len(batch) - 1) * GAP_MM
        left_margin = (STRIP_LENGTH_MM - occupied) / 2
        for idx, file in enumerate(batch):
            x = (left_margin + idx * (QR_MM + GAP_MM)) * mm
            with Image.open(file) as im:
                if im.width != im.height:
                    raise ValueError(f'QR должен быть квадратным: {file}')
                c.drawImage(ImageReader(im.convert('RGB')), x, 0, QR_MM * mm, QR_MM * mm)
        c.showPage()
    c.save()
    pages = (len(files) + PER_STRIP - 1) // PER_STRIP
    print(f'Готово: {OUTPUT_FILE.resolve()} | QR: {len(files)} | полос: {pages}')
    print('Печать: масштаб 100%, без Fit to page. Размер страницы: 1000 x 20 мм.')


if __name__ == '__main__':
    main()

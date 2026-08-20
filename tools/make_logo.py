"""
Sinh logo ứng dụng: SVG nguồn → installer/icon.ico (6 cỡ) + PNG xem trước.

Ý đồ thiết kế
─────────────
Logo cũ là hình vuông bo góc kèm chữ "MTB" — ở 16px chữ nhòe hết và bóng
ngoài đọc ra cái hộp đồ nghề. Bản mới lấy đúng chủ đề của phần mềm: **mặt cắt
ngang dầm hộp**.

- Bóng ngoài là hình thang có cánh hẫng — nhận ra được ngay ở 16px, không cần chữ.
- Hai cánh hẫng tô xanh sáng (tông TEDI), thân hộp tô xanh đậm (accent app):
  hai tông tạo chiều sâu và nối với nhận diện TEDI mà không chép logo TEDI.
- Lỗ rỗng để trống → tạo tương phản trong/ngoài, ở cỡ lớn thấy rõ là dầm hộp.
- Hai ký hiệu gối dưới đáy: chi tiết chỉ hiện ở cỡ ≥32px, đúng quy ước bản vẽ
  và trùng với cách chương trình vẽ mặt cắt.

    python tools/make_logo.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BLUE_DEEP = '#17538B'    # thân hộp — accent app đậm hơn một nấc
BLUE_MID = '#1B5E9E'     # accent app
BLUE_TEDI = '#1B8FE0'    # cánh hẫng — tông TEDI
RED_TEDI = '#EE1C2E'     # dấu tim dầm
SUPPORT = '#0E3A63'
VOID = '#EDF4FB'      # lỗ rỗng: xanh rất nhạt thay vì trắng tinh

# Toạ độ trên khung 256. Hình thang dầm hộp: bản mặt rộng, vách xiên vào,
# bản đáy hẹp — tỉ lệ lấy theo mặt cắt S16 thật (B/H ≈ 5.1).
SVG = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <!-- cánh hẫng trái/phải — tông TEDI sáng hơn để tạo chiều sâu -->
  <path d="M6 74 L60 74 L60 116 L6 96 Z" fill="{BLUE_TEDI}"/>
  <path d="M250 74 L196 74 L196 116 L250 96 Z" fill="{BLUE_TEDI}"/>
  <!-- thân hộp: bản mặt + vách xiên + bản đáy -->
  <path d="M52 74 L204 74 L204 96 L186 202 L70 202 L52 96 Z" fill="{BLUE_MID}"/>
  <!-- lỗ rỗng vát góc trên: chính chỗ vát LÀ vút, không cần chồng tam giác lên -->
  <path d="M78 126 L100 104 L156 104 L178 126 L166 178 L90 178 Z" fill="{VOID}"/>
  <!-- trục tim X=0 trong lỗ rỗng, đúng cách chương trình vẽ mặt cắt -->
  <rect x="126.6" y="122" width="2.8" height="42" rx="1.4" fill="{RED_TEDI}"/>
  <!-- gối: cố định (đặc) + di động (rỗng), tì sát bản đáy -->
  <path d="M100 202 L112 222 L88 222 Z" fill="{SUPPORT}"/>
  <path d="M156 202 L168 222 L144 222 Z" fill="none" stroke="{SUPPORT}" stroke-width="7"/>
  <rect x="84" y="227" width="88" height="7" rx="3.5" fill="{SUPPORT}"/>
</svg>'''

# Ở 16–20px mọi chi tiết bên trong đều nát, nên dùng bản rút gọn:
# chỉ giữ bóng ngoài + lỗ rỗng, nét dày hơn, bỏ gối và trục tim.
SVG_SMALL = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <path d="M6 62 L250 62 L250 100 L196 120 L186 212 L70 212 L60 120 L6 100 Z"
        fill="{BLUE_MID}"/>
  <path d="M6 62 L60 62 L60 120 L6 100 Z" fill="{BLUE_TEDI}"/>
  <path d="M250 62 L196 62 L196 120 L250 100 Z" fill="{BLUE_TEDI}"/>
  <path d="M84 122 L104 108 L152 108 L172 122 L162 176 L94 176 Z" fill="{VOID}"/>
</svg>'''

SIZES = [(16, SVG_SMALL), (20, SVG_SMALL), (32, SVG),
         (48, SVG), (64, SVG), (128, SVG), (256, SVG)]


def render(svg: str, px: int):
    """SVG → PIL.Image RGBA, dùng Qt để rasterise (đã có sẵn PyQt6)."""
    from PyQt6.QtCore import QByteArray, Qt
    from PyQt6.QtGui import QImage, QPainter
    from PyQt6.QtSvg import QSvgRenderer
    from PIL import Image

    img = QImage(px, px, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode())).render(p)
    p.end()

    buf = img.constBits().asstring(px * px * 4)
    return Image.frombytes('RGBA', (px, px), buf, 'raw', 'BGRA')


def main():
    from PyQt6.QtWidgets import QApplication
    # Phải GIỮ tham chiếu: QApplication không còn ai trỏ tới thì Python thu
    # hồi và Qt sập giữa chừng. Tên bắt đầu bằng gạch dưới để công cụ soi mã
    # không đòi xoá.
    _app = QApplication.instance() or QApplication(sys.argv)

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_ico = os.path.join(base, 'installer', 'icon.ico')
    out_svg = os.path.join(base, 'gui', 'assets', 'app_logo.svg')
    os.makedirs(os.path.dirname(out_svg), exist_ok=True)

    with open(out_svg, 'w', encoding='utf-8') as f:
        f.write(SVG)

    imgs = [(px, render(svg, px)) for px, svg in SIZES]
    imgs[-1][1].save(out_ico, format='ICO',
                     sizes=[(px, px) for px, _ in imgs],
                     append_images=[im for _, im in imgs[:-1]])

    # ảnh xem trước: các cỡ xếp cạnh nhau trên nền sáng và nền tối
    from PIL import Image
    small = [i for i in imgs if i[0] <= 128]
    W = 16 + sum(px + 16 for px, _ in small)
    strip = Image.new('RGBA', (W + 280, 300), (240, 242, 245, 255))
    x = 16
    for px, im in small:
        strip.paste(im, (x, 16 + (128 - px) // 2), im)
        x += px + 16
    dark = Image.new('RGBA', (W, 150), (30, 35, 42, 255))
    x = 16
    for px, im in small:
        dark.paste(im, (x, 12 + (128 - px) // 2), im)
        x += px + 16
    strip.paste(dark, (0, 150), dark)
    big = imgs[-1][1].resize((256, 256), Image.LANCZOS)
    strip.paste(big, (W + 12, 22), big)
    prev = os.path.join(base, 'gui', 'assets', 'app_logo_preview.png')
    strip.save(prev)

    print(f'ICO     : {out_ico}  ({os.path.getsize(out_ico)} bytes, '
          f'{len(imgs)} cỡ: {", ".join(str(p) for p, _ in imgs)})')
    print(f'SVG     : {out_svg}')
    print(f'Xem thử : {prev}')


if __name__ == '__main__':
    main()

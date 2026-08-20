"""
Đóng gói tài nguyên hình ảnh thành `gui/assets.py` (base64 nhúng thẳng).

Nhúng vào .py thay vì để file rời vì hai lý do:
  • PyInstaller không phải khai báo thêm `datas` — asset chắc chắn đi theo bản build.
  • Không có đường dẫn tương đối nào để hỏng khi chạy từ thư mục khác.

Nguồn:
  docs/logo_TEDI/LOGOTEDI-2.gif  → nền trắng bị bỏ, tách làm 2 phần:
      TEDI_MARK  — chỉ vòng tròn + tam giác (dùng ở cỡ nhỏ trên toolbar)
      TEDI_FULL  — cả dấu hiệu + chữ TEDI (dùng ở hộp thoại Giới thiệu)
  gui/assets/app_logo.svg        → APP_LOGO_SVG

    python tools/make_assets.py
"""

import base64
import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_GIF = os.path.join(BASE, 'docs', 'logo_TEDI', 'LOGOTEDI-2.gif')
SRC_SVG = os.path.join(BASE, 'gui', 'assets', 'app_logo.svg')
OUT_PY = os.path.join(BASE, 'gui', 'assets.py')

MARK_BOTTOM = 1240      # ranh giới dấu hiệu / chữ (khoảng trống y=1237..1371)


def to_rgba_trimmed(im, box=None):
    """Bỏ nền trắng → alpha, rồi cắt sát nội dung."""
    from PIL import Image
    import numpy as np

    if box:
        im = im.crop(box)
    a = np.array(im.convert('RGBA')).astype(np.int16)
    rgb = a[:, :, :3]
    # Trắng → trong suốt. Dùng MIN của 3 kênh làm thước đo "độ trắng":
    # chỉ pixel có cả ba kênh đều cao mới là nền. Nếu dùng max thì đỏ thuần
    # (255,0,0) cũng bị coi là trắng và biến mất.
    white = rgb.min(axis=2)
    alpha = np.clip((255 - white) * 255 // 60, 0, 255)   # rìa chuyển mượt
    alpha = np.where(white < 200, 255, alpha)
    a[:, :, 3] = alpha
    out = Image.fromarray(a.astype('uint8'), 'RGBA')
    return out.crop(out.getbbox())


def png_b64(im, height):
    from PIL import Image
    w = max(1, round(im.width * height / im.height))
    im = im.resize((w, height), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format='PNG', optimize=True)
    return base64.b64encode(buf.getvalue()).decode('ascii'), im.size


def wrap(name, b64, width=96):
    lines = [b64[i:i + width] for i in range(0, len(b64), width)]
    body = '\n'.join(f"    '{l}'" for l in lines)
    return f'{name} = (\n{body}\n)\n'


def main():
    from PIL import Image

    src = Image.open(SRC_GIF)
    mark = to_rgba_trimmed(src, (0, 0, src.width, MARK_BOTTOM))
    full = to_rgba_trimmed(src)

    b_mark, s_mark = png_b64(mark, 128)
    b_full, s_full = png_b64(full, 220)

    with open(SRC_SVG, encoding='utf-8') as f:
        svg = f.read().strip()

    with open(OUT_PY, 'w', encoding='utf-8') as f:
        f.write('"""\n')
        f.write('Tài nguyên hình ảnh nhúng sẵn — SINH TỰ ĐỘNG, ĐỪNG SỬA TAY.\n\n')
        f.write('Sinh lại bằng:  python tools/make_assets.py\n')
        f.write('Nguồn: docs/logo_TEDI/LOGOTEDI-2.gif, gui/assets/app_logo.svg\n')
        f.write('"""\n\n')
        f.write('import base64\n\n')
        f.write('from PyQt6.QtCore import QByteArray, Qt\n')
        f.write('from PyQt6.QtGui import QIcon, QPixmap\n\n')
        f.write('# ── Logo ứng dụng: mặt cắt ngang dầm hộp ──\n')
        f.write(f'APP_LOGO_SVG = """{svg}"""\n\n')
        f.write(f'# ── Dấu hiệu TEDI ({s_mark[0]}×{s_mark[1]}, nền trong suốt) ──\n')
        f.write(wrap('_TEDI_MARK_B64', b_mark))
        f.write(f'\n# ── Logo TEDI đầy đủ ({s_full[0]}×{s_full[1]}) ──\n')
        f.write(wrap('_TEDI_FULL_B64', b_full))
        f.write('''

def _pix(b64: str, height: int = 0) -> QPixmap:
    pm = QPixmap()
    pm.loadFromData(QByteArray(base64.b64decode(b64)), 'PNG')
    if height and pm.height() != height:
        pm = pm.scaledToHeight(height, Qt.TransformationMode.SmoothTransformation)
    return pm


def tedi_mark(height: int = 20) -> QPixmap:
    """Dấu hiệu TEDI (vòng tròn + tam giác) — dùng ở cỡ nhỏ trên toolbar."""
    return _pix(_TEDI_MARK_B64, height)


def tedi_full(height: int = 110) -> QPixmap:
    """Logo TEDI đầy đủ kèm chữ — dùng ở hộp thoại Giới thiệu."""
    return _pix(_TEDI_FULL_B64, height)


def app_icon() -> QIcon:
    """Icon ứng dụng, dựng từ SVG nhúng cho đủ mọi cỡ."""
    from PyQt6.QtGui import QImage, QPainter
    try:
        from PyQt6.QtSvg import QSvgRenderer
    except ImportError:
        return QIcon()
    ic = QIcon()
    r = QSvgRenderer(QByteArray(APP_LOGO_SVG.encode()))
    for px in (16, 20, 24, 32, 48, 64, 128, 256):
        img = QImage(px, px, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r.render(p)
        p.end()
        ic.addPixmap(QPixmap.fromImage(img))
    return ic
''')

    print(f'Dấu hiệu TEDI : {s_mark[0]}×{s_mark[1]}  ({len(b_mark) * 3 // 4} bytes PNG)')
    print(f'Logo đầy đủ   : {s_full[0]}×{s_full[1]}  ({len(b_full) * 3 // 4} bytes PNG)')
    print(f'Xuất ra       : {OUT_PY}  ({os.path.getsize(OUT_PY)} bytes)')


if __name__ == '__main__':
    main()

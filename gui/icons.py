"""
Bộ icon dạng SVG nội tuyến, tô màu theo token.

Không phụ thuộc file ảnh ngoài nên PyInstaller không cần bundle thêm gì.
Nếu môi trường thiếu PyQt6.QtSvg thì trả về QIcon rỗng — nút vẫn hiện chữ.
"""

from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QIcon, QPixmap, QPainter

from .theme import LIGHT

try:
    from PyQt6.QtSvg import QSvgRenderer
    _HAS_SVG = True
except ImportError:                                  # pragma: no cover
    _HAS_SVG = False

# path data 16×16, nét vẽ (stroke), không tô nền
_P = {
    'new':      'M9 1.5H4A1.5 1.5 0 0 0 2.5 3v10A1.5 1.5 0 0 0 4 14.5h8'
                'a1.5 1.5 0 0 0 1.5-1.5V6z M9 1.5V6h4.5',
    'open':     'M1.5 4.5A1.5 1.5 0 0 1 3 3h3l1.5 2H13a1.5 1.5 0 0 1 1.5 1.5v6'
                'A1.5 1.5 0 0 1 13 14H3a1.5 1.5 0 0 1-1.5-1.5z',
    'save':     'M2.5 2.5h8L13.5 5.5v8a1 1 0 0 1-1 1h-9a1 1 0 0 1-1-1v-10'
                'a1 1 0 0 1 1-1z M5 2.5v4h5v-4 M5 14.5v-4h6v4',
    'add':      'M8 3.5v9 M3.5 8h9',
    'generate': 'M3 8h3.4l1.6-3.2 2 6.4L11.6 8H13',
    'template': 'M2.5 2.5h11v11h-11z M2.5 6.5h11 M6.5 2.5v11',
    'load':     'M8 2.5v7 M5 6.8l3 3 3-3 M2.5 13h11',
    'check':    'M3 8.4l3.6 3.6L13 4.6',
    'excel':    'M2.5 2.5h11v11h-11z M2.5 6.5h11 M6.5 6.5v7',
    'folder':   'M1.5 4.5A1.5 1.5 0 0 1 3 3h3l1.5 2H13a1.5 1.5 0 0 1 1.5 1.5v6'
                'A1.5 1.5 0 0 1 13 14H3a1.5 1.5 0 0 1-1.5-1.5z',
    'clear':    'M4 4l8 8 M12 4l-8 8',
    'info':     'M8 1.8a6.2 6.2 0 1 0 0 12.4A6.2 6.2 0 0 0 8 1.8z M8 7.2v4 M8 4.9v.1',
    'fit':      'M2 5.5v-3h3 M14 5.5v-3h-3 M2 10.5v3h3 M14 10.5v3h-3',
}

_cache = {}


def icon(name: str, tone: str = 'ink', size: int = 18, theme: dict = None) -> QIcon:
    """QIcon từ tên trong bảng trên.

    Args:
        name: khóa trong _P
        tone: token màu ('ink', 'accent', 'ok', 'err'…)
        size: cạnh pixmap (px)
    """
    t = theme or LIGHT
    key = (name, tone, size)
    if key in _cache:
        return _cache[key]

    ic = QIcon()
    path = _P.get(name)
    if _HAS_SVG and path:
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" '
            f'width="{size}" height="{size}">'
            f'<path d="{path}" fill="none" stroke="{t.get(tone, t["ink"])}" '
            f'stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round"/>'
            f'</svg>'
        )
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        QSvgRenderer(QByteArray(svg.encode())).render(p)
        p.end()
        ic = QIcon(pm)

    _cache[key] = ic
    return ic


def available() -> bool:
    """True nếu vẽ được icon (có QtSvg)."""
    return _HAS_SVG

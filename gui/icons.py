"""
Bộ icon dạng SVG nội tuyến, tô màu theo token.

Không phụ thuộc file ảnh ngoài nên PyInstaller không cần bundle thêm gì.
Nếu môi trường thiếu PyQt6.QtSvg thì trả về QIcon rỗng — nút vẫn hiện chữ.
"""

import os

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
    # bánh răng: vòng trong + 8 răng, vẽ bằng nét nên hợp tông với bộ còn lại
    'gear':     'M8 5.9a2.1 2.1 0 1 0 0 4.2 2.1 2.1 0 0 0 0-4.2z'
                ' M8 1.9v1.6 M8 12.5v1.6 M1.9 8h1.6 M12.5 8h1.6'
                ' M3.7 3.7l1.1 1.1 M11.2 11.2l1.1 1.1'
                ' M12.3 3.7l-1.1 1.1 M4.8 11.2l-1.1 1.1',
}

_cache = {}
_arrow_cache = {}


def icon(name: str, tone: str = 'ink', size: int = 18, theme: dict = None) -> QIcon:
    """QIcon từ tên trong bảng trên.

    Args:
        name: khóa trong _P
        tone: token màu ('ink', 'accent', 'ok', 'err'…)
        size: cạnh pixmap (px)
    """
    t = theme or LIGHT
    # Khóa cache phải gồm màu THẬT đang dùng: thiếu nó thì đổi theme xong icon
    # vẫn lấy bản cũ trong cache và nằm chình ình màu mực đen trên nền than.
    key = (name, tone, size, t.get(tone, t['ink']))
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


def spin_arrows(theme: dict = None):
    """Hai file PNG mũi tên của ô xoay — trả về ``(url_lên, url_xuống)``.

    Đây là ngoại lệ duy nhất của nguyên tắc "không file ảnh ngoài", và có lý do:
    khi QSS đã đặt ``border``/``background`` lên ``QSpinBox`` thì Qt thôi nhờ
    style vẽ mũi tên, mà ``QSpinBox::up-arrow`` **chỉ** nhận ``image: url(...)``
    — không nhận SVG nội tuyến, không nhận QIcon, và mẹo tam giác bằng viền
    trong suốt của CSS thì Qt vẽ ra ô vuông. Không có ảnh thì ô xoay còn trơ hai
    vạch ngang, đúng như đã thấy ở mọi ô nhập số của bản v1.3.1.

    Ảnh ghi vào thư mục tạm, tên theo mã màu nên mỗi bảng màu chỉ ghi một lần.
    Chưa có ``QGuiApplication`` (lúc chạy test QSS) thì trả ``(None, None)``,
    phần QSS mũi tên được bỏ qua chứ không nổ.
    """
    t = theme or LIGHT
    col = t.get('ink_2', '#667085')
    if col in _arrow_cache:
        return _arrow_cache[col]

    from PyQt6.QtGui import QGuiApplication
    if QGuiApplication.instance() is None:
        return None, None

    from PyQt6.QtCore import QStandardPaths, QPointF
    from PyQt6.QtGui import QColor, QPolygonF
    root = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.TempLocation)
    folder = os.path.join(root or '.', 'MidasTransverseBoxgirder', 'qss')
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:                                   # pragma: no cover
        return None, None

    out = []
    tag = col.lstrip('#')
    for up in (True, False):
        path = os.path.join(folder, f'spin-{"up" if up else "down"}-{tag}.png')
        if not os.path.exists(path):
            pm = QPixmap(14, 14)
            pm.fill(Qt.GlobalColor.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setBrush(QColor(col))
            p.setPen(Qt.PenStyle.NoPen)
            pts = ([QPointF(3, 8.5), QPointF(11, 8.5), QPointF(7, 4.5)] if up
                   else [QPointF(3, 5.5), QPointF(11, 5.5), QPointF(7, 9.5)])
            p.drawPolygon(QPolygonF(pts))
            p.end()
            if not pm.save(path):                     # pragma: no cover
                return None, None
        out.append(path.replace('\\', '/'))

    _arrow_cache[col] = (out[0], out[1])
    return _arrow_cache[col]


# Ký hiệu gối — dùng chung cho nút bấm và chú giải, vẽ giống hệt trên canvas
# nên nút bấm chính là hình mà người dùng sẽ thấy trong mô hình.
# Ý tưởng lấy từ Fast Restraints của SAP2000: 4 nút icon thay cho danh sách chữ.
_SUPPORT_SVG = {
    'pin': ('<path d="M12 5 L19 17 L5 17 Z" fill="{c}"/>'
            '<path d="M3 17 H21" stroke="{c}" stroke-width="1.6"/>'
            '<path d="M5 17 l-2 3 M9 17 l-2 3 M13 17 l-2 3 M17 17 l-2 3 M21 17 l-2 3"'
            ' stroke="{c}" stroke-width="1.3"/>'),
    'roller': ('<path d="M12 4 L18.5 14 L5.5 14 Z" fill="none" stroke="{c}"'
               ' stroke-width="1.6"/>'
               '<circle cx="8.6" cy="16.6" r="2.4" fill="none" stroke="{c}"'
               ' stroke-width="1.4"/>'
               '<circle cx="15.4" cy="16.6" r="2.4" fill="none" stroke="{c}"'
               ' stroke-width="1.4"/>'
               '<path d="M3 20 H21" stroke="{c}" stroke-width="1.6"/>'),
    'fixed': ('<rect x="4" y="5" width="16" height="7" fill="{c}"/>'
              '<path d="M2 12 H22" stroke="{c}" stroke-width="1.6"/>'
              '<path d="M4 12 l-2 3 M8 12 l-2 3 M12 12 l-2 3 M16 12 l-2 3'
              ' M20 12 l-2 3 M24 12 l-2 3" stroke="{c}" stroke-width="1.3"/>'),
    'none': ('<circle cx="12" cy="12" r="7" fill="none" stroke="{c}"'
             ' stroke-width="1.5" stroke-dasharray="3 2"/>'),
}
SUPPORT_NAME = {'pin': 'Gối cố định', 'roller': 'Gối di động',
                'fixed': 'Ngàm', 'none': 'Bỏ gối'}
SUPPORT_CODE = {'pin': '111000', 'roller': '011000', 'fixed': '111111'}


def support_icon(kind: str, tone: str = 'ink', size: int = 24,
                 theme: dict = None) -> QIcon:
    """Icon ký hiệu gối, vẽ giống hệt trên canvas."""
    t = theme or LIGHT
    key = ('sup:' + kind, tone, size, t.get(tone, t['ink']))
    if key in _cache:
        return _cache[key]
    ic = QIcon()
    body = _SUPPORT_SVG.get(kind)
    if _HAS_SVG and body:
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
               f'width="{size}" height="{size}">'
               + body.format(c=t.get(tone, t['ink'])) + '</svg>')
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        pr = QPainter(pm)
        pr.setRenderHint(QPainter.RenderHint.Antialiasing)
        QSvgRenderer(QByteArray(svg.encode())).render(pr)
        pr.end()
        ic = QIcon(pm)
    _cache[key] = ic
    return ic


def available() -> bool:
    """True nếu vẽ được icon (có QtSvg)."""
    return _HAS_SVG

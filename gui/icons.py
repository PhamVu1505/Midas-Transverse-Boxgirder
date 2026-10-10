"""
Huy hiệu mức độ cho cửa sổ Messages — ảnh vẽ tay, tô theo token.

Đây là thứ duy nhất còn lại của bộ icon SVG cũ: từ 2026-10-10 nút bấm và mục
menu **không mang icon** (theo caldintav — nút là chữ có động từ đầy đủ). Huy
hiệu ở Messages thì vẫn cần vì đó là thứ người dùng quét mắt tìm trong nhật ký
dài, và ký tự `⚠` phụ thuộc phông hệ thống.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter

from .theme import LIGHT

_cache = {}


def level_image(level: str, theme: dict = None, size: int = 15):
    """Huy hiệu mức độ cho cửa sổ Messages — trả về QImage, None nếu chưa có Qt.

    Vẽ tay chứ không dùng ký tự: `⚠` phụ thuộc phông hệ thống (máy thiếu Segoe
    UI Symbol thì ra ô vuông), mà đây lại đúng là thứ người dùng quét mắt tìm
    khi log dài. Vẽ thì cỡ, màu và độ dày nét đều theo token của bảng màu.

      warn — tam giác vàng, chữ `i` trắng bên trong
      err  — tròn đỏ, dấu `×` trắng
      ok   — dấu kiểm màu xanh lá
      info — vòng tròn mảnh, chữ `i`, màu chữ mờ
    """
    t = theme or LIGHT
    col = {'info': t['ink_3'], 'ok': t['ok'],
           'warn': t['warn'], 'err': t['err']}.get(level, t['ink_3'])
    key = ('lvl', level, size, col)
    if key in _cache:
        return _cache[key]

    from PyQt6.QtGui import QGuiApplication
    if QGuiApplication.instance() is None:
        return None

    from PyQt6.QtCore import QPointF, QRectF
    from PyQt6.QtGui import QColor, QImage, QPen, QPolygonF

    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(col)
    s = float(size)

    if level == 'warn':
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(QPolygonF([QPointF(s / 2, s * 0.06),
                                 QPointF(s * 0.97, s * 0.92),
                                 QPointF(s * 0.03, s * 0.92)]))
        # chữ `i` vẽ bằng hình, không bằng drawText: ở 15px thì phông nào cũng
        # nhoè, mà chấm với thân vẽ tay lúc nào cũng sắc nét.
        p.setBrush(QColor('#FFFFFF'))
        p.drawEllipse(QPointF(s / 2, s * 0.38), s * 0.075, s * 0.075)
        p.drawRoundedRect(QRectF(s / 2 - s * 0.07, s * 0.52, s * 0.14, s * 0.26),
                          s * 0.07, s * 0.07)
    elif level == 'err':
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(s * 0.04, s * 0.04, s * 0.92, s * 0.92))
        pen = QPen(QColor('#FFFFFF'))
        pen.setWidthF(max(1.4, s * 0.12))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(s * 0.32, s * 0.32), QPointF(s * 0.68, s * 0.68))
        p.drawLine(QPointF(s * 0.68, s * 0.32), QPointF(s * 0.32, s * 0.68))
    elif level == 'ok':
        pen = QPen(c)
        pen.setWidthF(max(1.6, s * 0.14))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolyline(QPolygonF([QPointF(s * 0.18, s * 0.52),
                                  QPointF(s * 0.42, s * 0.76),
                                  QPointF(s * 0.84, s * 0.24)]))
    else:
        pen = QPen(c)
        pen.setWidthF(max(1.1, s * 0.09))
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(s * 0.09, s * 0.09, s * 0.82, s * 0.82))
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(s / 2, s * 0.31), s * 0.068, s * 0.068)
        p.drawRoundedRect(QRectF(s / 2 - s * 0.065, s * 0.44, s * 0.13, s * 0.27),
                          s * 0.065, s * 0.065)
    p.end()

    _cache[key] = img
    return img


# Ký hiệu gối — dùng chung cho nút bấm và chú giải, vẽ giống hệt trên canvas
# nên nút bấm chính là hình mà người dùng sẽ thấy trong mô hình.
# Ý tưởng lấy từ Fast Restraints của SAP2000: 4 nút icon thay cho danh sách chữ.

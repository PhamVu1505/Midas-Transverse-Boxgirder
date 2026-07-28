"""
Biểu đồ **bao** mômen và lực cắt của khung ngang, vẽ thẳng lên hình khung.

Vì sao cần: bảng tám (hoặc mười tám) điểm chỉ cho biết giá trị cực trị tại
những chỗ đã chọn sẵn. Nhìn biểu đồ mới thấy được **hình dạng** nội lực — chỗ
đổi dấu, chỗ vút, chỗ nào lẽ ra phải trơn mà lại gãy khúc (dấu hiệu chia lưới
hoặc gán tải sai). Đây cũng là hình quen thuộc trong hồ sơ.

Giá trị lấy từ **bao tổ hợp** `str_all` (Cường độ) và `ser_all` (Sử dụng): mỗi
đầu phần tử giữ min và max, vẽ cả hai đường bao.

Quy ước dấu: bảng Beam Force của Midas đã cho My **liên tục qua nút** — kiểm
trên số liệu thật của S1, `My` ở đầu J của phần tử n bằng đúng `My` ở đầu I của
phần tử n+1 — nên vẽ thẳng giá trị đọc được, không phải đổi dấu đầu nào.
Tung độ dựng theo **pháp tuyến** của từng phần tử, mômen dương vẽ về một phía
cố định để đường bao liền mạch khi đi vòng quanh khung.
"""

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (QPainter, QPen, QBrush, QColor, QPolygonF,
                         QPainterPath, QFont)
from PyQt6.QtWidgets import QWidget

from .pan_zoom import PanZoom
from .theme import LIGHT

# (khoá hiển thị, nhãn, trường, nhóm tổ hợp, đơn vị)
QUANTITIES = [
    ('My_str', 'Mômen bao — Cường độ', 'My', 'str', 'kN·m'),
    ('Vz_str', 'Lực cắt bao — Cường độ', 'Vz', 'str', 'kN'),
    ('My_ser', 'Mômen bao — Sử dụng', 'My', 'ser', 'kN·m'),
    ('Vz_ser', 'Lực cắt bao — Sử dụng', 'Vz', 'ser', 'kN'),
]
QUANTITY_LABELS = [q[1] for q in QUANTITIES]


def build_envelope(results: list) -> dict:
    """{elem: {'I'|'J': {'str_My': (min, max), 'str_Vz': …, 'ser_…'}}}.

    Chỉ lấy hai tổ hợp bao `str_all` và `ser_all` — đúng hai chuỗi mà
    `result_reader` vẫn tra để dựng bảng điểm kiểm toán, nên biểu đồ và bảng
    luôn nói cùng một con số.
    """
    env = {}
    for r in results:
        lc = r.get('load') or ''
        if lc.startswith('str_all'):
            grp = 'str'
        elif lc.startswith('ser_all'):
            grp = 'ser'
        else:
            continue
        d = env.setdefault(r['elem'], {}).setdefault(r['end'], {})
        for f in ('My', 'Vz'):
            v = r.get(f)
            if v is None:
                continue
            k = f'{grp}_{f}'
            lo, hi = d.get(k, (v, v))
            d[k] = (min(lo, v), max(hi, v))
    return env


class ForceDiagram(PanZoom, QWidget):
    """Khung khung ngang + hai đường bao nội lực, zoom/pan như thẻ Model."""

    # Lề rộng và tung độ nhỏ: biểu đồ vẽ RA NGOÀI khung nên phải chừa chỗ, nếu
    # không đường bao lớn nhất tràn khỏi ô ngay ở tỉ lệ vừa khung.
    MARGIN = 46
    ORD_FRAC = 0.13      # tung độ lớn nhất = 13% cạnh dài của khung

    def __init__(self, theme=None):
        QWidget.__init__(self)
        self.t = theme or LIGHT
        self.setMinimumSize(240, 170)
        self._nodes = {}      # {id: (x, z)}
        self._elems = []      # [(eid, n1, n2)]
        self._env = {}
        self._quantity = QUANTITIES[0][0]
        self._name = ''
        self._init_pan_zoom(
            'Lăn chuột để phóng to/thu nhỏ · kéo để di chuyển · '
            'bấm đúp hoặc phím F để vừa khung')

    def has_content(self):
        return bool(self._nodes and self._elems)

    def apply_theme(self, theme: dict):
        self.t = theme
        self.update()

    def set_quantity(self, key_or_label: str):
        for k, lb, _f, _g, _u in QUANTITIES:
            if key_or_label in (k, lb):
                self._quantity = k
                self.update()
                return

    def set_data(self, name, nodes: dict, elems: list, env: dict):
        self._name = name or ''
        self._nodes = {int(k): tuple(v) for k, v in (nodes or {}).items()}
        self._elems = list(elems or [])
        self._env = env or {}
        self.fit()

    # ── quy đổi toạ độ ──
    def _base_mapper(self):
        xs = [p[0] for p in self._nodes.values()]
        zs = [p[1] for p in self._nodes.values()]
        x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
        m = self.MARGIN
        cw = max(self.width() - 2 * m, 1)
        ch = max(self.height() - 2 * m, 1)
        s = min(cw / max(x1 - x0, 1e-9), ch / max(z1 - z0, 1e-9))
        ox = m + (cw - (x1 - x0) * s) / 2
        oz = m + (ch - (z1 - z0) * s) / 2

        def fn(x, z):
            return QPointF(ox + (x - x0) * s, oz + (z1 - z) * s)
        return fn, s, max(x1 - x0, z1 - z0)

    def _spec(self):
        for k, lb, f, g, u in QUANTITIES:
            if k == self._quantity:
                return f, g, u, lb
        return 'My', 'str', 'kN·m', ''

    def _values(self, eid, end, field, grp):
        d = (self._env.get(eid) or {}).get(end) or {}
        v = d.get(f'{grp}_{field}')
        if v is None:
            return None
        return (float(v[0]), float(v[1]))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.t
        p.fillRect(self.rect(), QColor(t['panel']))
        if not self.has_content():
            p.setPen(QPen(QColor(t['ink_3'])))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       'Chưa có nội lực — bấm “Xử lý tất cả”')
            p.end()
            return

        base, _s, span = self._base_mapper()
        def fn(x, z):
            return self.map_point(base(x, z))

        field, grp, unit, label = self._spec()

        # Biên độ lớn nhất trong TOÀN bộ khung, để hai biểu đồ cùng một tỉ lệ
        peak = 0.0
        for eid, n1, n2 in self._elems:
            for end in ('I', 'J'):
                v = self._values(eid, end, field, grp)
                if v:
                    peak = max(peak, abs(v[0]), abs(v[1]))
        # Tung độ quy về pixel: tính trên hình đã phóng nên biểu đồ phóng theo
        px_span = span * _s * self._zoom
        k = (self.ORD_FRAC * px_span / peak) if peak > 1e-9 else 0.0

        if k <= 0:
            p.setPen(QPen(QColor(t['dia_edge']), 1.4))
            for eid, n1, n2 in self._elems:
                if n1 in self._nodes and n2 in self._nodes:
                    p.drawLine(fn(*self._nodes[n1]), fn(*self._nodes[n2]))
            self._caption(p, f'{label} — không có số liệu')
            p.end()
            return

        for which, col_key, alpha in (('max', 'part_top', 38),
                                      ('min', 'part_bot', 38)):
            path = QPainterPath()
            col = QColor(t[col_key])
            for eid, n1, n2 in self._elems:
                if n1 not in self._nodes or n2 not in self._nodes:
                    continue
                vi = self._values(eid, 'I', field, grp)
                vj = self._values(eid, 'J', field, grp)
                if vi is None or vj is None:
                    continue
                a, b = self._nodes[n1], self._nodes[n2]
                pa, pb = fn(*a), fn(*b)
                dx, dy = pb.x() - pa.x(), pb.y() - pa.y()
                L = (dx * dx + dy * dy) ** 0.5
                if L < 1e-9:
                    continue
                nx, ny = -dy / L, dx / L       # pháp tuyến trái của phần tử
                i = vi[1] if which == 'max' else vi[0]
                j = vj[1] if which == 'max' else vj[0]
                qa = QPointF(pa.x() + nx * i * k, pa.y() + ny * i * k)
                qb = QPointF(pb.x() + nx * j * k, pb.y() + ny * j * k)
                poly = QPolygonF([pa, qa, qb, pb])
                path.addPolygon(poly)

            p.setPen(Qt.PenStyle.NoPen)
            fill = QColor(col)
            fill.setAlpha(alpha)
            p.setBrush(QBrush(fill))
            p.drawPath(path)
            pen = QPen(col, 1.6)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            # Chỉ vẽ viền phía ngoài của mỗi dải: vẽ cả path thì hai cạnh dựng
            # đứng ở mỗi phần tử thành một hàng rào răng lược.
            for eid, n1, n2 in self._elems:
                if n1 not in self._nodes or n2 not in self._nodes:
                    continue
                vi = self._values(eid, 'I', field, grp)
                vj = self._values(eid, 'J', field, grp)
                if vi is None or vj is None:
                    continue
                a, b = self._nodes[n1], self._nodes[n2]
                pa, pb = fn(*a), fn(*b)
                dx, dy = pb.x() - pa.x(), pb.y() - pa.y()
                L = (dx * dx + dy * dy) ** 0.5
                if L < 1e-9:
                    continue
                nx, ny = -dy / L, dx / L
                i = vi[1] if which == 'max' else vi[0]
                j = vj[1] if which == 'max' else vj[0]
                p.drawLine(QPointF(pa.x() + nx * i * k, pa.y() + ny * i * k),
                           QPointF(pb.x() + nx * j * k, pb.y() + ny * j * k))

        # Khung vẽ SAU CÙNG, đè lên hai dải bao — vẽ trước thì nó chìm dưới
        # phần tô và không còn nhìn ra hình mặt cắt để định vị.
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(t['dia_edge']), 1.6))
        for eid, n1, n2 in self._elems:
            if n1 in self._nodes and n2 in self._nodes:
                p.drawLine(fn(*self._nodes[n1]), fn(*self._nodes[n2]))

        self._caption(p, f'{label} · lớn nhất {peak:,.1f} {unit}'
                      .replace(',', ' '))
        p.end()

    def _caption(self, p, text):
        t = self.t
        f = QFont(self.font())
        f.setPointSizeF(max(7.0, f.pointSizeF() - 1))
        p.setFont(f)
        # Nền mờ dưới chữ: biểu đồ có thể chạy tới sát mép dưới, chữ đè lên
        # đường bao là không đọc được.
        bg = QColor(t['panel'])
        bg.setAlpha(215)
        p.fillRect(QRectF(0, self.height() - 22, self.width(), 22), bg)
        p.setPen(QPen(QColor(t['ink_2'])))
        p.drawText(QRectF(8, self.height() - 20, self.width() - 16, 16),
                   int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                   text)
        # chú giải hai đường bao
        p.setPen(QPen(QColor(t['part_top'])))
        p.drawText(QRectF(8, 4, self.width() - 16, 16),
                   int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                   'đường bao (max)')
        p.setPen(QPen(QColor(t['part_bot'])))
        p.drawText(QRectF(8, 18, self.width() - 16, 16),
                   int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                   'đường bao (min)')

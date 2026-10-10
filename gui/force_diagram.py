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
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics
from PyQt6.QtWidgets import QWidget

from .pan_zoom import PanZoom
from .theme import LIGHT, ui_font

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

    # Bước kẻ của kiểu tô "Line fill" (pixel). Midas mặc định kiểu này chứ
    # không phải tô đặc — nét kẻ cho thấy tung độ biến thiên thế nào dọc phần
    # tử, còn mảng màu đặc thì chỉ thấy đường bao.
    HATCH_STEP = 7.0

    def _segments(self, fn, field, grp, which, k):
        """[(pa, pb, qa, qb, vi, vj)] — trục phần tử và cạnh ngoài của biểu đồ."""
        out = []
        for eid, n1, n2 in self._elems:
            if n1 not in self._nodes or n2 not in self._nodes:
                continue
            vi = self._values(eid, 'I', field, grp)
            vj = self._values(eid, 'J', field, grp)
            if vi is None or vj is None:
                continue
            pa, pb = fn(*self._nodes[n1]), fn(*self._nodes[n2])
            dx, dy = pb.x() - pa.x(), pb.y() - pa.y()
            L = (dx * dx + dy * dy) ** 0.5
            if L < 1e-9:
                continue
            nx, ny = -dy / L, dx / L          # pháp tuyến trái của phần tử
            i = vi[1] if which == 'max' else vi[0]
            j = vj[1] if which == 'max' else vj[0]
            out.append((pa, pb,
                        QPointF(pa.x() + nx * i * k, pa.y() + ny * i * k),
                        QPointF(pb.x() + nx * j * k, pb.y() + ny * j * k),
                        i, j))
        return out

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

        # Biên độ lớn nhất trong TOÀN khung để hai đường bao cùng một tỉ lệ
        peak = 0.0
        for eid, n1, n2 in self._elems:
            for end in ('I', 'J'):
                v = self._values(eid, end, field, grp)
                if v:
                    peak = max(peak, abs(v[0]), abs(v[1]))
        px_span = span * _s * self._zoom
        k = (self.ORD_FRAC * px_span / peak) if peak > 1e-9 else 0.0

        # Trục khung: nét mảnh, vẽ TRƯỚC để biểu đồ nằm đè lên — đây là đường
        # chuẩn số 0 của biểu đồ, không phải hình trang trí.
        p.setPen(QPen(QColor(t['ink_3']), 1.0))
        for eid, n1, n2 in self._elems:
            if n1 in self._nodes and n2 in self._nodes:
                p.drawLine(fn(*self._nodes[n1]), fn(*self._nodes[n2]))

        if k <= 0:
            self._legend(p, label, unit, None, None)
            p.end()
            return

        hi = lo = None
        for which, col_key in (('max', 'part_top'), ('min', 'part_bot')):
            col = QColor(t[col_key])
            hatch = QColor(col)
            hatch.setAlpha(115)
            segs = self._segments(fn, field, grp, which, k)

            # 1. nét kẻ tô (Line fill kiểu Midas)
            p.setPen(QPen(hatch, 0.9))
            for pa, pb, qa, qb, _vi, _vj in segs:
                L = max(abs(pb.x() - pa.x()), abs(pb.y() - pa.y()))
                n = max(1, int(L / self.HATCH_STEP))
                for m in range(n + 1):
                    u = m / n
                    p.drawLine(
                        QPointF(pa.x() + (pb.x() - pa.x()) * u,
                                pa.y() + (pb.y() - pa.y()) * u),
                        QPointF(qa.x() + (qb.x() - qa.x()) * u,
                                qa.y() + (qb.y() - qa.y()) * u))

            # 2. đường bao ngoài
            p.setPen(QPen(col, 1.7))
            for _pa, _pb, qa, qb, _vi, _vj in segs:
                p.drawLine(qa, qb)

            # 3. nhãn giá trị cực trị — Midas gọi là "Abs Max": một con số duy
            #    nhất tại đúng chỗ nó xảy ra, không rải số khắp biểu đồ.
            best = None
            for _pa, _pb, qa, qb, vi, vj in segs:
                for q, v in ((qa, vi), (qb, vj)):
                    if best is None or abs(v) > abs(best[1]):
                        best = (q, v)
            if best and abs(best[1]) > 1e-9:
                self._value_label(p, best[0], best[1], col)
                if which == 'max':
                    hi = best[1]
                else:
                    lo = best[1]

        self._legend(p, label, unit, hi, lo)
        p.end()

    def _value_label(self, p, pt, value, col):
        """Số cực trị đặt cạnh đường bao, có nền để không lẫn vào nét kẻ."""
        f = ui_font(-1)          # chú giải trên hình vẽ: nhỏ 1 pt, không đậm
        p.setFont(f)
        txt = f'{value:,.1f}'.replace(',', ' ')
        w = QFontMetrics(f).horizontalAdvance(txt) + 8
        h = QFontMetrics(f).height() + 2
        x = min(max(pt.x() - w / 2, 2), self.width() - w - 2)
        y = min(max(pt.y() - h - 3, 2), self.height() - h - 2)
        bg = QColor(self.t['panel'])
        bg.setAlpha(225)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(bg))
        p.drawRect(QRectF(x, y, w, h))
        p.setPen(QPen(col))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawText(QRectF(x, y, w, h), int(Qt.AlignmentFlag.AlignCenter), txt)

    def _legend(self, p, label, unit, hi, lo):
        """Hộp chú giải góc trên trái, theo lối bảng Legend của Midas."""
        t = self.t
        f = ui_font(-1)          # dòng đầu (tên biểu đồ) đậm = tiêu đề hộp
        p.setFont(f)
        fm = QFontMetrics(f)
        rows = [(None, label), (None, f'Đơn vị: {unit}')]
        if hi is None and lo is None:
            rows.append((None, 'không có số liệu'))
        else:
            rows.append((t['part_top'],
                         f'Max  {hi:,.1f}'.replace(',', ' ') if hi is not None
                         else 'Max  —'))
            rows.append((t['part_bot'],
                         f'Min  {lo:,.1f}'.replace(',', ' ') if lo is not None
                         else 'Min  —'))
        # Bề rộng đo trên hàng ĐẦU ở kiểu đậm: hàng tiêu đề in đậm nên rộng hơn
        # số đo thường, tính theo kiểu thường thì tên biểu đồ bị cắt mất đuôi.
        fb = QFont(f)
        fb.setBold(True)
        w = max(max(fm.horizontalAdvance(s) for _c, s in rows),
                QFontMetrics(fb).horizontalAdvance(rows[0][1])) + 24
        h = len(rows) * (fm.height() + 1) + 10

        p.setPen(QPen(QColor(t['border'])))
        bg = QColor(t['panel'])
        bg.setAlpha(232)
        p.setBrush(QBrush(bg))
        p.drawRect(QRectF(6, 6, w, h))
        p.setBrush(Qt.BrushStyle.NoBrush)
        y = 11
        for i, (col, s) in enumerate(rows):
            f.setBold(i == 0)
            p.setFont(f)
            p.setPen(QPen(QColor(col or (t['ink'] if i == 0 else t['ink_2']))))
            p.drawText(QRectF(14, y, w - 16, fm.height()),
                       int(Qt.AlignmentFlag.AlignLeft
                           | Qt.AlignmentFlag.AlignVCenter), s)
            if col:
                p.fillRect(QRectF(10, y + fm.height() / 2 - 1.5, 0, 0), QColor(col))
                p.setPen(QPen(QColor(col), 2.4))
                p.drawLine(QPointF(9, y + fm.height() / 2),
                           QPointF(12, y + fm.height() / 2))
            y += fm.height() + 1

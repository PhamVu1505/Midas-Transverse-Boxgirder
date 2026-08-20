"""
Khung xem mặt cắt — thay cho QSvgWidget tĩnh.

Vẽ thẳng từ `topo.json`, tức là **đúng mô hình đã ghi ra MCT**, không phải hình
minh họa dựng lại. Có zoom/pan/fit, bật tắt lớp, truy vấn node khi rê chuột.

Ba chế độ xem:
  Model         — mọi phần tử một màu; hình dạng và cách chia phần tử là chính.
  Section shape — mỗi phần tử vẽ thành dải vuốt côn theo chiều dày hai đầu, đúng
                  quy ước offset của Midas (CT/CB/CC). Chồng lên biên bê tông
                  thật nên lệch chỗ nào lộ ra ngay — đây là chế độ để kiểm tra
                  mặt cắt Midas sắp dựng có giống hình học thật không.
  Parts         — tô theo bộ phận, dùng khi nghi frame builder gán sai.

Màu mã hóa **giá trị**, không mã hóa bộ phận: kiểu tô cầu vồng theo bộ phận chỉ
nói lại điều mà nhìn hình đã biết.
"""

import json
import math

from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import (QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
                         QPolygonF, QFontMetrics)
from PyQt6.QtWidgets import QWidget, QSizePolicy

from .theme import LIGHT, FONT_MONO

MODEL, SHAPE, PARTS = 'model', 'shape', 'parts'

# Quy ước offset mặt cắt của Midas
OFFSET = {'top': 'CT', 'bot': 'CB',
          'web_left': 'CC', 'web_center': 'CC', 'web_right': 'CC'}
PART_LABEL = {'top': 'Bản mặt', 'bot': 'Bản đáy', 'web_left': 'Bụng trái',
              'web_center': 'Vách giữa', 'web_right': 'Bụng phải'}
# Bộ phận → token màu trong bảng theme (không phải mã màu cứng: bản Tối cần
# sắc sáng hơn hẳn, xem gui/theme.py).
PART_TOKEN = {'top': 'part_top', 'bot': 'part_bot', 'web_left': 'part_web',
              'web_center': 'part_wc', 'web_right': 'part_web'}

DEFAULT_LAYERS = {
    'concrete': True, 'elements': True, 'nodes': True, 'supports': True,
    'pt': True, 'dims': True, 'grid': True, 'ids': False, 'eids': False,
}


class FrameView(QWidget):
    """Khung xem mặt cắt: zoom/pan/fit, lớp, truy vấn động."""

    node_hovered = pyqtSignal(int, dict)   # id, thông tin (id=-1 khi rời chuột)
    node_clicked = pyqtSignal(int)
    supports_changed = pyqtSignal(list)    # [{'x','kind'}] sau khi người dùng sửa

    def __init__(self, theme: dict = None, parent=None):
        super().__init__(parent)
        self.t = theme or LIGHT
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(280, 220)

        self.m = None                     # mô hình đang vẽ
        self.mode = MODEL
        self.layers = dict(DEFAULT_LAYERS)
        # Gối lưu theo TOẠ ĐỘ X (khớp với src/project.py), lúc vẽ mới quy về
        # node đáy gần nhất — đổi lưới thì gối vẫn nằm đúng chỗ.
        self.supports = []                # [{'x': float, 'kind': str}]
        self.edit_supports = False
        self._drag_sup = -1
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self._base = 1.0
        self._fitted = False
        self._hover = None
        self._sel = None
        self._drag = None

    # ─────────────────────────────────────────
    # Nạp dữ liệu
    # ─────────────────────────────────────────
    def load_topo(self, path: str) -> bool:
        """Nạp topo.json. Trả False nếu thiếu file hoặc thiếu khối geometry."""
        try:
            with open(path, encoding='utf-8') as f:
                topo = json.load(f)
        except Exception:
            self.clear()
            return False
        return self.set_topo(topo)

    def set_topo(self, topo: dict) -> bool:
        g = topo.get('geometry')
        if not g:
            self.clear()
            return False

        nodes, order = {}, []
        for pre, part in (('top', 'top'), ('bot', 'bot'), ('wL', 'web_left'),
                          ('wC', 'web_center'), ('wR', 'web_right')):
            ids, nds = topo.get(pre + '_ids'), topo.get(pre + '_nodes')
            if not ids or not nds:
                continue
            for i, n in zip(ids, nds):
                nodes[int(i)] = {'x': n['x'], 'z': n['z'], 't': n['thickness'],
                                 'kp': bool(n['is_keypoint']), 'part': part}
                order.append(int(i))
        order.sort()

        # Section THẬT của từng phần tử: (sid, type, offset, d_i, d_j, w).
        # Phải dùng cái này thay vì suy offset từ bộ phận của node — phần tử nối
        # (connector) mang offset CC và chiều dày của BỤNG, trong khi node đầu
        # của nó lại thuộc bản mặt (CT). Suy sai thì dải vẽ lệch hẳn chỗ giao.
        secmap = {int(sec[0]): sec for sec in topo.get('sections', [])
                  if len(sec) >= 5}
        elems = []
        for e in topo.get('elements', []):
            if len(e) < 3:
                continue
            sec = secmap.get(int(e[3])) if len(e) >= 4 else None
            elems.append({
                'id': int(e[0]), 'a': int(e[1]), 'b': int(e[2]),
                'offset': sec[2] if sec else None,
                'di': float(sec[3]) if sec else None,
                'dj': float(sec[4]) if sec else None,
            })
        ts = [nodes[i]['t'] for i in order if nodes[i]['t'] > 0.005]
        xs = [p[0] for p in g['outpoly']]

        self.m = {
            'nodes': nodes, 'order': order, 'elems': elems,
            'out': g['outpoly'], 'inn': g.get('inpolys', []),
            'H': g['H'], 'type': g.get('section_type', 'single'),
            'bot_ids': [int(i) for i in topo.get('bot_ids', [])],
            # Bản xem trước dựng thẳng từ DXF (src/preview.py): có hình học và
            # cáp nhưng chưa có node/phần tử. Mọi lớp vẽ đều chịu được danh sách
            # rỗng, chỉ cần nói rõ cho người dùng biết đây chưa phải mô hình MCT.
            'preview': bool(topo.get('preview')),
            # path_mct do writer xuất sẵn theo toạ độ MCT TOÀN CỤC; profile_points
            # là element-local, mỗi vị trí cáp một quy ước — không vẽ thẳng được
            'tendons': [{'name': t.get('name', ''),
                         'pts': [[float(a), float(b)] for a, b in t.get('path_mct', [])]}
                        for t in topo.get('tendons', [])],
            'tmin': min(ts) if ts else 0.0, 'tmax': max(ts) if ts else 1.0,
            'x0': min(xs), 'x1': max(xs),
        }
        self.m['B'] = self.m['x1'] - self.m['x0']
        # Gối lấy từ topo — đó là bộ ĐÃ GHI vào MCT, kể cả khi người dùng chưa
        # đặt gì (writer dùng bộ mặc định). Nhờ vậy khung xem luôn khớp với file.
        self.supports = [{'x': float(sp['x']), 'kind': sp.get('kind', 'roller')}
                         for sp in topo.get('supports', [])]
        self._fitted = False
        self._hover = self._sel = None
        self.update()
        return True

    def clear(self):
        self.m = None
        self._hover = self._sel = None
        self.update()

    def set_supports(self, supports):
        self.supports = [{'x': float(s['x']), 'kind': s.get('kind', 'roller')}
                         for s in (supports or [])]
        self.update()

    def set_edit_supports(self, on: bool):
        self.edit_supports = bool(on)
        self._drag_sup = -1
        self.setCursor(Qt.CursorShape.PointingHandCursor if on
                       else Qt.CursorShape.CrossCursor)
        self.update()

    def _bot_by_x(self, x):
        """Node đáy gần nhất theo X."""
        if not self.m or not self.m['bot_ids']:
            return None
        return min(self.m['bot_ids'],
                   key=lambda i: abs(self.m['nodes'][i]['x'] - x))

    def _sup_node(self, sp):
        return self._bot_by_x(sp['x'])

    def _emit_supports(self):
        self.supports.sort(key=lambda s: s['x'])
        self.supports_changed.emit([dict(s) for s in self.supports])

    def part_color(self, part: str) -> str:
        """Màu của một bộ phận theo theme đang dùng."""
        return self.t.get(PART_TOKEN.get(part, ''), self.t['ink'])

    def apply_theme(self, theme: dict):
        self.t = theme
        self.update()

    def set_mode(self, mode):
        self.mode = mode
        self.update()

    def set_layer(self, name, on):
        self.layers[name] = bool(on)
        self.update()

    def stats(self) -> dict:
        if not self.m:
            return {}
        return {'nodes': len(self.m['order']), 'elems': len(self.m['elems']),
                'H': self.m['H'], 'B': self.m['B'], 'type': self.m['type'],
                'tmin': self.m['tmin'], 'tmax': self.m['tmax']}

    # ─────────────────────────────────────────
    # Toạ độ
    # ─────────────────────────────────────────
    # Lề tính bằng PIXEL: đường kích thước H nằm bên trái, đường B và ký hiệu
    # gối nằm dưới đáy — chúng vẽ ngoài bao hình học nên phải chừa chỗ, nếu
    # không sẽ bị cắt mất khi vừa khung.
    MARGIN = (64, 24, 20, 74)     # trái, trên, phải, dưới

    def fit(self):
        if not self.m:
            return
        ml, mt, mr, mb = self.MARGIN
        aw = max(40, self.width() - ml - mr)
        ah = max(40, self.height() - mt - mb)
        w, h = self.m['B'] + 0.8, self.m['H'] + 0.5
        self._base = min(aw / w, ah / h) if w and h else 1.0
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self._fitted = True
        self.update()

    @property
    def _s(self):
        return self._base * self._zoom

    def _ox(self):
        ml, _, mr, _ = self.MARGIN
        cx = ml + (self.width() - ml - mr) / 2
        return cx - (self.m['x0'] + self.m['x1']) / 2 * self._s + self._pan.x()

    def _oy(self):
        _, mt, _, mb = self.MARGIN
        cy = mt + (self.height() - mt - mb) / 2
        return cy + self.m['H'] / 2 * self._s + self._pan.y()

    def TX(self, x):
        return self._ox() + x * self._s

    def TZ(self, z):
        return self._oy() - z * self._s

    def invX(self, px):
        return (px - self._ox()) / self._s

    def invZ(self, py):
        return (self._oy() - py) / self._s

    def zoom_by(self, f):
        self._zoom = max(0.3, min(12.0, self._zoom * f))
        self.update()

    # ─────────────────────────────────────────
    # Vẽ
    # ─────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(self.t['panel']))

        if not self.m:
            p.setPen(QPen(QColor(self.t['ink_3'])))
            f = QFont(); f.setPointSize(9); p.setFont(f)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       'Chưa có mô hình — thêm DXF (kéo thả được) rồi chọn ở cây mặt cắt')
            return

        if not self._fitted:
            self.fit()
        m, L = self.m, self.layers
        shape = self.mode == SHAPE

        if L['grid']:
            self._draw_grid(p)
        if L['concrete']:
            self._draw_concrete(p, shape)
        if L['dims']:
            self._draw_dims(p)
        if L['elements']:
            self._draw_shape(p) if shape else self._draw_elements(p)
        if L['pt']:
            self._draw_pt(p)
        if L['nodes']:
            self._draw_nodes(p)
        if L['ids']:
            self._draw_node_ids(p)
        if L['eids']:
            self._draw_elem_ids(p)
        if L['supports']:
            self._draw_supports(p)
        if self.edit_supports:
            self._draw_bot_hints(p)
        self._draw_marks(p)
        if m['preview']:
            self._draw_preview_banner(p)
        p.end()

    def _draw_preview_banner(self, p):
        """Nhắc rõ: đang xem hình DXF, chưa phải mô hình đã ghi ra MCT."""
        txt = 'XEM TRƯỚC TỪ DXF — chưa chia phần tử, chưa tạo MCT'
        f = QFont(); f.setPointSize(8); f.setBold(True)
        p.setFont(f)
        w = QFontMetrics(f).horizontalAdvance(txt) + 18
        ml, mt, _, _ = self.MARGIN
        r = QRectF(ml, mt, w, 21)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(self.t['warn'])))
        p.setOpacity(0.14)
        p.drawRoundedRect(r, 3, 3)
        p.setOpacity(1.0)
        p.setPen(QPen(QColor(self.t['warn'])))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, txt)

    def _draw_bot_hints(self, p):
        pen = QPen(QColor(self.t['accent']), 1)
        pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setOpacity(0.55)
        for i in self.m['bot_ids']:
            n = self.m['nodes'].get(i)
            if n:
                p.drawEllipse(QPointF(self.TX(n['x']), self.TZ(n['z'])), 6, 6)
        p.setOpacity(1.0)

    def _draw_grid(self, p):
        s = self._s
        step = 5 if s < 22 else (2 if s < 55 else 1)
        p.setPen(QPen(QColor(self.t['border_soft']), 1))
        x = math.ceil(self.invX(0) / step) * step
        while self.TX(x) < self.width():
            p.drawLine(QPointF(self.TX(x), 0), QPointF(self.TX(x), self.height()))
            x += step
        z = math.ceil(self.invZ(self.height()) / step) * step
        while self.TZ(z) > 0:
            p.drawLine(QPointF(0, self.TZ(z)), QPointF(self.width(), self.TZ(z)))
            z += step
        pen = QPen(QColor(self.t['border']), 1)
        pen.setStyle(Qt.PenStyle.DashDotLine)
        p.setPen(pen)
        p.drawLine(QPointF(self.TX(0), 0), QPointF(self.TX(0), self.height()))

    def _poly(self, pts):
        return QPolygonF([QPointF(self.TX(a), self.TZ(b)) for a, b in pts])

    def _draw_concrete(self, p, ghost):
        m = self.m
        path = QPainterPath()
        path.setFillRule(Qt.FillRule.OddEvenFill)
        path.addPolygon(self._poly(m['out']))
        path.closeSubpath()
        for ip in m['inn']:
            path.addPolygon(self._poly(ip))
            path.closeSubpath()
        p.fillPath(path, QBrush(QColor(self.t['panel_alt'] if ghost
                                       else self.t['sunken'])))
        pen = QPen(QColor(self.t['ink_3']), 1.0 if ghost else 1.3)
        if ghost:
            pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(self._poly(m['out']))
        for ip in m['inn']:
            p.drawPolygon(self._poly(ip))

    def _tag(self, p, txt, x, y):
        f = QFont(FONT_MONO.split(',')[0].strip()); f.setPointSize(8)
        p.setFont(f)
        w = QFontMetrics(f).horizontalAdvance(txt)
        p.fillRect(QRectF(x - w / 2 - 4, y - 15, w + 8, 14), QColor(self.t['panel']))
        p.setPen(QPen(QColor(self.t['ink_2'])))
        p.drawText(QRectF(x - w / 2 - 4, y - 15, w + 8, 14),
                   Qt.AlignmentFlag.AlignCenter, txt)

    def _arrow(self, p, x1, y1, x2, y2):
        a = math.atan2(y2 - y1, x2 - x1)
        L = 5.5
        p.setBrush(QBrush(QColor(self.t['ink_3'])))
        p.drawPolygon(QPolygonF([
            QPointF(x2, y2),
            QPointF(x2 - L * math.cos(a - .42), y2 - L * math.sin(a - .42)),
            QPointF(x2 - L * math.cos(a + .42), y2 - L * math.sin(a + .42))]))

    def _draw_dims(self, p):
        m = self.m
        p.setPen(QPen(QColor(self.t['ink_3']), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        x0, x1, yD = self.TX(m['x0']), self.TX(m['x1']), self.TZ(0) + 44
        p.drawLine(QPointF(x0, self.TZ(0) + 6), QPointF(x0, yD + 6))
        p.drawLine(QPointF(x1, self.TZ(0) + 6), QPointF(x1, yD + 6))
        p.drawLine(QPointF(x0, yD), QPointF(x1, yD))
        self._arrow(p, x0 + 14, yD, x0, yD)
        self._arrow(p, x1 - 14, yD, x1, yD)
        self._tag(p, f'B = {m["B"]:.3f} m', (x0 + x1) / 2, yD)

        xD = x0 - 42
        z0, z1 = self.TZ(0), self.TZ(m['H'])
        p.setPen(QPen(QColor(self.t['ink_3']), 1))
        p.drawLine(QPointF(x0 - 6, z0), QPointF(xD - 6, z0))
        p.drawLine(QPointF(x0 - 6, z1), QPointF(xD - 6, z1))
        p.drawLine(QPointF(xD, z0), QPointF(xD, z1))
        self._arrow(p, xD, z0 - 14, xD, z0)
        self._arrow(p, xD, z1 + 14, xD, z1)
        p.save()
        p.translate(xD - 4, (z0 + z1) / 2)
        p.rotate(-90)
        self._tag(p, f'H = {m["H"]:.3f} m', 0, 0)
        p.restore()

    def _draw_elements(self, p):
        m = self.m
        p.setBrush(Qt.BrushStyle.NoBrush)
        for e in m['elems']:
            A, B = m['nodes'].get(e['a']), m['nodes'].get(e['b'])
            if not A or not B:
                continue
            col = self.part_color(A['part']) if self.mode == PARTS else self.t['ink']
            pen = QPen(QColor(col), 2.4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(QPointF(self.TX(A['x']), self.TZ(A['z'])),
                       QPointF(self.TX(B['x']), self.TZ(B['z'])))

        # vạch cắt tại mỗi node — nhờ đó đếm được số phần tử bằng mắt
        if self._s > 16:
            p.setPen(QPen(QColor(self.t['ink_2']), 1))
            tk = 4.4 / self._s
            for e in m['elems']:
                A, B = m['nodes'].get(e['a']), m['nodes'].get(e['b'])
                if not A or not B:
                    continue
                dx, dz = B['x'] - A['x'], B['z'] - A['z']
                ln = math.hypot(dx, dz)
                if ln < 1e-9:
                    continue
                nx, nz = -dz / ln, dx / ln
                for N in (A, B):
                    p.drawLine(
                        QPointF(self.TX(N['x'] - nx * tk), self.TZ(N['z'] - nz * tk)),
                        QPointF(self.TX(N['x'] + nx * tk), self.TZ(N['z'] + nz * tk)))

    def _ribbon(self, A, B, off=None, ti=None, tj=None):
        """Dải vuốt côn theo offset của SECTION, không suy từ bộ phận của node.

        CT treo xuống · CB nhô lên · CC đối xứng ±t/2.
        """
        dx, dz = B['x'] - A['x'], B['z'] - A['z']
        ln = math.hypot(dx, dz)
        if ln < 1e-9:
            return None
        nx, nz = -dz / ln, dx / ln
        off = off or OFFSET.get(A['part'], 'CC')
        A = dict(A, t=A['t'] if ti is None else ti)
        B = dict(B, t=B['t'] if tj is None else tj)
        if off == 'CT':
            if nz > 0:
                nx, nz = -nx, -nz
            return [(A['x'], A['z']), (B['x'], B['z']),
                    (B['x'] + nx * B['t'], B['z'] + nz * B['t']),
                    (A['x'] + nx * A['t'], A['z'] + nz * A['t'])]
        if off == 'CB':
            if nz < 0:
                nx, nz = -nx, -nz
            return [(A['x'], A['z']), (B['x'], B['z']),
                    (B['x'] + nx * B['t'], B['z'] + nz * B['t']),
                    (A['x'] + nx * A['t'], A['z'] + nz * A['t'])]
        return [(A['x'] + nx * A['t'] / 2, A['z'] + nz * A['t'] / 2),
                (B['x'] + nx * B['t'] / 2, B['z'] + nz * B['t'] / 2),
                (B['x'] - nx * B['t'] / 2, B['z'] - nz * B['t'] / 2),
                (A['x'] - nx * A['t'] / 2, A['z'] - nz * A['t'] / 2)]

    def _draw_shape(self, p):
        """Tô HỢP NHẤT một lần, rồi mới vẽ viền từng phần tử.

        Tô từng dải chồng lên nhau thì alpha cộng dồn, chỗ giao bản–bụng hóa
        đậm sì trông như lỗi — trong khi thật ra các phần tử vốn chồng nhau tại
        nút, đúng như Midas dựng. Hợp nhất cho tông đều; viền vẫn cho thấy ranh
        giới từng phần tử và chỗ chồng lấn.
        """
        m = self.m
        quads = []
        for e in m['elems']:
            A, B = m['nodes'].get(e['a']), m['nodes'].get(e['b'])
            if not A or not B:
                continue
            q = self._ribbon(A, B, e.get('offset'), e.get('di'), e.get('dj'))
            if q:
                quads.append(q)

        union = QPainterPath()
        for q in quads:
            sub = QPainterPath()
            sub.addPolygon(self._poly(q))
            sub.closeSubpath()
            union = union.united(sub)
        fill = QColor(self.t['accent'])
        fill.setAlpha(58)
        p.fillPath(union, QBrush(fill))

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(self.t['accent']), 1))
        for q in quads:
            p.drawPolygon(self._poly(q))

        pen = QPen(QColor(self.t['ink_2']), 1)
        pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        for e in m['elems']:
            A, B = m['nodes'].get(e['a']), m['nodes'].get(e['b'])
            if A and B:
                p.drawLine(QPointF(self.TX(A['x']), self.TZ(A['z'])),
                           QPointF(self.TX(B['x']), self.TZ(B['z'])))

    def _draw_pt(self, p):
        pen = QPen(QColor(self.t['warn']), 2.6)
        pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for t in self.m['tendons']:
            if len(t['pts']) > 1:
                p.drawPolyline(self._poly(t['pts']))

    def _draw_nodes(self, p):
        if self._s <= 12:
            return
        m = self.m
        for i in m['order']:
            n = m['nodes'][i]
            r = 3.4 if n['kp'] else 2.4
            col = QColor(self.t['accent'] if n['kp'] else self.t['panel'])
            p.setBrush(QBrush(col))
            p.setPen(QPen(QColor(self.t['accent'] if n['kp'] else self.t['ink']), 1.2))
            p.drawEllipse(QPointF(self.TX(n['x']), self.TZ(n['z'])), r, r)

    def _draw_node_ids(self, p):
        if self._s <= 24:
            return
        f = QFont(FONT_MONO.split(',')[0].strip()); f.setPointSize(7)
        p.setFont(f)
        p.setPen(QPen(QColor(self.t['ink_2'])))
        m = self.m
        for i in m['order']:
            n = m['nodes'][i]
            if not n['kp'] and self._s < 44:
                continue
            p.drawText(QPointF(self.TX(n['x']) + 4, self.TZ(n['z']) - 4), str(i))

    def _draw_elem_ids(self, p):
        if self._s <= 28:
            return
        # phần tử ngắn hơn ~26px thì số sẽ chồng lên nhau, bỏ qua
        min_len = 26.0
        f = QFont(FONT_MONO.split(',')[0].strip()); f.setPointSize(7)
        p.setFont(f)
        fm = QFontMetrics(f)
        m = self.m
        for e in m['elems']:
            A, B = m['nodes'].get(e['a']), m['nodes'].get(e['b'])
            if not A or not B:
                continue
            ax, ay = self.TX(A['x']), self.TZ(A['z'])
            bx, by = self.TX(B['x']), self.TZ(B['z'])
            if math.hypot(bx - ax, by - ay) < min_len:
                continue
            x, y = (ax + bx) / 2, (ay + by) / 2
            s = str(e['id'])
            w = fm.horizontalAdvance(s)
            p.fillRect(QRectF(x - w / 2 - 2, y - 6, w + 4, 12),
                       QColor(self.t['panel']))
            p.setPen(QPen(QColor(self.t['ink_3'])))
            p.drawText(QRectF(x - w / 2 - 2, y - 6, w + 4, 12),
                       Qt.AlignmentFlag.AlignCenter, s)

    def _draw_supports(self, p):
        m = self.m
        for idx, s in enumerate(self.supports):
            n = m['nodes'].get(self._sup_node(s))
            if not n:
                continue
            X, Y = self.TX(n['x']), self.TZ(n['z'])
            kind = s.get('kind', 'roller')
            col = QColor(self.t['accent'] if (self.edit_supports
                                              and idx == self._drag_sup)
                         else self.t['ink'])
            p.setPen(QPen(col, 1.4))
            tri = QPolygonF([QPointF(X, Y), QPointF(X - 8, Y + 12),
                             QPointF(X + 8, Y + 12)])
            if kind == 'roller':
                # con lăn: tam giác rỗng trên hai bánh lăn
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPolygon(tri)
                p.drawEllipse(QPointF(X - 3.8, Y + 15), 2.8, 2.8)
                p.drawEllipse(QPointF(X + 3.8, Y + 15), 2.8, 2.8)
                p.drawLine(QPointF(X - 10, Y + 18.6), QPointF(X + 10, Y + 18.6))
            elif kind == 'fixed':
                # ngàm: khối đặc kề nền gạch chéo — phải khác hẳn gối cố định
                p.setBrush(QBrush(col))
                p.drawRect(QRectF(X - 9, Y, 18, 7))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawLine(QPointF(X - 12, Y + 7), QPointF(X + 12, Y + 7))
                for i in range(-3, 4):
                    p.drawLine(QPointF(X + i * 3.8, Y + 7),
                               QPointF(X + i * 3.8 - 3.4, Y + 11.6))
            else:
                # gối cố định: tam giác đặc trên nền gạch chéo
                p.setBrush(QBrush(col))
                p.drawPolygon(tri)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawLine(QPointF(X - 11, Y + 12), QPointF(X + 11, Y + 12))
                for i in range(-2, 3):
                    p.drawLine(QPointF(X + i * 4.4, Y + 12),
                               QPointF(X + i * 4.4 - 3.6, Y + 16.6))

    def _draw_marks(self, p):
        m = self.m
        p.setBrush(Qt.BrushStyle.NoBrush)
        for nid, col, r in ((self._hover, self.t['accent'], 7.5),
                            (self._sel, self.t['warn'], 9.5)):
            n = m['nodes'].get(nid) if nid is not None else None
            if n:
                p.setPen(QPen(QColor(col), 1.8))
                p.drawEllipse(QPointF(self.TX(n['x']), self.TZ(n['z'])), r, r)

    # ─────────────────────────────────────────
    # Tương tác
    # ─────────────────────────────────────────
    def _near(self, pos, ids=None):
        if not self.m:
            return None
        best, bd = None, 14.0
        for i in (ids if ids is not None else self.m['order']):
            n = self.m['nodes'].get(i)
            if not n:
                continue
            d = math.hypot(self.TX(n['x']) - pos.x(), self.TZ(n['z']) - pos.y())
            if d < bd:
                bd, best = d, i
        return best

    def resizeEvent(self, e):
        self._fitted = False
        super().resizeEvent(e)

    def wheelEvent(self, e):
        self.zoom_by(1.14 if e.angleDelta().y() > 0 else 1 / 1.14)

    def _sup_at(self, pos):
        """Chỉ số gối mà con trỏ đang chạm (tam giác vẽ PHÍA DƯỚI node)."""
        best, bd = -1, 1e9
        for i, sp in enumerate(self.supports):
            n = self.m['nodes'].get(self._sup_node(sp))
            if not n:
                continue
            X, Y = self.TX(n['x']), self.TZ(n['z'])
            if X - 13 < pos.x() < X + 13 and Y - 4 < pos.y() < Y + 24:
                d = abs(pos.x() - X)
                if d < bd:
                    bd, best = d, i
        return best

    def mousePressEvent(self, e):
        if not self.m:
            return
        if self.edit_supports:
            hit = self._sup_at(e.position())
            if hit >= 0:
                if e.button() == Qt.MouseButton.RightButton:
                    self.supports.pop(hit)
                    self._emit_supports()
                    self.update()
                else:
                    self._drag_sup = hit
                    self.update()
                return
            nid = self._near(e.position(), self.m['bot_ids'])
            if nid is not None and e.button() == Qt.MouseButton.LeftButton:
                x = self.m['nodes'][nid]['x']
                if not any(self._sup_node(sp) == nid for sp in self.supports):
                    self.supports.append({'x': x, 'kind': 'roller'})
                    self._emit_supports()
                    self.update()
                return
            self._drag = (e.position(), QPointF(self._pan))
            return
        hit = self._near(e.position())
        if hit is not None:
            self._sel = hit
            self.node_clicked.emit(hit)
            self.update()
        else:
            self._drag = (e.position(), QPointF(self._pan))
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseReleaseEvent(self, _):
        self._drag = None
        if self._drag_sup >= 0:
            self._drag_sup = -1
            self._emit_supports()
            self.update()
        self.setCursor(Qt.CursorShape.PointingHandCursor if self.edit_supports
                       else Qt.CursorShape.CrossCursor)

    def mouseMoveEvent(self, e):
        if not self.m:
            return
        if self._drag_sup >= 0:
            nid = self._bot_by_x(self.invX(e.position().x()))
            if nid is not None:
                x = self.m['nodes'][nid]['x']
                taken = any(self._sup_node(sp) == nid
                            for k, sp in enumerate(self.supports)
                            if k != self._drag_sup)
                if not taken:
                    self.supports[self._drag_sup]['x'] = x
            self.update()
            return
        if self._drag:
            start, pan0 = self._drag
            self._pan = pan0 + (e.position() - start)
            self.update()
            return
        hit = self._near(e.position())
        if hit != self._hover:
            self._hover = hit
            self.update()
        if hit is None:
            self.node_hovered.emit(-1, {'x': self.invX(e.position().x()),
                                        'z': self.invZ(e.position().y())})
        else:
            n = self.m['nodes'][hit]
            self.node_hovered.emit(hit, {
                'x': n['x'], 'z': n['z'], 't': n['t'], 'kp': n['kp'],
                'part': PART_LABEL.get(n['part'], n['part']),
                'offset': OFFSET.get(n['part'], 'CC'),
                'elems': [e['id'] for e in self.m['elems']
                      if hit in (e['a'], e['b'])],
            })

    def leaveEvent(self, _):
        self._hover = None
        self.node_hovered.emit(-1, {})
        self.update()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_F:
            self.fit()
        elif e.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom_by(1.25)
        elif e.key() == Qt.Key.Key_Minus:
            self.zoom_by(1 / 1.25)
        elif e.key() == Qt.Key.Key_Escape:
            self._sel = None
            self.update()
        else:
            super().keyPressEvent(e)

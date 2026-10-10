"""Results tab - Beam Force XLS to check table + Excel."""

import json
import os

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLineEdit, QLabel, QComboBox, QTableWidget,
                              QTableWidgetItem, QFileDialog,
                              QHeaderView, QSplitter, QListWidget,
                              QAbstractItemView, QMessageBox)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush

from .worker import ResultsWorker
from .widgets import LogView
from .theme import LIGHT
from .pan_zoom import PanZoom
from .force_diagram import ForceDiagram, QUANTITY_LABELS


POINTS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
GROUPS = ['Top slab', '', '', '', 'Bottom slab', '', 'Web', '']

# Bộ phận theo CHỮ CÁI ĐẦU, không theo chỉ số cột: mặt cắt nhiều hộp có thêm
# A1, E2, G3… nên tra theo vị trí trong danh sách là sai ngay từ cột thứ chín.
GROUP_OF = {'A': 'Top slab', 'B': 'Top slab', 'C': 'Top slab', 'D': 'Top slab',
            'E': 'Bottom slab', 'F': 'Bottom slab', 'G': 'Web', 'H': 'Web'}
# Bề rộng cột khi bảng có nhiều hơn số cột vừa khung — lúc đó cho cuộn ngang
# thay vì bóp mỗi cột còn vài chục pixel.
COL_W = 96
MAX_STRETCH_COLS = 9

# Nền nhóm hàng lấy từ token: bảng Tối cần nền tối, nếu giữ pastel sáng thì
# chữ (màu mực sáng của theme) biến mất trên đó.
GROUP_TOKEN = {'Top slab': 'grp_top', 'Bottom slab': 'grp_bot', 'Web': 'grp_web'}


def group_color(group: str, t: dict) -> QColor:
    return QColor(t.get(GROUP_TOKEN.get(group, ''), t['panel']))

DATA_ROWS = [
    ('Depth h (mm)', 'h', '{:.0f}'),
    ('Strength Mu (kN.m)', 'Mu', '{:.2f}'),
    ('  -> nút · phần tử', 'Mu_ref', '{}'),
    ('Strength Vu (kN)', 'Vu', '{:.2f}'),
    ('  -> nút · phần tử', 'Vu_ref', '{}'),
    ('Service Mser (kN.m)', 'Mser', '{:.2f}'),
    ('  -> nút · phần tử', 'Mser_ref', '{}'),
]

# Điểm kiểm toán tô theo bộ phận: A–D bản mặt, E–F bản đáy, G–H bụng. Lấy màu
# bộ phận của theme rồi biến thiên độ sáng cho phân biệt từng điểm trong nhóm.
POINT_TOKEN = {'A': ('part_top', 0), 'B': ('part_top', 1), 'C': ('part_top', 2),
               'D': ('part_top', 3), 'E': ('part_bot', 0), 'F': ('part_bot', 2),
               'G': ('part_web', 0), 'H': ('part_web', 2)}

# Bản Sáng là giao diện mặc định lúc chạy lần đầu nên giữ nguyên mã màu v1.3.0
# thay vì lấy giá trị suy ra — công thức cho ra tông gạch, bản cũ là đỏ tươi.
POINT_LEGACY_LIGHT = {
    'A': '#DC3232', 'B': '#C85050', 'C': '#B43C3C', 'D': '#A02828',
    'E': '#3250C8', 'F': '#4664DC', 'G': '#28A03C', 'H': '#3C8C50',
}


def point_color(pt: str, t: dict) -> QColor:
    if t.get('_id') == 'light':
        return QColor(POINT_LEGACY_LIGHT[pt])
    token, step = POINT_TOKEN.get(pt, ('ink', 0))
    c = QColor(t.get(token, t['ink']))
    return c if not step else c.lighter(100 + step * 12)


class CheckPointDiagram(PanZoom, QWidget):
    """Mặt cắt ngang THẬT (đọc từ topo, tức từ DXF) kèm ký hiệu vết cắt A–H.

    Bản trước vẽ một hình hộp tượng trưng với tỉ lệ cố định — không phản ánh mặt
    cắt đang xem, nên nhìn không biết vút ở đâu, bụng nghiêng bao nhiêu. Nay vẽ
    thẳng từ `topo['geometry']`, cùng nguồn với khung xem của tab Model.

    Ký hiệu vết cắt theo quy ước bản vẽ: đường cắt **nét mảnh vuông góc với cấu
    kiện** bị cắt (bản nằm ngang → cắt đứng; bụng thẳng đứng → cắt ngang), mũi
    tên tam giác đặc **vuông góc với đường cắt** chỉ hướng nhìn, vòng tròn mang
    tên mặt cắt ở đầu đường cắt.
    """

    # Lề phải đủ cho HAI hàng ký hiệu so le: 13 (nhô ra) + 15 (bán kính)
    #                     + 2.3×15 (hàng thứ hai) + 15 = 77 px.
    MARGIN = (58, 88, 58, 88)     # trái, trên, phải, dưới
    R_BUBBLE = 15                 # bán kính vòng tròn tên, pixel
    CUT_OUT = 13                  # đường cắt nhô ra ngoài mặt bê tông, pixel

    def __init__(self, theme=None):
        QWidget.__init__(self)
        self.t = theme or LIGHT
        # Tối thiểu để nhỏ: khung này nằm chung splitter với bảng nội lực, chặn
        # dưới 300 px thì trên màn hình thấp bảng chỉ còn một dòng. Hai hàng ký
        # hiệu so le tự bớt hàng khi lề không đủ (`_symbol_metrics`).
        self.setMinimumSize(240, 170)
        self._geom = None          # {'outpoly', 'inpolys', 'H'}
        self._marks = {}           # {tên: {'x','z','dir'}}
        self._name = ''
        self._init_pan_zoom()

    def has_content(self):
        return bool(self._geom)

    def apply_theme(self, theme: dict):
        self.t = theme
        self.update()

    def set_section(self, name: str, geometry: dict, marks: dict):
        """Nạp hình học và vị trí ký hiệu. geometry=None thì xoá hình."""
        self._name = name or ''
        self._geom = geometry or None
        self._marks = marks or {}
        self.fit()

    R_MIN = 8.0          # nhỏ hơn nữa là không đọc nổi chữ trong vòng tròn

    def _vertical_groups(self):
        """Ký hiệu cắt đứng, tách thành nhóm VẼ PHÍA TRÊN và nhóm VẼ PHÍA DƯỚI.

        Phải tách: ký hiệu bản mặt vẽ lên trên, ký hiệu bản đáy vẽ xuống dưới,
        hai bên không đụng nhau. Gộp chung một danh sách thì A (giữa bản mặt) và
        E (giữa bản đáy) cùng x = 0 → khoảng cách bằng 0 → cả hình bị coi là
        chật cứng và ký hiệu co lại vô cớ.
        """
        zs = [q[1] for q in self._geom['outpoly']]
        zmid = (max(zs) + min(zs)) / 2
        up, down = [], []
        for n, m in self._marks.items():
            if m['dir'] != 'v':
                continue
            (up if m['z'] > zmid else down).append(n)
        key = lambda n: self._marks[n]['x']
        return sorted(up, key=key), sorted(down, key=key)

    def _symbol_metrics(self, s):
        """(bán kính, số hàng so le) để các ký hiệu cắt ĐỨNG không chạm nhau.

        Chật thì **thêm hàng so le trước, thu nhỏ sau**. Mặt cắt hai hộp có tới
        mười hai ký hiệu đứng trên bản mặt; chỉ thu bán kính thì chữ trong vòng
        tròn nhỏ đến mức không đọc được, mà tên điểm chính là thứ duy nhất phải
        đọc được trên hình.
        """
        r0 = float(self.R_BUBBLE)
        best_rows, best_r = 1, r0
        for names in self._vertical_groups():
            xs = sorted(self._marks[n]['x'] for n in names)
            if len(xs) < 2:
                continue

            def gap_for(rows):
                if len(xs) <= rows:
                    return float('inf')
                return min((xs[i + rows] - xs[i]) * s * self._zoom
                           for i in range(len(xs) - rows))

            rows, r = 3, max(self.R_MIN, min(r0, gap_for(3) / 2.15))
            for k in (1, 2, 3):
                if gap_for(k) >= 2.15 * r0:
                    rows, r = k, r0
                    break
            best_rows = max(best_rows, rows)
            best_r = min(best_r, r)
        return best_r, best_rows

    # ── quy đổi toạ độ ──
    def _mapper(self):
        """Trả (fn, scale). fn(x, z) → QPointF pixel, giữ đúng tỉ lệ hình học."""
        g = self._geom
        xs = [p[0] for p in g['outpoly']]
        zs = [p[1] for p in g['outpoly']]
        x0, x1 = min(xs), max(xs)
        z0, z1 = min(zs), max(zs)
        W, H = self.width(), self.height()
        # Lề co theo kích thước: để cứng 88 px thì khi panel thấp (splitter kéo
        # nhỏ) lề ăn hết chỗ và mặt cắt bị bóp còn vài pixel.
        ml = mr = min(self.MARGIN[0], W * 0.14)

        def scale_for(mt):
            cw = max(W - ml - mr, 1)
            ch = max(H - 2 * mt, 1)
            return min(cw / max(x1 - x0, 1e-9), ch / max(z1 - z0, 1e-9)), cw, ch

        # Vòng lặp hai bước: cỡ ký hiệu quyết định lề trên, lề trên lại quyết
        # định tỉ lệ vẽ, mà tỉ lệ vẽ lại quyết định các ký hiệu có chật hay
        # không. Hai vòng là đủ hội tụ cho mọi mặt cắt đã gặp.
        # Lề trên KHÔNG được vượt 30% chiều cao: hình mặt cắt mới là thứ chính,
        # để ký hiệu tự nới lề thì mặt cắt bị bóp còn một dải mỏng.
        mt_cap = H * 0.30
        mt = min(self.MARGIN[1], mt_cap)
        s, cw, ch = scale_for(mt)
        r, rows, out = float(self.R_BUBBLE), 1, float(self.CUT_OUT)
        for _ in range(2):
            r, rows = self._symbol_metrics(s)
            out = min(self.CUT_OUT, max(4.0, H * 0.05))
            # Không đủ lề cho số hàng đó ở bán kính tối thiểu → bớt hàng đi
            while rows > 1 and out + self.R_MIN * (2 + 2.3 * (rows - 1)) + 4 > mt_cap:
                rows -= 1
            span = 2 + 2.3 * (rows - 1)
            mt = min(max(out + r * span + 4, 22.0), mt_cap)
            r = max(6.0, min(r, (mt - out - 4) / span))
            s, cw, ch = scale_for(mt)
        self._r, self._rows, self._out = r, rows, out

        ox = ml + (cw - (x1 - x0) * s) / 2
        oz = mt + (ch - (z1 - z0) * s) / 2

        # Zoom/pan chồng lên phép quy đổi cơ sở. Ký hiệu vết cắt (vòng tròn, mũi
        # tên) vẫn giữ nguyên cỡ pixel — đúng lối bản vẽ: phóng to là để nhìn
        # rõ hình, không phải để ký hiệu to ra.
        zm, off = self._zoom, self._off

        def fn(x, z):
            return QPointF(off.x() + (ox + (x - x0) * s) * zm,
                           off.y() + (oz + (z1 - z) * s) * zm)
        return fn, s * zm

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Tự tô nền theo token: dựa vào QSS của widget cha thì bản Tối sẽ ra hình
        # vẽ trên nền sáng khi widget đứng riêng (xuất ảnh, in báo cáo).
        p.fillRect(self.rect(), QColor(self.t['panel']))
        if not self._geom or not self._geom.get('outpoly'):
            p.setPen(QPen(QColor(self.t['ink_3'])))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       'Chưa có kết quả — bấm “Xử lý tất cả” sau khi gán Beam Force')
            p.end()
            return

        fn, _ = self._mapper()      # đặt luôn self._r / _out / _rows
        from PyQt6.QtGui import QPainterPath

        # bê tông = biên ngoài trừ lỗ rỗng, gạch 45° theo quy ước bản vẽ
        path = QPainterPath()
        path.setFillRule(Qt.FillRule.OddEvenFill)
        for poly in [self._geom['outpoly']] + list(self._geom.get('inpolys') or []):
            if len(poly) < 3:
                continue
            path.moveTo(fn(*poly[0]))
            for x, z in poly[1:]:
                path.lineTo(fn(x, z))
            path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(self.t['dia_hatch']), Qt.BrushStyle.BDiagPattern))
        p.drawPath(path)

        # nét bao mặt cắt: đậm
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(self.t['dia_edge']), 2.0))
        p.drawPath(path)

        # tim mặt cắt: nét gạch-chấm
        zs = [q[1] for q in self._geom['outpoly']]
        pen = QPen(QColor(self.t['dia_note']), 0.8)
        pen.setDashPattern([12, 3, 2, 3])
        p.setPen(pen)
        p.drawLine(fn(0.0, max(zs)) + QPointF(0, -18),
                   fn(0.0, min(zs)) + QPointF(0, 18))

        # Ký hiệu cắt đứng xếp so le nhiều hàng: các mặt cắt bản mặt cách nhau
        # chưa tới 1 m nên để một hàng là bubble chen nhau. Số hàng do
        # `_symbol_metrics` quyết định theo mật độ thực tế.
        rows = max(1, getattr(self, '_rows', 1))
        rank = {}
        for names in self._vertical_groups():
            # So le TRONG TỪNG NHÓM: đánh số chạy qua cả hai nhóm thì hàng của
            # ký hiệu bản đáy phụ thuộc số ký hiệu bản mặt, đổi mặt cắt là nhảy.
            rank.update({n: (i % rows) for i, n in enumerate(names)})
        for name in sorted(self._marks, key=lambda n: (n[0], n[1:])):
            self._draw_mark(p, fn, name, self._marks[name], rank.get(name, 0))
        p.end()

    def _draw_mark(self, p, fn, name, mk, row=0):
        """Một ký hiệu vết cắt: đường cắt · mũi tên · vòng tròn tên."""
        col = QColor(point_color(name[0], self.t))
        c = fn(mk['x'], mk['z'])
        zs = [q[1] for q in self._geom['outpoly']]
        r, out = self._r, self._out

        if mk['dir'] == 'v':
            # cắt thẳng đứng; ký hiệu ở phía gần mặt hơn (trên nếu z ở nửa trên)
            up = mk['z'] > (max(zs) + min(zs)) / 2
            sgn = -1 if up else 1
            reach = out + r + row * 2.3 * r
            end = QPointF(c.x(), c.y() + sgn * reach)
            far = QPointF(c.x(), c.y() - sgn * out)
            tri = [QPointF(end.x() + r, end.y() - r * 0.8),
                   QPointF(end.x() + r, end.y() + r * 0.8),
                   QPointF(end.x() + r + r * 1.5, end.y())]
        else:
            # bụng thẳng đứng → cắt nằm ngang; ký hiệu ra phía ngoài mặt cắt
            sgn = 1 if mk['x'] > 0 else -1
            end = QPointF(c.x() + sgn * (out + r), c.y())
            far = QPointF(c.x() - sgn * out, c.y())
            tri = [QPointF(end.x() - r * 0.8, end.y() + r),
                   QPointF(end.x() + r * 0.8, end.y() + r),
                   QPointF(end.x(), end.y() + r + r * 1.5)]

        p.setPen(QPen(col, 1.1))          # đường cắt: nét MẢNH
        p.drawLine(far, end)

        p.setPen(Qt.PenStyle.NoPen)       # mũi tên đặc, vuông góc đường cắt
        p.setBrush(QBrush(col))
        from PyQt6.QtGui import QPolygonF
        p.drawPolygon(QPolygonF(tri))

        p.setBrush(QBrush(QColor(self.t['panel'])))
        p.setPen(QPen(col, 1.6))
        p.drawEllipse(QRectF(end.x() - r, end.y() - r, 2 * r, 2 * r))

        # Phông lấy từ widget (theo theme) chứ không ghim 'Arial': ghim cứng thì
        # máy thiếu phông đó sẽ vẽ ra ô vuông, và cũng lệch với phần còn lại.
        f = self.font()
        f.setBold(True)
        f.setPointSizeF(max(6.0, min(f.pointSizeF(), r * 0.62)
                            - (1 if len(name) > 1 else 0)))
        p.setFont(f)
        p.setPen(QPen(col))
        p.drawText(QRectF(end.x() - r, end.y() - r, 2 * r, 2 * r),
                   Qt.AlignmentFlag.AlignCenter, name)


class ResultsTab(QWidget):
    progress_changed = pyqtSignal(int, int)
    project_changed = pyqtSignal()
    # Người dùng chọn mặt cắt khác ở ô "Xem mặt cắt" — kéo theo cả cây mặt cắt,
    # khung xem và dock Properties. Xem chú thích ở chỗ nối tín hiệu.
    section_selected = pyqtSignal(str)

    def __init__(self, status_bar, project=None, theme=None):
        super().__init__()
        from src.project import Project
        self.status_bar = status_bar
        self.project = project if project is not None else Project()
        self.t = theme or LIGHT
        self.worker = None
        self.all_results = {}
        self.all_env = {}      # {mặt cắt: bao nội lực để vẽ biểu đồ}
        self._points = list(POINTS)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Cặp Beam Force ↔ MCT lấy thẳng từ project — không còn dò theo tên file
        row = QHBoxLayout()
        row.addWidget(QLabel('Thư mục kết quả:'))
        self.out_edit = QLineEdit(self.project.output_dir)
        row.addWidget(self.out_edit, 1)
        btn_out = QPushButton('Duyệt…')
        btn_out.clicked.connect(self._browse_output)
        row.addWidget(btn_out)
        layout.addLayout(row)

        self.pair_list = QListWidget()
        self.pair_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.pair_list.setMaximumHeight(112)
        self.pair_list.setStyleSheet('font-family: Consolas, monospace;')
        self.pair_list.itemDoubleClicked.connect(self._assign_bf_from_item)
        layout.addWidget(self.pair_list)

        # Dải nhắc cách xuất Beam Force. Đặt cố định chứ không chỉ để chữ chìm:
        # thiếu một tổ hợp là bảng kiểm toán không dựng được, mà lỗi đó chỉ lộ ra
        # ở cuối quy trình.
        self.lb_hint = QLabel(
            '⚠  File Beam Force phải xuất mặc định từ Midas: '
            '<b>Results → Result Tables → Beam → Beam Force</b>, chọn '
            '<b>tất cả trường hợp tải và tổ hợp</b> rồi <b>Export → Excel</b>. '
            'Thiếu <tt>str_all</tt> hoặc <tt>ser_all</tt> thì không dựng được '
            'bảng kiểm toán. Công cụ tự đọc <b>mọi sheet</b> trong file.')
        self.lb_hint.setWordWrap(True)
        self.lb_hint.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.lb_hint)

        row_btn = QHBoxLayout()
        self.lb_ready = QLabel('')
        self.lb_ready.setStyleSheet(
            f'color: {self.t["ink_2"]}; font-size: 8pt;')
        row_btn.addWidget(self.lb_ready)
        row_btn.addStretch()
        btn_bf = QPushButton('Gán Beam Force…')
        btn_bf.clicked.connect(self._assign_bf_selected)
        row_btn.addWidget(btn_bf)
        self.btn_process = QPushButton('Xử lý tất cả')
        _f = self.btn_process.font()
        _f.setBold(True)          # nút chính: in đậm, để Windows vẽ thân nút
        self.btn_process.setFont(_f)
        self.btn_process.clicked.connect(self._process)
        row_btn.addWidget(self.btn_process)
        layout.addLayout(row_btn)

        # Section selector + chọn biểu đồ
        row_view = QHBoxLayout()
        row_view.addWidget(QLabel('Xem mặt cắt:'))
        self.section_combo = QComboBox()
        self.section_combo.setMinimumWidth(120)
        self.section_combo.currentTextChanged.connect(self._on_section_changed)
        # `textActivated` chỉ phát khi NGƯỜI DÙNG chọn trong danh sách, không
        # phát khi code dựng lại combo (`clear`/`addItem` lúc xử lý xong Beam
        # Force). Nhờ vậy không cần cờ chặn và không có vòng lặp tín hiệu.
        self.section_combo.textActivated.connect(self.section_selected)
        row_view.addWidget(self.section_combo)
        row_view.addSpacing(16)
        row_view.addWidget(QLabel('Biểu đồ:'))
        self.diag_combo = QComboBox()
        self.diag_combo.addItems(QUANTITY_LABELS)
        self.diag_combo.setMinimumWidth(190)
        row_view.addWidget(self.diag_combo)
        row_view.addStretch()
        layout.addLayout(row_view)

        # Mặt cắt TRÊN, bảng DƯỚI. Trước đây chia ngang nên mặt cắt bị bó vào
        # một cột hẹp, không vẽ nổi tỉ lệ thật; bảng 8 cột thì bị nén.
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Hàng trên chia đôi: trái là mặt cắt kèm ký hiệu vết cắt, phải là biểu
        # đồ bao nội lực. Hai hình cùng một khung ngang nên đặt cạnh nhau đọc
        # được ngay chỗ nào mômen lớn ứng với điểm kiểm toán nào.
        top = QSplitter(Qt.Orientation.Horizontal)
        self.diagram = CheckPointDiagram(self.t)
        self.forces = ForceDiagram(self.t)
        self.diag_combo.currentTextChanged.connect(self.forces.set_quantity)
        top.addWidget(self.diagram)
        top.addWidget(self.forces)
        top.setSizes([520, 460])
        splitter.addWidget(top)

        self.table = QTableWidget(len(DATA_ROWS), len(POINTS))
        self.table.setVerticalHeaderLabels([r[0] for r in DATA_ROWS])
        self.table.verticalHeader().setMinimumWidth(180)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel)
        # Đủ chỗ cho cả bảy hàng ngay từ đầu; chỗ dôi ra khi phóng to cửa sổ
        # dồn hết cho hình (stretch 1 / 0) vì bảng không cần cao thêm.
        self.table.setMinimumHeight(140)
        self._set_points(POINTS)
        splitter.addWidget(self.table)
        splitter.setSizes([360, 250])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        layout.addWidget(splitter, 1)

        # Log
        self.log_area = LogView(theme=self.t)
        self.log_area.setMaximumHeight(130)
        layout.addWidget(self.log_area)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_open = QPushButton('Mở thư mục kết quả')
        btn_open.clicked.connect(self._open_folder)
        btn_row.addWidget(btn_open)
        layout.addLayout(btn_row)

        self._pairs = []      # [(name, bf_path, topo_path)] dựng từ project
        self.refresh()

    def _set_points(self, points):
        """Dựng lại cột theo ĐÚNG các điểm kiểm toán của mặt cắt đang xem.

        Bản trước ghim cứng tám cột A–H, nên mặt cắt hai hộp (18 điểm) mất mười
        cột mà không có gì báo. Quá chín cột thì bỏ chế độ Stretch và cho cuộn
        ngang — bóp mỗi cột còn vài chục pixel thì số dính vào nhau.
        """
        self._points = list(points)
        self.table.setColumnCount(len(self._points))
        self.table.setHorizontalHeaderLabels(self._points)
        hdr = self.table.horizontalHeader()
        if len(self._points) <= MAX_STRETCH_COLS:
            hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        else:
            hdr.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            for j in range(len(self._points)):
                self.table.setColumnWidth(j, COL_W)
        self._style_table_headers()

    def _style_table_headers(self):
        for j, pt in enumerate(self._points):
            color = group_color(GROUP_OF.get(pt[0], ''), self.t)
            for i in range(len(DATA_ROWS)):
                item = QTableWidgetItem('')
                item.setBackground(color)
                self.table.setItem(i, j, item)

    def apply_theme(self, theme: dict, size: dict = None):
        self.t = theme
        self.lb_ready.setStyleSheet(f'color: {theme["ink_2"]}; font-size: 8pt;')
        self.diagram.apply_theme(theme)
        self.forces.apply_theme(theme)
        self.log_area.apply_theme(theme, size)
        # Nền nhóm nằm trong từng ô của bảng — phải đặt lại, QSS không với tới.
        self._style_table_headers()
        if self.all_results:
            self._on_section_changed(self.section_combo.currentText())

    def set_log(self, log):
        """Chuyển sang dùng cửa sổ Messages chung.

        Phải GIẤU khung log riêng của tab đi. Trước đây chỉ gán lại biến, còn
        widget cũ vẫn nằm trong layout và chiếm 130 px trắng ngay dưới bảng nội
        lực — đó là lý do bảng bị bóp chỉ còn một dòng.
        """
        if log is not self.log_area and self.log_area is not None:
            self.log_area.hide()
        self.log_area = log

    def set_project(self, project):
        self.project = project
        self.out_edit.setText(project.output_dir)
        self.refresh()

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(
            self, 'Chọn thư mục kết quả', self.out_edit.text() or '.')
        if folder:
            self.out_edit.setText(folder)
            self.project.output_dir = folder
            self.project.touch()

    def refresh(self):
        """Dựng lại danh sách cặp từ project — thay cho _match_pairs() dò tên file."""
        self.pair_list.clear()
        self._pairs = []
        n_ready = n_missing = 0
        for s in self.project:
            if not s.topo or not os.path.exists(s.topo):
                self.pair_list.addItem(f'{s.name:<12} chưa tạo MCT')
                continue
            if s.beam_force and os.path.exists(s.beam_force):
                self._pairs.append((s.name, s.beam_force, s.topo))
                self.pair_list.addItem(
                    f'{s.name:<12} {s.n_elems:>4} phần tử  ←  '
                    f'{os.path.basename(s.beam_force)}')
                n_ready += 1
            else:
                self.pair_list.addItem(
                    f'{s.name:<12} {s.n_elems:>4} phần tử  ←  '
                    f'(chưa gán Beam Force — bấm đúp để chọn)')
                n_missing += 1
        # Danh sách cao vừa đủ số dòng (tối đa 4). Để cứng 112 px thì project
        # một mặt cắt vẫn chừa gần trăm pixel trắng, trong khi bảng nội lực
        # ngay dưới đang thiếu chỗ.
        rh = self.pair_list.sizeHintForRow(0) if self.pair_list.count() else 24
        self.pair_list.setFixedHeight(
            min(112, max(30, (rh if rh > 0 else 24) * self.pair_list.count() + 6)))
        bits = []
        if n_ready:
            bits.append(f'{n_ready} mặt cắt sẵn sàng')
        if n_missing:
            bits.append(f'{n_missing} chưa có Beam Force')
        self.lb_ready.setText(' · '.join(bits) or 'Chưa có mặt cắt nào đã tạo MCT')
        self.btn_process.setEnabled(n_ready > 0 and self.worker is None)

    # API công khai
    def process(self): self._process()
    def clear(self): self._clear()

    def _row_name(self, item):
        return item.text().split()[0] if item else ''

    def _assign_bf_from_item(self, item):
        self._assign_bf([self._row_name(item)])

    def _assign_bf_selected(self):
        names = [self._row_name(i) for i in self.pair_list.selectedItems()]
        self._assign_bf([n for n in names if n])

    def _assign_bf(self, names):
        if not names:
            self.status_bar.showMessage('Chọn mặt cắt trong danh sách trước.')
            return
        if len(names) == 1:
            sec = self.project.find(names[0])
            start = os.path.dirname(sec.mct) if sec and sec.mct else '.'
            path, _ = QFileDialog.getOpenFileName(
                self, f'Chọn Beam Force cho {names[0]}', start,
                'File Excel (*.xls *.xlsx);;Tất cả (*)')
            if path:
                self.project.set_beam_force(names[0], path)
        else:
            files, _ = QFileDialog.getOpenFileNames(
                self, 'Chọn các file Beam Force', '.',
                'File Excel (*.xls *.xlsx);;Tất cả (*)')
            # ghép theo tên mặt cắt xuất hiện trong tên file
            for n in names:
                hit = next((f for f in files
                            if n.upper() in os.path.basename(f).upper()), None)
                if hit:
                    self.project.set_beam_force(n, hit)
        self.refresh()
        self.project_changed.emit()

    def _clear(self):
        self.log_area.clear()
        self.all_results.clear()
        self.all_env.clear()
        self.section_combo.clear()
        self.refresh()

    def _process(self):
        if not self._pairs:
            self.status_bar.showMessage(
                'Chưa mặt cắt nào sẵn sàng — cần đã tạo MCT và đã gán Beam Force.')
            return

        self.btn_process.setEnabled(False)
        self.log_area.clear()
        self.all_results.clear()
        self.all_env.clear()
        self.section_combo.clear()

        output_dir = self.out_edit.text() or 'output'
        self.worker = ResultsWorker(self._pairs, output_dir)
        self.worker.log.connect(self._on_log)
        self._total = len(self._pairs)
        self._done = 0
        self.progress_changed.emit(0, self._total)
        self.worker.section_done.connect(self._on_section_done)
        self.worker.envelope_done.connect(self._on_envelope)
        self.worker.error_mismatch.connect(self._on_mismatch)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.start()

    def _on_log(self, msg):
        self.log_area.append_auto(msg)

    def _on_envelope(self, name, env):
        self.all_env[name] = env

    def _on_section_done(self, name, check_points):
        self.all_results[name] = check_points
        self.project.record_checked(name)
        self.section_combo.addItem(name)
        self._done += 1
        self.progress_changed.emit(self._done, self._total)
        self.status_bar.showMessage(f'Đã xử lý: {name}')

    def _on_mismatch(self, name, mct_count, result_count, bf_path):
        """Handle element mismatch - ask user to select a different file."""
        reply = QMessageBox.warning(
            self, f'Element Mismatch - {name}',
            f'Beam Force file has {result_count} elements,\n'
            f'but MCT model has {mct_count} elements.\n\n'
            f'File: {os.path.basename(bf_path)}\n\n'
            f'Select a different Beam Force file?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            new_file, _ = QFileDialog.getOpenFileName(
                self, f'Select Beam Force for {name}', os.path.dirname(bf_path),
                'Excel Files (*.xls *.xlsx);;All Files (*)')
            if new_file:
                # Update pair and re-process this one
                for i, (n, bf, tp) in enumerate(self._pairs):
                    if n == name:
                        self._pairs[i] = (name, new_file, tp)
                        break
                self.worker.retry_section(name, new_file)

    def _on_finished(self, count):
        self.btn_process.setEnabled(True)
        self.progress_changed.emit(count, max(count, getattr(self, '_total', count)))
        self.status_bar.showMessage(
            f'Xong: {count} mặt cắt — {self.log_area.summary()}')
        self.log_area.success(f'Hoàn tất {count} mặt cắt')

    def _on_section_changed(self, name):
        if not name or name not in self.all_results:
            return
        self._fill_table(self.all_results[name])
        geom, marks, nodes, elems = self._section_geometry(name)
        self.diagram.set_section(name, geom, marks)
        self.forces.set_data(name, nodes, elems, self.all_env.get(name) or {})

    def _section_geometry(self, name):
        """(geometry, marks, nodes, elements) đọc từ topo.json của mặt cắt.

        Cùng nguồn với MCT — biểu đồ bao vẽ trên đúng bộ node/phần tử mà Midas
        đã tính, nên không có chuyện hình một đằng số một nẻo.
        """
        from src.result_reader import check_point_marks, node_coords
        sec = self.project.find(name)
        path = sec.topo if sec else None
        if not path or not os.path.exists(path):
            return None, {}, {}, []
        try:
            with open(path, encoding='utf-8') as f:
                topo = json.load(f)
            topo['elements'] = [tuple(e) for e in topo['elements']]
            elems = [(e[0], e[1], e[2]) for e in topo['elements']]
            return (topo.get('geometry'), check_point_marks(topo),
                    node_coords(topo), elems)
        except Exception as e:
            self.log_area.warning(f'[{name}] không vẽ được mặt cắt: {e}')
            return None, {}, {}, []

    def _fill_table(self, check_points):
        from src.result_reader import order_points
        bold_font = QFont()
        bold_font.setBold(True)

        points = order_points(check_points.keys())
        if points != getattr(self, '_points', None):
            self._set_points(points)

        for j, pt in enumerate(points):
            color = group_color(GROUP_OF.get(pt[0], ''), self.t)
            for i, (label, key, fmt) in enumerate(DATA_ROWS):
                val = check_points[pt][key]
                text = val if isinstance(val, str) else fmt.format(val)
                item = QTableWidgetItem(text)
                item.setBackground(color)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                      | Qt.AlignmentFlag.AlignVCenter)
                if not label.startswith(' '):
                    item.setFont(bold_font)
                self.table.setItem(i, j, item)

    def _open_folder(self):
        name = self.section_combo.currentText()
        folder = self.out_edit.text()
        if name:
            target = os.path.join(folder, name)
        else:
            target = folder

        if os.path.isdir(target):
            os.startfile(target)

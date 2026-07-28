"""Results tab - Beam Force XLS to check table + Excel."""

import json
import os

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLineEdit, QLabel, QComboBox, QTableWidget,
                              QTableWidgetItem, QPlainTextEdit, QFileDialog,
                              QHeaderView, QSplitter, QListWidget,
                              QAbstractItemView, QMessageBox)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QFontMetrics

from .worker import ResultsWorker
from .widgets import LogView
from .theme import LIGHT


POINTS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
LABELS = ['Center +', 'Haunch M-', 'Haunch M+', 'Out Side',
          'Center', 'Haunch', 'Mid->upper', 'Mid->lower']
GROUPS = ['Top slab', '', '', '', 'Bottom slab', '', 'Web', '']

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


class CheckPointDiagram(QWidget):
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
        super().__init__()
        self.t = theme or LIGHT
        # Cao tối thiểu 300: lề trên = 26% chiều cao phải đạt 77 px mới xếp
        # được hai hàng ký hiệu so le, thấp hơn thì B bị D che.
        self.setMinimumSize(380, 300)
        self._geom = None          # {'outpoly', 'inpolys', 'H'}
        self._marks = {}           # {tên: {'x','z','dir'}}
        self._name = ''

    def apply_theme(self, theme: dict):
        self.t = theme
        self.update()

    def set_section(self, name: str, geometry: dict, marks: dict):
        """Nạp hình học và vị trí ký hiệu. geometry=None thì xoá hình."""
        self._name = name or ''
        self._geom = geometry or None
        self._marks = marks or {}
        self.update()

    # ── quy đổi toạ độ ──
    def _mapper(self):
        """Trả (fn, scale). fn(x, z) → QPointF pixel, giữ đúng tỉ lệ hình học."""
        g = self._geom
        xs = [p[0] for p in g['outpoly']]
        zs = [p[1] for p in g['outpoly']]
        x0, x1 = min(xs), max(xs)
        z0, z1 = min(zs), max(zs)
        # Lề co theo kích thước: để cứng 88 px thì khi panel thấp (splitter kéo
        # nhỏ) lề ăn hết chỗ và mặt cắt bị bóp còn vài pixel.
        # Lề co theo kích thước: để cứng 88 px thì khi panel thấp (splitter kéo
        # nhỏ) lề ăn hết chỗ và mặt cắt bị bóp còn vài pixel.
        ml, mt, mr, mb = self.MARGIN
        ml = mr = min(ml, self.width() * 0.14)
        mt = mb = min(mt, self.height() * 0.26)
        cw = max(self.width() - ml - mr, 1)
        ch = max(self.height() - mt - mb, 1)
        # Ký hiệu cũng phải co theo: bán kính và độ nhô ra vừa đúng lề còn lại,
        # và chỉ xếp hai hàng khi lề đủ chỗ — không thì hàng thứ hai bị cắt.
        self._r = max(8.0, min(self.R_BUBBLE, (mt - 6) / 2.2))
        self._out = max(5.0, min(self.CUT_OUT, mt - 2 * self._r - 2))
        self._two_rows = (self._out + self._r * (2 + 2.3)) <= mt
        sx = cw / max(x1 - x0, 1e-9)
        sz = ch / max(z1 - z0, 1e-9)
        s = min(sx, sz)
        ox = ml + (cw - (x1 - x0) * s) / 2
        oz = mt + (ch - (z1 - z0) * s) / 2

        def fn(x, z):
            return QPointF(ox + (x - x0) * s, oz + (z1 - z) * s)
        return fn, s

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

        fn, _ = self._mapper()      # đặt luôn self._r / _out / _two_rows
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

        # Ký hiệu cắt đứng xếp thành hai hàng so le: các mặt cắt bản mặt cách
        # nhau chưa tới 1 m nên để một hàng là bubble chen nhau.
        vert = sorted((n for n, m in self._marks.items() if m['dir'] == 'v'),
                      key=lambda n: self._marks[n]['x'])
        rank = {n: (i % 2 if self._two_rows else 0) for i, n in enumerate(vert)}
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

    def __init__(self, status_bar, project=None, theme=None):
        super().__init__()
        from src.project import Project
        self.status_bar = status_bar
        self.project = project if project is not None else Project()
        self.t = theme or LIGHT
        self.worker = None
        self.all_results = {}
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
        self.btn_process.setProperty('primary', True)
        self.btn_process.clicked.connect(self._process)
        row_btn.addWidget(self.btn_process)
        layout.addLayout(row_btn)

        # Section selector
        row_view = QHBoxLayout()
        row_view.addWidget(QLabel('Xem mặt cắt:'))
        self.section_combo = QComboBox()
        self.section_combo.setMinimumWidth(120)
        self.section_combo.currentTextChanged.connect(self._on_section_changed)
        row_view.addWidget(self.section_combo)
        row_view.addStretch()
        layout.addLayout(row_view)

        # Mặt cắt TRÊN, bảng DƯỚI. Trước đây chia ngang nên mặt cắt bị bó vào
        # một cột hẹp, không vẽ nổi tỉ lệ thật; bảng 8 cột thì bị nén.
        splitter = QSplitter(Qt.Orientation.Vertical)

        self.diagram = CheckPointDiagram(self.t)
        splitter.addWidget(self.diagram)

        self.table = QTableWidget(len(DATA_ROWS), 8)
        self.table.setHorizontalHeaderLabels(POINTS)
        self.table.setVerticalHeaderLabels([r[0] for r in DATA_ROWS])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setMinimumWidth(180)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._style_table_headers()
        splitter.addWidget(self.table)
        splitter.setSizes([380, 240])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
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

    def _style_table_headers(self):
        current_group = ''
        for j in range(8):
            if GROUPS[j]:
                current_group = GROUPS[j]
            color = group_color(current_group, self.t)
            for i in range(len(DATA_ROWS)):
                item = QTableWidgetItem('')
                item.setBackground(color)
                self.table.setItem(i, j, item)

    def apply_theme(self, theme: dict, size: dict = None):
        self.t = theme
        self.lb_ready.setStyleSheet(f'color: {theme["ink_2"]}; font-size: 8pt;')
        self.diagram.apply_theme(theme)
        self.log_area.apply_theme(theme, size)
        # Nền nhóm nằm trong từng ô của bảng — phải đặt lại, QSS không với tới.
        self._style_table_headers()
        if self.all_results:
            self._on_section_changed(self.section_combo.currentText())

    # API công khai cho menu/toolbar
    def process(self): self._process()
    def clear(self): self._clear()
    def open_folder(self): self._open_folder()

    def set_log(self, log):
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
    def open_folder(self): self._open_folder()

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
        self.section_combo.clear()

        output_dir = self.out_edit.text() or 'output'
        self.worker = ResultsWorker(self._pairs, output_dir)
        self.worker.log.connect(self._on_log)
        self._total = len(self._pairs)
        self._done = 0
        self.progress_changed.emit(0, self._total)
        self.worker.section_done.connect(self._on_section_done)
        self.worker.error_mismatch.connect(self._on_mismatch)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.start()

    def _on_log(self, msg):
        self.log_area.append_auto(msg)

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
        self.diagram.set_section(name, *self._section_geometry(name))

    def _section_geometry(self, name):
        """(geometry, marks) đọc từ topo.json của mặt cắt — cùng nguồn với MCT."""
        from src.result_reader import check_point_marks
        sec = self.project.find(name)
        path = sec.topo if sec else None
        if not path or not os.path.exists(path):
            return None, {}
        try:
            with open(path, encoding='utf-8') as f:
                topo = json.load(f)
            topo['elements'] = [tuple(e) for e in topo['elements']]
            return topo.get('geometry'), check_point_marks(topo)
        except Exception as e:
            self.log_area.warn(f'[{name}] không vẽ được mặt cắt: {e}')
            return None, {}

    def _fill_table(self, check_points):
        bold_font = QFont()
        bold_font.setBold(True)

        current_group = ''
        for j, pt in enumerate(POINTS):
            if GROUPS[j]:
                current_group = GROUPS[j]
            color = group_color(current_group, self.t)

            for i, (label, key, fmt) in enumerate(DATA_ROWS):
                val = check_points[pt][key]
                if isinstance(val, str):
                    text = val
                else:
                    text = fmt.format(val)

                item = QTableWidgetItem(text)
                item.setBackground(color)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
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

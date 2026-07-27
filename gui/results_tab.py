"""Results tab - Beam Force XLS to check table + Excel."""

import os

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLineEdit, QLabel, QComboBox, QTableWidget,
                              QTableWidgetItem, QPlainTextEdit, QFileDialog,
                              QHeaderView, QSplitter, QListWidget,
                              QAbstractItemView, QMessageBox)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
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
    ('  -> element', 'Mu_ref', '{}'),
    ('Strength Vu (kN)', 'Vu', '{:.2f}'),
    ('  -> element', 'Vu_ref', '{}'),
    ('Service Mser (kN.m)', 'Mser', '{:.2f}'),
    ('  -> element', 'Mser_ref', '{}'),
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
    """Simple schematic of box girder cross-section with check points A-H."""

    def __init__(self, theme=None):
        super().__init__()
        self.t = theme or LIGHT
        self.setMinimumSize(320, 220)

    def apply_theme(self, theme: dict):
        self.t = theme
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()

        mx, my = 40, 25
        cw = w - 2 * mx
        ch = h - 2 * my

        bw = 0.56
        bh = 0.65
        tt = 0.06
        tb = 0.05
        tw = 0.03
        cant_drop = 0.08

        def px(rx): return mx + rx * cw
        def py(ry): return my + ry * ch

        x_left = 0.0
        x_right = 1.0
        x_wL = (1.0 - bw) / 2
        x_wR = (1.0 + bw) / 2
        y_top = 0.0
        y_tip = cant_drop
        y_wj = cant_drop + 0.02
        y_bot = bh

        from PyQt6.QtGui import QPolygonF
        from PyQt6.QtCore import QPointF

        outer = QPolygonF([
            QPointF(px(x_left), py(y_top)),
            QPointF(px(x_right), py(y_top)),
            QPointF(px(x_right), py(y_tip)),
            QPointF(px(x_wR), py(y_wj)),
            QPointF(px(x_wR), py(y_bot)),
            QPointF(px(x_wL), py(y_bot)),
            QPointF(px(x_wL), py(y_wj)),
            QPointF(px(x_left), py(y_tip)),
        ])

        ix_L = x_wL + tw
        ix_R = x_wR - tw
        iy_top = tt
        iy_bot = bh - tb
        inner = QPolygonF([
            QPointF(px(ix_L), py(iy_top + 0.02)),
            QPointF(px(0.5 - 0.12), py(iy_top)),
            QPointF(px(0.5 + 0.12), py(iy_top)),
            QPointF(px(ix_R), py(iy_top + 0.02)),
            QPointF(px(ix_R), py(iy_bot - 0.02)),
            QPointF(px(ix_R - 0.01), py(iy_bot)),
            QPointF(px(ix_L + 0.01), py(iy_bot)),
            QPointF(px(ix_L), py(iy_bot - 0.02)),
        ])

        p.setPen(QPen(QColor(self.t['dia_edge']), 1.5))
        p.setBrush(QBrush(QColor(self.t['dia_fill'])))
        p.drawPolygon(outer)

        p.setBrush(QBrush(QColor(self.t['panel'])))
        p.drawPolygon(inner)

        font = QFont('Arial', 9, QFont.Weight.Bold)
        p.setFont(font)
        fm = QFontMetrics(font)
        r = 10

        points_pos = {
            'A': (0.50, tt / 2, 0, -16),
            'B': (x_wL + tw / 2 + 0.03, tt / 2 + 0.01, -20, -16),
            'C': (x_wR - tw / 2 - 0.03, tt / 2 + 0.01, 8, -16),
            'D': (x_left + 0.06, y_tip / 2, -18, -14),
            'E': (0.50, bh - tb / 2, 0, 14),
            'F': (x_wL + tw / 2 + 0.03, bh - tb / 2 - 0.01, -20, 14),
            'G': (x_wR, (y_wj + 0.5 * (y_wj + iy_top)) / 2 + 0.06, 14, -4),
            'H': (x_wL, (iy_bot + y_bot) / 2 - 0.02, -24, -4),
        }

        for pt, (rx, ry, lox, loy) in points_pos.items():
            cx = px(rx)
            cy = py(ry)
            color = point_color(pt, self.t)

            p.setPen(QPen(color, 2))
            p.setBrush(QBrush(color))
            p.drawEllipse(QRectF(cx - r/2, cy - r/2, r, r))

            p.setPen(QPen(color, 1))
            label = f'{pt}'
            lw = fm.horizontalAdvance(label)
            p.drawText(int(cx + lox - lw / 2), int(cy + loy), label)

        ly = h - 12
        p.setFont(QFont('Arial', 7))
        p.setPen(QPen(QColor(self.t['dia_note'])))
        legend = 'A-D: Top slab | E-F: Bottom slab | G-H: Web'
        p.drawText(mx, ly, legend)

        p.end()


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

        # Table + Diagram
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.table = QTableWidget(len(DATA_ROWS), 8)
        self.table.setHorizontalHeaderLabels(POINTS)
        self.table.setVerticalHeaderLabels([r[0] for r in DATA_ROWS])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setMinimumWidth(180)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._style_table_headers()
        splitter.addWidget(self.table)

        self.diagram = CheckPointDiagram(self.t)
        splitter.addWidget(self.diagram)

        splitter.setSizes([550, 320])
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
        if name and name in self.all_results:
            self._fill_table(self.all_results[name])

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

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


POINTS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
LABELS = ['Center +', 'Haunch M-', 'Haunch M+', 'Out Side',
          'Center', 'Haunch', 'Mid->upper', 'Mid->lower']
GROUPS = ['Top slab', '', '', '', 'Bottom slab', '', 'Web', '']

GROUP_COLORS = {
    'Top slab': QColor(255, 230, 230),
    'Bottom slab': QColor(230, 240, 255),
    'Web': QColor(230, 255, 230),
}

DATA_ROWS = [
    ('Depth h (mm)', 'h', '{:.0f}'),
    ('Strength Mu (kN.m)', 'Mu', '{:.2f}'),
    ('  -> element', 'Mu_ref', '{}'),
    ('Strength Vu (kN)', 'Vu', '{:.2f}'),
    ('  -> element', 'Vu_ref', '{}'),
    ('Service Mser (kN.m)', 'Mser', '{:.2f}'),
    ('  -> element', 'Mser_ref', '{}'),
]

POINT_COLORS = {
    'A': QColor(220, 50, 50),
    'B': QColor(200, 80, 80),
    'C': QColor(180, 60, 60),
    'D': QColor(160, 40, 40),
    'E': QColor(50, 80, 200),
    'F': QColor(70, 100, 220),
    'G': QColor(40, 160, 60),
    'H': QColor(60, 140, 80),
}


class CheckPointDiagram(QWidget):
    """Simple schematic of box girder cross-section with check points A-H."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(320, 220)

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

        p.setPen(QPen(QColor(80, 80, 80), 1.5))
        p.setBrush(QBrush(QColor(220, 220, 220)))
        p.drawPolygon(outer)

        p.setBrush(QBrush(QColor(255, 255, 255)))
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
            color = POINT_COLORS[pt]

            p.setPen(QPen(color, 2))
            p.setBrush(QBrush(color))
            p.drawEllipse(QRectF(cx - r/2, cy - r/2, r, r))

            p.setPen(QPen(color, 1))
            label = f'{pt}'
            lw = fm.horizontalAdvance(label)
            p.drawText(int(cx + lox - lw / 2), int(cy + loy), label)

        ly = h - 12
        p.setFont(QFont('Arial', 7))
        p.setPen(QPen(QColor(100, 100, 100)))
        legend = 'A-D: Top slab | E-F: Bottom slab | G-H: Web'
        p.drawText(mx, ly, legend)

        p.end()


class ResultsTab(QWidget):
    progress_changed = pyqtSignal(int, int)

    def __init__(self, status_bar):
        super().__init__()
        self.status_bar = status_bar
        self.worker = None
        self.all_results = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Beam Force files row
        row_bf = QHBoxLayout()
        row_bf.addWidget(QLabel('File Beam Force:'))
        self.bf_edit = QLineEdit()
        self.bf_edit.setPlaceholderText('Chọn file Beam Force XLS xuất từ Midas…')
        self.bf_edit.setReadOnly(True)
        row_bf.addWidget(self.bf_edit, 1)
        btn_bf = QPushButton('Chọn file…')
        btn_bf.clicked.connect(self._browse_beam_force)
        row_bf.addWidget(btn_bf)
        layout.addLayout(row_bf)

        # MCT files row (generated from Generate tab, contains topology)
        row_mct = QHBoxLayout()
        row_mct.addWidget(QLabel('File MCT:'))
        self.mct_edit = QLineEdit()
        self.mct_edit.setPlaceholderText('Chọn file MCT do bước Tạo mô hình sinh ra…')
        self.mct_edit.setReadOnly(True)
        row_mct.addWidget(self.mct_edit, 1)
        btn_mct = QPushButton('Chọn file…')
        btn_mct.clicked.connect(self._browse_mct)
        row_mct.addWidget(btn_mct)
        layout.addLayout(row_mct)

        # Output dir row
        row_out = QHBoxLayout()
        row_out.addWidget(QLabel('Thư mục kết quả:'))
        self.out_edit = QLineEdit('.')
        row_out.addWidget(self.out_edit, 1)
        btn_out = QPushButton('Duyệt…')
        btn_out.clicked.connect(self._browse_output)
        row_out.addWidget(btn_out)
        layout.addLayout(row_out)

        # File pair list
        self.pair_list = QListWidget()
        self.pair_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.pair_list.setMaximumHeight(80)
        self.pair_list.setStyleSheet('font-family: Consolas, monospace;')
        layout.addWidget(self.pair_list)

        # Buttons row
        row_btn = QHBoxLayout()
        row_btn.addStretch()
        btn_clear = QPushButton('Xóa danh sách')
        btn_clear.clicked.connect(self._clear)
        row_btn.addWidget(btn_clear)
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

        self.diagram = CheckPointDiagram()
        splitter.addWidget(self.diagram)

        splitter.setSizes([550, 320])
        layout.addWidget(splitter, 1)

        # Log
        self.log_area = LogView()
        self.log_area.setMaximumHeight(130)
        layout.addWidget(self.log_area)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_open = QPushButton('Mở thư mục kết quả')
        btn_open.clicked.connect(self._open_folder)
        btn_row.addWidget(btn_open)
        layout.addLayout(btn_row)

        # Internal storage
        self._bf_files = []   # list of Beam Force XLS paths
        self._mct_files = []  # list of MCT file paths
        self._pairs = []      # list of (name, bf_path, topo_path)

    def _style_table_headers(self):
        current_group = ''
        for j in range(8):
            if GROUPS[j]:
                current_group = GROUPS[j]
            color = GROUP_COLORS.get(current_group, QColor(255, 255, 255))
            for i in range(len(DATA_ROWS)):
                item = QTableWidgetItem('')
                item.setBackground(color)
                self.table.setItem(i, j, item)

    # API công khai cho menu/toolbar
    def process(self): self._process()
    def clear(self): self._clear()
    def open_folder(self): self._open_folder()

    def _browse_beam_force(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, 'Chọn file Beam Force', '.',
            'File Excel (*.xls *.xlsx);;Tất cả (*)')
        if files:
            self._bf_files = files
            self.bf_edit.setText(f'{len(files)} file đã chọn')
            self._match_pairs()

    def _browse_mct(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, 'Chọn file MCT', '.',
            'File MCT (*.mct)')
        if files:
            self._mct_files = files
            self.mct_edit.setText(f'{len(files)} file đã chọn')
            self._match_pairs()

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(
            self, 'Chọn thư mục kết quả', self.out_edit.text())
        if folder:
            self.out_edit.setText(folder)

    def _match_pairs(self):
        """Auto-match Beam Force files with MCT files by section name.

        Each MCT file ({name}_frame.mct) must have a companion
        {name}_topo.json in the same directory (created by Generate).
        """
        self.pair_list.clear()
        self._pairs = []

        if not self._bf_files or not self._mct_files:
            return

        # Build MCT lookup: section name -> topo.json path
        mct_map = {}   # NAME (upper) -> (name, topo_path)
        dir_map = {}   # directory path -> (name, topo_path)
        for mct in self._mct_files:
            mct_base = os.path.splitext(os.path.basename(mct))[0]
            # Strip "_frame" suffix: "S16_frame" -> "S16"
            name = mct_base
            if name.endswith('_frame'):
                name = name[:-6]
            # Look for companion topo.json
            mct_dir = os.path.dirname(mct)
            topo_path = os.path.join(mct_dir, f'{name}_topo.json')
            if os.path.exists(topo_path):
                mct_map[name.upper()] = (name, topo_path)
                dir_map[os.path.normpath(mct_dir)] = (name, topo_path)

        for bf in self._bf_files:
            bf_base = os.path.splitext(os.path.basename(bf))[0]
            # Extract section name from filename: "Beam Force_S16" -> "S16"
            bf_name = bf_base
            for prefix in ['Beam Force_', 'Beam Force ', 'BeamForce_', 'BeamForce ']:
                if bf_base.startswith(prefix):
                    bf_name = bf_base[len(prefix):]
                    break

            # If name is still generic (e.g. "Beam Force"), use parent folder name
            if bf_name.upper().replace(' ', '') in ('BEAMFORCE', 'BEAM FORCE', ''):
                bf_name = os.path.basename(os.path.dirname(bf))

            # Try match by name first, then by same directory
            match = mct_map.get(bf_name.upper())
            if not match:
                bf_dir = os.path.normpath(os.path.dirname(bf))
                match = dir_map.get(bf_dir)
            if match:
                name, topo_path = match
                # Count elements from topo.json for display
                try:
                    import json
                    with open(topo_path, 'r', encoding='utf-8') as f:
                        topo = json.load(f)
                    n_elem = len(topo['elements'])
                    info = f'{n_elem} elements'
                except Exception:
                    info = 'topo loaded'
                self._pairs.append((name, bf, topo_path))
                self.pair_list.addItem(
                    f'{name}: {os.path.basename(bf)} <-> MCT ({info})')
            else:
                self.pair_list.addItem(
                    f'{bf_name}: {os.path.basename(bf)} <-> ??? (no matching MCT/topo)')

    def _clear(self):
        self._bf_files = []
        self._mct_files = []
        self._pairs = []
        self.bf_edit.clear()
        self.mct_edit.clear()
        self.pair_list.clear()
        self.log_area.clear()
        self.all_results.clear()
        self.section_combo.clear()

    def _process(self):
        if not self._pairs:
            self.status_bar.showMessage('Chưa ghép được cặp file nào — chọn cả Beam Force lẫn MCT.')
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
            color = GROUP_COLORS.get(current_group, QColor(255, 255, 255))

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

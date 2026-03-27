"""Results tab - Beam Force XLS to check table + Excel."""

import os
import glob

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLineEdit, QLabel, QComboBox, QTableWidget,
                              QTableWidgetItem, QPlainTextEdit, QFileDialog,
                              QHeaderView, QSplitter)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QFontMetrics

from .worker import ResultsWorker


POINTS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
LABELS = ['Center +', 'Haunch M-', 'Haunch M+', 'Out Side',
          'Center', 'Haunch', 'Mid->upper', 'Mid->lower']
GROUPS = ['Top slab', '', '', '', 'Bottom slab', '', 'Web', '']

# Colors per group
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

# Check point colors for diagram
POINT_COLORS = {
    'A': QColor(220, 50, 50),     # red
    'B': QColor(200, 80, 80),
    'C': QColor(180, 60, 60),
    'D': QColor(160, 40, 40),
    'E': QColor(50, 80, 200),     # blue
    'F': QColor(70, 100, 220),
    'G': QColor(40, 160, 60),     # green
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

        # Margins
        mx, my = 40, 25
        cw = w - 2 * mx  # content width
        ch = h - 2 * my  # content height

        # Box girder proportions (normalized)
        # Total width = 1.0, box width ~ 0.56, height ~ 0.6
        bw = 0.56   # box width ratio
        bh = 0.65   # box height ratio
        tt = 0.06   # top slab thickness
        tb = 0.05   # bottom slab thickness
        tw = 0.03   # web thickness
        cant_drop = 0.08  # cantilever tip drop

        # Convert to pixel coords
        def px(rx): return mx + rx * cw
        def py(ry): return my + ry * ch

        # Outer profile
        x_left = 0.0
        x_right = 1.0
        x_wL = (1.0 - bw) / 2
        x_wR = (1.0 + bw) / 2
        y_top = 0.0
        y_tip = cant_drop
        y_wj = cant_drop + 0.02  # web junction
        y_bot = bh

        # Draw filled outer shape
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

        # Inner void
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

        # Fill concrete
        p.setPen(QPen(QColor(80, 80, 80), 1.5))
        p.setBrush(QBrush(QColor(220, 220, 220)))
        p.drawPolygon(outer)

        # Fill void (white)
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.drawPolygon(inner)

        # ── Draw check points ──
        font = QFont('Arial', 9, QFont.Weight.Bold)
        p.setFont(font)
        fm = QFontMetrics(font)
        r = 10  # circle radius

        points_pos = {
            # (rx, ry, label_offset_x, label_offset_y)
            'A': (0.50, tt / 2, 0, -16),                           # top center
            'B': (x_wL + tw / 2 + 0.03, tt / 2 + 0.01, -20, -16), # top haunch L
            'C': (x_wR - tw / 2 - 0.03, tt / 2 + 0.01, 8, -16),   # top haunch R
            'D': (x_left + 0.06, y_tip / 2, -18, -14),             # cantilever
            'E': (0.50, bh - tb / 2, 0, 14),                       # bot center
            'F': (x_wL + tw / 2 + 0.03, bh - tb / 2 - 0.01, -20, 14),  # bot haunch
            'G': (x_wR, (y_wj + 0.5 * (y_wj + iy_top)) / 2 + 0.06, 14, -4),  # web upper
            'H': (x_wL, (iy_bot + y_bot) / 2 - 0.02, -24, -4),    # web lower
        }

        for pt, (rx, ry, lox, loy) in points_pos.items():
            cx = px(rx)
            cy = py(ry)
            color = POINT_COLORS[pt]

            # Circle
            p.setPen(QPen(color, 2))
            p.setBrush(QBrush(color))
            p.drawEllipse(QRectF(cx - r/2, cy - r/2, r, r))

            # Label
            p.setPen(QPen(color, 1))
            label = f'{pt}'
            lw = fm.horizontalAdvance(label)
            p.drawText(int(cx + lox - lw / 2), int(cy + loy), label)

        # ── Legend ──
        ly = h - 12
        p.setFont(QFont('Arial', 7))
        p.setPen(QPen(QColor(100, 100, 100)))
        legend = 'A-D: Top slab | E-F: Bottom slab | G-H: Web'
        p.drawText(mx, ly, legend)

        p.end()


class ResultsTab(QWidget):
    def __init__(self, status_bar):
        super().__init__()
        self.status_bar = status_bar
        self.worker = None
        self.all_results = {}  # name -> check_points
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Output folder row
        row1 = QHBoxLayout()
        row1.addWidget(QLabel('Output folder:'))
        self.folder_edit = QLineEdit('output')
        row1.addWidget(self.folder_edit, 1)
        btn_browse = QPushButton('Browse...')
        btn_browse.clicked.connect(self._browse_folder)
        row1.addWidget(btn_browse)
        btn_scan = QPushButton('Scan')
        btn_scan.clicked.connect(self._scan_sections)
        row1.addWidget(btn_scan)
        layout.addLayout(row1)

        # Found sections + process button
        row2 = QHBoxLayout()
        self.sections_label = QLabel('Sections: (none)')
        row2.addWidget(self.sections_label, 1)
        self.btn_process = QPushButton('Process All')
        self.btn_process.setStyleSheet('font-weight: bold; padding: 6px 20px;')
        self.btn_process.clicked.connect(self._process)
        row2.addWidget(self.btn_process)
        layout.addLayout(row2)

        # Section selector
        row3 = QHBoxLayout()
        row3.addWidget(QLabel('View section:'))
        self.section_combo = QComboBox()
        self.section_combo.setMinimumWidth(120)
        self.section_combo.currentTextChanged.connect(self._on_section_changed)
        row3.addWidget(self.section_combo)
        row3.addStretch()
        layout.addLayout(row3)

        # Table + Diagram side by side
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Check table
        self.table = QTableWidget(len(DATA_ROWS), 8)
        self.table.setHorizontalHeaderLabels(POINTS)
        self.table.setVerticalHeaderLabels([r[0] for r in DATA_ROWS])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setMinimumWidth(180)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._style_table_headers()
        splitter.addWidget(self.table)

        # Diagram
        self.diagram = CheckPointDiagram()
        splitter.addWidget(self.diagram)

        splitter.setSizes([550, 320])
        layout.addWidget(splitter, 1)

        # Log
        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(120)
        self.log_area.setStyleSheet('font-family: Consolas, monospace; font-size: 11px;')
        layout.addWidget(self.log_area)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_open = QPushButton('Open Output Folder')
        btn_open.clicked.connect(self._open_folder)
        btn_row.addWidget(btn_open)
        layout.addLayout(btn_row)

    def _style_table_headers(self):
        """Apply group colors to column headers."""
        current_group = ''
        for j in range(8):
            if GROUPS[j]:
                current_group = GROUPS[j]
            color = GROUP_COLORS.get(current_group, QColor(255, 255, 255))
            for i in range(len(DATA_ROWS)):
                item = QTableWidgetItem('')
                item.setBackground(color)
                self.table.setItem(i, j, item)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder', self.folder_edit.text())
        if folder:
            self.folder_edit.setText(folder)
            self._scan_sections()

    def _scan_sections(self):
        """Scan for sections with Beam Force XLS."""
        folder = self.folder_edit.text()
        if not os.path.isdir(folder):
            self.sections_label.setText('Sections: (folder not found)')
            return

        self.found_dirs = []
        subdirs = sorted([d for d in os.listdir(folder)
                          if os.path.isdir(os.path.join(folder, d))])
        for sub in subdirs:
            sub_path = os.path.join(folder, sub)
            if glob.glob(os.path.join(sub_path, 'Beam Force*.xls')):
                self.found_dirs.append(sub_path)

        names = [os.path.basename(d) for d in self.found_dirs]
        if names:
            self.sections_label.setText(f'Sections: {", ".join(names)}')
        else:
            self.sections_label.setText('Sections: (no Beam Force files found)')

    def _process(self):
        if not hasattr(self, 'found_dirs') or not self.found_dirs:
            self._scan_sections()
            if not hasattr(self, 'found_dirs') or not self.found_dirs:
                self.status_bar.showMessage('No sections with Beam Force found.')
                return

        self.btn_process.setEnabled(False)
        self.log_area.clear()
        self.all_results.clear()
        self.section_combo.clear()

        self.worker = ResultsWorker(self.found_dirs)
        self.worker.log.connect(self._on_log)
        self.worker.section_done.connect(self._on_section_done)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.start()

    def _on_log(self, msg):
        self.log_area.appendPlainText(msg)

    def _on_section_done(self, name, check_points):
        self.all_results[name] = check_points
        self.section_combo.addItem(name)
        self.status_bar.showMessage(f'Processed: {name}')

    def _on_finished(self, count):
        self.btn_process.setEnabled(True)
        self.status_bar.showMessage(f'Done: {count} section(s) processed.')
        self.log_area.appendPlainText(f'\nCompleted: {count} section(s)')

    def _on_section_changed(self, name):
        if name and name in self.all_results:
            self._fill_table(self.all_results[name])

    def _fill_table(self, check_points):
        """Populate table with check point data."""
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
        """Open current section's output folder."""
        name = self.section_combo.currentText()
        folder = self.folder_edit.text()
        if name:
            target = os.path.join(folder, name)
        else:
            target = folder

        if os.path.isdir(target):
            os.startfile(target)

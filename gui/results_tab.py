"""Results tab - Beam Force XLS to check table + Excel."""

import os
import glob

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLineEdit, QLabel, QComboBox, QTableWidget,
                              QTableWidgetItem, QPlainTextEdit, QFileDialog,
                              QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

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


class ResultsTab(QWidget):
    def __init__(self, status_bar):
        super().__init__()
        self.status_bar = status_bar
        self.worker = None
        self.all_results = {}  # name -> check_points
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Excel data row
        row_excel = QHBoxLayout()
        row_excel.addWidget(QLabel('Excel data:'))
        self.excel_edit = QLineEdit()
        self.excel_edit.setPlaceholderText('Select Excel file (.xls) for material & load data...')
        self.excel_edit.setReadOnly(True)
        row_excel.addWidget(self.excel_edit, 1)
        btn_excel = QPushButton('Browse...')
        btn_excel.clicked.connect(self._browse_excel)
        row_excel.addWidget(btn_excel)
        layout.addLayout(row_excel)

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

        # Check table
        self.table = QTableWidget(len(DATA_ROWS), 8)
        self.table.setHorizontalHeaderLabels(POINTS)
        self.table.setVerticalHeaderLabels([r[0] for r in DATA_ROWS])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setMinimumWidth(180)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMaximumHeight(250)
        self._style_table_headers()
        layout.addWidget(self.table)

        # Log
        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150)
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

    def _browse_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select Excel Data File', '',
            'Excel Files (*.xls *.xlsx);;All Files (*)')
        if path:
            self.excel_edit.setText(path)

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

        excel_path = self.excel_edit.text().strip() or None
        self.worker = ResultsWorker(self.found_dirs, excel_path)
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
        for j, p in enumerate(POINTS):
            if GROUPS[j]:
                current_group = GROUPS[j]
            color = GROUP_COLORS.get(current_group, QColor(255, 255, 255))

            for i, (label, key, fmt) in enumerate(DATA_ROWS):
                val = check_points[p][key]
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

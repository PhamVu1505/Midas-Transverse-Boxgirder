"""Generate tab - DXF to MCT + SVG."""

import os
import glob

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLineEdit, QLabel, QListWidget, QPlainTextEdit,
                              QFileDialog, QSplitter, QAbstractItemView)
from PyQt6.QtCore import Qt

from .worker import GenerateWorker


class GenerateTab(QWidget):
    def __init__(self, status_bar):
        super().__init__()
        self.status_bar = status_bar
        self.worker = None
        self._svg_widget = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # DXF input row
        row1 = QHBoxLayout()
        row1.addWidget(QLabel('Input DXF:'))
        self.dxf_edit = QLineEdit()
        self.dxf_edit.setPlaceholderText('Select DXF file(s) or folder...')
        self.dxf_edit.setReadOnly(True)
        row1.addWidget(self.dxf_edit, 1)
        btn_file = QPushButton('Files...')
        btn_file.clicked.connect(self._browse_files)
        row1.addWidget(btn_file)
        btn_folder = QPushButton('Folder...')
        btn_folder.clicked.connect(self._browse_folder)
        row1.addWidget(btn_folder)
        layout.addLayout(row1)

        # Output dir row
        row2 = QHBoxLayout()
        row2.addWidget(QLabel('Output dir:'))
        self.out_edit = QLineEdit('output')
        row2.addWidget(self.out_edit, 1)
        btn_out = QPushButton('Browse...')
        btn_out.clicked.connect(self._browse_output)
        row2.addWidget(btn_out)
        layout.addLayout(row2)

        # File list
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.setMaximumHeight(120)
        layout.addWidget(self.file_list)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_clear = QPushButton('Clear')
        self.btn_clear.clicked.connect(self._clear)
        btn_row.addWidget(self.btn_clear)
        self.btn_generate = QPushButton('Generate All')
        self.btn_generate.setStyleSheet('font-weight: bold; padding: 6px 20px;')
        self.btn_generate.clicked.connect(self._generate)
        btn_row.addWidget(self.btn_generate)
        layout.addLayout(btn_row)

        # Log + SVG preview
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet('font-family: Consolas, monospace; font-size: 11px;')
        splitter.addWidget(self.log_area)

        # SVG preview - try QSvgWidget, fallback to QLabel
        try:
            from PyQt6.QtSvgWidgets import QSvgWidget
            self._svg_widget = QSvgWidget()
            splitter.addWidget(self._svg_widget)
        except ImportError:
            lbl = QLabel('SVG preview not available\n(install PyQt6-QSvgWidgets)')
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            splitter.addWidget(lbl)

        splitter.setSizes([500, 400])
        layout.addWidget(splitter, 1)

    def _browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, 'Select DXF Files', 'input/dxf', 'DXF Files (*.dxf)')
        if files:
            for f in files:
                if not self._in_list(f):
                    self.file_list.addItem(f)
            self.dxf_edit.setText(f'{self.file_list.count()} file(s) selected')

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select DXF Folder', 'input/dxf')
        if folder:
            dxf_files = sorted(glob.glob(os.path.join(folder, '*.dxf')))
            for f in dxf_files:
                if not self._in_list(f):
                    self.file_list.addItem(f)
            self.dxf_edit.setText(f'{self.file_list.count()} file(s) selected')

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Output Folder', self.out_edit.text())
        if folder:
            self.out_edit.setText(folder)

    def _in_list(self, path):
        for i in range(self.file_list.count()):
            if self.file_list.item(i).text() == path:
                return True
        return False

    def _clear(self):
        self.file_list.clear()
        self.dxf_edit.clear()
        self.log_area.clear()

    def _generate(self):
        dxf_paths = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        if not dxf_paths:
            self.status_bar.showMessage('No DXF files selected.')
            return

        output_dir = self.out_edit.text() or 'output'
        self.btn_generate.setEnabled(False)
        self.log_area.clear()
        self.status_bar.showMessage(f'Generating {len(dxf_paths)} section(s)...')

        self.worker = GenerateWorker(dxf_paths, output_dir)
        self.worker.log.connect(self._on_log)
        self.worker.section_done.connect(self._on_section_done)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.start()

    def _on_log(self, msg):
        self.log_area.appendPlainText(msg)

    def _on_section_done(self, name, svg_path):
        self.status_bar.showMessage(f'Generated: {name}')
        if self._svg_widget and svg_path and os.path.exists(svg_path):
            self._svg_widget.load(svg_path)

    def _on_finished(self, count):
        self.btn_generate.setEnabled(True)
        self.status_bar.showMessage(f'Done: {count} section(s) generated.')
        self.log_area.appendPlainText(f'\nCompleted: {count} section(s)')

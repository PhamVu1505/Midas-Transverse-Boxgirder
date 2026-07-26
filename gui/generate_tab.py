"""Generate tab - DXF to MCT + SVG."""

import os
import glob

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLineEdit, QLabel, QListWidget, QPlainTextEdit,
                              QFileDialog, QSplitter, QAbstractItemView, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal

from .worker import GenerateWorker
from .widgets import LogView


class GenerateTab(QWidget):
    progress_changed = pyqtSignal(int, int)   # done, total

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
        row1.addWidget(QLabel('File DXF:'))
        self.dxf_edit = QLineEdit()
        self.dxf_edit.setPlaceholderText('Chọn file DXF hoặc cả thư mục…')
        self.dxf_edit.setReadOnly(True)
        row1.addWidget(self.dxf_edit, 1)
        btn_file = QPushButton('Chọn file…')
        btn_file.clicked.connect(self._browse_files)
        row1.addWidget(btn_file)
        btn_folder = QPushButton('Chọn thư mục…')
        btn_folder.clicked.connect(self._browse_folder)
        row1.addWidget(btn_folder)
        layout.addLayout(row1)

        # Excel data row
        row_excel = QHBoxLayout()
        row_excel.addWidget(QLabel('Template số liệu:'))
        self.excel_edit = QLineEdit()
        self.excel_edit.setPlaceholderText('Chọn file Excel chứa sheet INPUT (vật liệu + tải trọng)…')
        self.excel_edit.setReadOnly(True)
        row_excel.addWidget(self.excel_edit, 1)
        btn_excel = QPushButton('Duyệt…')
        btn_excel.clicked.connect(self._browse_excel)
        row_excel.addWidget(btn_excel)
        layout.addLayout(row_excel)

        # Output dir row
        row2 = QHBoxLayout()
        row2.addWidget(QLabel('Thư mục kết quả:'))
        self.out_edit = QLineEdit('.')
        row2.addWidget(self.out_edit, 1)
        btn_out = QPushButton('Duyệt…')
        btn_out.clicked.connect(self._browse_output)
        row2.addWidget(btn_out)
        layout.addLayout(row2)

        # File list
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.setMaximumHeight(148)
        layout.addWidget(self.file_list)

        # Buttons
        btn_row = QHBoxLayout()
        self.chk_pt = QCheckBox('Kèm cáp DƯL — tự nhận từ layer PT-<LOC>-<N>')
        self.chk_pt.setChecked(True)
        self.chk_pt.setToolTip(
            'Khi tick: scan DXF layers PT-TOP-N / PT-BOT-N / PT-WEB-L-N / PT-WEB-R-N\n'
            'và sinh block *TDN-PROPERTY / *TDN-PROFILE / *TDN-PRESTRESS.\n'
            'Bỏ tick: bỏ qua PT, MCT chỉ chứa khung không cáp.')
        btn_row.addWidget(self.chk_pt)
        btn_row.addStretch()
        self.btn_clear = QPushButton('Xóa danh sách')
        self.btn_clear.clicked.connect(self._clear)
        btn_row.addWidget(self.btn_clear)
        self.btn_generate = QPushButton('Tạo MCT')
        self.btn_generate.setProperty('primary', True)
        self.btn_generate.clicked.connect(self._generate)
        btn_row.addWidget(self.btn_generate)
        layout.addLayout(btn_row)

        # Log + SVG preview
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.log_area = LogView()
        splitter.addWidget(self.log_area)

        # SVG preview - try QSvgWidget, fallback to QLabel
        try:
            from PyQt6.QtSvgWidgets import QSvgWidget
            self._svg_widget = QSvgWidget()
            splitter.addWidget(self._svg_widget)
        except ImportError:
            lbl = QLabel('Chưa xem được hình mặt cắt\n(thiếu gói PyQt6-QSvgWidgets)')
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            splitter.addWidget(lbl)

        splitter.setSizes([500, 400])
        layout.addWidget(splitter, 1)

    # API công khai cho menu/toolbar
    def browse_files(self): self._browse_files()
    def browse_excel(self): self._browse_excel()
    def generate(self): self._generate()
    def clear(self): self._clear()

    def _browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, 'Chọn file DXF', '.', 'File DXF (*.dxf)')
        if files:
            for f in files:
                if not self._in_list(f):
                    self.file_list.addItem(f)
            self.dxf_edit.setText(f'{self.file_list.count()} file đã chọn')

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Chọn thư mục chứa DXF', '.')
        if folder:
            dxf_files = sorted(glob.glob(os.path.join(folder, '*.dxf')))
            for f in dxf_files:
                if not self._in_list(f):
                    self.file_list.addItem(f)
            self.dxf_edit.setText(f'{self.file_list.count()} file đã chọn')

    def _browse_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Chọn template số liệu', '.',
            'File Excel (*.xls *.xlsx);;Tất cả (*)')
        if path:
            self.excel_edit.setText(path)

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, 'Chọn thư mục kết quả', self.out_edit.text())
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
            self.status_bar.showMessage('Chưa chọn file DXF nào.')
            return

        excel_path = self.excel_edit.text().strip() or None
        output_dir = self.out_edit.text() or 'output'
        # None = auto-detect (only generate PT block if DXF has PT-* layers)
        # False = explicitly skip PT
        include_pt = None if self.chk_pt.isChecked() else False
        self.btn_generate.setEnabled(False)
        self.log_area.clear()
        self.status_bar.showMessage(f'Đang tạo {len(dxf_paths)} mặt cắt…')

        self.worker = GenerateWorker(dxf_paths, output_dir, excel_path,
                                     include_pt=include_pt)
        self.worker.log.connect(self._on_log)
        self._total = len(dxf_paths)
        self._done = 0
        self.progress_changed.emit(0, self._total)
        self.worker.section_done.connect(self._on_section_done)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.start()

    def _on_log(self, msg):
        self.log_area.append_auto(msg)

    def _on_section_done(self, name, svg_path):
        self._done += 1
        self.progress_changed.emit(self._done, self._total)
        self.status_bar.showMessage(f'Đã tạo: {name}')
        if self._svg_widget and svg_path and os.path.exists(svg_path):
            self._svg_widget.load(svg_path)

    def _on_finished(self, count):
        self.btn_generate.setEnabled(True)
        self.progress_changed.emit(count, max(count, getattr(self, '_total', count)))
        self.status_bar.showMessage(
            f'Xong: {count} mặt cắt — {self.log_area.summary()}')
        self.log_area.success(f'Hoàn tất {count} mặt cắt')

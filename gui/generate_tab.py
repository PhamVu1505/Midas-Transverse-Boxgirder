"""Tab Tạo mô hình — DXF → MCT + SVG.

Danh sách mặt cắt không còn nằm ở đây nữa mà do panel Project bên trái giữ
(`gui/project_panel.py`), nên hai tab dùng chung một nguồn sự thật.
"""

import os

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLineEdit, QLabel, QFileDialog, QSplitter,
                             QCheckBox, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal

from src.project import Project
from .worker import GenerateWorker
from .widgets import LogView
from .theme import LIGHT, FONT_MONO


class GenerateTab(QWidget):
    progress_changed = pyqtSignal(int, int)   # done, total
    project_changed = pyqtSignal()

    def __init__(self, status_bar, project: Project = None, theme: dict = None):
        super().__init__()
        self.status_bar = status_bar
        self.project = project if project is not None else Project()
        self.t = theme or LIGHT
        self.worker = None
        self._svg_widget = None
        self._total = self._done = 0
        self._init_ui()

    # ─────────────────────────────────────────
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Template chung của project
        row = QHBoxLayout()
        row.addWidget(QLabel('Template số liệu (chung):'))
        self.excel_edit = QLineEdit()
        self.excel_edit.setPlaceholderText(
            'Chọn file Excel có sheet INPUT — mặt cắt riêng có thể gán template khác…')
        self.excel_edit.setReadOnly(True)
        row.addWidget(self.excel_edit, 1)
        b = QPushButton('Duyệt…')
        b.clicked.connect(self._browse_excel)
        row.addWidget(b)
        layout.addLayout(row)

        # Thư mục kết quả
        row = QHBoxLayout()
        row.addWidget(QLabel('Thư mục kết quả:'))
        self.out_edit = QLineEdit(self.project.output_dir)
        self.out_edit.textChanged.connect(self._on_out_changed)
        row.addWidget(self.out_edit, 1)
        b = QPushButton('Duyệt…')
        b.clicked.connect(self._browse_output)
        row.addWidget(b)
        layout.addLayout(row)

        # Tuỳ chọn + nút chạy
        row = QHBoxLayout()
        self.chk_pt = QCheckBox('Kèm cáp DƯL — tự nhận từ layer PT-<LOC>-<N>')
        self.chk_pt.setChecked(True)
        self.chk_pt.setToolTip(
            'Khi tick: quét layer PT-TOP-N / PT-BOT-N / PT-WEB-L-N / PT-WEB-R-N\n'
            'và sinh khối *TDN-PROPERTY / *TDN-PROFILE / *TDN-PRESTRESS.\n'
            'Bỏ tick: bỏ qua PT, MCT chỉ có khung không cáp.')
        row.addWidget(self.chk_pt)
        row.addStretch()
        self.lb_scope = QLabel('')
        self.lb_scope.setStyleSheet(
            f'color: {self.t["ink_3"]}; font-family: {FONT_MONO}; font-size: 8pt;')
        row.addWidget(self.lb_scope)
        self.btn_generate = QPushButton('Tạo MCT')
        self.btn_generate.setProperty('primary', True)
        self.btn_generate.clicked.connect(self._generate)
        row.addWidget(self.btn_generate)
        layout.addLayout(row)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f'color: {self.t["border_soft"]};')
        layout.addWidget(line)

        # Log + xem hình
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.log_area = LogView(theme=self.t)
        splitter.addWidget(self.log_area)
        try:
            from PyQt6.QtSvgWidgets import QSvgWidget
            self._svg_widget = QSvgWidget()
            splitter.addWidget(self._svg_widget)
        except ImportError:
            lbl = QLabel('Chưa xem được hình mặt cắt\n(thiếu gói PyQt6-QSvgWidgets)')
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            splitter.addWidget(lbl)
        splitter.setSizes([560, 420])
        layout.addWidget(splitter, 1)

        self.refresh()

    # ─────────────────────────────────────────
    # API công khai cho menu/toolbar/panel
    # ─────────────────────────────────────────
    def set_project(self, project: Project):
        self.project = project
        self.excel_edit.setText(project.template)
        self.out_edit.setText(project.output_dir)
        self.refresh()

    def browse_excel(self):
        self._browse_excel()

    def generate(self, names=None):
        self._generate(names)

    def clear(self):
        self.log_area.clear()

    def refresh(self):
        """Cập nhật dòng tóm tắt phạm vi sẽ chạy."""
        n = len(self.project)
        if not n:
            self.lb_scope.setText('chưa có mặt cắt nào')
        else:
            n_tpl = sum(1 for s in self.project if s.template)
            txt = f'{n} mặt cắt'
            if n_tpl:
                txt += f' · {n_tpl} dùng template riêng'
            self.lb_scope.setText(txt)
        self.btn_generate.setEnabled(n > 0 and self.worker is None)

    def show_section(self, name):
        """Panel chọn mặt cắt nào thì xem hình mặt cắt đó."""
        sec = self.project.find(name)
        if not sec or not self._svg_widget:
            return
        svg = os.path.join(self.project.output_dir, name, f'{name}_frame.svg')
        if os.path.exists(svg):
            self._svg_widget.load(svg)

    # ─────────────────────────────────────────
    def _browse_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Chọn template số liệu', '.',
            'File Excel (*.xls *.xlsx);;Tất cả (*)')
        if path:
            self.excel_edit.setText(path)
            self.project.template = path
            self.project.touch()
            self.project_changed.emit()

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(
            self, 'Chọn thư mục kết quả', self.out_edit.text() or '.')
        if folder:
            self.out_edit.setText(folder)

    def _on_out_changed(self, text):
        if self.project.output_dir != text:
            self.project.output_dir = text
            self.project.touch()

    # ─────────────────────────────────────────
    def _generate(self, names=None):
        if self.worker is not None:
            return
        secs = ([self.project.find(n) for n in names] if names
                else list(self.project))
        secs = [s for s in secs if s]
        if not secs:
            self.status_bar.showMessage(
                'Chưa có mặt cắt nào — thêm DXF ở panel bên trái.')
            return

        include_pt = self.chk_pt.isChecked()
        jobs = [{'name': s.name, 'dxf': s.dxf,
                 'excel': self.project.template_for(s),
                 'include_pt': include_pt and s.include_pt}
                for s in secs]

        self.btn_generate.setEnabled(False)
        self.log_area.clear()
        self._total, self._done = len(jobs), 0
        self.progress_changed.emit(0, self._total)
        self.status_bar.showMessage(f'Đang tạo {self._total} mặt cắt…')

        self.worker = GenerateWorker(jobs, self.project.output_dir or 'output')
        self.worker.log.connect(self.log_area.append_auto)
        self.worker.section_info.connect(self._on_info)
        self.worker.section_error.connect(self._on_error)
        self.worker.section_done.connect(self._on_done)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.start()

    def _on_info(self, name, info):
        self.project.record_generated(
            name, info['mct'], info['topo'], info['section_type'],
            info['n_nodes'], info['n_elems'], info.get('pt_cables'))
        self.project_changed.emit()

    def _on_error(self, name, msg):
        self.project.record_error(name, msg)
        self.project_changed.emit()

    def _on_done(self, name, svg_path):
        self._done += 1
        self.progress_changed.emit(self._done, self._total)
        self.status_bar.showMessage(f'Đã tạo: {name}')
        if self._svg_widget and svg_path and os.path.exists(svg_path):
            self._svg_widget.load(svg_path)

    def _on_finished(self, count):
        self.worker = None
        self.progress_changed.emit(count, max(count, self._total))
        self.status_bar.showMessage(
            f'Xong: {count}/{self._total} mặt cắt — {self.log_area.summary()}')
        self.log_area.success(f'Hoàn tất {count}/{self._total} mặt cắt')
        self.refresh()
        self.project_changed.emit()

"""Tab Tạo mô hình — DXF → MCT + SVG.

Danh sách mặt cắt không còn nằm ở đây nữa mà do panel Project bên trái giữ
(`gui/project_panel.py`), nên hai tab dùng chung một nguồn sự thật.
"""

import os

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLineEdit, QLabel, QFileDialog, QSplitter,
                             QCheckBox, QFrame, QToolButton, QButtonGroup,
                             QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal

from src.project import Project
from .worker import GenerateWorker
from .widgets import LogView
from .frame_view import FrameView, DEFAULT_LAYERS, MODEL, SHAPE, PARTS
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
        self._total = self._done = 0
        self._current = ''
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

        # Log + khung xem mặt cắt
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.log_area = LogView(theme=self.t)
        splitter.addWidget(self.log_area)
        splitter.addWidget(self._build_viewer())
        splitter.setSizes([470, 640])
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        self.refresh()

    def _build_viewer(self):
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        bar = QWidget()
        bar.setStyleSheet(f'background: {self.t["panel_alt"]};'
                          f' border-bottom: 1px solid {self.t["border"]};')
        h = QHBoxLayout(bar)
        h.setContentsMargins(6, 4, 6, 4)
        h.setSpacing(3)

        self.mode_group = QButtonGroup(self)
        SHAPE_TIP = ('Mặt cắt Midas sẽ dựng — dải vuốt côn theo offset CT/CB/CC, '
                     'chồng lên biên bê tông thật để thấy chỗ lệch')
        for key, label, tip in ((MODEL, 'Model', 'Khung và cách chia phần tử'),
                                (SHAPE, 'Section shape', SHAPE_TIP),
                                (PARTS, 'Parts', 'Tô theo bộ phận — soi frame builder')):
            b = QToolButton()
            b.setText(label)
            b.setCheckable(True)
            b.setToolTip(tip)
            b.setChecked(key == MODEL)
            b.clicked.connect(lambda _=False, k=key: self.view.set_mode(k))
            self.mode_group.addButton(b)
            h.addWidget(b)

        h.addSpacing(10)
        for name, label in (('nodes', 'Node'), ('ids', 'Số node'),
                            ('eids', 'Số phần tử'), ('supports', 'Gối'),
                            ('pt', 'PT'), ('dims', 'Kích thước'), ('grid', 'Lưới')):
            c = QCheckBox(label)
            c.setChecked(DEFAULT_LAYERS.get(name, True))
            c.setStyleSheet('font-size: 8pt;')
            c.toggled.connect(lambda on, n=name: self.view.set_layer(n, on))
            h.addWidget(c)

        h.addStretch()
        self.btn_sup = QToolButton()
        self.btn_sup.setText('Sửa gối')
        self.btn_sup.setCheckable(True)
        self.btn_sup.setToolTip('Bấm node đáy để đặt gối · kéo tam giác để dời · '
                                'chuột phải để xóa')
        self.btn_sup.toggled.connect(self._toggle_supports)
        h.addWidget(self.btn_sup)
        h.addSpacing(8)
        for label, tip, fn in (('−', 'Thu nhỏ', lambda: self.view.zoom_by(1 / 1.25)),
                               ('+', 'Phóng to', lambda: self.view.zoom_by(1.25)),
                               ('⤢', 'Vừa khung (F)', lambda: self.view.fit())):
            b = QToolButton()
            b.setText(label)
            b.setToolTip(tip)
            b.setFixedWidth(26)
            b.clicked.connect(fn)
            h.addWidget(b)
        v.addWidget(bar)

        self.view = FrameView(theme=self.t)
        self.view.node_hovered.connect(self._on_hover)
        self.view.supports_changed.connect(self._on_supports_changed)
        v.addWidget(self.view, 1)

        self.sup_bar = QWidget()
        self.sup_bar.setVisible(False)
        self.sup_bar.setStyleSheet(
            f'background: {self.t["accent_soft"]};'
            f' border-top: 1px solid {self.t["accent_line"]};')
        self.sup_lay = QHBoxLayout(self.sup_bar)
        self.sup_lay.setContentsMargins(8, 5, 8, 5)
        self.sup_lay.setSpacing(6)
        v.addWidget(self.sup_bar)

        self.lb_query = QLabel('Rê chuột lên mặt cắt để tra node')
        self.lb_query.setStyleSheet(
            f'color: {self.t["ink_2"]}; font-family: {FONT_MONO}; font-size: 8pt;'
            f' padding: 5px 10px; background: {self.t["panel_alt"]};'
            f' border-top: 1px solid {self.t["border"]};')
        v.addWidget(self.lb_query)
        return box

    # ── sửa gối ──
    def _toggle_supports(self, on):
        self.view.set_edit_supports(on)
        self.sup_bar.setVisible(on)
        if on:
            self._rebuild_sup_bar()
            self.lb_query.setText(
                'Bấm node đáy để đặt gối · kéo tam giác để dời · chuột phải để xóa')

    def _on_supports_changed(self, supports):
        name = self._current
        if name:
            self.project.set_supports(name, supports)
            self.project_changed.emit()
        self._rebuild_sup_bar()

    def _rebuild_sup_bar(self):
        while self.sup_lay.count():
            it = self.sup_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        sups = self.view.supports
        if not sups:
            lb = QLabel('Chưa đặt gối — dùng bộ mặc định khi tạo MCT')
            lb.setStyleSheet(f'color: {self.t["ink_2"]}; font-size: 8pt;')
            self.sup_lay.addWidget(lb)
            self.sup_lay.addStretch()
            return
        for i, sp in enumerate(sups):
            nid = self.view._sup_node(sp)
            lb = QLabel(f'n{nid}  X={sp["x"]:+.3f}')
            lb.setStyleSheet(
                f'font-family: {FONT_MONO}; font-size: 8pt; color: {self.t["ink"]};')
            self.sup_lay.addWidget(lb)
            cb = QComboBox()
            cb.addItem('Gối cố định', 'pin')
            cb.addItem('Gối di động', 'roller')
            cb.addItem('Ngàm', 'fixed')
            cb.setCurrentIndex(['pin', 'roller', 'fixed'].index(sp['kind']))
            cb.setFixedWidth(112)
            cb.currentIndexChanged.connect(
                lambda k, idx=i: self._set_sup_kind(idx, k))
            self.sup_lay.addWidget(cb)
            if i < len(sups) - 1:
                self.sup_lay.addSpacing(10)
        self.sup_lay.addStretch()
        b = QToolButton()
        b.setText('Đặt lại mặc định')
        b.clicked.connect(self._reset_supports)
        self.sup_lay.addWidget(b)

    def _set_sup_kind(self, idx, k):
        kinds = ['pin', 'roller', 'fixed']
        if 0 <= idx < len(self.view.supports):
            self.view.supports[idx]['kind'] = kinds[k]
            self.view.update()
            self._on_supports_changed(self.view.supports)

    def _reset_supports(self):
        self.view.set_supports([])
        self._on_supports_changed([])

    def _on_hover(self, nid, info):
        if nid < 0:
            self.lb_query.setText(
                f'X {info["x"]:.3f}   Z {info["z"]:.3f}' if info
                else 'Rê chuột lên mặt cắt để tra node')
            return
        els = ', '.join(str(e) for e in info['elems']) or '—'
        self.lb_query.setText(
            f'Node {nid}   X {info["x"]:.4f}   Z {info["z"]:.4f}   '
            f't {info["t"]:.4f} m   {info["part"]} · offset {info["offset"]}   '
            f'phần tử {els}')

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
        """Nạp mô hình ĐÃ GHI RA MCT của mặt cắt đang chọn."""
        sec = self.project.find(name)
        if not sec:
            return
        topo = sec.topo or os.path.join(
            self.project.output_dir, name, f'{name}_topo.json')
        self._current = name
        if os.path.exists(topo) and self.view.load_topo(topo):
            self.view.set_supports(sec.supports)
            self._rebuild_sup_bar()
            st = self.view.stats()
            self.status_bar.showMessage(
                f'{name}: {st["type"]} · {st["nodes"]} node · {st["elems"]} phần tử'
                f' · H {st["H"]:.3f} m · B {st["B"]:.3f} m')
        else:
            self.view.clear()

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
                 'include_pt': include_pt and s.include_pt,
                 'supports': list(s.supports)}
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
        self.show_section(name)

    def _on_finished(self, count):
        self.worker = None
        self.progress_changed.emit(count, max(count, self._total))
        self.status_bar.showMessage(
            f'Xong: {count}/{self._total} mặt cắt — {self.log_area.summary()}')
        self.log_area.success(f'Hoàn tất {count}/{self._total} mặt cắt')
        self.refresh()
        self.project_changed.emit()

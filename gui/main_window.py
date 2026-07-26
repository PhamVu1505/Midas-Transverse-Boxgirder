"""Cửa sổ chính: menu bar, toolbar, thanh bước quy trình, status bar."""

import os
import webbrowser

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QStatusBar, QLabel,
                             QProgressBar, QWidget, QVBoxLayout, QToolBar,
                             QMessageBox, QFrame)

from .generate_tab import GenerateTab
from .results_tab import ResultsTab
from .icons import icon
from .theme import LIGHT, FONT_MONO, SIZE
from .widgets import StepBar, ACTIVE, DONE, IDLE

VERSION = 'v1.3.0'
APP_NAME = 'Midas Transverse Boxgirder'


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.t = LIGHT
        self.setWindowTitle(f'{APP_NAME} {VERSION} — Phân tích khung ngang dầm hộp')
        self.resize(1240, 840)
        self.setMinimumSize(980, 660)

        self._build_status()
        self._build_central()
        self._build_menu()
        self._build_toolbar()

        self.status_msg('Sẵn sàng')

    # ─────────────────────────────────────────────
    # Vùng trung tâm: thanh bước + tabs
    # ─────────────────────────────────────────────
    def _build_central(self):
        root = QWidget()
        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.steps = StepBar(theme=self.t)
        lay.addWidget(self.steps)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.gen_tab = GenerateTab(self.status)
        self.res_tab = ResultsTab(self.status)
        self.tabs.addTab(self.gen_tab, 'Tạo mô hình  (DXF → MCT)')
        self.tabs.addTab(self.res_tab, 'Kiểm toán  (Beam Force → Check)')
        self.tabs.currentChanged.connect(self._on_tab)
        lay.addWidget(self.tabs, 1)

        self.setCentralWidget(root)

        # Tab tự báo tiến độ về thanh bước và status bar nếu hỗ trợ
        for tab, hook in ((self.gen_tab, self._on_generate_progress),
                          (self.res_tab, self._on_results_progress)):
            if hasattr(tab, 'progress_changed'):
                tab.progress_changed.connect(hook)

        self.steps.set_state(0, ACTIVE)

    # ─────────────────────────────────────────────
    # Status bar
    # ─────────────────────────────────────────────
    def _build_status(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.lb_msg = QLabel('Sẵn sàng')
        self.lb_msg.setStyleSheet(f'color: {self.t["ok"]}; font-weight: 600;')
        self.status.addWidget(self.lb_msg)

        self.lb_detail = QLabel('')
        self.status.addWidget(self.lb_detail, 1)

        self.prog = QProgressBar()
        self.prog.setFixedWidth(120)
        self.prog.setTextVisible(False)
        self.prog.setVisible(False)
        self.status.addPermanentWidget(self.prog)

        self.lb_count = QLabel('—')
        self.lb_count.setStyleSheet(
            f'font-family: {FONT_MONO}; color: {self.t["ink_2"]};')
        self.status.addPermanentWidget(self._sep())
        self.status.addPermanentWidget(self.lb_count)

        self.lb_units = QLabel('kN, m')
        self.lb_units.setStyleSheet(
            f'font-family: {FONT_MONO}; color: {self.t["ink_2"]};')
        self.lb_units.setToolTip('Hệ đơn vị của mô hình MCT xuất ra')
        self.status.addPermanentWidget(self._sep())
        self.status.addPermanentWidget(self.lb_units)

        self.status.addPermanentWidget(self._sep())
        lb_ver = QLabel(VERSION)
        lb_ver.setStyleSheet(
            f'font-family: {FONT_MONO}; color: {self.t["ink_3"]};')
        self.status.addPermanentWidget(lb_ver)

        # QStatusBar.showMessage() từ các tab cũ vẫn chạy, chuyển vào lb_detail
        self.status.messageChanged.connect(self._on_status_message)

    def _sep(self):
        f = QFrame()
        f.setFrameShape(QFrame.Shape.VLine)
        f.setStyleSheet(f'color: {self.t["border"]};')
        f.setFixedHeight(14)
        return f

    def _on_status_message(self, text):
        if text:
            self.lb_detail.setText(text)

    def status_msg(self, text, level='ok'):
        col = {'ok': self.t['ok'], 'warn': self.t['warn'],
               'err': self.t['err'], 'busy': self.t['accent']}[level]
        self.lb_msg.setText(text)
        self.lb_msg.setStyleSheet(f'color: {col}; font-weight: 600;')

    def set_counts(self, text):
        self.lb_count.setText(text)

    def set_progress(self, done, total):
        if total <= 0:
            self.prog.setVisible(False)
            return
        self.prog.setVisible(True)
        self.prog.setMaximum(total)
        self.prog.setValue(done)
        if done >= total:
            self.prog.setVisible(False)

    # ─────────────────────────────────────────────
    # Menu
    # ─────────────────────────────────────────────
    def _act(self, text, slot, shortcut=None, ic=None, tip=None):
        a = QAction(text, self)
        if ic:
            a.setIcon(icon(ic, theme=self.t))
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        if tip:
            a.setStatusTip(tip)
        a.triggered.connect(slot)
        return a

    def _build_menu(self):
        mb = self.menuBar()

        m = mb.addMenu('&Tệp')
        self.a_dxf = self._act('Thêm &DXF…', self._add_dxf, 'Ctrl+O', 'add',
                               'Chọn file DXF mặt cắt')
        self.a_tpl = self._act('Chọn &template số liệu…', self._pick_template,
                               'Ctrl+T', 'template',
                               'Chọn file Excel chứa sheet INPUT')
        m.addAction(self.a_dxf)
        m.addAction(self.a_tpl)
        m.addSeparator()
        m.addAction(self._act('&Mở thư mục kết quả', self._open_output,
                              'Ctrl+Shift+O', 'folder'))
        m.addSeparator()
        m.addAction(self._act('T&hoát', self.close, 'Alt+F4'))

        m = mb.addMenu('&Mô hình')
        self.a_gen = self._act('&Tạo MCT', self._generate, 'F5', 'generate',
                               'Sinh file MCT cho toàn bộ mặt cắt đã chọn')
        m.addAction(self.a_gen)
        m.addAction(self._act('&Xóa danh sách', self._clear, 'Ctrl+L', 'clear'))

        m = mb.addMenu('&Kết quả')
        self.a_run = self._act('&Xử lý Beam Force', self._process, 'F6', 'check')
        m.addAction(self.a_run)

        m = mb.addMenu('&Công cụ')
        m.addAction(self._act('Kiểm tra &template số liệu…', self._check_template,
                              None, 'info',
                              'Đọc thử Excel và liệt kê 40 khóa đầu vào'))

        m = mb.addMenu('Trợ &giúp')
        m.addAction(self._act('&Hướng dẫn sử dụng', self._open_guide, 'F1'))
        m.addAction(self._act('&Giới thiệu', self._about))

    # ─────────────────────────────────────────────
    # Toolbar
    # ─────────────────────────────────────────────
    def _build_toolbar(self):
        tb = QToolBar('Chính')
        tb.setMovable(False)
        tb.setIconSize(QSize(17, 17))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        tb.addAction(self.a_dxf)
        tb.addAction(self.a_tpl)
        tb.addSeparator()
        tb.addAction(self.a_gen)
        tb.addSeparator()
        tb.addAction(self.a_run)
        tb.addSeparator()
        tb.addAction(self._act('Mở thư mục kết quả', self._open_output,
                               None, 'folder'))

        # nút chính nổi bật
        for act in (self.a_gen,):
            w = tb.widgetForAction(act)
            if w:
                w.setStyleSheet(
                    f'QToolButton {{ background: {self.t["accent"]};'
                    f' color: {self.t["on_accent"]}; font-weight: 600;'
                    f' border: 1px solid {self.t["accent"]};'
                    f' border-radius: 3px; padding: 5px 12px; }}'
                    f'QToolButton:hover {{ background: #17538B; }}')

    # ─────────────────────────────────────────────
    # Hành động — ủy quyền về tab tương ứng
    # ─────────────────────────────────────────────
    def _tab_call(self, tab, *names):
        """Gọi method đầu tiên tồn tại trên tab."""
        for n in names:
            fn = getattr(tab, n, None)
            if callable(fn):
                fn()
                return True
        return False

    def _add_dxf(self):
        self.tabs.setCurrentIndex(0)
        self._tab_call(self.gen_tab, 'browse_files', '_browse_files')

    def _pick_template(self):
        self.tabs.setCurrentIndex(0)
        self._tab_call(self.gen_tab, 'browse_excel', '_browse_excel')

    def _generate(self):
        self.tabs.setCurrentIndex(0)
        self._tab_call(self.gen_tab, 'generate', '_generate')

    def _clear(self):
        tab = self.tabs.currentWidget()
        self._tab_call(tab, 'clear', '_clear')

    def _process(self):
        self.tabs.setCurrentIndex(1)
        self._tab_call(self.res_tab, 'process', '_process')

    def _open_output(self):
        tab = self.tabs.currentWidget()
        if self._tab_call(tab, 'open_folder', '_open_folder'):
            return
        edit = getattr(tab, 'out_edit', None)
        path = edit.text() if edit else '.'
        if os.path.isdir(path):
            os.startfile(path)

    def _check_template(self):
        """Đọc thử template và hiện bảng 40 khóa — bắt lỗi trước khi tạo MCT."""
        edit = getattr(self.gen_tab, 'excel_edit', None)
        path = edit.text().strip() if edit else ''
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, 'Chưa có template',
                                'Chọn file Excel số liệu trước '
                                '(Tệp → Chọn template số liệu).')
            return
        try:
            from src.input_reader import describe, crosscheck
            text = describe(path)
            bad = crosscheck(path)
            if bad:
                text += ('\n\nCẢNH BÁO — giá trị trên sheet INPUT lệch so với ô gốc '
                         '(công thức có thể đã bị dán thành số cứng):\n')
                text += '\n'.join(
                    f'  {k}: INPUT={a:g}, ô gốc {addr}={b:g}' for k, a, b, addr in bad)
        except Exception as e:
            text = f'Không đọc được:\n{e}'

        box = QMessageBox(self)
        box.setWindowTitle('Số liệu đầu vào')
        box.setText('Kết quả đọc template:')
        box.setDetailedText(text)
        box.setIcon(QMessageBox.Icon.Information)
        box.exec()

    def _open_guide(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for rel in ('docs/USER-GUIDE.txt', 'README.md'):
            p = os.path.join(base, rel)
            if os.path.exists(p):
                webbrowser.open(p)
                return
        QMessageBox.information(self, 'Hướng dẫn', 'Chưa có tài liệu đi kèm.')

    def _about(self):
        QMessageBox.about(
            self, f'Giới thiệu {APP_NAME}',
            f'<b>{APP_NAME}</b> {VERSION}<br><br>'
            'Phân tích khung ngang dầm hộp BTCT dự ứng lực.<br>'
            'Cầu Lạch Tray — Cao tốc Hà Nội – Hải Phòng (EX-10).<br><br>'
            '<span style="color:#667085">Quy trình: DXF → MCT → Midas/Civil → '
            'Beam Force → Bảng kiểm toán</span>')

    # ─────────────────────────────────────────────
    # Đồng bộ thanh bước
    # ─────────────────────────────────────────────
    def _on_tab(self, idx):
        if idx == 0 and self.steps.state[1] != DONE:
            self.steps.set_state(0, ACTIVE)
        elif idx == 1:
            self.steps.set_state(3, ACTIVE)

    def _on_generate_progress(self, done, total):
        self.set_progress(done, total)
        if total:
            self.steps.set_state(0, DONE, f'{total} file')
            self.steps.set_state(1, DONE if done >= total else ACTIVE,
                                 f'{done}/{total}')
            if done >= total:
                self.steps.set_state(2, ACTIVE)
            self.set_counts(f'{done}/{total} mặt cắt')

    def _on_results_progress(self, done, total):
        self.set_progress(done, total)
        if total:
            # có kết quả nghĩa là đã chạy xong Midas
            self.steps.set_state(2, DONE)
            self.steps.set_state(3, DONE if done >= total else ACTIVE,
                                 f'{done}/{total}')
            if done >= total:
                self.steps.set_state(4, DONE)

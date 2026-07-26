"""Cửa sổ chính: dock project, menu, toolbar, thanh bước, status bar."""

import os
import webbrowser

from PyQt6.QtCore import Qt, QSize, QSettings
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QStatusBar, QLabel,
                             QProgressBar, QWidget, QVBoxLayout, QToolBar,
                             QMessageBox, QFrame, QDockWidget, QFileDialog,
                             QDialog, QHBoxLayout, QPushButton)

from src.project import Project, FILE_EXT, CHECKED, ERROR
from .generate_tab import GenerateTab
from .results_tab import ResultsTab
from .project_panel import ProjectPanel
from .icons import icon
from .theme import LIGHT, FONT_MONO
from .widgets import StepBar, ACTIVE, DONE
from . import assets

VERSION = 'v1.3.0'
APP_NAME = 'Midas Transverse Boxgirder'
ORG, APP = 'TEDI', 'MidasTransverseBoxgirder'
MAX_RECENT = 8


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.t = LIGHT
        self.settings = QSettings(ORG, APP)
        self.project = Project()

        self.setWindowIcon(assets.app_icon())
        self.resize(1320, 860)
        self.setMinimumSize(1040, 680)

        self._build_status()
        self._build_central()
        self._build_dock()
        self._build_menu()
        self._build_toolbar()
        self._connect()

        self._restore_settings()
        self._update_title()
        self.status_msg('Sẵn sàng')

    # ─────────────────────────────────────────
    # Dựng giao diện
    # ─────────────────────────────────────────
    def _build_central(self):
        root = QWidget()
        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.steps = StepBar(theme=self.t)
        lay.addWidget(self.steps)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.gen_tab = GenerateTab(self.status, self.project, self.t)
        self.res_tab = ResultsTab(self.status, self.project, self.t)
        self.tabs.addTab(self.gen_tab, 'Tạo mô hình  (DXF → MCT)')
        self.tabs.addTab(self.res_tab, 'Kiểm toán  (Beam Force → Check)')
        self.tabs.currentChanged.connect(self._on_tab)
        lay.addWidget(self.tabs, 1)

        self.setCentralWidget(root)
        self.steps.set_state(0, ACTIVE)

    def _build_dock(self):
        self.panel = ProjectPanel(self.project, self.t)
        dock = QDockWidget('Project', self)
        dock.setObjectName('projectDock')
        dock.setWidget(self.panel)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable
                         | QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        dock.setMinimumWidth(230)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self.dock = dock

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

        mono = f'font-family: {FONT_MONO}; color: {self.t["ink_2"]};'
        self.lb_count = QLabel('—')
        self.lb_count.setStyleSheet(mono)
        self.status.addPermanentWidget(self._sep())
        self.status.addPermanentWidget(self.lb_count)

        self.lb_units = QLabel('kN, m')
        self.lb_units.setStyleSheet(mono)
        self.lb_units.setToolTip('Hệ đơn vị của mô hình MCT xuất ra')
        self.status.addPermanentWidget(self._sep())
        self.status.addPermanentWidget(self.lb_units)

        self.status.addPermanentWidget(self._sep())
        lb_ver = QLabel(VERSION)
        lb_ver.setStyleSheet(f'font-family: {FONT_MONO}; color: {self.t["ink_3"]};')
        self.status.addPermanentWidget(lb_ver)

        self.status.messageChanged.connect(
            lambda s: self.lb_detail.setText(s) if s else None)

    def _sep(self):
        f = QFrame()
        f.setFrameShape(QFrame.Shape.VLine)
        f.setStyleSheet(f'color: {self.t["border"]};')
        f.setFixedHeight(14)
        return f

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
        m.addAction(self._act('Project &mới', self.new_project, 'Ctrl+N', 'new'))
        m.addAction(self._act('&Mở project…', self.open_project, 'Ctrl+Shift+O', 'open'))
        self.a_save = self._act('&Lưu project', self.save_project, 'Ctrl+S', 'save')
        m.addAction(self.a_save)
        m.addAction(self._act('Lưu project &thành…', self.save_project_as, 'Ctrl+Shift+S'))
        self.recent_menu = m.addMenu('Project &gần đây')
        m.addSeparator()
        self.a_dxf = self._act('Thêm &DXF…', self.panel_add_dxf, 'Ctrl+O', 'add',
                               'Thêm mặt cắt DXF vào project')
        self.a_dxf_dir = self._act('Thêm cả thư &mục DXF…', self.panel_add_folder,
                                   None, 'folder')
        self.a_tpl = self._act('Chọn &template số liệu…', self.pick_template,
                               'Ctrl+T', 'template',
                               'Template chung; từng mặt cắt có thể gán riêng')
        m.addAction(self.a_dxf)
        m.addAction(self.a_dxf_dir)
        m.addAction(self.a_tpl)
        m.addSeparator()
        m.addAction(self._act('Mở thư mục &kết quả', self.open_output, None, 'folder'))
        m.addSeparator()
        m.addAction(self._act('T&hoát', self.close, 'Alt+F4'))

        m = mb.addMenu('&Mô hình')
        self.a_gen = self._act('&Tạo MCT toàn bộ', self.generate_all, 'F5', 'generate')
        self.a_gen_sel = self._act('Tạo MCT cho mặt cắt &đang chọn',
                                   self.generate_selected, 'Shift+F5')
        m.addAction(self.a_gen)
        m.addAction(self.a_gen_sel)
        m.addSeparator()
        m.addAction(self._act('&Xóa nhật ký', self.clear_log, 'Ctrl+L', 'clear'))

        m = mb.addMenu('&Kết quả')
        self.a_bf = self._act('&Gán file Beam Force…', self.assign_bf, 'Ctrl+B', 'load')
        self.a_run = self._act('&Xử lý Beam Force', self.process_results, 'F6', 'check')
        m.addAction(self.a_bf)
        m.addAction(self.a_run)

        m = mb.addMenu('&Công cụ')
        m.addAction(self._act('Kiểm tra &template số liệu…', self.check_template,
                              None, 'info',
                              'Đọc thử Excel, liệt kê 40 khóa và đối chiếu ô gốc'))

        m = mb.addMenu('Trợ &giúp')
        m.addAction(self._act('&Hướng dẫn sử dụng', self.open_guide, 'F1'))
        m.addAction(self._act('&Giới thiệu', self.about))

        self._refresh_recent()

    def _build_toolbar(self):
        tb = QToolBar('Chính')
        tb.setObjectName('mainToolbar')
        tb.setMovable(False)
        tb.setIconSize(QSize(17, 17))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        for a in (self.a_dxf, self.a_tpl):
            tb.addAction(a)
        tb.addSeparator()
        tb.addAction(self.a_gen)
        tb.addSeparator()
        tb.addAction(self.a_bf)
        tb.addAction(self.a_run)

        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy().Expanding,
                             spacer.sizePolicy().verticalPolicy().Preferred)
        tb.addWidget(spacer)

        # Dấu hiệu TEDI ở mép phải — badge đơn vị, không phải nút bấm
        badge = QLabel()
        badge.setPixmap(assets.tedi_mark(22))
        badge.setToolTip('Tổng công ty Tư vấn thiết kế Giao thông vận tải — TEDI')
        badge.setStyleSheet('padding: 0 10px 0 4px;')
        tb.addWidget(badge)

        w = tb.widgetForAction(self.a_gen)
        if w:
            w.setStyleSheet(
                f'QToolButton {{ background: {self.t["accent"]};'
                f' color: {self.t["on_accent"]}; font-weight: 600;'
                f' border: 1px solid {self.t["accent"]};'
                f' border-radius: 3px; padding: 5px 12px; }}'
                f'QToolButton:hover {{ background: #17538B; }}')

    def _connect(self):
        self.panel.section_selected.connect(self.gen_tab.show_section)
        self.panel.generate_requested.connect(self.gen_tab.generate)
        self.panel.project_changed.connect(self._on_project_changed)
        for tab in (self.gen_tab, self.res_tab):
            tab.project_changed.connect(self._on_project_changed)
        self.gen_tab.progress_changed.connect(self._on_generate_progress)
        self.res_tab.progress_changed.connect(self._on_results_progress)

    # ─────────────────────────────────────────
    # Project
    # ─────────────────────────────────────────
    def _apply_project(self, project: Project):
        self.project = project
        self.panel.set_project(project)
        self.gen_tab.set_project(project)
        self.res_tab.set_project(project)
        self._on_project_changed()
        self.steps.reset()
        self.steps.set_state(0, DONE if len(project) else ACTIVE,
                             f'{len(project)} file' if len(project) else '')

    def _on_project_changed(self):
        self.panel.refresh()
        self.gen_tab.refresh()
        self.res_tab.refresh()
        self._update_title()
        n = len(self.project)
        self.lb_count.setText(
            f'{n} mặt cắt · {self.project.total_elements} phần tử' if n else '—')

    def _update_title(self):
        mark = ' •' if self.project.dirty else ''
        self.setWindowTitle(
            f'{self.project.title}{mark} — {APP_NAME} {VERSION}')

    def new_project(self):
        if not self._confirm_discard():
            return
        self._apply_project(Project())
        self.status_msg('Project mới')

    def open_project(self, path=None):
        if not self._confirm_discard():
            return
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, 'Mở project', '.', f'Project (*{FILE_EXT});;Tất cả (*)')
        if not path:
            return
        try:
            p = Project.load(path)
            p.refresh_status()
        except Exception as e:
            QMessageBox.critical(self, 'Không mở được project', str(e))
            return
        self._apply_project(p)
        self._push_recent(path)
        self.status_msg(f'Đã mở {os.path.basename(path)}')

    def save_project(self):
        if not self.project.path:
            return self.save_project_as()
        try:
            self.project.save()
        except Exception as e:
            QMessageBox.critical(self, 'Không lưu được', str(e))
            return False
        self._push_recent(self.project.path)
        self._update_title()
        self.status_msg('Đã lưu project')
        return True

    def save_project_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, 'Lưu project thành', self.project.title + FILE_EXT,
            f'Project (*{FILE_EXT})')
        if not path:
            return False
        try:
            self.project.save(path)
        except Exception as e:
            QMessageBox.critical(self, 'Không lưu được', str(e))
            return False
        self._push_recent(self.project.path)
        self._update_title()
        self.status_msg('Đã lưu project')
        return True

    def _confirm_discard(self) -> bool:
        if not self.project.dirty or not len(self.project):
            return True
        r = QMessageBox.question(
            self, 'Project chưa lưu',
            'Project hiện tại có thay đổi chưa lưu. Lưu lại trước khi tiếp tục?',
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Cancel:
            return False
        if r == QMessageBox.StandardButton.Save:
            return bool(self.save_project())
        return True

    # ── recent ──
    def _recent(self) -> list:
        return [p for p in (self.settings.value('recent', []) or [])
                if isinstance(p, str)]

    def _push_recent(self, path):
        r = [p for p in self._recent() if os.path.normpath(p) != os.path.normpath(path)]
        r.insert(0, path)
        self.settings.setValue('recent', r[:MAX_RECENT])
        self._refresh_recent()

    def _refresh_recent(self):
        self.recent_menu.clear()
        r = [p for p in self._recent() if os.path.exists(p)]
        if not r:
            a = QAction('(trống)', self)
            a.setEnabled(False)
            self.recent_menu.addAction(a)
            return
        for p in r:
            a = QAction(os.path.basename(p), self)
            a.setStatusTip(p)
            a.triggered.connect(lambda _=False, q=p: self.open_project(q))
            self.recent_menu.addAction(a)
        self.recent_menu.addSeparator()
        a = QAction('Xóa danh sách', self)
        a.triggered.connect(lambda: (self.settings.setValue('recent', []),
                                     self._refresh_recent()))
        self.recent_menu.addAction(a)

    # ─────────────────────────────────────────
    # Hành động
    # ─────────────────────────────────────────
    def panel_add_dxf(self):
        self.panel.add_dxf_dialog()

    def panel_add_folder(self):
        self.panel.add_folder_dialog()

    def pick_template(self):
        self.tabs.setCurrentIndex(0)
        self.gen_tab.browse_excel()

    def generate_all(self):
        self.tabs.setCurrentIndex(0)
        self.gen_tab.generate()

    def generate_selected(self):
        names = self.panel.selected_names()
        self.tabs.setCurrentIndex(0)
        self.gen_tab.generate(names or None)

    def clear_log(self):
        w = self.tabs.currentWidget()
        if hasattr(w, 'clear'):
            w.clear()

    def assign_bf(self):
        self.tabs.setCurrentIndex(1)
        self.res_tab._assign_bf_selected()

    def process_results(self):
        self.tabs.setCurrentIndex(1)
        self.res_tab.process()

    def open_output(self):
        d = self.project.output_dir or '.'
        if os.path.isdir(d):
            os.startfile(d)
        else:
            QMessageBox.information(self, 'Chưa có thư mục',
                                    f'Thư mục kết quả chưa tồn tại:\n{d}')

    def check_template(self):
        path = self.project.template
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, 'Chưa có template',
                                'Chọn template số liệu trước '
                                '(Tệp → Chọn template số liệu).')
            return
        try:
            from src.input_reader import describe, crosscheck
            text = describe(path)
            bad = crosscheck(path)
            if bad:
                text += ('\n\nCẢNH BÁO — giá trị trên sheet INPUT lệch so với ô gốc '
                         '(công thức có thể đã bị dán thành số cứng):\n')
                text += '\n'.join(f'  {k}: INPUT={a:g}, ô gốc {addr}={b:g}'
                                  for k, a, b, addr in bad)
        except Exception as e:
            text = f'Không đọc được:\n{e}'
        box = QMessageBox(self)
        box.setWindowTitle('Số liệu đầu vào')
        box.setText('Kết quả đọc template:')
        box.setDetailedText(text)
        box.setIcon(QMessageBox.Icon.Information)
        box.exec()

    def open_guide(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for rel in ('docs/USER-GUIDE.txt', 'README.md'):
            p = os.path.join(base, rel)
            if os.path.exists(p):
                webbrowser.open(p)
                return
        QMessageBox.information(self, 'Hướng dẫn', 'Chưa có tài liệu đi kèm.')

    def about(self):
        d = QDialog(self)
        d.setWindowTitle(f'Giới thiệu {APP_NAME}')
        d.setFixedWidth(520)
        lay = QVBoxLayout(d)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(18)
        app_lb = QLabel()
        app_lb.setPixmap(assets.app_icon().pixmap(72, 72))
        top.addWidget(app_lb, 0, Qt.AlignmentFlag.AlignTop)

        txt = QLabel(
            f'<div style="font-size:14pt;font-weight:600">{APP_NAME}</div>'
            f'<div style="color:{self.t["ink_2"]};font-size:10pt">{VERSION}</div>'
            f'<div style="height:8px"></div>'
            f'<div>Phân tích khung ngang dầm hộp BTCT dự ứng lực.</div>'
            f'<div style="color:{self.t["ink_2"]}">Cầu Lạch Tray — '
            f'Cao tốc Hà Nội – Hải Phòng (EX-10)</div>'
            f'<div style="height:10px"></div>'
            f'<div style="color:{self.t["ink_2"]};font-size:9pt">DXF → MCT → '
            f'Midas/Civil → Beam Force → Bảng kiểm toán</div>')
        txt.setWordWrap(True)
        top.addWidget(txt, 1)

        tedi = QLabel()
        tedi.setPixmap(assets.tedi_full(96))
        tedi.setToolTip('Tổng công ty Tư vấn thiết kế Giao thông vận tải')
        top.addWidget(tedi, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(top)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f'color: {self.t["border_soft"]};')
        lay.addWidget(line)

        foot = QHBoxLayout()
        cr = QLabel(f'<span style="color:{self.t["ink_3"]};font-size:9pt">'
                    f'TEDI — Tổng công ty Tư vấn thiết kế GTVT</span>')
        foot.addWidget(cr)
        foot.addStretch()
        ok = QPushButton('Đóng')
        ok.setProperty('primary', True)
        ok.clicked.connect(d.accept)
        foot.addWidget(ok)
        lay.addLayout(foot)
        d.exec()

    # ─────────────────────────────────────────
    # Trạng thái
    # ─────────────────────────────────────────
    def status_msg(self, text, level='ok'):
        col = {'ok': self.t['ok'], 'warn': self.t['warn'],
               'err': self.t['err'], 'busy': self.t['accent']}[level]
        self.lb_msg.setText(text)
        self.lb_msg.setStyleSheet(f'color: {col}; font-weight: 600;')

    def set_progress(self, done, total):
        if total <= 0 or done >= total:
            self.prog.setVisible(False)
            return
        self.prog.setVisible(True)
        self.prog.setMaximum(total)
        self.prog.setValue(done)

    def _on_tab(self, idx):
        if idx == 1:
            self.res_tab.refresh()
            self.steps.set_state(3, ACTIVE)

    def _on_generate_progress(self, done, total):
        self.set_progress(done, total)
        if not total:
            return
        self.steps.set_state(0, DONE, f'{len(self.project)} file')
        self.steps.set_state(1, DONE if done >= total else ACTIVE, f'{done}/{total}')
        if done >= total:
            self.steps.set_state(2, ACTIVE)
            self.status_msg('Đã tạo xong MCT — chạy Midas/Civil rồi quay lại',
                            'ok' if not self.project.by_status(ERROR) else 'warn')
        else:
            self.status_msg('Đang tạo mô hình…', 'busy')

    def _on_results_progress(self, done, total):
        self.set_progress(done, total)
        if not total:
            return
        self.steps.set_state(2, DONE)
        self.steps.set_state(3, DONE if done >= total else ACTIVE, f'{done}/{total}')
        if done >= total:
            n = len(self.project.by_status(CHECKED))
            self.steps.set_state(4, DONE, f'{n} mặt cắt')
            self.status_msg('Đã kiểm toán xong')

    # ─────────────────────────────────────────
    def _restore_settings(self):
        g = self.settings.value('geometry')
        if g:
            self.restoreGeometry(g)
        s = self.settings.value('windowState')
        if s:
            self.restoreState(s)
        last = self.settings.value('lastProject', '')
        if last and os.path.exists(last):
            try:
                p = Project.load(last)
                p.refresh_status()
                self._apply_project(p)
            except Exception:
                pass

    def closeEvent(self, e):
        if not self._confirm_discard():
            e.ignore()
            return
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('windowState', self.saveState())
        self.settings.setValue('lastProject', self.project.path or '')
        e.accept()

"""
Bộ điều khiển sinh MCT — không còn là một tab.

Theo bố cục mockup, vùng trung tâm là các tab CHẾ ĐỘ XEM chứ không phải tab quy
trình, nên lớp này chỉ còn giữ phần điều phối: dựng danh sách job từ project,
chạy worker, ghi kết quả ngược vào project. Thiết lập (template, thư mục kết
quả) nằm ở panel Project bên trái; khung xem là `ViewerPanel` dùng chung.
"""

import os

from PyQt6.QtCore import QObject, pyqtSignal

from src.project import Project
from .worker import GenerateWorker


class GenerateController(QObject):
    progress_changed = pyqtSignal(int, int)   # done, total
    project_changed = pyqtSignal()
    section_shown = pyqtSignal(str)

    def __init__(self, status_bar, project: Project = None, viewer=None, log=None):
        super().__init__()
        self.status_bar = status_bar
        self.project = project if project is not None else Project()
        self.viewer = viewer
        self.log_area = log
        self.worker = None
        self.include_pt = True
        self._total = self._done = 0
        self._current = ''

    # ─────────────────────────────────────────
    @property
    def view(self):
        return self.viewer.view if self.viewer else None

    def set_log(self, log):
        self.log_area = log

    def set_viewer(self, viewer):
        self.viewer = viewer

    def set_project(self, project: Project):
        self.project = project
        self._current = ''
        if self.view:
            self.view.clear()

    def clear(self):
        if self.log_area:
            self.log_area.clear()

    def refresh(self):
        pass

    # ─────────────────────────────────────────
    def show_section(self, name):
        """Nạp mô hình ĐÃ GHI RA MCT của mặt cắt đang chọn."""
        sec = self.project.find(name)
        if not sec or not self.view:
            return
        self._current = name
        topo = sec.topo or os.path.join(
            self.project.output_dir, name, f'{name}_topo.json')
        if os.path.exists(topo) and self.view.load_topo(topo):
            # load_topo đã nạp bộ gối GHI TRONG MCT; chỉ ghi đè khi người dùng
            # thực sự đặt gối riêng cho mặt cắt này
            if sec.supports:
                self.view.set_supports(sec.supports)
            self.viewer.rebuild_sup_bar()
            st = self.view.stats()
            self.status_bar.showMessage(
                f'{name}: {st["type"]} · {st["nodes"]} node · {st["elems"]} phần tử'
                f' · H {st["H"]:.3f} m · B {st["B"]:.3f} m')
        else:
            self.view.clear()
            self.status_bar.showMessage(f'{name}: chưa tạo MCT')
        self.section_shown.emit(name)

    def on_supports_changed(self, supports):
        if self._current:
            self.project.set_supports(self._current, supports)
            self.project_changed.emit()

    def current_mct_text(self) -> str:
        sec = self.project.find(self._current)
        if not sec or not sec.mct or not os.path.exists(sec.mct):
            return ''
        try:
            with open(sec.mct, encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f'Không đọc được {sec.mct}:\n{e}'

    # ─────────────────────────────────────────
    def generate(self, names=None):
        if self.worker is not None:
            return
        secs = ([self.project.find(n) for n in names] if names
                else list(self.project))
        secs = [s for s in secs if s]
        if not secs:
            self.status_bar.showMessage(
                'Chưa có mặt cắt nào — thêm DXF ở panel bên trái.')
            return

        jobs = [{'name': s.name, 'dxf': s.dxf,
                 'excel': self.project.template_for(s),
                 'include_pt': self.include_pt and s.include_pt,
                 'supports': list(s.supports)}
                for s in secs]

        if self.log_area:
            self.log_area.clear()
        self._total, self._done = len(jobs), 0
        self.progress_changed.emit(0, self._total)
        self.status_bar.showMessage(f'Đang tạo {self._total} mặt cắt…')

        self.worker = GenerateWorker(jobs, self.project.output_dir or 'output')
        if self.log_area:
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
        summary = self.log_area.summary() if self.log_area else ''
        self.status_bar.showMessage(f'Xong: {count}/{self._total} mặt cắt — {summary}')
        if self.log_area:
            self.log_area.success(f'Hoàn tất {count}/{self._total} mặt cắt')
        self.project_changed.emit()


# tên cũ, để phần còn lại của mã không phải đổi
GenerateTab = GenerateController

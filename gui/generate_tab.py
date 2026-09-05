"""
Bộ điều khiển sinh MCT — không còn là một tab.

Theo bố cục mockup, vùng trung tâm là các tab CHẾ ĐỘ XEM chứ không phải tab quy
trình, nên lớp này chỉ còn giữ phần điều phối: dựng danh sách job từ project,
chạy worker, ghi kết quả ngược vào project. Thiết lập (template, thư mục kết
quả) nằm ở panel Project bên trái; khung xem là `ViewerPanel` dùng chung.
"""

import os

from PyQt6.QtCore import QObject, pyqtSignal

from src.project import Project, NEW
from src.security import usage_log
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
        # Còn tự nhảy theo mặt cắt vừa tạo xong hay không (xem `_on_done`).
        self._theo_duoc = True
        self._tu_nhay = ''

    # ─────────────────────────────────────────
    @property
    def view(self):
        return self.viewer.view if self.viewer else None

    def set_log(self, log):
        self.log_area = log

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
        """Nạp mô hình ĐÃ GHI RA MCT; chưa có thì xem trước thẳng từ DXF."""
        sec = self.project.find(name)
        if not sec or not self.view:
            return
        self._current = name
        # Chỉ đoán đường dẫn topo khi mặt cắt ĐÃ từng sinh MCT. Mặt cắt mới thêm
        # mà đoán bừa `output/<tên>/<tên>_topo.json` thì rất dễ vớ phải file cũ
        # của lần chạy trước với cùng tên — hiện mô hình của một DXF khác mà
        # không ai biết. Chưa sinh thì đi đường xem trước từ chính DXF.
        topo = sec.topo or ('' if sec.status == NEW else os.path.join(
            self.project.output_dir, name, f'{name}_topo.json'))
        if topo and os.path.exists(topo) and self.view.load_topo(topo):
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
            self._show_preview(name, sec)
        self.section_shown.emit(name)

    def _show_preview(self, name, sec):
        """Xem trước hình học + cáp đọc thẳng từ DXF, chưa cần sinh MCT.

        Biên bê tông và đường cáp vốn nằm sẵn trong DXF — bắt người dùng chạy
        hết một lượt tạo MCT rồi mới được nhìn thì lỗi bản vẽ (thiếu layer, sai
        đơn vị, cáp lệch chỗ) đến cuối quy trình mới lộ.
        """
        from src.preview import preview_topo
        if not sec.dxf or not os.path.exists(sec.dxf):
            self.view.clear()
            self.status_bar.showMessage(f'{name}: không tìm thấy DXF {sec.dxf}')
            return
        try:
            topo = preview_topo(sec.dxf)
        except Exception as e:
            self.view.clear()
            self.status_bar.showMessage(f'{name}: DXF đọc không được — {e}')
            if self.log_area:
                self.log_area.error(f'{name}: không xem trước được DXF — {e}')
            return

        self.view.set_topo(topo)
        if sec.supports:
            self.view.set_supports(sec.supports)
        self.viewer.rebuild_sup_bar()
        g = topo['geometry']
        n_pt = len(topo['tendons'])
        self.status_bar.showMessage(
            f'{name}: xem trước từ DXF · {g["section_type"]} · H {g["H"]:.3f} m'
            f' · {n_pt} cáp DƯL · chưa tạo MCT')
        if self.log_area:
            for layer, why in (topo.get('pt_suspect') or {}).items():
                self.log_area.warning(f'{name}: layer {layer!r} — {why}')

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
    # Tiền kiểm số liệu đầu vào
    # ─────────────────────────────────────────
    def _metrics_for(self, sec):
        """Hình học của một mặt cắt — chỉ là chỗ nối `Section` với `src`."""
        from src.input_check import section_metrics
        return section_metrics(dxf=sec.dxf, topo=sec.topo,
                               excel=self.project.template_for(sec))

    def template_notes(self, secs) -> list:
        """Đối chiếu template ↔ hình học cho một danh sách mặt cắt.

        Dùng chung cho hai chỗ: hộp thoại hỏi-trước-khi-tạo (`preflight`) và
        menu *Kiểm tra template số liệu…*. Bản đầu để hai chỗ tự gom lấy — mà
        gom sai một chỗ thì chỗ kia vẫn báo đúng, nên chênh lệch giữa chúng
        không lộ ra bao giờ.
        """
        from src.input_check import check_template, check_shared_template
        from src.input_reader import read_inputs

        entries, notes = [], []
        for s in secs:
            excel = self.project.template_for(s)
            metrics = self._metrics_for(s)
            entries.append({'name': s.name, 'template': excel, 'metrics': metrics})
            if not (excel and os.path.exists(excel) and metrics):
                continue
            try:
                notes += check_template(read_inputs(excel), metrics, s.name)
            except Exception:
                pass
        return notes + check_shared_template(entries)

    def preflight(self, secs) -> bool:
        """Đối chiếu template với hình học trước khi sinh. False = người dùng huỷ.

        Hoạt tải trong template tính theo phương pháp dải tương đương cho MỘT
        mặt cắt cụ thể. Dùng lại cho mặt cắt khác thì tải sai, và nếu sai về phía
        thiếu thì không có gì khác trong cả quy trình lộ ra — mô hình vẫn chạy,
        bảng kiểm toán vẫn ra số đẹp.
        """
        notes = self.template_notes(secs)

        if self.log_area:
            for n in notes:
                if n['level'] == 'warn':
                    self.log_area.warning(n['text'])
                else:
                    self.log_area.info(n['text'])

        hard = [n for n in notes if n['level'] == 'warn']
        if not hard:
            return True

        from PyQt6.QtWidgets import QMessageBox
        box = QMessageBox(self.viewer)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle('Số liệu đầu vào không khớp hình học')
        box.setText(f'{len(hard)} cảnh báo về số liệu đầu vào.')
        box.setInformativeText(
            'Hoạt tải trong template tính theo dải tương đương cho một mặt cắt '
            'cụ thể — dùng cho mặt cắt khác thì tải sai.')
        box.setDetailedText('\n\n'.join(n['text'] for n in hard))
        go = box.addButton('Vẫn tạo', QMessageBox.ButtonRole.AcceptRole)
        box.addButton('Huỷ', QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(go)
        box.exec()
        if box.clickedButton() is not go:
            self.status_bar.showMessage('Đã huỷ tạo MCT — số liệu đầu vào chưa khớp')
            return False
        return True

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

        if not self.preflight(secs):
            return

        jobs = [{'name': s.name, 'dxf': s.dxf,
                 'excel': self.project.template_for(s),
                 'include_pt': self.include_pt and s.include_pt,
                 'supports': list(s.supports),
                 'pt_jacking': s.pt_jacking}
                for s in secs]

        if self.log_area:
            self.log_area.clear()
        self._total, self._done = len(jobs), 0
        self.progress_changed.emit(0, self._total)
        self.status_bar.showMessage(f'Đang tạo {self._total} mặt cắt…')
        # Mỗi lượt chạy bắt đầu lại: lần trước người dùng có tự chọn thì
        # cũng không nên làm câm phản hồi của lượt này.
        self._theo_duoc, self._tu_nhay = True, ''

        self.worker = GenerateWorker(
            jobs, self.project.output_dir or 'output',
            con_can=lambda ten: self.project.find(ten) is not None)
        if self.log_area:
            self.worker.log.connect(self.log_area.append_auto)
        self.worker.section_info.connect(self._on_info)
        self.worker.section_error.connect(self._on_error)
        self.worker.section_done.connect(self._on_done)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.start()

    def _on_info(self, name, info):
        usage_log.record('mct')      # đếm đúng số MCT ra lò, không đếm số lần bấm
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

        # Chỉ tự nhảy theo mặt cắt vừa xong khi NGƯỜI DÙNG chưa tự chọn gì
        # trong lượt chạy này.
        #
        # Tự nhảy là phản hồi tốt khi người dùng ngồi nhìn, nhưng nếu họ bấm
        # một mặt cắt khác trong cây để xem hình trong lúc chờ thì phần mềm
        # giành lấy lựa chọn: cây tô mặt cắt họ chọn, còn khung xem và dock
        # nhảy sang mặt cắt vừa tạo xong, rồi tiếp tục nhảy sau mỗi mặt cắt —
        # và xong lượt thì ba chỗ vẫn lệch nhau, không tự về lại. Đúng loại
        # lệch mà luật "chỉ có MỘT mặt cắt đang chọn cho cả app" sinh ra để
        # tránh; chỉ khác là ở đây phần mềm mới là bên giành.
        if self._theo_duoc:
            self._tu_nhay = name
            self.show_section(name)

    def nguoi_dung_da_chon(self, name):
        """Người dùng tự chọn một mặt cắt — thôi tự nhảy cho hết lượt này."""
        if name and name != getattr(self, '_tu_nhay', ''):
            self._theo_duoc = False

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

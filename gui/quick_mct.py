"""Tạo MCT thẳng từ file DXF — lối chuột phải trong Explorer.

Bấm chuột phải vào .dxf → *Tạo file MCT* → cửa sổ này hiện lên, chạy, rồi báo
kết quả. Không mở app, không lập project, không phải chọn gì.

Vì sao vẫn có cửa sổ chứ không im lặng hoàn toàn
────────────────────────────────────────────────
Sinh MCT không phải phép đổi đuôi file. Nó có thể **cảnh báo**: thiếu layer
INPOLY, cáp sai quy ước, và nhất là **template khai hoạt tải không khớp hình
học mặt cắt** — cái sai không làm hỏng file mà làm sai tải bánh xe 5–15%. Chạy
im lặng thì mọi cảnh báo ấy rơi vào hư không, đúng lỗi mà cả dự án đã mất công
vá (xem mục "Cảnh báo phải tra được bất cứ lúc nào" trong CLAUDE.md).

Nên: một cửa sổ nhỏ, có nhật ký, tự đóng thì không — nhưng nó KHÔNG phải app.
Không project, không dock, không thẻ; xong việc là đóng.

Dùng lại y nguyên GenerateWorker của app, không viết đường sinh MCT thứ hai:
hai đường thì sớm muộn cũng lệch nhau, và lệch ở chỗ không ai soi.
"""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLabel,
                             QMessageBox, QProgressBar, QPushButton,
                             QVBoxLayout, QWidget)

from src.security import guard, usage_log
from .widgets import LogView
from .worker import GenerateWorker

#: Template mặc định của kho — dùng khi Tùy chọn chưa trỏ template nào.
_REPO_TEMPLATE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'Midas-Transverse-Boxgirder-analysis.xls')


def default_output_for(dxf_paths: list[str], prefs) -> str:
    """Nơi ghi kết quả cho lối chuột phải.

    Tùy chọn của app mặc định là 'output' — một đường dẫn TƯƠNG ĐỐI. Mở từ
    Explorer thì thư mục làm việc là chỗ nào cũng có thể, nên 'output' sẽ mọc
    ra ở nơi không ai đoán được. Chỉ nhận đường dẫn tuyệt đối; còn lại thì ghi
    ngay cạnh bản vẽ, đúng chỗ người dùng đang đứng.
    """
    configured = str(getattr(prefs, 'output_dir', '') or '').strip()
    if configured and os.path.isabs(configured):
        return configured
    if dxf_paths:
        return os.path.dirname(os.path.abspath(dxf_paths[0]))
    return os.path.abspath('output')


def default_template(prefs) -> str:
    tpl = str(getattr(prefs, 'template', '') or '').strip()
    if tpl and os.path.exists(tpl):
        return tpl
    return _REPO_TEMPLATE if os.path.exists(_REPO_TEMPLATE) else ''


class QuickMctDialog(QDialog):
    """Cửa sổ nhỏ: chạy một loạt DXF ra MCT rồi báo kết quả."""

    #: (số đạt, số hỏng) — phát khi chạy xong. Có tín hiệu này thì kiểm thử
    #: bám được vào lúc kết thúc thật, khỏi phải đoán bằng đồng hồ.
    finished_run = pyqtSignal(int, int)

    def __init__(self, dxf_paths: list[str], prefs, theme: dict | None = None,
                 parent=None):
        super().__init__(parent)
        self.t = theme or {}
        self.paths = [p for p in dxf_paths if p.lower().endswith('.dxf')]
        self.out_dir = default_output_for(self.paths, prefs)
        self.template = default_template(prefs)
        self.prefs = prefs
        self.worker = None
        self._ok = 0
        self._failed = 0
        self._made: list[str] = []

        self.setWindowTitle('Tạo file MCT')
        self.setMinimumSize(720, 460)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        self.lb_head = QLabel()
        self.lb_head.setWordWrap(True)
        self.lb_head.setStyleSheet('font-weight:600')
        lay.addWidget(self.lb_head)

        lay.addWidget(self._path_row('Template số liệu:', 'template'))
        lay.addWidget(self._path_row('Thư mục kết quả:', 'out'))

        self.log = LogView()
        lay.addWidget(self.log, 1)

        self.prog = QProgressBar()
        self.prog.setTextVisible(True)
        lay.addWidget(self.prog)

        foot = QHBoxLayout()
        self.b_open = QPushButton('Mở thư mục kết quả')
        self.b_open.setEnabled(False)
        self.b_open.clicked.connect(self._open_folder)
        foot.addWidget(self.b_open)
        foot.addStretch(1)
        self.b_go = QPushButton('Tạo MCT')
        self.b_go.setDefault(True)
        self.b_go.clicked.connect(self.start)
        foot.addWidget(self.b_go)
        self.b_close = QPushButton('Đóng')
        self.b_close.clicked.connect(self.reject)
        foot.addWidget(self.b_close)
        lay.addLayout(foot)

        self._refresh_head()

    # ── dựng ──────────────────────────────────────────────────────────────
    def _path_row(self, label: str, which: str) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(label))
        lb = QLabel()
        lb.setWordWrap(True)
        lb.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(lb, 1)
        btn = QPushButton('Đổi…')
        btn.clicked.connect(self._pick_template if which == 'template' else self._pick_out)
        lay.addWidget(btn)
        setattr(self, f'lb_{which}', lb)
        return row

    def _refresh_head(self) -> None:
        names = ', '.join(os.path.basename(p) for p in self.paths[:4])
        more = f' … (+{len(self.paths) - 4})' if len(self.paths) > 4 else ''
        self.lb_head.setText(f'{len(self.paths)} bản vẽ: {names}{more}'
                             if self.paths else 'Không có file DXF nào.')
        self.lb_template.setText(self.template or '(chưa có — sẽ bỏ toàn bộ '
                                                  'khối tải trọng và vật liệu)')
        self.lb_out.setText(self.out_dir)
        self.b_go.setEnabled(bool(self.paths))
        self.prog.setMaximum(max(len(self.paths), 1))
        self.prog.setValue(0)

    def _pick_template(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Chọn template số liệu',
                                              self.template or '',
                                              'Excel (*.xls *.xlsx);;Tất cả (*.*)')
        if path:
            self.template = path
            self._refresh_head()

    def _pick_out(self) -> None:
        path = QFileDialog.getExistingDirectory(self, 'Chọn thư mục kết quả',
                                                self.out_dir)
        if path:
            self.out_dir = path
            self._refresh_head()

    # ── chạy ──────────────────────────────────────────────────────────────
    def start(self) -> None:
        if self.worker is not None or not self.paths:
            return
        state = guard.get_runtime_state('mct')
        if not state.ready:
            QMessageBox.warning(self, 'Chưa được phép', state.message)
            self.log.error(state.message.replace('\n', ' · '))
            return

        usage_log.record('context_menu')
        jobs = [{'name': os.path.splitext(os.path.basename(p))[0],
                 'dxf': p, 'excel': self.template,
                 'include_pt': True, 'supports': [], 'pt_jacking': 'begin'}
                for p in self.paths]

        self.b_go.setEnabled(False)
        self.log.info(f'Thư mục kết quả: {self.out_dir}')
        self.worker = GenerateWorker(jobs, self.out_dir)
        self.worker.log.connect(self.log.append_auto)
        self.worker.section_info.connect(self._on_info)
        self.worker.section_error.connect(self._on_error)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.start()

    def _on_info(self, name: str, info: dict) -> None:
        usage_log.record('mct')
        self._ok += 1
        self._made.append(info.get('mct', ''))
        self.prog.setValue(self._ok + self._failed)

    def _on_error(self, name: str, msg: str) -> None:
        self._failed += 1
        self.prog.setValue(self._ok + self._failed)

    def _on_finished(self, count: int) -> None:
        self.worker = None
        self.b_go.setEnabled(True)
        self.b_open.setEnabled(self._ok > 0)
        self.prog.setValue(self.prog.maximum())
        summary = f'Xong: {self._ok} đạt · {self._failed} hỏng'
        if self._failed:
            self.log.warning(summary + ' — đọc các dòng đỏ ở trên.')
        else:
            self.log.success(summary)
        self.setWindowTitle(f'Tạo file MCT — {summary}')
        self.finished_run.emit(self._ok, self._failed)

    def _open_folder(self) -> None:
        target = self.out_dir
        if self._made and os.path.exists(os.path.dirname(self._made[0])):
            target = os.path.dirname(self._made[0])
        if os.path.isdir(target):
            os.startfile(target)


def run_quick_mct(dxf_paths: list[str], prefs, theme: dict | None = None,
                  auto_start: bool = True) -> int:
    """Mở cửa sổ tạo MCT nhanh. Trả về số mặt cắt tạo được."""
    dlg = QuickMctDialog(dxf_paths, prefs, theme)
    if auto_start:
        # Chạy ngay khi cửa sổ đã hiện: người dùng bấm chuột phải là đã ra lệnh
        # rồi, bắt bấm thêm một nút "Tạo" nữa là thừa một nhịp.
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(120, dlg.start)
    dlg.exec()
    return dlg._ok

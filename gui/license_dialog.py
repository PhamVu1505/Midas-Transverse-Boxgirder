"""Hộp thoại Giấy phép — trạng thái · đăng ký · kích hoạt.

Ba thẻ, đi từ trái sang phải đúng thứ tự việc phải làm, đánh số như phần mềm
thương mại (midas, SAP): người dùng không cần ai giải thích cũng biết bước nào
trước bước nào.

    Trạng thái      đang ở đâu: dùng thử còn mấy ngày, hay giấy phép tới bao giờ
    ① Đăng ký       điền tên, chọn thời hạn, lưu tệp đăng ký rồi gửi đi
    ② Kích hoạt     dán mã nhận về (hoặc nhập từ tệp), kiểm tra, kích hoạt

Ba điều đã cân nhắc rồi mới bỏ khỏi giao diện này
─────────────────────────────────────────────────
* **Mã máy** không hiện ở thẻ Trạng thái nữa — nó chỉ có ích lúc đăng ký, và
  đúng chỗ đó (thẻ ①) vẫn hiện đầy đủ kèm nút chép.
* **Thư mục đồng bộ** (nơi phần mềm báo về và nhận lệnh thu hồi) do người cấp
  giấy phép đặt, nằm trong phần đã ký. Người dùng không chọn được và không cần
  biết, nên không bày ra; việc đồng bộ chạy nền lúc khởi động.
* **Số liệu sử dụng** không có thẻ riêng. Người cấp lấy qua thư mục đồng bộ;
  máy không nối được thì xuất bằng dòng lệnh
  ``run_gui.py --xuat-su-dung <tệp>``.

**Ô nhập mã là một dòng, không phải ô soạn thảo nhiều dòng.** Mã giấy phép của
phần mềm này dài (chữ ký số RSA ràng theo máy — không thể ngắn 25 ký tự như
loại kích hoạt qua máy chủ), nhưng thao tác thì phải giống nhau: dán vào một ô,
bấm Kiểm tra, bấm Kích hoạt.
"""
from __future__ import annotations

import json
import os
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (QComboBox, QDialog, QFileDialog, QFormLayout,
                             QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                             QPushButton, QVBoxLayout, QWidget)

from src.security import guard, license_manager as lm, trial
from src.security.hwid import get_machine_id, machine_label

_OK, _WARN, _BAD = 'ok', 'warn', 'bad'


def _banner_qss(theme: dict, level: str) -> str:
    """Dải trạng thái: nền panel + vạch màu bên trái.

    Chỉ đọc token, không viết mã màu cứng — mã cứng đứng yên khi đổi bảng màu
    và chỉ lộ ra khi đã sang bản Tối. Bảng màu có sẵn ok/warn/err làm màu CHỮ;
    dùng chúng làm nền thì chữ đen trên nền đỏ tươi, nên đây lấy làm vạch.
    """
    accent = {_OK: 'ok', _WARN: 'warn'}.get(level, 'err')
    return (f"background:{theme.get('panel', '#F7F9FC')};"
            f"color:{theme.get('ink', '#101828')};"
            f"border-left:4px solid {theme.get(accent, '#B42318')};"
            'padding:10px;border-radius:4px;font-weight:600')


class LicenseDialog(QDialog):
    """Hộp thoại giấy phép: trạng thái · đăng ký · kích hoạt."""

    def __init__(self, parent=None, theme: dict | None = None,
                 app_version: str = ''):
        super().__init__(parent)
        self.t = theme or {}
        self.app_version = app_version
        self.setWindowTitle('Giấy phép')
        self.setMinimumSize(660, 470)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.banner)

        from PyQt6.QtWidgets import QTabWidget
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_status(), 'Trạng thái')
        self.tabs.addTab(self._tab_register(), '① Đăng ký giấy phép')
        self.tabs.addTab(self._tab_activate(), '② Kích hoạt')
        lay.addWidget(self.tabs, 1)

        foot = QHBoxLayout()
        foot.addStretch(1)
        b_close = QPushButton('Đóng')
        b_close.setDefault(True)
        b_close.clicked.connect(self.accept)
        foot.addWidget(b_close)
        lay.addLayout(foot)

        self.refresh()

    # ── Trạng thái ────────────────────────────────────────────────────────
    def _tab_status(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(8)

        self.lb_detail = QLabel()
        self.lb_detail.setWordWrap(True)
        self.lb_detail.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.lb_detail)

        self.lb_huong_dan = QLabel()
        self.lb_huong_dan.setWordWrap(True)
        lay.addWidget(self.lb_huong_dan)

        lay.addStretch(1)
        row = QHBoxLayout()
        self.b_remove = QPushButton('Gỡ giấy phép khỏi máy này…')
        self.b_remove.clicked.connect(self._remove_license)
        row.addWidget(self.b_remove)
        row.addStretch(1)
        lay.addLayout(row)
        return page

    # ── ① Đăng ký ─────────────────────────────────────────────────────────
    def _tab_register(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(10)

        head = QLabel('Điền thông tin rồi lưu tệp đăng ký, gửi tệp đó cho '
                      'người cấp giấy phép.')
        head.setWordWrap(True)
        lay.addWidget(head)

        form = QFormLayout()
        form.setSpacing(8)
        self.ed_name = QLineEdit(os.environ.get('USERNAME', ''))
        self.ed_email = QLineEdit()
        self.ed_company = QLineEdit()
        self.ed_note = QLineEdit()
        self.cb_term = QComboBox()
        for months, label in lm.TERM_CHOICES:
            self.cb_term.addItem(label, months)
        self.cb_term.setCurrentIndex(1)          # 6 tháng
        form.addRow('Họ và tên:', self.ed_name)
        form.addRow('Email:', self.ed_email)
        form.addRow('Đơn vị:', self.ed_company)
        form.addRow('Thời hạn đăng ký:', self.cb_term)
        form.addRow('Ghi chú:', self.ed_note)
        lay.addLayout(form)

        # Mã máy đứng ở ĐÂY chứ không ở thẻ Trạng thái: đây là chỗ duy nhất nó
        # có ích, và người cấp thường hỏi đúng con số này.
        row = QHBoxLayout()
        row.addWidget(QLabel('Mã máy:'))
        self.ed_machine = QLineEdit(get_machine_id())
        self.ed_machine.setReadOnly(True)
        row.addWidget(self.ed_machine, 1)
        b_copy = QPushButton('Chép')
        b_copy.setToolTip('Chép mã máy vào bộ nhớ tạm')
        b_copy.clicked.connect(self._copy_machine)
        row.addWidget(b_copy)
        lay.addLayout(row)

        lay.addStretch(1)
        row2 = QHBoxLayout()
        row2.addStretch(1)
        b_save = QPushButton('Lưu tệp đăng ký…')
        b_save.setProperty('primary', True)
        b_save.clicked.connect(self._save_request)
        row2.addWidget(b_save)
        lay.addLayout(row2)
        return page

    # ── ② Kích hoạt ───────────────────────────────────────────────────────
    def _tab_activate(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(10)

        head = QLabel('Nhập mã giấy phép nhận được, bấm Kiểm tra rồi Kích hoạt.')
        head.setWordWrap(True)
        lay.addWidget(head)

        form = QFormLayout()
        form.setSpacing(8)
        self.ed_key = QLineEdit()
        self.ed_key.setPlaceholderText('Dán mã giấy phép vào đây…')
        self.ed_key.returnPressed.connect(self._preview_token)
        form.addRow('Mã giấy phép:', self.ed_key)
        lay.addLayout(form)

        row = QHBoxLayout()
        b_paste = QPushButton('Dán')
        b_paste.setToolTip('Dán mã từ bộ nhớ tạm')
        b_paste.clicked.connect(self._paste_key)
        row.addWidget(b_paste)
        b_import = QPushButton('Nhập từ tệp…')
        b_import.setToolTip('Chọn tệp giấy phép (.mtblic) nhận được')
        b_import.clicked.connect(self._import_license_file)
        row.addWidget(b_import)
        row.addStretch(1)
        b_check = QPushButton('Kiểm tra')
        b_check.clicked.connect(self._preview_token)
        row.addWidget(b_check)
        self.b_activate = QPushButton('Kích hoạt')
        self.b_activate.setProperty('primary', True)
        self.b_activate.clicked.connect(self._activate)
        row.addWidget(self.b_activate)
        lay.addLayout(row)

        self.lb_preview = QLabel()
        self.lb_preview.setWordWrap(True)
        self.lb_preview.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.lb_preview)
        lay.addStretch(1)
        return page

    # ── việc ──────────────────────────────────────────────────────────────
    def refresh(self) -> None:
        state = guard.get_runtime_state()
        if state.ready and state.source == guard.SOURCE_LICENSE:
            level = _OK
        elif state.ready:
            level = _WARN
        else:
            level = _BAD
        self.banner.setStyleSheet(_banner_qss(self.t, level))
        self.banner.setText(state.message)

        lines = []
        info = state.license
        if info is not None:
            left = info.days_remaining()
            han = ('Vĩnh viễn' if lm.is_permanent(info.expires_at)
                   else f'{info.issued_at} → {info.expires_at}'
                        + (f'  (còn {left} ngày)' if left is not None else ''))
            lines += [
                f'Cấp cho: {info.customer}' + (f' · {info.company}' if info.company else ''),
                f'Thời hạn: {han}',
                f'Tính năng: {info.feature_text}',
                f'Mã giấy phép: {info.license_id}',
            ]
            self.lb_huong_dan.setText('')
        else:
            st = trial.get_trial_status(start_if_missing=False)
            if st.started_at:
                lines.append(f'Bắt đầu dùng thử: {st.started_at}'
                             + (f' · hết ngày {st.expires_on}' if st.expires_on else ''))
            self.lb_huong_dan.setText(
                f'Bản dùng thử {trial.TRIAL_DAYS} ngày mở đầy đủ tính năng.\n'
                'Để dùng tiếp: sang thẻ ① Đăng ký giấy phép, lưu tệp đăng ký và '
                'gửi cho người cấp; nhận mã về thì nhập ở thẻ ② Kích hoạt.')
        self.lb_detail.setText('\n'.join(lines))
        # Chưa có giấy phép thì không có gì để gỡ. Để nút mở thì bấm vào chỉ
        # nhận được một hộp thoại nói "không có file nào" — vô ích.
        self.b_remove.setEnabled(info is not None)
        self.ed_machine.setText(get_machine_id())

    def _copy_machine(self) -> None:
        QGuiApplication.clipboard().setText(get_machine_id())
        QMessageBox.information(self, 'Đã chép',
                                'Đã chép mã máy vào bộ nhớ tạm.')

    def _paste_key(self) -> None:
        text = QGuiApplication.clipboard().text().strip()
        if not text:
            QMessageBox.information(self, 'Bộ nhớ tạm trống',
                                    'Chưa chép mã giấy phép nào.')
            return
        self.ed_key.setText(''.join(text.split()))
        self._preview_token()

    def _import_license_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, 'Chọn tệp giấy phép', '',
            'Tệp giấy phép (*.mtblic *.txt);;Tất cả (*.*)')
        if not path:
            return
        # Bộ lọc có mục "Tất cả (*.*)" nên người dùng chọn nhầm PDF/DOCX là
        # chuyện bình thường. `UnicodeDecodeError` là `ValueError`, không phải
        # `OSError`; bắt hụt nó thì PyQt6 không có excepthook và **cả tiến
        # trình bị abort** — mà người dùng chưa kích hoạt đang kẹt đúng ở màn
        # hình này, tức họ không còn đường nào vào phần mềm.
        try:
            noi_dung = open(path, encoding='utf-8').read().strip()
        except OSError as exc:
            QMessageBox.warning(self, 'Không đọc được tệp', str(exc))
            return
        except (UnicodeDecodeError, ValueError):
            QMessageBox.warning(
                self, 'Không đọc được tệp',
                'Tệp này không phải văn bản giấy phép.\n\n'
                'Hãy chọn tệp .mtblic mà người cấp phép gửi cho bạn.')
            return
        self.ed_key.setText(''.join(noi_dung.split()))
        self._preview_token()

    def _preview_token(self) -> lm.LicenseStatus | None:
        token = self.ed_key.text().strip()
        if not token:
            self.lb_preview.setText('Chưa nhập mã giấy phép.')
            return None
        status = lm.inspect_license_token(token)
        lines = [status.message]
        if status.info is not None:
            han = ('Vĩnh viễn' if lm.is_permanent(status.info.expires_at)
                   else status.info.expires_at)
            lines += [f'Cấp cho: {status.info.customer}',
                      f'Máy: {status.info.machine_id}',
                      f'Thời hạn: {han}',
                      f'Tính năng: {status.info.feature_text}']
        self.lb_preview.setText('\n'.join(lines))
        return status

    def _activate(self) -> None:
        status = self._preview_token()
        if status is None:
            QMessageBox.information(self, 'Chưa có mã',
                                    'Dán mã giấy phép hoặc nhập từ tệp trước.')
            return
        if not status.ok:
            QMessageBox.warning(self, 'Chưa kích hoạt được', status.message)
            return
        try:
            lm.save_license(status.token)
        except lm.LicenseError as exc:
            QMessageBox.critical(self, 'Không ghi được giấy phép', str(exc))
            return

        # Ghi xong đọc LẠI từ đĩa: đó mới là thứ lần chạy sau nhìn thấy.
        after = guard.get_runtime_state()
        self.refresh()
        if after.ready:
            self.tabs.setCurrentIndex(0)
            QMessageBox.information(self, 'Đã kích hoạt', status.message)
        else:
            QMessageBox.warning(self, 'Ghi xong nhưng chưa dùng được',
                                after.message)

    def _remove_license(self) -> None:
        if QMessageBox.question(
                self, 'Gỡ giấy phép',
                'Xoá giấy phép khỏi máy này?\nPhần mềm sẽ trở lại trạng thái '
                'chưa kích hoạt.') != QMessageBox.StandardButton.Yes:
            return
        removed = lm.remove_license()
        self.refresh()
        QMessageBox.information(
            self, 'Đã gỡ',
            'Đã xoá:\n' + '\n'.join(str(p) for p in removed)
            if removed else 'Không có tệp giấy phép nào để xoá.')

    def _save_request(self) -> None:
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, 'Thiếu tên',
                                'Nhập họ tên để người cấp biết là ai.')
            self.ed_name.setFocus()
            return
        payload = lm.build_request(name, self.ed_email.text(),
                                   self.ed_company.text(), self.ed_note.text(),
                                   self.cb_term.currentData(), self.app_version)
        default = f"{name.replace(' ', '_')}_{datetime.now():%Y%m%d}.mtbreq"
        path, _ = QFileDialog.getSaveFileName(self, 'Lưu tệp đăng ký', default,
                                              'Tệp đăng ký (*.mtbreq)')
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
        except OSError as exc:
            QMessageBox.critical(self, 'Không lưu được', str(exc))
            return
        QMessageBox.information(
            self, 'Đã lưu tệp đăng ký',
            f'{path}\n\nGửi tệp này cho người cấp giấy phép. Nhận mã về thì '
            'sang thẻ ② Kích hoạt.')


def show_license_dialog(parent=None, theme: dict | None = None,
                        app_version: str = '') -> bool:
    """Mở hộp thoại; trả về True nếu sau khi đóng đã ở trạng thái chạy được."""
    dlg = LicenseDialog(parent, theme, app_version)
    dlg.exec()
    return guard.get_runtime_state().ready

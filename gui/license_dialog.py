"""Hộp thoại Giấy phép — trạng thái · kích hoạt · xin cấp · số liệu sử dụng.

Ba việc người dùng cần làm, ba thẻ, không hơn:

* **Trạng thái** — dải màu nói ngay đang ở đâu: xanh = đã kích hoạt, vàng =
  đang dùng thử, đỏ = hết hạn / bị chặn. Kèm mã máy để copy gửi đi.
* **Kích hoạt** — dán chuỗi hoặc mở file .mtblic. Bấm Kiểm tra trước khi ghi:
  giấy phép cấp cho máy khác vẫn phải **hiện được nội dung** kèm lý do bị chối,
  nếu không người dùng chỉ thấy "không hợp lệ" mà không biết sai ở đâu.
* **Xin cấp giấy phép** — điền tên/đơn vị, lưu file .mtbreq gửi người cấp.

Thẻ **Sử dụng** cho người dùng thấy đúng những gì phần mềm đang ghi lại về họ.
Giấu đi thì đó là theo dõi lén; bày ra thì đó là sổ ghi công việc.
"""
from __future__ import annotations

import os
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (QDialog, QFileDialog, QFormLayout, QFrame,
                             QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                             QPlainTextEdit, QPushButton, QSpinBox, QTabWidget,
                             QVBoxLayout, QWidget)

from src.security import checkpoint, guard, license_manager as lm, trial, usage_log
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
    """Hộp thoại giấy phép. Trả về True nếu kết thúc ở trạng thái chạy được."""

    def __init__(self, parent=None, theme: dict | None = None,
                 app_version: str = ''):
        super().__init__(parent)
        self.t = theme or {}
        self.app_version = app_version
        self.setWindowTitle('Giấy phép')
        self.setMinimumSize(660, 520)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.banner)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_status(), 'Trạng thái')
        self.tabs.addTab(self._tab_activate(), 'Kích hoạt')
        self.tabs.addTab(self._tab_request(), 'Xin cấp giấy phép')
        self.tabs.addTab(self._tab_usage(), 'Sử dụng')
        lay.addWidget(self.tabs, 1)

        foot = QHBoxLayout()
        b_sync = QPushButton('Đồng bộ điểm hẹn')
        b_sync.setToolTip('Thả nhịp tim và lấy danh sách chặn mới nhất')
        b_sync.clicked.connect(self._sync_now)
        foot.addWidget(b_sync)
        foot.addStretch(1)
        b_close = QPushButton('Đóng')
        b_close.setDefault(True)
        b_close.clicked.connect(self.accept)
        foot.addWidget(b_close)
        lay.addLayout(foot)

        self.refresh()

    # ── thẻ Trạng thái ────────────────────────────────────────────────────
    def _tab_status(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(8)

        self.lb_detail = QLabel()
        self.lb_detail.setWordWrap(True)
        self.lb_detail.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.lb_detail)

        row = QHBoxLayout()
        row.addWidget(QLabel('Mã máy:'))
        self.ed_machine = QLineEdit(get_machine_id())
        self.ed_machine.setReadOnly(True)
        row.addWidget(self.ed_machine, 1)
        b_copy = QPushButton('Chép')
        b_copy.clicked.connect(self._copy_machine)
        row.addWidget(b_copy)
        lay.addLayout(row)

        self.lb_checkpoint = QLabel()
        self.lb_checkpoint.setWordWrap(True)
        lay.addWidget(self.lb_checkpoint)

        lay.addStretch(1)
        row2 = QHBoxLayout()
        self.b_remove = QPushButton('Gỡ giấy phép khỏi máy này…')
        self.b_remove.clicked.connect(self._remove_license)
        row2.addWidget(self.b_remove)
        row2.addStretch(1)
        lay.addLayout(row2)
        return page

    # ── thẻ Kích hoạt ─────────────────────────────────────────────────────
    def _tab_activate(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(8)
        lay.addWidget(QLabel('Dán nội dung giấy phép, hoặc mở file .mtblic:'))

        self.ed_token = QPlainTextEdit()
        self.ed_token.setPlaceholderText('MTB1.mtb-v1.…')
        lay.addWidget(self.ed_token, 1)

        row = QHBoxLayout()
        b_open = QPushButton('Mở file .mtblic…')
        b_open.clicked.connect(self._open_license_file)
        row.addWidget(b_open)
        b_check = QPushButton('Kiểm tra')
        b_check.clicked.connect(self._preview_token)
        row.addWidget(b_check)
        row.addStretch(1)
        self.b_activate = QPushButton('Kích hoạt')
        self.b_activate.clicked.connect(self._activate)
        row.addWidget(self.b_activate)
        lay.addLayout(row)

        self.lb_preview = QLabel()
        self.lb_preview.setWordWrap(True)
        self.lb_preview.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.lb_preview)
        return page

    # ── thẻ Xin cấp ───────────────────────────────────────────────────────
    def _tab_request(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        form = QFormLayout()
        form.setSpacing(8)
        self.ed_name = QLineEdit(os.environ.get('USERNAME', ''))
        self.ed_email = QLineEdit()
        self.ed_company = QLineEdit()
        self.ed_note = QLineEdit()
        self.sp_days = QSpinBox()
        self.sp_days.setRange(7, 3650)
        self.sp_days.setValue(lm.DEFAULT_TERM_DAYS)
        self.sp_days.setSuffix(' ngày')
        form.addRow('Họ và tên:', self.ed_name)
        form.addRow('Email:', self.ed_email)
        form.addRow('Đơn vị:', self.ed_company)
        form.addRow('Ghi chú:', self.ed_note)
        form.addRow('Xin dùng trong:', self.sp_days)
        lay.addLayout(form)

        hint = QLabel(f'Máy: {machine_label()} · {get_machine_id()}\n'
                      'File yêu cầu không chứa gì ngoài thông tin trên.')
        hint.setWordWrap(True)
        lay.addWidget(hint)

        row = QHBoxLayout()
        row.addStretch(1)
        b_save = QPushButton('Lưu file yêu cầu…')
        b_save.clicked.connect(self._save_request)
        row.addWidget(b_save)
        lay.addLayout(row)
        lay.addStretch(1)
        return page

    # ── thẻ Sử dụng ───────────────────────────────────────────────────────
    def _tab_usage(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        self.lb_usage = QLabel()
        self.lb_usage.setWordWrap(True)
        self.lb_usage.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.lb_usage)

        note = QLabel('Phần mềm chỉ đếm số lần, không ghi tên bản vẽ, đường dẫn '
                      'hay bất kỳ số liệu tính toán nào.')
        note.setWordWrap(True)
        lay.addWidget(note)

        lay.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        b_export = QPushButton('Xuất báo cáo sử dụng…')
        b_export.setToolTip('Gửi file này cho người cấp phép khi gia hạn')
        b_export.clicked.connect(self._export_usage)
        row.addWidget(b_export)
        lay.addLayout(row)
        return page

    # ── việc ──────────────────────────────────────────────────────────────
    def refresh(self) -> None:
        state = guard.get_runtime_state()
        if state.source == guard.SOURCE_LICENSE and state.ready:
            level = _OK
        elif state.source == guard.SOURCE_TRIAL and state.ready:
            level = _WARN
        elif state.source == guard.SOURCE_DEV:
            level = _WARN
        else:
            level = _BAD
        self.banner.setStyleSheet(_banner_qss(self.t, level))
        self.banner.setText(state.message)

        lines = []
        info = state.license
        if info is not None:
            left = info.days_remaining()
            lines += [
                f'Cấp cho: {info.customer}' + (f' · {info.company}' if info.company else ''),
                f'Mã giấy phép: {info.license_id}',
                f'Hiệu lực: {info.issued_at} → {info.expires_at}'
                + (f' (còn {left} ngày)' if left is not None else ''),
                f'Tính năng: {info.feature_text}',
            ]
            if state.path:
                lines.append(f'File: {state.path}')
        else:
            # KHÔNG lặp lại câu đã nằm trên dải trạng thái ngay phía trên: đọc
            # hai lần cùng một dòng thì mắt bỏ qua cả hai.
            st = trial.get_trial_status(start_if_missing=False)
            if st.started_at:
                lines.append(f'Bắt đầu dùng thử: {st.started_at}'
                             + (f' · hết ngày {st.expires_on}' if st.expires_on else ''))
            lines.append('Chưa có giấy phép trên máy này. Sang thẻ '
                         '"Xin cấp giấy phép" để tạo file yêu cầu; bản dùng thử '
                         f'{trial.TRIAL_DAYS} ngày mở đầy đủ tính năng.')
        self.lb_detail.setText('\n'.join(lines))
        # Chưa có giấy phép thì không có gì để gỡ. Để nút mở thì bấm vào chỉ
        # nhận được một hộp thoại nói "không có file nào" — vô ích.
        self.b_remove.setEnabled(info is not None)
        self.lb_checkpoint.setText('\n'.join(checkpoint.status_lines(info)))
        self.lb_usage.setText('\n'.join(usage_log.summary_lines()))
        self.ed_machine.setText(get_machine_id())

    def _copy_machine(self) -> None:
        QGuiApplication.clipboard().setText(get_machine_id())
        QMessageBox.information(self, 'Đã chép', 'Đã chép mã máy vào bộ nhớ tạm.')

    def _open_license_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, 'Chọn file giấy phép', '',
            'Giấy phép (*.mtblic *.txt);;Tất cả (*.*)')
        if not path:
            return
        try:
            self.ed_token.setPlainText(open(path, encoding='utf-8').read().strip())
        except OSError as exc:
            QMessageBox.warning(self, 'Không đọc được', str(exc))
            return
        self._preview_token()

    def _token_text(self) -> str:
        return self.ed_token.toPlainText().strip()

    def _preview_token(self) -> lm.LicenseStatus | None:
        token = self._token_text()
        if not token:
            self.lb_preview.setText('Chưa có nội dung giấy phép.')
            return None
        status = lm.inspect_license_token(token)
        lines = [status.message]
        if status.info is not None:
            lines += [f'Cấp cho: {status.info.customer}',
                      f'Máy: {status.info.machine_id}',
                      f'Hạn: {status.info.expires_at}',
                      f'Tính năng: {status.info.feature_text}']
        self.lb_preview.setText('\n'.join(lines))
        return status

    def _activate(self) -> None:
        status = self._preview_token()
        if status is None:
            return
        if not status.ok:
            QMessageBox.warning(self, 'Chưa kích hoạt được', status.message)
            return
        try:
            written = lm.save_license(status.token)
        except lm.LicenseError as exc:
            QMessageBox.critical(self, 'Không ghi được giấy phép', str(exc))
            return

        # Ghi xong đọc LẠI từ đĩa: đó mới là thứ lần chạy sau nhìn thấy.
        after = guard.get_runtime_state()
        self.refresh()
        if after.ready:
            QMessageBox.information(
                self, 'Đã kích hoạt',
                status.message + '\n\nĐã ghi vào:\n'
                + '\n'.join(str(p) for p in written))
        else:
            QMessageBox.warning(self, 'Ghi xong nhưng chưa dùng được', after.message)

    def _remove_license(self) -> None:
        if QMessageBox.question(
                self, 'Gỡ giấy phép',
                'Xoá giấy phép khỏi máy này?\nPhần mềm sẽ trở lại trạng thái '
                'chưa kích hoạt.') != QMessageBox.StandardButton.Yes:
            return
        removed = lm.remove_license()
        self.refresh()
        QMessageBox.information(self, 'Đã gỡ',
                                'Đã xoá:\n' + '\n'.join(str(p) for p in removed)
                                if removed else 'Không có file nào để xoá.')

    def _save_request(self) -> None:
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, 'Thiếu tên', 'Nhập họ tên để người cấp biết là ai.')
            return
        payload = lm.build_request(name, self.ed_email.text(),
                                   self.ed_company.text(), self.ed_note.text(),
                                   self.sp_days.value(), self.app_version)
        default = f"{name.replace(' ', '_')}_{datetime.now():%Y%m%d}.mtbreq"
        path, _ = QFileDialog.getSaveFileName(self, 'Lưu file yêu cầu', default,
                                              'Yêu cầu cấp phép (*.mtbreq)')
        if not path:
            return
        import json
        try:
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
        except OSError as exc:
            QMessageBox.critical(self, 'Không lưu được', str(exc))
            return
        QMessageBox.information(
            self, 'Đã lưu yêu cầu',
            f'Đã lưu:\n{path}\n\nGửi file này cho người cấp giấy phép.')

    def _export_usage(self) -> None:
        state = guard.get_runtime_state()
        default = f'su-dung_{get_machine_id()[:8]}_{datetime.now():%Y%m%d}.mtbusage'
        path, _ = QFileDialog.getSaveFileName(self, 'Xuất báo cáo sử dụng', default,
                                              'Báo cáo sử dụng (*.mtbusage)')
        if not path:
            return
        try:
            usage_log.export_report(path, state.license)
        except OSError as exc:
            QMessageBox.critical(self, 'Không xuất được', str(exc))
            return
        QMessageBox.information(self, 'Đã xuất', f'Đã lưu:\n{path}')

    def _sync_now(self) -> None:
        state = guard.get_runtime_state()
        result = checkpoint.sync(state.license, app_version=self.app_version)
        self.refresh()
        if not result.configured:
            QMessageBox.information(self, 'Điểm hẹn',
                                    'Giấy phép này không cấu hình điểm hẹn theo dõi.')
        elif result.ok:
            QMessageBox.information(self, 'Điểm hẹn', result.message)
        else:
            QMessageBox.warning(self, 'Không đồng bộ được',
                                result.message + '\n\nPhần mềm vẫn chạy bình thường.')


def show_license_dialog(parent=None, theme: dict | None = None,
                        app_version: str = '') -> bool:
    """Mở hộp thoại; trả về True nếu sau khi đóng đã ở trạng thái chạy được."""
    dlg = LicenseDialog(parent, theme, app_version)
    dlg.exec()
    return guard.get_runtime_state().ready

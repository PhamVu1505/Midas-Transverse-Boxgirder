"""Công cụ cấp phép và theo dõi — CHỈ DÙNG NỘI BỘ.

    python tools/license_admin.py

Bốn thẻ, đi đúng theo trình tự công việc:

    Yêu cầu     nạp file .mtbreq khách gửi → cấp giấy phép .mtblic
    Giấy phép   ai đang giữ giấy phép nào, còn bao nhiêu ngày, thu hồi ở đâu
    Máy đang dùng  ai thật sự đang chạy phần mềm, lần cuối khi nào, làm bao nhiêu
    Thư mục đồng bộ  công bố danh sách chặn, nạp nhịp tim

KHÔNG BAO GIỜ gửi công cụ này — hay thư mục secrets/ — cho người dùng cuối. Nó
ký được giấy phép, tức ai có nó thì tự cấp cho mình được.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateEdit,
                             QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
                             QHeaderView, QInputDialog, QLabel, QLineEdit,
                             QMainWindow, QMessageBox, QPushButton,
                             QTableWidget, QTableWidgetItem, QTabWidget,
                             QVBoxLayout, QWidget)

from src.security import checkpoint, license_manager as lm, signing
from src.security.hwid import normalize_machine_id
from tools.license_registry import (LicenseRegistry, STATUS_REVOKED,
                                    REQ_PENDING, REQ_ARCHIVED, DEFAULT_DB)

APP_TITLE = 'Cấp phép & theo dõi — Midas Transverse Boxgirder'


def _cell(text, *, mono=False, align_right=False) -> QTableWidgetItem:
    item = QTableWidgetItem('' if text is None else str(text))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    if align_right:
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight
                              | Qt.AlignmentFlag.AlignVCenter)
    return item


def _fill(table: QTableWidget, headers: list[str], rows: list[list]) -> None:
    table.clear()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            table.setItem(r, c, _cell(value))
    table.resizeColumnsToContents()
    table.horizontalHeader().setStretchLastSection(True)


class AdminWindow(QMainWindow):
    def __init__(self, db_path: str | Path = DEFAULT_DB):
        super().__init__()
        self.reg = LicenseRegistry(db_path)
        self.setWindowTitle(f'{APP_TITLE} — {Path(db_path).name}')
        self.resize(1180, 720)

        central = QWidget()
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        self.lb_summary = QLabel()
        self.lb_summary.setStyleSheet('font-weight:600')
        lay.addWidget(self.lb_summary)

        self.lb_key = QLabel()
        self.lb_key.setWordWrap(True)
        lay.addWidget(self.lb_key)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_requests(), 'Yêu cầu')
        self.tabs.addTab(self._tab_licenses(), 'Giấy phép')
        self.tabs.addTab(self._tab_machines(), 'Máy đang dùng')
        self.tabs.addTab(self._tab_checkpoint(), 'Thư mục đồng bộ')
        lay.addWidget(self.tabs, 1)

        self.refresh()

    # ── thẻ Yêu cầu ───────────────────────────────────────────────────────
    def _tab_requests(self) -> QWidget:
        page = QWidget()
        lay = QHBoxLayout(page)

        left = QVBoxLayout()
        bar = QHBoxLayout()
        b_imp = QPushButton('Nạp file .mtbreq…')
        b_imp.clicked.connect(self._import_requests)
        bar.addWidget(b_imp)
        self.cb_req_status = QComboBox()
        self.cb_req_status.addItems(['Tất cả', REQ_PENDING, 'Đã cấp', REQ_ARCHIVED])
        self.cb_req_status.currentIndexChanged.connect(self.refresh)
        bar.addWidget(self.cb_req_status)
        bar.addStretch(1)
        left.addLayout(bar)

        self.tb_req = QTableWidget()
        self.tb_req.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tb_req.itemSelectionChanged.connect(self._on_request_selected)
        left.addWidget(self.tb_req, 1)
        lay.addLayout(left, 3)

        box = QGroupBox('Cấp giấy phép')
        form = QFormLayout(box)
        self.ed_machine = QLineEdit()
        self.ed_machine.setPlaceholderText('Dán mã máy nếu cấp không qua file yêu cầu')
        self.ed_customer = QLineEdit()
        self.ed_company = QLineEdit()
        self.ed_email = QLineEdit()
        self.ed_note = QLineEdit()
        self.de_expiry = QDateEdit()
        self.de_expiry.setCalendarPopup(True)
        self.de_expiry.setDisplayFormat('yyyy-MM-dd')
        self.de_expiry.setDate(QDate.currentDate().addDays(lm.DEFAULT_TERM_DAYS))
        self.ed_checkpoint = QLineEdit()
        self.ed_checkpoint.setPlaceholderText('Để trống nếu không cần theo dõi và thu hồi từ xa')

        form.addRow('Mã máy:', self.ed_machine)
        form.addRow('Người dùng:', self.ed_customer)
        form.addRow('Đơn vị:', self.ed_company)
        form.addRow('Email:', self.ed_email)
        form.addRow('Hết hạn:', self.de_expiry)
        form.addRow('Thư mục đồng bộ:', self.ed_checkpoint)
        form.addRow('Ghi chú:', self.ed_note)

        self.ck_features = {}
        feat_box = QWidget()
        feat_lay = QVBoxLayout(feat_box)
        feat_lay.setContentsMargins(0, 0, 0, 0)
        self.ck_all = QCheckBox('Mở tất cả tính năng')
        self.ck_all.setChecked(True)
        self.ck_all.toggled.connect(self._toggle_features)
        feat_lay.addWidget(self.ck_all)
        for key, label in lm.FEATURES.items():
            ck = QCheckBox(label)
            ck.setChecked(True)
            ck.setEnabled(False)
            self.ck_features[key] = ck
            feat_lay.addWidget(ck)
        form.addRow('Tính năng:', feat_box)

        b_issue = QPushButton('Cấp giấy phép…')
        b_issue.clicked.connect(self._issue)
        form.addRow(b_issue)

        # Cộng theo THÁNG chứ không theo 30 ngày: khách chọn 6 tháng thì hạn
        # phải rơi đúng ngày ấy sáu tháng sau. Vĩnh viễn = mốc rất xa, không
        # phải một nhánh riêng trong mã.
        quick = QHBoxLayout()
        for months, label in lm.TERM_CHOICES:
            b = QPushButton(label)
            b.clicked.connect(lambda _=False, m=months: self.de_expiry.setDate(
                QDate.fromString(lm.expiry_after_months(m), 'yyyy-MM-dd')))
            quick.addWidget(b)
        form.addRow('Thời hạn:', self._wrap(quick))

        lay.addWidget(box, 2)
        return page

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        return w

    def _toggle_features(self, on: bool) -> None:
        for ck in self.ck_features.values():
            ck.setEnabled(not on)
            if on:
                ck.setChecked(True)

    def _selected_features(self) -> list[str]:
        if self.ck_all.isChecked():
            return ['all']
        chosen = [k for k, ck in self.ck_features.items() if ck.isChecked()]
        return chosen or ['all']

    def _import_requests(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, 'Chọn file yêu cầu', '', 'Yêu cầu (*.mtbreq *.json)')
        loaded, bad = 0, []
        for path in paths:
            try:
                payload = json.loads(Path(path).read_text(encoding='utf-8'))
                self.reg.import_request(payload, source_path=path)
                loaded += 1
            except Exception as exc:
                bad.append(f'{Path(path).name}: {exc}')
        self.refresh()
        if bad:
            QMessageBox.warning(self, 'Có file không nạp được',
                                f'Nạp {loaded} file.\n\n' + '\n'.join(bad))

    def _on_request_selected(self) -> None:
        row = self.tb_req.currentRow()
        if row < 0 or row >= len(self._requests):
            return
        req = self._requests[row]
        self.ed_machine.setText(req.machine_id)
        self.ed_customer.setText(req.display_name)
        self.ed_company.setText(req.company)
        self.ed_email.setText(req.email)
        self.ed_note.setText(req.note)
        if req.requested_expires_at:
            qd = QDate.fromString(req.requested_expires_at, 'yyyy-MM-dd')
            if qd.isValid():
                self.de_expiry.setDate(qd)

    def _issue(self) -> None:
        machine = normalize_machine_id(self.ed_machine.text())
        customer = self.ed_customer.text().strip()
        if not machine:
            QMessageBox.warning(self, 'Thiếu mã máy', 'Chọn một yêu cầu hoặc dán mã máy.')
            return
        if not customer:
            QMessageBox.warning(self, 'Thiếu tên', 'Nhập tên người dùng/đơn vị.')
            return
        try:
            key = signing.load_private_key()
        except signing.SignatureError as exc:
            QMessageBox.critical(self, 'Không có khoá riêng', str(exc))
            return

        expires = self.de_expiry.date().toString('yyyy-MM-dd')
        try:
            token, info = lm.generate_license(
                machine, expires, customer=customer,
                features=self._selected_features(),
                email=self.ed_email.text(), company=self.ed_company.text(),
                note=self.ed_note.text(),
                checkpoint=self.ed_checkpoint.text().strip(),
                private_key=key)
        except Exception as exc:
            QMessageBox.critical(self, 'Không cấp được', str(exc))
            return

        safe = ''.join(c if c.isalnum() or c in '-_' else '_' for c in customer)[:40]
        default = str(Path.home() / 'Desktop' / f'{safe}_{expires}.mtblic')
        path, _ = QFileDialog.getSaveFileName(self, 'Lưu giấy phép', default,
                                              'Giấy phép (*.mtblic)')
        if not path:
            return
        Path(path).write_text(token + '\n', encoding='utf-8')

        row = self.tb_req.currentRow()
        request_id = (self._requests[row].request_id
                      if 0 <= row < len(self._requests)
                      and self._requests[row].machine_id == machine else '')
        machine_label = (self._requests[row].machine_label
                         if 0 <= row < len(self._requests) else '')
        self.reg.record_license(info, token, machine_label=machine_label,
                                request_id=request_id)
        self.refresh()
        QMessageBox.information(
            self, 'Đã cấp',
            f'Đã lưu:\n{path}\n\nCấp cho: {customer}\nMáy: {machine}\n'
            f'Hết hạn: {expires}\nTính năng: {info.feature_text}\n\n'
            'Gửi file này cho người dùng; họ nạp ở Trợ giúp → Giấy phép → Kích hoạt.')

    # ── thẻ Giấy phép ─────────────────────────────────────────────────────
    def _tab_licenses(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)

        bar = QHBoxLayout()
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText('Tìm theo tên, đơn vị, mã máy…')
        self.ed_search.textChanged.connect(self.refresh)
        bar.addWidget(self.ed_search, 1)
        for label, slot in (('Thu hồi…', self._revoke),
                            ('Bỏ thu hồi', self._unrevoke),
                            ('Lưu lại .mtblic…', self._resave),
                            ('Xuất CSV…', self._export_licenses)):
            b = QPushButton(label)
            b.clicked.connect(slot)
            bar.addWidget(b)
        lay.addLayout(bar)

        self.tb_lic = QTableWidget()
        self.tb_lic.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        lay.addWidget(self.tb_lic, 1)
        return page

    def _current_license(self):
        row = self.tb_lic.currentRow()
        if row < 0 or row >= len(self._licenses):
            QMessageBox.information(self, 'Chưa chọn', 'Chọn một dòng giấy phép.')
            return None
        return self._licenses[row]

    def _revoke(self) -> None:
        row = self._current_license()
        if row is None:
            return
        reason, ok = QInputDialog.getText(
            self, 'Thu hồi giấy phép',
            f'Lý do thu hồi ({row.customer}):\n\nLý do này hiện ra trên màn hình '
            'người dùng khi phần mềm bị chặn.')
        if not ok:
            return
        self.reg.revoke(row.license_id, reason.strip())
        self.refresh()
        QMessageBox.information(
            self, 'Đã ghi vào sổ',
            'Đã đánh dấu thu hồi.\n\nMáy đó CHƯA bị chặn cho tới khi bạn sang '
            'thẻ "Thư mục đồng bộ" và bấm Công bố danh sách chặn.')

    def _unrevoke(self) -> None:
        row = self._current_license()
        if row is None:
            return
        self.reg.unrevoke(row.license_id)
        self.refresh()

    def _resave(self) -> None:
        row = self._current_license()
        if row is None:
            return
        if not row.token:
            QMessageBox.warning(self, 'Không có bản sao',
                                'Sổ không giữ chuỗi giấy phép này. Cấp lại giấy '
                                'phép mới cho máy đó.')
            return
        path, _ = QFileDialog.getSaveFileName(
            self, 'Lưu lại giấy phép',
            str(Path.home() / 'Desktop' / f'{row.customer}_{row.expires_at}.mtblic'),
            'Giấy phép (*.mtblic)')
        if path:
            Path(path).write_text(row.token + '\n', encoding='utf-8')

    def _export_licenses(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, 'Xuất danh sách giấy phép',
            str(Path.home() / f'giay-phep_{date.today()}.csv'), 'CSV (*.csv)')
        if path:
            self.reg.export_licenses_csv(path, self._licenses)
            QMessageBox.information(self, 'Đã xuất', path)

    # ── thẻ Máy đang dùng ─────────────────────────────────────────────────
    def _tab_machines(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)

        bar = QHBoxLayout()
        for label, slot in (('Nạp nhịp tim từ thư mục đồng bộ', self._pull_heartbeats),
                            ('Nạp file .mtbusage…', self._import_usage),
                            ('Chặn máy này…', self._block_machine),
                            ('Bỏ chặn', self._unblock_machine),
                            ('Xuất CSV…', self._export_machines)):
            b = QPushButton(label)
            b.clicked.connect(slot)
            bar.addWidget(b)
        bar.addStretch(1)
        lay.addLayout(bar)

        self.tb_mach = QTableWidget()
        self.tb_mach.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        lay.addWidget(self.tb_mach, 1)

        self.lb_blocks = QLabel()
        self.lb_blocks.setWordWrap(True)
        lay.addWidget(self.lb_blocks)
        return page

    def _pull_heartbeats(self) -> None:
        root = self.ed_cp.text().strip()
        if not root:
            QMessageBox.information(self, 'Chưa có thư mục đồng bộ',
                                    'Điền thư mục ở thẻ "Thư mục đồng bộ".')
            return
        try:
            n = self.reg.import_heartbeats(root)
        except Exception as exc:
            QMessageBox.warning(self, 'Không đọc được', str(exc))
            return
        self.refresh()
        QMessageBox.information(self, 'Đã nạp', f'Đọc {n} nhịp tim.')

    def _import_usage(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, 'Chọn báo cáo sử dụng', '', 'Báo cáo (*.mtbusage *.json)')
        for path in paths:
            try:
                self.reg.import_usage_report(path)
            except Exception as exc:
                QMessageBox.warning(self, 'Không nạp được', f'{path}\n{exc}')
        self.refresh()

    def _current_machine(self):
        row = self.tb_mach.currentRow()
        if row < 0 or row >= len(self._machines):
            QMessageBox.information(self, 'Chưa chọn', 'Chọn một dòng máy.')
            return None
        return self._machines[row]

    def _block_machine(self) -> None:
        row = self._current_machine()
        if row is None:
            return
        reason, ok = QInputDialog.getText(self, 'Chặn máy',
                                          f'Lý do chặn {row.machine_label or row.machine_id}:')
        if ok:
            self.reg.block_machine(row.machine_id, reason)
            self.refresh()

    def _unblock_machine(self) -> None:
        row = self._current_machine()
        if row is None:
            return
        self.reg.unblock_machine(row.machine_id)
        self.refresh()

    def _export_machines(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, 'Xuất danh sách máy',
            str(Path.home() / f'may-dung_{date.today()}.csv'), 'CSV (*.csv)')
        if path:
            self.reg.export_machines_csv(path)
            QMessageBox.information(self, 'Đã xuất', path)

    # ── thẻ Điểm hẹn ──────────────────────────────────────────────────────
    def _tab_checkpoint(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)

        row = QHBoxLayout()
        row.addWidget(QLabel('Thư mục đồng bộ:'))
        self.ed_cp = QLineEdit(os.environ.get('MTB_CHECKPOINT', ''))
        row.addWidget(self.ed_cp, 1)
        b_pick = QPushButton('Chọn…')
        b_pick.clicked.connect(self._pick_checkpoint)
        row.addWidget(b_pick)
        lay.addLayout(row)

        note = QLabel(
            'Thư mục dùng chung giữa bạn và người dùng: ổ mạng nội bộ, OneDrive '
            'hay Google Drive đồng bộ, đều được.\n\n'
            'Máy người dùng lặng lẽ thả vào đây một tệp nhỏ báo còn đang chạy, và '
            'đọc ngược về danh sách máy bị thu hồi. Người dùng không thấy và không '
            'chọn được: đường dẫn do bạn điền lúc cấp (ô "Thư mục đồng bộ" ở thẻ '
            'Yêu cầu) và nằm trong phần đã ký của giấy phép.\n\n'
            'ĐỂ TRỐNG CŨNG ĐƯỢC — phần mềm vẫn chạy bình thường, chỉ mất phần theo '
            'dõi từ xa và chặn nhanh; vẫn cắt được bằng cách không gia hạn.')
        note.setWordWrap(True)
        lay.addWidget(note)

        bar = QHBoxLayout()
        b_pub = QPushButton('Công bố danh sách chặn')
        b_pub.clicked.connect(self._publish)
        bar.addWidget(b_pub)
        b_clear = QPushButton('Xoá danh sách chặn khỏi thư mục đồng bộ')
        b_clear.clicked.connect(self._clear_blocklist)
        bar.addWidget(b_clear)
        bar.addStretch(1)
        lay.addLayout(bar)

        self.lb_cp = QLabel()
        self.lb_cp.setWordWrap(True)
        self.lb_cp.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.lb_cp)
        lay.addStretch(1)
        return page

    def _pick_checkpoint(self) -> None:
        path = QFileDialog.getExistingDirectory(self, 'Chọn thư mục đồng bộ',
                                                self.ed_cp.text())
        if path:
            self.ed_cp.setText(path)
            self.refresh()

    def _publish(self) -> None:
        root = self.ed_cp.text().strip()
        if not root:
            QMessageBox.information(self, 'Chưa có thư mục đồng bộ', 'Chọn thư mục trước.')
            return
        entries = self.reg.blocklist_entries()
        try:
            key = signing.load_private_key()
            target = checkpoint.publish_blocklist(root, entries, key)
        except Exception as exc:
            QMessageBox.critical(self, 'Không công bố được', str(exc))
            return
        self.refresh()
        QMessageBox.information(
            self, 'Đã công bố',
            f'{target}\n\n{len(entries)} mục chặn.\n\nMáy khách nhận được ở lần '
            'chạy sau, khi nó đồng bộ với thư mục này.')

    def _clear_blocklist(self) -> None:
        root = self.ed_cp.text().strip()
        target = Path(root) / checkpoint.BLOCKLIST_NAME if root else None
        if not target or not target.exists():
            QMessageBox.information(self, 'Không có gì để xoá', 'Thư mục đồng bộ chưa có '
                                                                'danh sách chặn.')
            return
        if QMessageBox.question(self, 'Xoá danh sách chặn',
                                'Xoá file danh sách chặn khỏi thư mục đồng bộ?\n'
                                'Mọi máy đang bị chặn sẽ chạy lại được sau lần '
                                'đồng bộ tới.') == QMessageBox.StandardButton.Yes:
            target.unlink()
            self.refresh()

    # ── làm mới ───────────────────────────────────────────────────────────
    def refresh(self) -> None:
        s = self.reg.summary()
        self.lb_summary.setText(
            f"Giấy phép: {s['licenses']} (còn hiệu lực {s['active_licenses']} · "
            f"hết hạn {s['expired']} · thu hồi {s['revoked']}) · "
            f"sắp hết hạn ≤30 ngày: {s['expiring_30d']} · "
            f"yêu cầu chờ: {s['requests_pending']} · "
            f"máy đã thấy: {s['machines']} (đang dùng 30 ngày: {s['machines_active']}) · "
            f"tổng {s['sessions']} lần mở · {s['mct']} file MCT")

        try:
            key = signing.load_private_key()
            self.lb_key.setText(f"Khoá ký: {key.get('key_id')} · vân tay "
                                f'{signing.key_fingerprint(key.get("key_id"))[:16]}…')
        except Exception as exc:
            self.lb_key.setText(f'KHÔNG CÓ KHOÁ RIÊNG — chưa cấp được giấy phép. {exc}')

        want = self.cb_req_status.currentText()
        self._requests = self.reg.list_requests(
            status='all' if want == 'Tất cả' else want)
        _fill(self.tb_req,
              ['Người dùng', 'Đơn vị', 'Mã máy', 'Tên máy', 'Xin đến', 'Trạng thái', 'Nhận lúc'],
              [[r.user_name or r.display_name, r.company, r.machine_id, r.machine_label,
                r.requested_expires_at, r.status, r.imported_at] for r in self._requests])

        self._licenses = self.reg.list_licenses(search=self.ed_search.text())
        _fill(self.tb_lic,
              ['Người dùng', 'Đơn vị', 'Mã máy', 'Cấp', 'Hết hạn', 'Còn (ngày)',
               'Tính năng', 'Trạng thái', 'Lý do thu hồi'],
              [[r.customer, r.company, r.machine_id, r.issued_at, r.expires_at,
                r.days_remaining(), r.feature_text, r.status, r.revoke_reason]
               for r in self._licenses])

        self._machines = self.reg.list_machines()
        _fill(self.tb_mach,
              ['Mã máy', 'Tên máy', 'Người dùng', 'Phiên bản', 'Lần cuối',
               'Im (ngày)', 'Đang dùng', 'Lần mở', 'MCT', 'Midas', 'Kiểm toán',
               'Chuột phải', 'Nguồn'],
              [[m.machine_id, m.machine_label, m.customer, m.app_version,
                m.last_seen, m.days_idle(), 'có' if m.is_active() else '',
                (m.counters or {}).get('sessions', 0), (m.counters or {}).get('mct', 0),
                (m.counters or {}).get('midas', 0), (m.counters or {}).get('check', 0),
                (m.counters or {}).get('context_menu', 0), m.source]
               for m in self._machines])

        blocks = self.reg.blocklist_entries()
        self.lb_blocks.setText(
            f'Danh sách chặn hiện có {len(blocks)} mục: '
            + ('; '.join(f"{b.get('machine_id', b.get('license_id'))} — {b['reason']}"
                         for b in blocks) if blocks else 'không có mục nào.'))

        root = self.ed_cp.text().strip() if hasattr(self, 'ed_cp') else ''
        lines = []
        if root:
            target = Path(root) / checkpoint.BLOCKLIST_NAME
            lines.append(f'Danh sách chặn ở thư mục đồng bộ: '
                         + (str(target) if target.exists() else 'chưa công bố'))
            beat_dir = Path(root) / checkpoint.HEARTBEAT_DIR
            n = len(list(beat_dir.glob('*.json'))) if beat_dir.exists() else 0
            lines.append(f'Nhịp tim ở thư mục đồng bộ: {n} máy')
        else:
            lines.append('Chưa chọn thư mục đồng bộ.')
        if hasattr(self, 'lb_cp'):
            self.lb_cp.setText('\n'.join(lines))


def main() -> int:
    app = QApplication(sys.argv)
    db = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    win = AdminWindow(db)
    win.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())

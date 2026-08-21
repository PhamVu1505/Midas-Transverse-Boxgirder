"""Sổ cấp phép của người quản trị — SQLite, chạy hoàn toàn ngoại tuyến.

CHỈ CHẠY Ở MÁY NGƯỜI CẤP. File này cố ý nằm ở tools/ chứ không phải src/ vì
hai lẽ:

* nó dùng sqlite3, mà installer/build.bat đang loại trừ module đó khỏi bản
  đóng gói cho khách — để nhầm vào src/ rồi lỡ nhập từ GUI là bản đóng gói vỡ;
* ai đọc mã cũng thấy ngay ranh giới: máy khách không bao giờ chạm vào sổ này.

Ba loại bản ghi:

    requests   yêu cầu cấp phép nhận từ khách (.mtbreq)
    licenses   giấy phép đã cấp, kèm trạng thái Issued/Activated/Expired/Revoked
    machines   máy đã thấy hoạt động, gộp từ nhịp tim ở điểm hẹn và từ file
               .mtbusage khách gửi về

Danh sách chặn công bố ra điểm hẹn được dựng từ chính sổ này: mọi giấy phép
Revoked, cộng các máy chặn tay.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.security.hwid import normalize_machine_id                # noqa: E402
from src.security.license_manager import LicenseInfo              # noqa: E402

STATUS_ISSUED = 'Đã cấp'
STATUS_ACTIVE = 'Đang dùng'
STATUS_EXPIRED = 'Hết hạn'
STATUS_REVOKED = 'Đã thu hồi'
STATUSES = (STATUS_ISSUED, STATUS_ACTIVE, STATUS_EXPIRED, STATUS_REVOKED)

REQ_PENDING = 'Chờ xử lý'
REQ_ISSUED = 'Đã cấp'
REQ_ARCHIVED = 'Lưu trữ'

# Sổ nằm cạnh khoá riêng: cùng một thư mục bí mật, cùng một chế độ sao lưu.
# Bản đóng gói thì cạnh exe (ROOT trong gói là ruột _internal, không phải chỗ
# người vận hành nhìn thấy).
DEFAULT_DB = ((Path(sys.executable).resolve().parent
               if getattr(sys, 'frozen', False) else ROOT)
              / 'secrets' / 'license_admin.sqlite3')

#: Máy có nhịp tim trong ngần này ngày thì tính là "đang dùng".
ACTIVE_WINDOW_DAYS = 30


def _now() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


@dataclass(frozen=True)
class LicenseRow:
    license_id: str
    customer: str
    machine_id: str
    issued_at: str
    expires_at: str
    features: tuple[str, ...]
    status: str
    email: str = ''
    company: str = ''
    note: str = ''
    machine_label: str = ''
    token: str = ''
    revoke_reason: str = ''
    activated_at: str = ''
    created_at: str = ''
    updated_at: str = ''

    def days_remaining(self, today: date | None = None) -> int | None:
        try:
            expiry = datetime.strptime(self.expires_at, '%Y-%m-%d').date()
        except ValueError:
            return None
        return (expiry - (today or date.today())).days

    @property
    def feature_text(self) -> str:
        return 'tất cả' if 'all' in self.features else ', '.join(self.features)


@dataclass(frozen=True)
class RequestRow:
    request_id: str
    machine_id: str
    user_name: str = ''
    email: str = ''
    company: str = ''
    machine_label: str = ''
    requested_expires_at: str = ''
    note: str = ''
    app_version: str = ''
    status: str = REQ_PENDING
    source_path: str = ''
    created_at: str = ''
    imported_at: str = ''
    license_id: str = ''

    @property
    def display_name(self) -> str:
        if self.company and self.user_name:
            return f'{self.company} — {self.user_name}'
        return self.company or self.user_name or self.email or self.machine_id


@dataclass(frozen=True)
class MachineRow:
    machine_id: str
    machine_label: str = ''
    customer: str = ''
    license_id: str = ''
    expires_at: str = ''
    app_version: str = ''
    first_seen: str = ''
    last_seen: str = ''
    counters: dict = None
    source: str = ''
    tampered: bool = False

    def days_idle(self, now: datetime | None = None) -> int | None:
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                seen = datetime.strptime(self.last_seen, fmt)
            except (ValueError, TypeError):
                continue
            return ((now or datetime.now()) - seen).days
        return None

    def is_active(self, now: datetime | None = None) -> bool:
        idle = self.days_idle(now)
        return idle is not None and idle <= ACTIVE_WINDOW_DAYS


class LicenseRegistry:
    """Sổ cấp phép. Mở nhiều lần cùng một file là an toàn."""

    def __init__(self, path: str | Path = DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    # ── nền ───────────────────────────────────────────────────────────────
    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def _ensure_schema(self) -> None:
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS licenses (
                    license_id TEXT PRIMARY KEY,
                    customer TEXT NOT NULL,
                    machine_id TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    features_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    email TEXT NOT NULL DEFAULT '',
                    company TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    machine_label TEXT NOT NULL DEFAULT '',
                    token TEXT NOT NULL DEFAULT '',
                    revoke_reason TEXT NOT NULL DEFAULT '',
                    activated_at TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )""")
            con.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    request_id TEXT PRIMARY KEY,
                    machine_id TEXT NOT NULL,
                    user_name TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    company TEXT NOT NULL DEFAULT '',
                    machine_label TEXT NOT NULL DEFAULT '',
                    requested_expires_at TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    app_version TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    source_path TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT '',
                    imported_at TEXT NOT NULL,
                    license_id TEXT NOT NULL DEFAULT ''
                )""")
            con.execute("""
                CREATE TABLE IF NOT EXISTS machines (
                    machine_id TEXT PRIMARY KEY,
                    machine_label TEXT NOT NULL DEFAULT '',
                    customer TEXT NOT NULL DEFAULT '',
                    license_id TEXT NOT NULL DEFAULT '',
                    expires_at TEXT NOT NULL DEFAULT '',
                    app_version TEXT NOT NULL DEFAULT '',
                    first_seen TEXT NOT NULL DEFAULT '',
                    last_seen TEXT NOT NULL DEFAULT '',
                    counters_json TEXT NOT NULL DEFAULT '{}',
                    source TEXT NOT NULL DEFAULT '',
                    tampered INTEGER NOT NULL DEFAULT 0
                )""")
            con.execute("""
                CREATE TABLE IF NOT EXISTS blocks (
                    machine_id TEXT PRIMARY KEY,
                    reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )""")
            con.execute('CREATE INDEX IF NOT EXISTS idx_lic_machine ON licenses(machine_id)')
            con.execute('CREATE INDEX IF NOT EXISTS idx_lic_status ON licenses(status)')
            con.execute('CREATE INDEX IF NOT EXISTS idx_req_status ON requests(status)')

    # ── giấy phép ─────────────────────────────────────────────────────────
    def record_license(self, info: LicenseInfo, token: str, *,
                       machine_label: str = '', request_id: str = '') -> LicenseRow:
        now = _now()
        with self._connect() as con:
            con.execute("""
                INSERT OR REPLACE INTO licenses (
                    license_id, customer, machine_id, issued_at, expires_at,
                    features_json, status, email, company, note, machine_label,
                    token, revoke_reason, activated_at, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                        COALESCE((SELECT created_at FROM licenses WHERE license_id=?), ?), ?)
                """, (info.license_id, info.customer, info.machine_id, info.issued_at,
                      info.expires_at, json.dumps(list(info.features)), STATUS_ISSUED,
                      info.email, info.company, info.note, machine_label, token, '', '',
                      info.license_id, now, now))
            if request_id:
                con.execute('UPDATE requests SET status=?, license_id=? WHERE request_id=?',
                            (REQ_ISSUED, info.license_id, request_id))
        return self.get_license(info.license_id)

    def get_license(self, license_id: str) -> LicenseRow | None:
        with self._connect() as con:
            row = con.execute('SELECT * FROM licenses WHERE license_id=?',
                              (license_id,)).fetchone()
        return self._license_row(row) if row else None

    def list_licenses(self, *, search: str = '', status: str = 'all') -> list[LicenseRow]:
        with self._connect() as con:
            rows = con.execute('SELECT * FROM licenses ORDER BY created_at DESC').fetchall()
        out = [self._license_row(r) for r in rows]
        if status != 'all':
            out = [r for r in out if r.status == status]
        if search:
            needle = search.strip().lower()
            out = [r for r in out
                   if needle in ' '.join([r.customer, r.machine_id, r.email, r.company,
                                          r.note, r.license_id, r.machine_label]).lower()]
        return out

    def set_status(self, license_id: str, status: str, *, reason: str = '') -> None:
        if status not in STATUSES:
            raise ValueError(f'Trạng thái lạ: {status}')
        with self._connect() as con:
            con.execute('UPDATE licenses SET status=?, revoke_reason=?, updated_at=? '
                        'WHERE license_id=?',
                        (status, reason if status == STATUS_REVOKED else '',
                         _now(), license_id))

    def revoke(self, license_id: str, reason: str) -> None:
        self.set_status(license_id, STATUS_REVOKED, reason=reason)

    def unrevoke(self, license_id: str) -> None:
        self.set_status(license_id, STATUS_ISSUED)

    def _license_row(self, row: sqlite3.Row) -> LicenseRow:
        try:
            features = tuple(json.loads(row['features_json']))
        except (ValueError, TypeError):
            features = ()
        status = row['status']
        # Hết hạn thì tự hiện là hết hạn, khỏi phải chạy tác vụ dọn dẹp nào.
        if status == STATUS_ISSUED:
            try:
                if datetime.strptime(row['expires_at'], '%Y-%m-%d').date() < date.today():
                    status = STATUS_EXPIRED
            except ValueError:
                pass
        return LicenseRow(
            license_id=row['license_id'], customer=row['customer'],
            machine_id=row['machine_id'], issued_at=row['issued_at'],
            expires_at=row['expires_at'], features=features, status=status,
            email=row['email'], company=row['company'], note=row['note'],
            machine_label=row['machine_label'], token=row['token'],
            revoke_reason=row['revoke_reason'], activated_at=row['activated_at'],
            created_at=row['created_at'], updated_at=row['updated_at'])

    # ── yêu cầu ───────────────────────────────────────────────────────────
    def import_request(self, payload: dict, *, source_path: str = '') -> RequestRow:
        machine_id = normalize_machine_id(str(payload.get('machine_id', '')))
        if not machine_id:
            raise ValueError('File yêu cầu không có mã máy.')
        request_id = f"{machine_id}|{payload.get('created_at', '')}"
        with self._connect() as con:
            con.execute("""
                INSERT OR REPLACE INTO requests (
                    request_id, machine_id, user_name, email, company, machine_label,
                    requested_expires_at, note, app_version, status, source_path,
                    created_at, imported_at, license_id)
                VALUES (?,?,?,?,?,?,?,?,?,
                        COALESCE((SELECT status FROM requests WHERE request_id=?), ?),
                        ?,?,?,
                        COALESCE((SELECT license_id FROM requests WHERE request_id=?), ''))
                """, (request_id, machine_id, str(payload.get('user_name', '')),
                      str(payload.get('email', '')), str(payload.get('company', '')),
                      str(payload.get('machine_label', '')),
                      str(payload.get('requested_expires_at', '')),
                      str(payload.get('note', '')), str(payload.get('app_version', '')),
                      request_id, REQ_PENDING, source_path,
                      str(payload.get('created_at', '')), _now(), request_id))
        return self.get_request(request_id)

    def get_request(self, request_id: str) -> RequestRow | None:
        with self._connect() as con:
            row = con.execute('SELECT * FROM requests WHERE request_id=?',
                              (request_id,)).fetchone()
        return self._request_row(row) if row else None

    def list_requests(self, *, status: str = 'all') -> list[RequestRow]:
        with self._connect() as con:
            rows = con.execute('SELECT * FROM requests ORDER BY imported_at DESC').fetchall()
        out = [self._request_row(r) for r in rows]
        return out if status == 'all' else [r for r in out if r.status == status]

    def set_request_status(self, request_id: str, status: str) -> None:
        with self._connect() as con:
            con.execute('UPDATE requests SET status=? WHERE request_id=?',
                        (status, request_id))

    def _request_row(self, row: sqlite3.Row) -> RequestRow:
        return RequestRow(
            request_id=row['request_id'], machine_id=row['machine_id'],
            user_name=row['user_name'], email=row['email'], company=row['company'],
            machine_label=row['machine_label'],
            requested_expires_at=row['requested_expires_at'], note=row['note'],
            app_version=row['app_version'], status=row['status'],
            source_path=row['source_path'], created_at=row['created_at'],
            imported_at=row['imported_at'], license_id=row['license_id'])

    # ── máy đang dùng ─────────────────────────────────────────────────────
    def record_machine(self, payload: dict, *, source: str = 'nhịp tim') -> None:
        """Gộp một nhịp tim hoặc một báo cáo sử dụng vào sổ.

        Lấy mốc **muộn nhất** cho last_seen và **sớm nhất** cho first_seen: hai
        nguồn (điểm hẹn và file gửi tay) có thể cùng nói về một máy, và không
        nguồn nào được phép làm mất lịch sử của nguồn kia.
        """
        machine_id = normalize_machine_id(str(payload.get('machine_id', '')))
        if not machine_id:
            return
        counters = payload.get('counters') or {}
        if not isinstance(counters, dict):
            counters = {}
        with self._connect() as con:
            old = con.execute('SELECT * FROM machines WHERE machine_id=?',
                              (machine_id,)).fetchone()
            first_seen = str(payload.get('first_seen', ''))
            last_seen = str(payload.get('last_seen', ''))
            if old:
                if old['first_seen'] and (not first_seen or old['first_seen'] < first_seen):
                    first_seen = old['first_seen']
                if old['last_seen'] and old['last_seen'] > last_seen:
                    last_seen = old['last_seen']
                    counters = json.loads(old['counters_json'] or '{}') or counters
            con.execute("""
                INSERT OR REPLACE INTO machines (
                    machine_id, machine_label, customer, license_id, expires_at,
                    app_version, first_seen, last_seen, counters_json, source, tampered)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (machine_id, str(payload.get('machine_label', '')),
                      str(payload.get('customer', '')), str(payload.get('license_id', '')),
                      str(payload.get('expires_at', '')), str(payload.get('app_version', '')),
                      first_seen, last_seen, json.dumps(counters), source,
                      1 if payload.get('usage_tampered') or payload.get('tampered') else 0))

    def import_heartbeats(self, root: str | Path) -> int:
        from src.security.checkpoint import read_heartbeats
        beats = read_heartbeats(root)
        for beat in beats:
            self.record_machine(beat, source='nhịp tim')
        return len(beats)

    def import_usage_report(self, path: str | Path) -> str:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        usage = data.get('usage') or {}
        payload = dict(usage)
        payload.update({k: v for k, v in (data.get('license') or {}).items()})
        self.record_machine(payload, source='báo cáo gửi tay')
        return normalize_machine_id(str(usage.get('machine_id', '')))

    def list_machines(self) -> list[MachineRow]:
        with self._connect() as con:
            rows = con.execute('SELECT * FROM machines ORDER BY last_seen DESC').fetchall()
        out = []
        for row in rows:
            try:
                counters = json.loads(row['counters_json'] or '{}')
            except ValueError:
                counters = {}
            out.append(MachineRow(
                machine_id=row['machine_id'], machine_label=row['machine_label'],
                customer=row['customer'], license_id=row['license_id'],
                expires_at=row['expires_at'], app_version=row['app_version'],
                first_seen=row['first_seen'], last_seen=row['last_seen'],
                counters=counters, source=row['source'], tampered=bool(row['tampered'])))
        return out

    # ── chặn tay ──────────────────────────────────────────────────────────
    def block_machine(self, machine_id: str, reason: str) -> None:
        with self._connect() as con:
            con.execute('INSERT OR REPLACE INTO blocks VALUES (?,?,?)',
                        (normalize_machine_id(machine_id), reason.strip(), _now()))

    def unblock_machine(self, machine_id: str) -> None:
        with self._connect() as con:
            con.execute('DELETE FROM blocks WHERE machine_id=?',
                        (normalize_machine_id(machine_id),))

    def list_blocks(self) -> list[dict]:
        with self._connect() as con:
            rows = con.execute('SELECT * FROM blocks ORDER BY created_at DESC').fetchall()
        return [dict(r) for r in rows]

    def blocklist_entries(self) -> list[dict]:
        """Mọi mục cần đưa vào danh sách chặn công bố ra điểm hẹn."""
        entries: list[dict] = []
        for row in self.list_licenses(status=STATUS_REVOKED):
            entries.append({'license_id': row.license_id,
                            'machine_id': row.machine_id,
                            'reason': row.revoke_reason or 'Giấy phép đã thu hồi.',
                            'at': row.updated_at[:10]})
        seen = {e.get('machine_id') for e in entries}
        for block in self.list_blocks():
            if block['machine_id'] in seen:
                continue
            entries.append({'machine_id': block['machine_id'],
                            'reason': block['reason'] or 'Máy bị chặn.',
                            'at': block['created_at'][:10]})
        return entries

    # ── tổng hợp và xuất ──────────────────────────────────────────────────
    def summary(self, now: datetime | None = None) -> dict:
        licenses = self.list_licenses()
        machines = self.list_machines()
        soon = [r for r in licenses
                if r.status in (STATUS_ISSUED, STATUS_ACTIVE)
                and (r.days_remaining() or 999) <= 30]
        total_sessions = sum(int((m.counters or {}).get('sessions', 0)) for m in machines)
        total_mct = sum(int((m.counters or {}).get('mct', 0)) for m in machines)
        return {
            'licenses': len(licenses),
            'active_licenses': len([r for r in licenses if r.status in (STATUS_ISSUED, STATUS_ACTIVE)]),
            'expired': len([r for r in licenses if r.status == STATUS_EXPIRED]),
            'revoked': len([r for r in licenses if r.status == STATUS_REVOKED]),
            'expiring_30d': len(soon),
            'requests_pending': len(self.list_requests(status=REQ_PENDING)),
            'machines': len(machines),
            'machines_active': len([m for m in machines if m.is_active(now)]),
            'sessions': total_sessions,
            'mct': total_mct,
        }

    def export_licenses_csv(self, path: str | Path,
                            rows: Iterable[LicenseRow] | None = None) -> Path:
        rows = list(rows if rows is not None else self.list_licenses())
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('w', newline='', encoding='utf-8-sig') as fh:
            writer = csv.writer(fh)
            writer.writerow(['Mã giấy phép', 'Khách hàng', 'Đơn vị', 'Email',
                             'Mã máy', 'Tên máy', 'Ngày cấp', 'Hết hạn',
                             'Còn (ngày)', 'Tính năng', 'Trạng thái', 'Lý do thu hồi',
                             'Ghi chú'])
            for row in rows:
                writer.writerow([row.license_id, row.customer, row.company, row.email,
                                 row.machine_id, row.machine_label, row.issued_at,
                                 row.expires_at, row.days_remaining(), row.feature_text,
                                 row.status, row.revoke_reason, row.note])
        return out

    def export_machines_csv(self, path: str | Path) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('w', newline='', encoding='utf-8-sig') as fh:
            writer = csv.writer(fh)
            writer.writerow(['Mã máy', 'Tên máy', 'Khách hàng', 'Phiên bản',
                             'Lần đầu', 'Lần cuối', 'Số ngày im', 'Đang dùng',
                             'Lần mở', 'MCT', 'Midas', 'Kiểm toán', 'Chuột phải',
                             'Nguồn', 'Sổ bị sửa'])
            for m in self.list_machines():
                c = m.counters or {}
                writer.writerow([m.machine_id, m.machine_label, m.customer,
                                 m.app_version, m.first_seen, m.last_seen,
                                 m.days_idle(), 'có' if m.is_active() else 'không',
                                 c.get('sessions', 0), c.get('mct', 0),
                                 c.get('midas', 0), c.get('check', 0),
                                 c.get('context_menu', 0), m.source,
                                 'có' if m.tampered else ''])
        return out


def expiring_soon(rows: Iterable[LicenseRow], days: int = 30) -> list[LicenseRow]:
    limit = date.today() + timedelta(days=days)
    out = []
    for row in rows:
        try:
            expiry = datetime.strptime(row.expires_at, '%Y-%m-%d').date()
        except ValueError:
            continue
        if row.status in (STATUS_ISSUED, STATUS_ACTIVE) and expiry <= limit:
            out.append(row)
    return out

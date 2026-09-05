"""Nhật ký sử dụng — đếm ai đã dùng, đang dùng, và dùng bao nhiêu.

Mục đích là **theo dõi và đánh giá**, không phải giám sát: file này ghi số lần,
không ghi nội dung công việc.

Có ghi                        | Không bao giờ ghi
------------------------------|---------------------------------------
mã máy, tên máy\\tên đăng nhập | tên file DXF / tên dự án / đường dẫn
phiên bản app                 | số liệu tính toán, kích thước mặt cắt
số phiên, mốc đầu/cuối        | nội dung bản vẽ hay bảng kiểm toán
số MCT sinh ra, số lần chạy   |
Midas, số lần xuất kiểm toán  |

Bản ghi ký HMAC gắn mã máy (cùng cách với trial.py) nên sửa tay là lộ; đây là
**bằng chứng sửa**, không phải chống sửa — xoá file thì mất số, và điều đó
chấp nhận được vì con số này để đánh giá mức dùng chứ không để tính tiền.

Ghi hai chỗ (%ProgramData% + %LOCALAPPDATA%), mỗi lượt đọc lấy bản có số lớn
hơn — xoá một bản không làm mất lịch sử.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import paths as _paths
from .hwid import get_machine_id, machine_label

USAGE_FILENAME = 'usage.json'
USAGE_FILE_ENV = 'MTB_USAGE_FILE'
_PEPPER = b'midas-transverse-boxgirder/usage/v1'

#: Giữ 24 tháng gần nhất — đủ nhìn xu hướng, không phình file.
_KEEP_MONTHS = 24
#: Giữ 60 mốc phiên gần nhất, đủ để trả lời "tuần này có ai mở không".
_KEEP_SESSIONS = 60

#: Các loại việc được đếm. Thêm loại mới thì thêm vào đây để bảng thống kê của
#: công cụ quản trị không phải đoán tên cột.
EVENTS = {
    'sessions': 'Lần mở phần mềm',
    'mct': 'File MCT đã sinh',
    'midas': 'Lượt tự chạy Midas',
    'check': 'Lượt xuất kiểm toán',
    'context_menu': 'Lượt tạo MCT từ chuột phải',
    'nx': 'Lượt kiểm chéo bằng Midas NX',
}


@dataclass
class UsageSnapshot:
    machine_id: str = ''
    machine_label: str = ''
    first_seen: str = ''
    last_seen: str = ''
    app_version: str = ''
    counters: dict = field(default_factory=dict)
    months: dict = field(default_factory=dict)
    sessions: list = field(default_factory=list)
    tampered: bool = False

    def as_dict(self) -> dict:
        return {
            'machine_id': self.machine_id,
            'machine_label': self.machine_label,
            'first_seen': self.first_seen,
            'last_seen': self.last_seen,
            'app_version': self.app_version,
            'counters': dict(self.counters),
            'months': dict(self.months),
            'sessions': list(self.sessions),
            'tampered': self.tampered,
        }


def _usage_paths() -> list[Path]:
    return _paths.data_paths(USAGE_FILENAME, USAGE_FILE_ENV)


def _sign(payload: dict, machine_id: str) -> str:
    key = hashlib.sha256(_PEPPER + machine_id.encode('utf-8')).digest()
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'),
                     ensure_ascii=False).encode('utf-8')
    return hmac.new(key, raw, hashlib.sha256).hexdigest()


def _load_one(path: Path, machine_id: str) -> tuple[dict | None, bool]:
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None, False
    if not isinstance(raw, dict):
        return None, True
    signature = str(raw.pop('sig', ''))
    if not hmac.compare_digest(signature, _sign(raw, machine_id)):
        return raw, True
    return raw, False


def _total(record: dict) -> int:
    counters = record.get('counters') or {}
    return sum(int(v) for v in counters.values() if isinstance(v, (int, float)))


def load() -> UsageSnapshot:
    """Đọc bản ghi ở mọi vị trí, lấy bản **nhiều số liệu nhất**."""
    machine_id = get_machine_id()
    best: dict | None = None
    tampered = False
    for path in _usage_paths():
        if not path.exists():
            continue
        record, bad = _load_one(path, machine_id)
        tampered = tampered or bad
        if record is None:
            continue
        if best is None or _total(record) > _total(best):
            best = record
    if best is None:
        return UsageSnapshot(machine_id=machine_id, machine_label=machine_label(),
                             tampered=tampered)
    return UsageSnapshot(
        machine_id=str(best.get('machine_id', machine_id)),
        machine_label=str(best.get('machine_label', '')),
        first_seen=str(best.get('first_seen', '')),
        last_seen=str(best.get('last_seen', '')),
        app_version=str(best.get('app_version', '')),
        counters={k: int(v) for k, v in (best.get('counters') or {}).items()
                  if isinstance(v, (int, float))},
        months={str(k): int(v) for k, v in (best.get('months') or {}).items()
                if isinstance(v, (int, float))},
        sessions=[str(x) for x in (best.get('sessions') or [])][-_KEEP_SESSIONS:],
        tampered=tampered)


def _save(snap: UsageSnapshot) -> list[Path]:
    payload = snap.as_dict()
    payload.pop('tampered', None)
    payload['sig'] = _sign({k: v for k, v in payload.items() if k != 'sig'},
                           snap.machine_id)
    return _paths.write_all(_usage_paths(),
                            json.dumps(payload, ensure_ascii=False, sort_keys=True))


def record(event: str = 'sessions', count: int = 1, *, app_version: str = '',
           now: datetime | None = None) -> UsageSnapshot:
    """Đếm thêm một việc. Trả về bản ghi sau khi cộng.

    Không bao giờ ném: nhật ký hỏng thì phần mềm vẫn phải chạy. Đây là sổ theo
    dõi, không phải cổng kiểm tra — cổng nằm ở guard.py.
    """
    try:
        stamp = (now or datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
        month = stamp[:7]
        snap = load()
        snap.machine_id = snap.machine_id or get_machine_id()
        snap.machine_label = machine_label() or snap.machine_label
        snap.first_seen = snap.first_seen or stamp
        snap.last_seen = stamp
        if app_version:
            snap.app_version = app_version

        key = event if event in EVENTS else 'other'
        snap.counters[key] = int(snap.counters.get(key, 0)) + int(count)
        snap.months[month] = int(snap.months.get(month, 0)) + int(count)
        if len(snap.months) > _KEEP_MONTHS:
            for old in sorted(snap.months)[:-_KEEP_MONTHS]:
                snap.months.pop(old, None)
        if event == 'sessions':
            snap.sessions = (snap.sessions + [stamp])[-_KEEP_SESSIONS:]
        _save(snap)
        return snap
    except Exception:
        return load()


def start_session(app_version: str = '') -> UsageSnapshot:
    return record('sessions', 1, app_version=app_version)


def build_report(license_info=None, note: str = '') -> dict:
    """Gói số liệu thành nội dung file .mtbusage để gửi lại người cấp phép."""
    snap = load()
    report = {
        'schema': 1,
        'product': 'midas-transverse-boxgirder',
        'kind': 'usage-report',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'note': str(note).strip(),
        'usage': snap.as_dict(),
    }
    if license_info is not None:
        report['license'] = {
            'license_id': getattr(license_info, 'license_id', ''),
            'customer': getattr(license_info, 'customer', ''),
            'expires_at': getattr(license_info, 'expires_at', ''),
        }
    return report


def export_report(path: str | os.PathLike, license_info=None,
                  note: str = '') -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_report(license_info, note),
                              ensure_ascii=False, indent=2), encoding='utf-8')
    return out


def summary_lines() -> list[str]:
    """Vài dòng gọn để hiện trong hộp thoại Giấy phép."""
    snap = load()
    if not snap.first_seen:
        return ['Chưa có số liệu sử dụng trên máy này.']
    lines = [f'Lần đầu: {snap.first_seen} · Gần nhất: {snap.last_seen}']
    for key, label in EVENTS.items():
        value = snap.counters.get(key)
        if value:
            lines.append(f'{label}: {value}')
    if snap.tampered:
        lines.append('CẢNH BÁO: bản ghi sử dụng đã bị sửa tay.')
    return lines


def reset() -> list[Path]:
    """Xoá sổ. Chỉ dùng khi phát triển và trong test."""
    removed = []
    for path in _usage_paths():
        try:
            if path.exists():
                path.unlink()
                removed.append(path)
        except OSError:
            continue
    return removed

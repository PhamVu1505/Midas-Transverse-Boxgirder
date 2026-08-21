"""Dùng thử 7 ngày, đầy đủ tính năng.

Máy chưa có giấy phép vẫn chạy được trọn vẹn trong 7 ngày kể từ lần mở đầu
tiên — đủ đi hết một vòng DXF → MCT → Midas → kiểm toán, vốn là thứ người ta
cần thấy trước khi xin cấp phép.

Chống lách ở ba chỗ, và chỉ ba chỗ đó:

* **Ghi hai nơi** (%ProgramData% + %LOCALAPPDATA%): xoá một bản vẫn còn bản
  kia, và ngày bắt đầu lấy bản **sớm nhất**.
* **Ký HMAC gắn mã máy**: sửa tay nội dung, hay bê file từ máy khác sang, đều
  làm chữ ký sai. Sai chữ ký thì **khoá luôn**, không phải "bắt đầu lại".
* **Chống lùi đồng hồ**: ngày hệ thống lùi quá 1 ngày so với lần chạy gần nhất
  thì coi như hết hạn.

Đây là hàng rào cho người dùng ngay tình, không phải chống bẻ khoá — ứng dụng
Python đóng gói thì luôn gỡ ngược được. Xem docs/LICENSE-SYSTEM.md.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from . import paths as _paths
from .hwid import get_machine_id

TRIAL_DAYS = 7
TRIAL_FILENAME = 'trial.runtime'
TRIAL_FILE_ENV = 'MTB_TRIAL_FILE'
_DATE_FMT = '%Y-%m-%d'

#: Đồng hồ máy chạy sai vài giờ là chuyện thường; lùi hẳn hơn một ngày thì
#: không.
_ROLLBACK_TOLERANCE_DAYS = 1

#: Hạt muối trộn vào khoá HMAC. Không phải bí mật thật (nằm trong bản đóng gói)
#: — nó chỉ khiến bản ghi không thể dựng lại bằng một dòng lệnh hash thông
#: thường.
_PEPPER = b'midas-transverse-boxgirder/trial/v1'


@dataclass(frozen=True)
class TrialStatus:
    active: bool
    days_left: int
    message: str
    started_at: str = ''
    expires_on: str = ''
    tampered: bool = False


def _trial_paths() -> list[Path]:
    return _paths.data_paths(TRIAL_FILENAME, TRIAL_FILE_ENV)


def _hmac_key(machine_id: str) -> bytes:
    return hashlib.sha256(_PEPPER + machine_id.encode('utf-8')).digest()


def _sign(payload: dict, machine_id: str) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hmac.new(_hmac_key(machine_id), raw, hashlib.sha256).hexdigest()


def _parse_day(value: str) -> date | None:
    try:
        return datetime.strptime(str(value).strip(), _DATE_FMT).date()
    except (ValueError, TypeError):
        return None


def _today(now: datetime | date | None = None) -> date:
    if now is None:
        return date.today()
    return now.date() if isinstance(now, datetime) else now


def _load(path: Path, machine_id: str) -> tuple[dict | None, bool]:
    """Trả về (bản ghi, đã_bị_sửa). Không đọc được thì (None, False)."""
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None, False
    if not isinstance(raw, dict):
        return None, True
    signature = str(raw.get('sig', ''))
    payload = {k: v for k, v in raw.items() if k != 'sig'}
    if not hmac.compare_digest(signature, _sign(payload, machine_id)):
        return None, True
    if str(payload.get('machine_id', '')) != machine_id:
        return None, True
    return payload, False


def _write(payload: dict, machine_id: str) -> bool:
    record = dict(payload)
    record['sig'] = _sign(payload, machine_id)
    text = json.dumps(record, ensure_ascii=False, sort_keys=True)
    return bool(_paths.write_all(_trial_paths(), text))


def _status_from_dates(started: date, last_seen: date, today: date) -> TrialStatus:
    if today < last_seen - timedelta(days=_ROLLBACK_TOLERANCE_DAYS):
        return TrialStatus(
            False, 0,
            'Đồng hồ máy đang lùi so với lần chạy gần nhất — bản dùng thử '
            'khoá lại. Chỉnh lại ngày giờ hệ thống hoặc xin cấp giấy phép.',
            started_at=started.strftime(_DATE_FMT),
            expires_on=(started + timedelta(days=TRIAL_DAYS)).strftime(_DATE_FMT),
            tampered=True)

    expires_on = started + timedelta(days=TRIAL_DAYS)
    days_left = (expires_on - today).days
    if days_left > 0:
        return TrialStatus(
            True, days_left,
            f'Đang dùng thử — còn {days_left} ngày (hết ngày {expires_on:%d/%m/%Y}).',
            started_at=started.strftime(_DATE_FMT),
            expires_on=expires_on.strftime(_DATE_FMT))
    return TrialStatus(
        False, 0,
        f'Đã hết {TRIAL_DAYS} ngày dùng thử (từ {started:%d/%m/%Y}). '
        'Xin cấp giấy phép để dùng tiếp.',
        started_at=started.strftime(_DATE_FMT),
        expires_on=expires_on.strftime(_DATE_FMT))


def get_trial_status(now: datetime | date | None = None,
                     *, start_if_missing: bool = True) -> TrialStatus:
    """Trạng thái dùng thử; lần đầu gọi sẽ mở sổ dùng thử.

    ``start_if_missing=False`` để xem mà không khởi động (hộp thoại giấy phép
    dùng khi chỉ hiển thị trạng thái).
    """
    machine_id = get_machine_id()
    today = _today(now)
    # Chỉ ghi sổ khi đang hỏi bằng đồng hồ THẬT. Truyền `now` vào là để xem thử
    # hoặc để test; nếu lượt xem đó cũng ghi "lần chạy gần nhất" thì một lần
    # xem trước ngày mai sẽ làm chính máy đó bị coi là lùi đồng hồ hôm sau.
    persist = now is None

    started: date | None = None
    last_seen: date | None = None
    tampered = False
    for path in _trial_paths():
        if not path.exists():
            continue
        payload, bad = _load(path, machine_id)
        if bad:
            tampered = True
            continue
        if payload is None:
            continue
        day = _parse_day(payload.get('started_at', ''))
        if day and (started is None or day < started):
            started = day          # bản ghi SỚM NHẤT thắng
        seen = _parse_day(payload.get('last_seen', ''))
        if seen and (last_seen is None or seen > last_seen):
            last_seen = seen       # lần chạy MUỘN NHẤT thắng

    if tampered and started is None:
        return TrialStatus(
            False, 0,
            'Bản ghi dùng thử đã bị sửa hoặc mang từ máy khác sang — '
            'bản dùng thử khoá lại. Xin cấp giấy phép để dùng tiếp.',
            tampered=True)

    if started is None:
        if not start_if_missing or not persist:
            return TrialStatus(True, TRIAL_DAYS,
                               f'Chưa mở sổ dùng thử — còn đủ {TRIAL_DAYS} ngày.')
        started = today
        last_seen = today
        _write({'machine_id': machine_id,
                'started_at': started.strftime(_DATE_FMT),
                'last_seen': today.strftime(_DATE_FMT)}, machine_id)
        return _status_from_dates(started, last_seen, today)

    last_seen = last_seen or started
    status = _status_from_dates(started, last_seen, today)

    # Ghi lại mốc "lần chạy gần nhất" để còn bắt được cú lùi đồng hồ sau này.
    # Bản ghi bị sửa thì không ghi đè: giữ nguyên dấu vết.
    if persist and start_if_missing and not status.tampered and today > last_seen:
        _write({'machine_id': machine_id,
                'started_at': started.strftime(_DATE_FMT),
                'last_seen': today.strftime(_DATE_FMT)}, machine_id)
    return status


def reset_trial() -> list[Path]:
    """Xoá sổ dùng thử. CHỈ dùng khi phát triển và trong test."""
    removed = []
    for path in _trial_paths():
        try:
            if path.exists():
                path.unlink()
                removed.append(path)
        except OSError:
            continue
    return removed


if __name__ == '__main__':
    os.environ.setdefault(TRIAL_FILE_ENV, '')
    print(get_trial_status(start_if_missing=False))

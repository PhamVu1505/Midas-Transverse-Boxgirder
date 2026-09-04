"""Điểm hẹn: một THƯ MỤC dùng chung, không phải máy chủ.

Thư mục có thể là ổ mạng nội bộ, OneDrive/Google Drive đồng bộ, hay bất cứ chỗ
nào cả hai bên với tới. Đường dẫn nằm ngay trong giấy phép (trường checkpoint)
nên nó đã được **ký** — không ai đổi hướng điểm hẹn của máy mình được.

    <điểm hẹn>/
        blocklist.mtbbl              ← người cấp ghi, đã ký; máy khách chỉ đọc
        heartbeat/<MÃ MÁY>.json      ← mỗi máy một file, không ai đè lên ai

Hai chiều, mỗi chiều một việc:

* **Ra** — máy khách thả một nhịp tim mỗi lần chạy: mã máy, tên máy, giấy phép
  nào, phiên bản nào, đếm được bao nhiêu việc. Người cấp mở công cụ quản trị là
  thấy ai đang dùng, lần cuối khi nào.
* **Vào** — máy khách đọc danh sách chặn đã ký rồi cất bản sao cục bộ. Trúng
  danh sách thì cổng kiểm tra chặn ngay lần chạy sau.

Ba giới hạn phải nói thẳng, đừng hứa quá:

1. **Không với tới điểm hẹn thì không chặn được.** Máy ngoài mạng vẫn chạy tới
   khi giấy phép hết hạn. Đó là lý do hạn mặc định chỉ 6 tháng — hạn ngắn mới
   là đòn bẩy chặn thật, danh sách chặn chỉ là đường nhanh.
2. **Mất mạng KHÔNG chặn.** Người dùng đang ở công trường mà app tự khoá vì
   không thấy ổ mạng thì đó là lỗi của ta, không phải của họ. Không đọc được
   thì giữ nguyên bản sao cũ và ghi lại ngày giờ.
3. Xoá bản sao cục bộ trong lúc mất mạng thì gỡ được chặn cho tới lần đồng bộ
   sau. Vá chỗ này đòi hỏi máy chủ thật; xem docs/LICENSE-SYSTEM.md.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import paths as _paths
from .hwid import get_machine_id, machine_label, normalize_machine_id
from .signing import SignatureError, encode_token, verify_token

BLOCKLIST_PREFIX = 'MTBBL1'
BLOCKLIST_NAME = 'blocklist.mtbbl'
HEARTBEAT_DIR = 'heartbeat'
CACHE_FILENAME = 'blocklist.cache'
STATE_FILENAME = 'checkpoint.json'
CHECKPOINT_ENV = 'MTB_CHECKPOINT'
PRODUCT_ID = 'midas-transverse-boxgirder'


@dataclass(frozen=True)
class SyncResult:
    configured: bool
    ok: bool = False
    path: str = ''
    message: str = ''
    heartbeat_written: bool = False
    blocklist_entries: int = 0


@dataclass(frozen=True)
class BlockDecision:
    blocked: bool
    reason: str = ''
    issued_at: str = ''


def resolve(license_info=None) -> Path | None:
    """Thư mục điểm hẹn, hoặc None nếu không cấu hình.

    Biến môi trường thắng, **nhưng chỉ khi chạy từ mã nguồn** — để dev và test
    khỏi phải ký lại giấy phép.

    Bản đóng gói bỏ qua biến này. Nếu không thì bất kỳ máy nào bị thu hồi cũng
    tự gỡ chặn được bằng đúng hai bước: trỏ `MTB_CHECKPOINT` sang một thư mục
    rỗng, chạy một lần để nhánh "không có danh sách chặn" xoá bản sao cục bộ,
    thế là thoát vĩnh viễn. Cùng lẽ với `guard.dev_bypass_active()`: cửa dành
    cho người phát triển không được đi theo ra bản phát hành.
    """
    raw = ''
    if not getattr(sys, 'frozen', False):
        raw = os.environ.get(CHECKPOINT_ENV, '').strip()
    if not raw and license_info is not None:
        raw = str(getattr(license_info, 'checkpoint', '') or '').strip()
    return Path(raw) if raw else None


# ── bản sao cục bộ ────────────────────────────────────────────────────────

def _cache_paths() -> list[Path]:
    return _paths.data_paths(CACHE_FILENAME)


def _state_paths() -> list[Path]:
    return _paths.data_paths(STATE_FILENAME)


def _read_state() -> dict:
    text, _path = _paths.read_first(_state_paths())
    if not text:
        return {}
    try:
        data = json.loads(text)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _write_state(**fields) -> None:
    state = _read_state()
    state.update(fields)
    _paths.write_all(_state_paths(), json.dumps(state, ensure_ascii=False, sort_keys=True))


def last_sync() -> str:
    return str(_read_state().get('last_sync', ''))


def last_error() -> str:
    return str(_read_state().get('last_error', ''))


def days_since_sync(now: datetime | None = None) -> int | None:
    stamp = last_sync()
    if not stamp:
        return None
    try:
        when = datetime.strptime(stamp, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None
    return ((now or datetime.now()) - when).days


# ── danh sách chặn ────────────────────────────────────────────────────────

def parse_blocklist(token: str) -> dict:
    """Kiểm chữ ký rồi trả nội dung danh sách chặn."""
    payload = verify_token(token, BLOCKLIST_PREFIX)
    if str(payload.get('product', PRODUCT_ID)) != PRODUCT_ID:
        raise SignatureError('Danh sách chặn không phải của phần mềm này.')
    entries = payload.get('entries')
    if not isinstance(entries, list):
        raise SignatureError('Danh sách chặn sai cấu trúc.')
    return payload


def cached_blocklist() -> dict | None:
    """Bản sao cục bộ, đã kiểm chữ ký. Hỏng hoặc không có thì trả None."""
    text, _path = _paths.read_first(_cache_paths())
    if not text:
        return None
    try:
        return parse_blocklist(text)
    except (SignatureError, ValueError):
        return None


def check_blocked(license_info=None, *, machine_id: str | None = None) -> BlockDecision:
    """Máy này / giấy phép này có nằm trong danh sách chặn không."""
    payload = cached_blocklist()
    if not payload:
        return BlockDecision(False)

    current_machine = normalize_machine_id(machine_id or get_machine_id())
    license_id = str(getattr(license_info, 'license_id', '') or '')
    for entry in payload.get('entries', []):
        if not isinstance(entry, dict):
            continue
        entry_machine = normalize_machine_id(str(entry.get('machine_id', '')))
        entry_license = str(entry.get('license_id', '') or '')
        hit = ((entry_machine and entry_machine == current_machine)
               or (entry_license and license_id and entry_license == license_id))
        if hit:
            reason = str(entry.get('reason', '')).strip() or 'Không nêu lý do.'
            return BlockDecision(True, reason, str(payload.get('issued_at', '')))
    return BlockDecision(False)


# ── đồng bộ ───────────────────────────────────────────────────────────────

def _heartbeat_payload(license_info=None, app_version: str = '') -> dict:
    from . import usage_log            # nhập trễ: tránh vòng nhập lẫn nhau
    snap = usage_log.load()
    payload = {
        'schema': 1,
        'product': PRODUCT_ID,
        'machine_id': get_machine_id(),
        'machine_label': machine_label(),
        'app_version': app_version,
        'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'first_seen': snap.first_seen,
        'counters': dict(snap.counters),
        'months': dict(snap.months),
        'usage_tampered': snap.tampered,
    }
    if license_info is not None:
        payload.update({
            'license_id': getattr(license_info, 'license_id', ''),
            'customer': getattr(license_info, 'customer', ''),
            'company': getattr(license_info, 'company', ''),
            'expires_at': getattr(license_info, 'expires_at', ''),
        })
    return payload


def sync(license_info=None, *, app_version: str = '',
         write_heartbeat: bool = True) -> SyncResult:
    """Thả nhịp tim và lấy danh sách chặn. KHÔNG BAO GIỜ ném.

    Gọi từ luồng nền: đường dẫn UNC hỏng có thể treo vài giây, và không việc gì
    để cửa sổ đứng hình vì một ổ mạng.
    """
    root = resolve(license_info)
    if root is None:
        return SyncResult(False, message='Chưa cấu hình điểm hẹn.')

    wrote = False
    entries = 0
    problems: list[str] = []

    if write_heartbeat:
        try:
            beat_dir = root / HEARTBEAT_DIR
            beat_dir.mkdir(parents=True, exist_ok=True)
            target = beat_dir / f'{get_machine_id()}.json'
            tmp = target.with_suffix('.json.tmp')
            tmp.write_text(json.dumps(_heartbeat_payload(license_info, app_version),
                                      ensure_ascii=False, indent=1), encoding='utf-8')
            os.replace(tmp, target)     # thay một nhát: người đọc không gặp file dở
            wrote = True
        except Exception as exc:
            problems.append(f'không ghi được nhịp tim ({exc})')

    try:
        source = root / BLOCKLIST_NAME
        if source.exists():
            token = source.read_text(encoding='utf-8').strip()
            payload = parse_blocklist(token)          # sai chữ ký thì đừng cất
            entries = len(payload.get('entries', []))
            _paths.write_all(_cache_paths(), token + '\n')
        else:
            # Không có danh sách chặn nghĩa là không chặn ai — bỏ bản sao cũ đi,
            # nếu không thì một lần chặn nhầm sẽ sống mãi trên máy đó.
            for path in _cache_paths():
                try:
                    if path.exists():
                        path.unlink()
                except OSError:
                    pass
    except Exception as exc:
        problems.append(f'không đọc được danh sách chặn ({exc})')

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if problems:
        _write_state(last_error=f'{now}: ' + ' · '.join(problems))
        return SyncResult(True, False, str(root), ' · '.join(problems), wrote, entries)
    _write_state(last_sync=now, last_error='')
    return SyncResult(True, True, str(root),
                      f'Đã đồng bộ điểm hẹn ({entries} mục chặn).', wrote, entries)


def status_lines(license_info=None) -> list[str]:
    root = resolve(license_info)
    if root is None:
        return ['Điểm hẹn: chưa cấu hình.']
    lines = [f'Điểm hẹn: {root}']
    stamp = last_sync()
    lines.append(f'Đồng bộ gần nhất: {stamp}' if stamp else 'Chưa đồng bộ lần nào.')
    err = last_error()
    if err:
        lines.append(f'Lỗi gần nhất: {err}')
    payload = cached_blocklist()
    if payload:
        lines.append(f"Danh sách chặn: {len(payload.get('entries', []))} mục "
                     f"(lập {payload.get('issued_at', '?')})")
    return lines


# ── phía người cấp ────────────────────────────────────────────────────────

def build_blocklist(entries: list[dict], *, note: str = '') -> dict:
    clean = []
    for entry in entries:
        machine = normalize_machine_id(str(entry.get('machine_id', '')))
        license_id = str(entry.get('license_id', '') or '').strip()
        if not machine and not license_id:
            continue
        item = {'reason': str(entry.get('reason', '')).strip(),
                'at': str(entry.get('at', '')).strip()
                      or datetime.now().strftime('%Y-%m-%d')}
        if machine:
            item['machine_id'] = machine
        if license_id:
            item['license_id'] = license_id
        clean.append(item)
    return {
        'schema': 1,
        'product': PRODUCT_ID,
        'issued_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'note': str(note).strip(),
        'entries': clean,
    }


def sign_blocklist(entries: list[dict], private_key: dict, *, note: str = '') -> str:
    return encode_token(build_blocklist(entries, note=note),
                        BLOCKLIST_PREFIX, private_key)


def publish_blocklist(root: str | os.PathLike, entries: list[dict],
                      private_key: dict, *, note: str = '') -> Path:
    """Ghi danh sách chặn đã ký vào điểm hẹn."""
    token = sign_blocklist(entries, private_key, note=note)
    target = Path(root) / BLOCKLIST_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(token + '\n', encoding='utf-8')
    return target


def read_heartbeats(root: str | os.PathLike) -> list[dict]:
    """Đọc mọi nhịp tim ở điểm hẹn — dùng cho công cụ quản trị."""
    beat_dir = Path(root) / HEARTBEAT_DIR
    out: list[dict] = []
    if not beat_dir.exists():
        return out
    for path in sorted(beat_dir.glob('*.json')):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            data['_file'] = str(path)
            out.append(data)
    return out

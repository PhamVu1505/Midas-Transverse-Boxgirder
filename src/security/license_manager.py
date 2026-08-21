"""Giấy phép ngoại tuyến, ràng theo máy.

Bản đã cài chỉ mang **khoá công khai** (keys.py) nên chỉ kiểm được chữ ký,
không ký được. Khoá riêng nằm ở máy người cấp.

Vòng đời
────────
1. Máy khách mở hộp thoại Giấy phép, lưu file yêu cầu .mtbreq (mã máy + họ
   tên/đơn vị) rồi gửi cho người cấp.
2. Người cấp mở tools/license_admin.py, nạp yêu cầu, chọn hạn và tính năng,
   bấm Cấp, ra file .mtblic.
3. Máy khách nạp .mtblic; nội dung ghi vào mtb.runtime ở cả %ProgramData% lẫn
   %LOCALAPPDATA%.

Giấy phép hợp lệ khi: chữ ký đúng · product khớp · machine_id khớp máy hiện
tại · chưa quá expires_at · có tính năng được hỏi · không nằm trong danh sách
chặn (checkpoint.py lo phần này).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from . import paths as _paths
from .hwid import get_machine_id, machine_label, normalize_machine_id
from .signing import (SignatureError, decode_token, encode_token,
                      load_private_key, verify_token)

TOKEN_PREFIX = 'MTB1'
PRODUCT_ID = 'midas-transverse-boxgirder'
LICENSE_FILENAME = 'mtb.runtime'
LICENSE_FILE_ENV = 'MTB_LICENSE_FILE'
SCHEMA = 1

#: Hạn mặc định khi cấp: 6 tháng. Hạn ngắn là đòn bẩy chặn mạnh nhất mà không
#: cần hạ tầng, và mỗi lần gia hạn là một lần đếm được ai còn dùng thật.
DEFAULT_TERM_DAYS = 183

#: Tính năng khoá được. Giá trị "all" mở hết.
FEATURES = {
    'mct': 'Sinh file MCT từ DXF',
    'check': 'Kiểm toán tiết diện + xuất Excel',
    'midas': 'Tự chạy Midas/Civil',
    'nx': 'Kiểm chéo bằng Midas NX',
}


class LicenseError(ValueError):
    """Giấy phép không dùng được — kèm lý do đọc được cho người dùng."""


@dataclass(frozen=True)
class LicenseInfo:
    license_id: str
    customer: str
    machine_id: str
    issued_at: str
    expires_at: str
    features: tuple[str, ...]
    product: str = PRODUCT_ID
    schema: int = SCHEMA
    email: str = ''
    company: str = ''
    checkpoint: str = ''
    note: str = ''

    @property
    def feature_text(self) -> str:
        return 'tất cả' if 'all' in self.features else ', '.join(self.features)

    def has_feature(self, feature: str | None) -> bool:
        if not feature:
            return True
        return 'all' in self.features or feature.strip().lower() in self.features

    def days_remaining(self, today: date | None = None) -> int | None:
        try:
            expiry = datetime.strptime(self.expires_at, '%Y-%m-%d').date()
        except ValueError:
            return None
        return (expiry - (today or date.today())).days


@dataclass(frozen=True)
class LicenseStatus:
    ok: bool
    message: str
    info: LicenseInfo | None = None
    path: str | None = None
    token: str = ''


# ── công cụ nhỏ ───────────────────────────────────────────────────────────

def _parse_date(value: str) -> date:
    return datetime.strptime(str(value).strip(), '%Y-%m-%d').date()


def _today(now: datetime | date | None = None) -> date:
    if now is None:
        return datetime.now(timezone.utc).astimezone().date()
    if isinstance(now, datetime):
        return now.date()
    return now


def normalize_features(features: Iterable[str] | None) -> tuple[str, ...]:
    cleaned: list[str] = []
    for item in features or ('all',):
        text = str(item).strip().lower()
        if text and text not in cleaned:
            cleaned.append(text)
    return tuple(cleaned or ('all',))


def default_expiry(days: int = DEFAULT_TERM_DAYS, today: date | None = None) -> str:
    return ((today or date.today()) + timedelta(days=days)).strftime('%Y-%m-%d')


# ── phía máy khách: đọc và kiểm ───────────────────────────────────────────

def get_license_paths() -> list[Path]:
    return _paths.data_paths(LICENSE_FILENAME, LICENSE_FILE_ENV)


def _to_info(payload: dict) -> LicenseInfo:
    try:
        machine_id = str(payload['machine_id']).strip()
        expires_at = str(payload['expires_at']).strip()
    except KeyError as exc:
        raise LicenseError(f'Giấy phép thiếu trường {exc}.') from exc
    return LicenseInfo(
        schema=int(payload.get('schema', SCHEMA)),
        product=str(payload.get('product', PRODUCT_ID)),
        license_id=str(payload.get('license_id', '')),
        customer=str(payload.get('customer', '')).strip() or 'Người dùng',
        machine_id=machine_id,
        issued_at=str(payload.get('issued_at', '')),
        expires_at=expires_at,
        features=normalize_features(payload.get('features')),
        email=str(payload.get('email', '')).strip(),
        company=str(payload.get('company', '')).strip(),
        checkpoint=str(payload.get('checkpoint', '')).strip(),
        note=str(payload.get('note', '')).strip(),
    )


def decode_license(token: str) -> LicenseInfo:
    """Đọc nội dung mà KHÔNG kiểm chữ ký — chỉ dùng để hiển thị."""
    payload, _key_id, _raw, _sig = decode_token(token, TOKEN_PREFIX)
    return _to_info(payload)


def verify_license_token(token: str, *, machine_id: str | None = None,
                         feature: str | None = None,
                         now: datetime | date | None = None) -> LicenseInfo:
    """Kiểm đủ mọi điều kiện. Ném LicenseError kèm lý do đọc được."""
    try:
        payload = verify_token(token, TOKEN_PREFIX)
    except SignatureError as exc:
        raise LicenseError(str(exc)) from exc

    info = _to_info(payload)
    if info.schema != SCHEMA:
        raise LicenseError(f'Giấy phép theo lược đồ {info.schema}, '
                           f'bản này chỉ đọc được {SCHEMA}.')
    if info.product != PRODUCT_ID:
        raise LicenseError('Giấy phép không phải của phần mềm này.')

    current = normalize_machine_id(machine_id) if machine_id else get_machine_id()
    if normalize_machine_id(info.machine_id) != current:
        raise LicenseError('Giấy phép không khớp máy này.\n'
                           f'Máy này:     {current}\n'
                           f'Cấp cho máy: {info.machine_id}')

    try:
        expiry = _parse_date(info.expires_at)
    except ValueError as exc:
        raise LicenseError(f'Ngày hết hạn không đọc được: {info.expires_at!r}.') from exc
    if _today(now) > expiry:
        raise LicenseError(f'Giấy phép đã hết hạn ngày {info.expires_at}.')

    if not info.has_feature(feature):
        label = FEATURES.get(str(feature).lower(), feature)
        raise LicenseError(f'Giấy phép chưa mở tính năng: {label}.')
    return info


def inspect_license_token(token: str, *, machine_id: str | None = None,
                          feature: str | None = None,
                          now: datetime | date | None = None) -> LicenseStatus:
    """Như verify_license_token nhưng trả trạng thái thay vì ném.

    Hộp thoại kích hoạt cần thứ này: một giấy phép ký đúng nhưng cấp cho máy
    khác vẫn phải hiện được nội dung để người dùng thấy vì sao bị chối.
    """
    try:
        info = verify_license_token(token, machine_id=machine_id,
                                    feature=feature, now=now)
    except LicenseError as exc:
        try:
            partial = decode_license(token)
        except Exception:
            partial = None
        return LicenseStatus(False, str(exc), info=partial, token=token)
    left = info.days_remaining(_today(now))
    return LicenseStatus(
        True,
        f'Giấy phép hợp lệ tới {info.expires_at} (còn {left} ngày) — {info.customer}.',
        info=info, token=token)


def get_license_status(token: str | None = None, *, feature: str | None = None,
                       machine_id: str | None = None,
                       now: datetime | date | None = None) -> LicenseStatus:
    """Trạng thái giấy phép đang cài (hoặc của một chuỗi cho sẵn).

    Quét **mọi** vị trí và lấy giấy phép hợp lệ đầu tiên. Bản mtb.runtime cũ
    hoặc sai máy nằm ở ProgramData không được phép chặn một giấy phép hợp lệ
    nằm ở vị trí sau.
    """
    if token is not None:
        return inspect_license_token(token, feature=feature,
                                     machine_id=machine_id, now=now)

    first_failure: LicenseStatus | None = None
    for path in get_license_paths():
        try:
            if not path.exists():
                continue
            candidate = path.read_text(encoding='utf-8').strip()
        except OSError:
            continue
        st = inspect_license_token(candidate, feature=feature,
                                   machine_id=machine_id, now=now)
        st = LicenseStatus(st.ok, st.message, st.info, str(path), st.token)
        if st.ok:
            return st
        if first_failure is None:
            first_failure = st
    if first_failure is not None:
        return first_failure
    return LicenseStatus(False, 'Chưa có giấy phép trên máy này.')


def save_license(token: str) -> list[Path]:
    """Ghi giấy phép ra mọi vị trí ghi được. Trả về danh sách nơi đã ghi."""
    written = _paths.write_all(get_license_paths(), token.strip() + '\n')
    if not written:
        raise LicenseError('Không ghi được giấy phép vào bất kỳ thư mục nào:\n'
                           + '\n'.join(str(p) for p in get_license_paths()))
    return written


def remove_license() -> list[Path]:
    removed = []
    for path in get_license_paths():
        try:
            if path.exists():
                path.unlink()
                removed.append(path)
        except OSError:
            continue
    return removed


# ── phía máy khách: file yêu cầu cấp phép ─────────────────────────────────

def build_request(user_name: str = '', email: str = '', company: str = '',
                  note: str = '', requested_days: int = DEFAULT_TERM_DAYS,
                  app_version: str = '') -> dict:
    """Nội dung file .mtbreq gửi cho người cấp.

    Không ký: trong đó không có gì bí mật, và người cấp vẫn phải tự nhìn rồi
    quyết định. Ký ở đây chỉ tạo cảm giác an toàn giả.
    """
    return {
        'schema': SCHEMA,
        'product': PRODUCT_ID,
        'kind': 'license-request',
        'machine_id': get_machine_id(),
        'machine_label': machine_label(),
        'user_name': str(user_name).strip(),
        'email': str(email).strip(),
        'company': str(company).strip(),
        'note': str(note).strip(),
        'requested_expires_at': default_expiry(requested_days),
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'app_version': str(app_version or os.environ.get('MTB_APP_VERSION', '')),
    }


# ── phía người cấp: ký ────────────────────────────────────────────────────

def build_license_payload(machine_id: str, expires_at: str, *, customer: str,
                          features: Iterable[str] | None = None,
                          email: str = '', company: str = '', note: str = '',
                          checkpoint: str = '', license_id: str | None = None,
                          issued_at: str | None = None) -> dict:
    _parse_date(expires_at)      # hỏng ngày thì hỏng ngay, đừng ký rồi mới biết
    if issued_at:
        _parse_date(issued_at)
    else:
        issued_at = date.today().strftime('%Y-%m-%d')

    clean_machine = normalize_machine_id(machine_id)
    if not clean_machine:
        raise LicenseError('Chưa có mã máy.')
    clean_customer = str(customer).strip()
    if not clean_customer:
        raise LicenseError('Chưa nhập tên người dùng/đơn vị.')

    payload = {
        'schema': SCHEMA,
        'product': PRODUCT_ID,
        'license_id': license_id or str(uuid4()),
        'customer': clean_customer,
        'machine_id': clean_machine,
        'issued_at': issued_at,
        'expires_at': expires_at,
        'features': list(normalize_features(features)),
    }
    # Trường rỗng thì bỏ hẳn khỏi nội dung ký: giấy phép ngắn hơn, và không có
    # chuỗi rỗng nào lẫn vào để sau này phải đoán "rỗng" nghĩa là gì.
    for key, value in (('email', email), ('company', company),
                       ('note', note), ('checkpoint', checkpoint)):
        text = str(value or '').strip()
        if text:
            payload[key] = text
    return payload


def generate_license(machine_id: str, expires_at: str, *, customer: str,
                     features: Iterable[str] | None = None, email: str = '',
                     company: str = '', note: str = '', checkpoint: str = '',
                     private_key: dict | None = None,
                     private_key_path: str | os.PathLike | None = None,
                     license_id: str | None = None) -> tuple[str, LicenseInfo]:
    """Ký một giấy phép. Trả về (chuỗi giấy phép, nội dung đã đọc lại)."""
    key = private_key or load_private_key(private_key_path)
    payload = build_license_payload(
        machine_id, expires_at, customer=customer, features=features,
        email=email, company=company, note=note, checkpoint=checkpoint,
        license_id=license_id)
    token = encode_token(payload, TOKEN_PREFIX, key)
    return token, _to_info(payload)

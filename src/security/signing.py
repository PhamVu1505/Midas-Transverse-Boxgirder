"""Phong bì ký số dùng chung cho giấy phép và danh sách chặn.

Định dạng chuỗi: ``<PREFIX>.<key_id>.<payload_b64url>.<chữ_ký_b64url>``

RSA-2048 PKCS#1 v1.5 + SHA-256, cài bằng `pow()` của Python. Không dùng
`cryptography`/`nacl` vì `installer/build.bat` đang loại trừ cả hai; thêm phụ
thuộc chỉ để ký một chuỗi JSON là đổi cả bản đóng gói.

Máy khách chỉ cần **kiểm** chữ ký (`verify_token`). Hàm `encode_token` cần khoá
riêng nên chỉ chạy được ở máy người cấp — mã nằm chung file này là không sao,
thứ phải giữ kín là khoá chứ không phải thuật toán.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path

from .keys import PUBLIC_KEYS

# DigestInfo của SHA-256 theo RFC 8017 §9.2.
_SHA256_DIGEST_INFO = bytes.fromhex('3031300d060960864801650304020105000420')

PRIVATE_KEY_ENV = 'MTB_LICENSE_PRIVATE_KEY'


class SignatureError(ValueError):
    """Chuỗi sai định dạng, sai khoá, hoặc đã bị sửa."""


def json_bytes(data: dict) -> bytes:
    """JSON tất định — thứ tự khoá cố định, không khoảng trắng thừa.

    Chữ ký ký trên đúng chuỗi byte này, nên hai lần tuần tự hoá cùng một dict
    phải ra cùng một chuỗi byte.
    """
    return json.dumps(data, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8')


def b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def b64u_decode(text: str) -> bytes:
    text = text.strip()
    pad = '=' * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode((text + pad).encode('ascii'))


def _key_len(n: int) -> int:
    return (n.bit_length() + 7) // 8


def _emsa_pkcs1_v1_5(data: bytes, key_len: int) -> bytes:
    t = _SHA256_DIGEST_INFO + hashlib.sha256(data).digest()
    ps_len = key_len - len(t) - 3
    if ps_len < 8:
        raise SignatureError('Khoá RSA quá ngắn cho chữ ký SHA-256.')
    return b'\x00\x01' + (b'\xff' * ps_len) + b'\x00' + t


def verify_rs256(payload: bytes, signature: bytes, public_key: dict) -> bool:
    n = int(public_key['n'], 16)
    e = int(public_key['e'], 16)
    key_len = _key_len(n)
    if len(signature) != key_len:
        return False
    opened = pow(int.from_bytes(signature, 'big'), e, n).to_bytes(key_len, 'big')
    return hmac.compare_digest(opened, _emsa_pkcs1_v1_5(payload, key_len))


def sign_rs256(payload: bytes, private_key: dict) -> bytes:
    n = int(private_key['n'], 16)
    d = int(private_key['d'], 16)
    key_len = _key_len(n)
    encoded = _emsa_pkcs1_v1_5(payload, key_len)
    return pow(int.from_bytes(encoded, 'big'), d, n).to_bytes(key_len, 'big')


def decode_token(text: str, prefix: str) -> tuple[dict, str, bytes, bytes]:
    """Tách chuỗi ra các phần — CHƯA kiểm chữ ký."""
    token = ''.join(str(text or '').strip().split())
    parts = token.split('.')
    if len(parts) != 4 or parts[0] != prefix:
        raise SignatureError('Sai định dạng.')
    try:
        payload_bytes = b64u_decode(parts[2])
        signature = b64u_decode(parts[3])
        payload = json.loads(payload_bytes.decode('utf-8'))
    except SignatureError:
        raise
    except Exception as exc:
        raise SignatureError(f'Không đọc được nội dung: {exc}') from exc
    if not isinstance(payload, dict):
        raise SignatureError('Nội dung không phải một bản ghi.')
    return payload, parts[1], payload_bytes, signature


def verify_token(text: str, prefix: str) -> dict:
    """Kiểm chữ ký rồi trả nội dung. Ném `SignatureError` nếu không hợp lệ."""
    payload, key_id, payload_bytes, signature = decode_token(text, prefix)
    public_key = PUBLIC_KEYS.get(key_id)
    if public_key is None:
        raise SignatureError(f'Ký bằng khoá phát hành không được hỗ trợ ({key_id}).')
    if not verify_rs256(payload_bytes, signature, public_key):
        raise SignatureError('Chữ ký không hợp lệ — nội dung đã bị sửa.')
    return payload


def encode_token(payload: dict, prefix: str, private_key: dict) -> str:
    """Ký nội dung. Chỉ dùng ở máy người cấp giấy phép."""
    key_id = private_key.get('key_id', 'mtb-v1')
    if key_id not in PUBLIC_KEYS:
        raise SignatureError(
            f'key_id "{key_id}" chưa có trong PUBLIC_KEYS — máy khách sẽ chối '
            'mọi thứ ký bằng khoá này.')
    payload_bytes = json_bytes(payload)
    signature = sign_rs256(payload_bytes, private_key)
    return f'{prefix}.{key_id}.{b64u_encode(payload_bytes)}.{b64u_encode(signature)}'


def default_private_key_path() -> Path:
    """secrets/mtb_license_private.json cạnh kho mã, hoặc cạnh exe khi đóng gói.

    Bản đóng gói có __file__ nằm trong _internal, nên leo hai cấp thư mục sẽ
    trỏ vào ruột gói chứ không phải chỗ người vận hành đặt khoá.
    """
    import sys
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent / 'secrets' / 'mtb_license_private.json'
    return Path(__file__).resolve().parents[2] / 'secrets' / 'mtb_license_private.json'


def load_private_key(path: str | os.PathLike | None = None) -> dict:
    """Nạp khoá riêng cho công cụ nội bộ.

    Thứ tự: tham số → biến `MTB_LICENSE_PRIVATE_KEY` (đường dẫn hoặc chính nội
    dung JSON) → `secrets/mtb_license_private.json`.
    """
    if path is None:
        raw = os.environ.get(PRIVATE_KEY_ENV, '').strip()
        if raw.startswith('{'):
            return json.loads(raw)
        if raw:
            path = raw
    key_path = Path(path) if path else default_private_key_path()
    if not key_path.exists():
        raise SignatureError(
            f'Không thấy khoá riêng ở {key_path}.\n'
            'Sinh khoá: python tools/gen_keypair.py')
    key = json.loads(key_path.read_text(encoding='utf-8-sig'))
    for field in ('n', 'd', 'key_id'):
        if field not in key:
            raise SignatureError(f'Khoá riêng thiếu trường "{field}".')
    return key


def key_fingerprint(key_id: str = 'mtb-v1') -> str:
    """Vân tay SHA-256 của khoá công khai — để ghim trong test."""
    pub = PUBLIC_KEYS[key_id]
    raw = f"{pub['n']}:{pub['e']}".encode('ascii')
    return hashlib.sha256(raw).hexdigest()

"""Sinh cặp khoá RSA-2048 để ký giấy phép.

    python tools/gen_keypair.py --key-id mtb-v1

Khoá riêng ghi ra `secrets/mtb_license_private.json` (thư mục này đã nằm trong
`.gitignore` và KHÔNG được đóng gói vào installer). Phần công khai in ra màn
hình để dán vào `src/security/keys.py`.

Viết bằng Python thuần — không cần `cryptography`/`nacl`, hai thư viện đó đang
bị `installer/build.bat` loại trừ khỏi bản đóng gói.

LUẬT KHÔNG ĐƯỢC PHÁ: không bao giờ thay modulus dưới một `key_id` đã phát
hành. Cần đổi khoá thì THÊM `key_id` mới và giữ nguyên bản cũ trong
`PUBLIC_KEYS`, nếu không mọi bản đã cài sẽ chối sạch giấy phép mới.
"""
from __future__ import annotations

import argparse
import json
import secrets as _secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SMALL_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53,
                59, 61, 67, 71, 73, 79, 83, 89, 97]


def _is_probable_prime(n: int, rounds: int = 40) -> bool:
    """Miller–Rabin. 40 vòng: xác suất lọt < 2^-80."""
    if n < 2:
        return False
    for p in SMALL_PRIMES:
        if n % p == 0:
            return n == p
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for _ in range(rounds):
        a = _secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _gen_prime(bits: int, e: int) -> int:
    while True:
        cand = _secrets.randbits(bits) | (1 << (bits - 1)) | 1
        # gcd(p-1, e) == 1 để nghịch đảo d tồn tại.
        if (cand - 1) % e == 0:
            continue
        if _is_probable_prime(cand):
            return cand


def generate_keypair(bits: int = 2048, key_id: str = 'mtb-v1') -> dict:
    e = 65537
    half = bits // 2
    while True:
        p = _gen_prime(half, e)
        q = _gen_prime(half, e)
        if p == q:
            continue
        n = p * q
        if n.bit_length() != bits:
            continue
        d = pow(e, -1, (p - 1) * (q - 1))
        # Kiểm ngay tại chỗ: ký rồi mở lại phải ra đúng số ban đầu.
        probe = _secrets.randbelow(n - 2) + 1
        if pow(pow(probe, d, n), e, n) != probe:
            continue
        return {
            'key_id': key_id,
            'algorithm': 'RS256-PKCS1-v1_5',
            'n': format(n, 'x').zfill(bits // 4),
            'e': format(e, 'x').zfill(6),
            'd': format(d, 'x'),
            'p': format(p, 'x'),
            'q': format(q, 'x'),
        }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='Sinh cặp khoá ký giấy phép')
    ap.add_argument('--key-id', default='mtb-v1')
    ap.add_argument('--bits', type=int, default=2048)
    ap.add_argument('--out', default=str(ROOT / 'secrets' / 'mtb_license_private.json'))
    ap.add_argument('--force', action='store_true',
                    help='ghi đè khoá riêng đã có (nguy hiểm: mọi giấy phép cũ ký bằng khoá cũ)')
    args = ap.parse_args(argv)

    out = Path(args.out)
    if out.exists() and not args.force:
        print(f'Đã có khoá riêng ở {out}. Muốn ghi đè thì thêm --force.', file=sys.stderr)
        print('CẢNH BÁO: đổi khoá dưới cùng một key_id sẽ làm mọi bản đã cài chối', file=sys.stderr)
        print('giấy phép mới. Đổi khoá thì phải đặt key_id mới.', file=sys.stderr)
        return 2

    print(f'Đang sinh RSA-{args.bits}… (mất vài giây)')
    key = generate_keypair(args.bits, args.key_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(key, indent=2), encoding='utf-8')
    try:
        out.chmod(0o600)
    except OSError:
        pass

    print(f'Khoá riêng: {out}')
    print('\nDán khối dưới đây vào src/security/keys.py:\n')
    n = key['n']
    chunks = [n[i:i + 64] for i in range(0, len(n), 64)]
    print(f"_{args.key_id.upper().replace('-', '_')}_N = (")
    for c in chunks:
        print(f'    "{c}"')
    print(')')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

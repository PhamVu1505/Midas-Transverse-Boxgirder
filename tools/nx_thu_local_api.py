"""
Thử xem MIDAS CIVIL NX có chạy được ở chế độ **Local API** hay không.

    python tools/nx_thu_local_api.py

Vì sao đáng thử
───────────────
Cả đường kiểm chéo NX hiện đi qua **máy chủ MIDAS ở Seoul** (`moa-engineers.
midasit.com`). Hai hệ quả:

* Người dùng ở công trường không có mạng thì không kiểm chéo được.
* Mô hình cầu đi ra khỏi máy, qua một máy chủ nước ngoài. Với hồ sơ thiết kế
  thì đó là chuyện đáng cân nhắc, không phải chuyện kỹ thuật thuần tuý.

Hộp *Apps → API Settings* của NX có ba lựa chọn: `MOA API` · **`Local API`** ·
`SAS API`, kèm ô **Port**. `GC_api.dll` chứa chuỗi `localhost`. Tức rất có thể
NX phục vụ được ngay trên máy — nhưng **chưa ai kiểm chứng**, và dự án này đã
hai lần kết luận sai về khả năng của NX vì suy từ menu ra API. Nên phải đo.

Công cụ này KHÔNG điều khiển NX
───────────────────────────────
Luật của dự án: không mở, không đóng, không bấm hộ vào NX — phiên là của người
dùng. Nên phần đổi chế độ phải do **bạn** làm, công cụ chỉ đo kết quả.

Các bước
────────
1. Mở MIDAS CIVIL NX (không cần mở mô hình nào).
2. `Apps → API Settings` → chọn **Local API** → `Connect`.
3. Chạy lệnh trên.

Đọc kết quả
───────────
* **ĐẠT** — registry đổi sang địa chỉ cục bộ, CVLw mở cổng lắng nghe, và
  `db/UNIT` trả về JSON. Khi đó rút cáp mạng rồi chạy lại `tools/nx_crosscheck.py`
  một mặt cắt: chạy được nghĩa là cả quy trình thoát khỏi máy chủ Seoul.
* **CHƯA** — giữ nguyên đường Seoul như hiện nay, không mất gì.

Công cụ chỉ gọi đúng **một** lệnh đọc (`db/UNIT`). Nó không mở, không sửa, không
giải mô hình nào.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.midas_nx import base_url, doc_registry, NXError, NX  # noqa: E402

CHE_DO = {0: 'MOA API (máy chủ MIDAS ở Seoul)',
          1: 'MOA API (máy chủ MIDAS ở Seoul)',
          2: 'Local API (ngay trên máy này)',
          3: 'SAS API'}


def _cong_dang_nghe() -> list:
    """Cổng TCP mà tiến trình CVLw đang lắng nghe, nếu đọc được."""
    try:
        import subprocess
        r = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             "$p = (Get-Process CVLw -ErrorAction SilentlyContinue).Id; "
             "if ($p) { Get-NetTCPConnection -State Listen -ErrorAction "
             "SilentlyContinue | Where-Object { $_.OwningProcess -in $p } | "
             "ForEach-Object { \"$($_.LocalAddress):$($_.LocalPort)\" } }"],
            capture_output=True, text=True, timeout=20)
        return [l.strip() for l in r.stdout.splitlines() if l.strip()]
    except Exception:
        return []


def main() -> int:
    print('Thử chế độ Local API của MIDAS CIVIL NX')
    print('=' * 58)

    r = doc_registry()
    if not r:
        print('KHÔNG đọc được registry của NX.')
        print('  → NX đã cài chưa? Đã bấm Apps → API Settings → Connect lần nào chưa?')
        return 2

    kieu = r.get('TYPE')
    print(f'  Chế độ hiện tại : {CHE_DO.get(kieu, f"không rõ (TYPE={kieu})")}')
    print(f'  Địa chỉ         : {base_url()}')
    print(f'  Khoá MAPI       : {"có" if r.get("Key") else "CHƯA CÓ"}')

    cong = _cong_dang_nghe()
    print(f'  CVLw lắng nghe  : {", ".join(cong) if cong else "không cổng nào"}')
    print()

    cuc_bo = str(r.get('URI') or '').lower() in ('127.0.0.1', 'localhost', '::1')
    if not cuc_bo:
        print('CHƯA ở chế độ Local API.')
        print('  Trong NX: Apps → API Settings → chọn "Local API" → Connect,')
        print('  rồi chạy lại lệnh này. Không đổi được thì giữ nguyên đường')
        print('  hiện tại — không mất gì.')
        return 1

    print('Đang ở địa chỉ cục bộ. Thử gọi một lệnh đọc vô hại (db/UNIT)…')
    try:
        nx = NX(log=lambda *a: None)
        d = nx.get('db/UNIT')
    except NXError as e:
        print(f'  HỎNG: {e}')
        return 1
    except Exception as e:                     # noqa: BLE001
        print(f'  HỎNG: {type(e).__name__} — {e}')
        return 1

    print(f'  ĐẠT — trả về {len(str(d))} ký tự JSON.')
    print()
    print('Bước tiếp theo, và đây mới là phép kiểm thật:')
    print('  RÚT CÁP MẠNG rồi chạy  python tools/nx_crosscheck.py --chon S16')
    print('  Chạy được nghĩa là cả quy trình đã thoát khỏi máy chủ Seoul.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

"""Khoá công khai để máy khách kiểm chữ ký giấy phép.

LUẬT QUẢN LÝ KHOÁ — đọc trước khi sửa file này
──────────────────────────────────────────────
1. **Không bao giờ thay modulus dưới một `key_id` đã phát hành.** Bản đã cài
   trên máy người dùng chỉ mang modulus mà nó được đóng gói cùng; đổi ruột mà
   giữ tên thì mọi giấy phép ký bằng khoá mới đều bị bản cũ chối, và cách sửa
   duy nhất là phát lại installer cho từng người. (Dự án `Mcoc_python` đã mắc
   đúng lỗi này ngày 9/7/2026.)
2. Bắt buộc đổi khoá — ví dụ lộ khoá riêng — thì **thêm** `key_id` mới và
   **giữ nguyên** entry cũ, để bản mới còn đọc được giấy phép đã cấp.
3. Khoá riêng nằm ngoài repo: `secrets/mtb_license_private.json`, hoặc chỉ
   đường bằng biến môi trường `MTB_LICENSE_PRIVATE_KEY`.
4. Vân tay khoá được ghim trong `tests/test_license.py` — sửa file này là test
   đổ, và đó là chủ ý.
"""
from __future__ import annotations

# mtb-v1 — RSA-2048, sinh 2026-08-21 bằng tools/gen_keypair.py.
_MTB_V1_N = (
    "b6a7b284a572f1fed81d1a813d7c1f2a0661f96db07804a1061f590e5e98d7bc"
    "262a7083efb49d879aed0e9383fd94ad70c35ab64206ccdde5a3641f75a310e0"
    "87eefabaf9313d82dcd1ee8be32a10de1318063cb058c6aeccd10f286d914a07"
    "a14977e19184329770534ea86f813408276a7ffb15818b7b33ad49b9f7c34f50"
    "8d01efef0e37df9b2622af695cefa13b54ad0e1966352785e8a38831367daae3"
    "2a5caca03e53f53c2ad3a625b64cddb3b7e40f0d98f2f3ce33e4672c90e7f288"
    "032428b60f372f1459efcc5b31c48693f6215058df5da9d40d97b62db9b868be"
    "570fab544d8cb658865bdee4df857bddbfbc5071b9275a0c8792e7b1d56ce42f"
)

PUBLIC_KEYS = {
    'mtb-v1': {
        'algorithm': 'RS256-PKCS1-v1_5',
        'n': _MTB_V1_N,
        'e': '010001',
    },
}

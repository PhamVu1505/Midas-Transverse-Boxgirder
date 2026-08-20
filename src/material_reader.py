"""
Material Reader — thông số vật liệu bê tông.

Việc đọc số liệu đã chuyển sang `src/input_reader.py` (sheet INPUT khóa–giá trị,
có đường lui legacy đọc ô cứng). Module này giữ lại API cũ để mọi call site chạy
nguyên, và giữ phần ghi khối MCT vật liệu.
"""

from .input_reader import read_material as _read_material


def read_material(excel_path: str) -> dict:
    """Đọc thông số vật liệu. Ủy quyền cho input_reader.

    Returns:
        dict với keys: fc_mpa, Ec_mpa, Ec_kpa, nu, alpha, density, RH
    """
    return _read_material(excel_path)

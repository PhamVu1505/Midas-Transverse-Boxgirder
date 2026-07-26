"""
PT Property Reader — thông số cáp dự ứng lực ngang.

Việc đọc số liệu đã chuyển sang `src/input_reader.py` (sheet INPUT khóa–giá trị,
có đường lui legacy đọc ô cứng). Module này giữ lại API cũ để mọi call site chạy
nguyên.
"""

from .geometry import TendonProperty
from .input_reader import read_pt_properties as _read_pt_properties


def read_pt_properties(excel_path: str) -> TendonProperty:
    """Đọc thông số cáp DƯL. Ủy quyền cho input_reader."""
    return _read_pt_properties(excel_path)


if __name__ == '__main__':
    import os
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    xls = os.path.join(base, 'data', 'Midas-Transverse-Boxgirder-analysis.xls')
    p = read_pt_properties(xls)
    for f in p.__dataclass_fields__:
        print(f'{f:12s} = {getattr(p, f)}')

"""
Load Reader — thông số tải trọng.

Việc đọc số liệu đã chuyển sang `src/input_reader.py` (sheet INPUT khóa–giá trị,
có đường lui legacy đọc ô cứng). Module này giữ lại API cũ để mọi call site chạy
nguyên, và giữ phần ghi khối MCT tải trọng.
"""

import os

from .input_reader import read_loads as _read_loads


def read_loads(excel_path: str) -> dict:
    """Đọc thông số tải trọng. Ủy quyền cho input_reader."""
    return _read_loads(excel_path)


def write_loads_mct(loads: dict, output_path: str):
    """Xuất file MCT block cho tải trọng (standalone, để kiểm tra)."""
    lines = []
    lines.append('; === LOAD PARAMETERS (from Excel) ===')
    lines.append(f'; TpG(+)           = {loads["tg_pos"]:+.1f} °C')
    lines.append(f'; TpG(-)           = {loads["tg_neg"]:+.1f} °C')
    lines.append(f'; System Temp      = {loads["sys_temp"]:.1f} °C')
    lines.append(f'; Barrier Left     = {loads["barrier_left"]:.2f} kN/m2  (first top elem, width d_L={loads["d_L"]:.3f} m)')
    lines.append(f'; Barrier Right    = {loads["barrier_right"]:.2f} kN/m2  (last top elem, width d_R={loads["d_R"]:.3f} m)')
    lines.append(f'; Pavement         = {loads["pavement"]:.2f} kN/m   (interior top elems)')
    lines.append(f'; WS Fx            = {loads["ws_fx"]:.4f} kN   (nodal, last top node)')
    lines.append(f'; WS My            = {loads["ws_my"]:.4f} kN.m (nodal, last top node)')
    lines.append(f'; WS PD            = {loads["ws_pd"]:.4f} kN/m (beam load, web elements)')
    lines.append(f'; WL Fx            = {loads["wl_fx"]:.2f} kN   (nodal, last top node)')
    lines.append(f'; WL My            = {loads["wl_my"]:.2f} kN.m (nodal, last top node)')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return output_path


if __name__ == '__main__':
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    excel_path = os.path.join(base, 'data', 'Midas-Transverse-Boxgirder-analysis.xls')
    output_path = os.path.join(base, 'output', 'loads.mct')

    loads = read_loads(excel_path)
    write_loads_mct(loads, output_path)

    print('Load parameters from Excel:')
    for k, v in loads.items():
        print(f'  {k:20s} = {v}')
    print(f'  -> {output_path}')

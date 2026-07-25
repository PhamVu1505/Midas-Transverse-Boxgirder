"""
Load Reader - Đọc tải trọng từ Excel và xuất file MCT block.

Input:  data/Midas-Transverse-Boxgirder-analysis.xls (sheet Load)
Output: output/loads.mct (standalone block để kiểm tra)
"""

import os
import re
import xlrd


def _parse_temp(val):
    """Parse temperature string like '+23oC' or '-7oC' → float."""
    if isinstance(val, (int, float)):
        return float(val)
    m = re.match(r'([+-]?\d+\.?\d*)', str(val))
    return float(m.group(1)) if m else 0.0


def _to_float(val, default=0.0):
    """Safely convert Excel value to float."""
    if val is None or val == '':
        return default
    try:
        # Handle cases like "1.2 kN/m2" if necessary (stripping text)
        if isinstance(val, str):
            m = re.match(r'([+-]?\d+\.?\d*)', val)
            return float(m.group(1)) if m else default
        return float(val)
    except (ValueError, TypeError):
        return default


def read_loads(excel_path: str) -> dict:
    """Đọc thông số tải trọng từ sheet 'Load'.

    Returns:
        dict với keys cho từng load case
    """
    wb = xlrd.open_workbook(excel_path)
    ws = wb.sheet_by_name('Load')

    return {
        # Barrier loads + widths (split L/R for half-section box girder)
        # Left = outer curb & handrail; Right = center divider (median strip)
        'barrier_left':  _to_float(ws.cell(9, 8).value, 1.2),    # I10: outer curb (kN/m²)
        'd_L':           _to_float(ws.cell(10, 8).value, 0.4),   # I11: distance from inner edge of left barrier to cantilever tip (m)
        'barrier_right': _to_float(ws.cell(11, 8).value, 1.2),   # I12: median strip / right barrier (kN/m²)
        'd_R':           _to_float(ws.cell(12, 8).value, 0.4),   # I13: distance from inner edge of right barrier to cantilever tip (m)

        # Pavement (interior top slab)
        'pavement': _to_float(ws.cell(8, 6).value, 4.0),         # G9: Pavement (kN/m)

        # Wind on structure (nodal)
        'ws_fx': _to_float(ws.cell(69, 5).value, 0.0),           # F70: WS Fx (kN)
        'ws_my': _to_float(ws.cell(70, 5).value, 0.0),           # F71: WS My (kN.m)

        # Wind on structure (beam load on webs)
        'ws_pd': _to_float(ws.cell(67, 6).value, 0.0),           # G68: PD*At (kN/m)

        # Wind on live load (nodal)
        'wl_fx': _to_float(ws.cell(72, 2).value, 0.0),           # C73: WL Fx (kN)
        'wl_my': _to_float(ws.cell(73, 2).value, 0.0),           # C74: WL My (kN.m)

        # Temperature
        'sys_temp': _to_float(ws.cell(75, 5).value, 0.0),        # F76: System Temp
        'tg_pos':   _parse_temp(ws.cell(76, 5).value),           # F77: TpG(+)
        'tg_neg':   _parse_temp(ws.cell(77, 5).value),           # F78: TpG(-)

        # Live load HL93 - vehicle point loads (kN)
        'lane_load':  _to_float(ws.cell(50, 7).value, 9.3),      # H51: lane load (kN/m)
        'truck_can':  _to_float(ws.cell(50, 8).value, 0.0),      # I51: truck overhang (kN)
        'tandem_can': _to_float(ws.cell(50, 9).value, 0.0),      # J51: tandem overhang (kN)
        'truck_pos':  _to_float(ws.cell(51, 8).value, 145.0),    # I52: truck interior +M (kN)
        'tandem_pos': _to_float(ws.cell(51, 9).value, 110.0),    # J52: tandem interior +M (kN)
        'truck_neg':  _to_float(ws.cell(52, 8).value, 145.0),    # I53: truck interior -M (kN)
        'tandem_neg': _to_float(ws.cell(52, 9).value, 110.0),    # J53: tandem interior -M (kN)

        # Impact factor
        'impact': _to_float(ws.cell(27, 6).value, 0.33),         # G28: IM
    }


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

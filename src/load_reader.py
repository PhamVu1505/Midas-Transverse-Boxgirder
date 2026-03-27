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


def read_loads(excel_path: str) -> dict:
    """Đọc thông số tải trọng từ sheet 'Load'.

    Returns:
        dict với keys cho từng load case
    """
    wb = xlrd.open_workbook(excel_path)
    ws = wb.sheet_by_name('Load')

    return {
        # Temperature
        'tg_pos': _parse_temp(ws.cell(74, 5).value),    # F75: TpG(+)
        'tg_neg': _parse_temp(ws.cell(75, 5).value),    # F76: TpG(-)
        'sys_temp': float(ws.cell(73, 5).value),         # F74: System Temp

        # Dead loads (kN/m as beam load on 1m strip)
        'barrier': float(ws.cell(9, 8).value),           # I10: Barrier
        'pavement': float(ws.cell(8, 6).value),          # G9: Pavement
        'median_strip': float(ws.cell(10, 8).value),     # I11: Center barrier

        # Wind on structure (nodal)
        'ws_fx': float(ws.cell(67, 5).value),            # F68: WS Fx (kN)
        'ws_my': float(ws.cell(68, 5).value),            # F69: WS My (kN.m)

        # Wind on structure (beam load on webs)
        'ws_pd': float(ws.cell(65, 6).value),             # G66: PD*At (kN/m)

        # Wind on live load (nodal)
        'wl_fx': float(ws.cell(70, 2).value),            # C71: WL Fx (kN)
        'wl_my': float(ws.cell(71, 2).value),            # C72: WL My (kN.m)

        # Live load HL93 - vehicle point loads (kN)
        'lane_load': float(ws.cell(48, 7).value),         # H49: lane load (kN/m)
        'truck_can': float(ws.cell(48, 8).value),          # I49: truck overhang (kN)
        'tandem_can': float(ws.cell(48, 9).value),         # J49: tandem overhang (kN)
        'truck_pos': float(ws.cell(49, 8).value),          # I50: truck interior +M (kN)
        'tandem_pos': float(ws.cell(49, 9).value),         # J50: tandem interior +M (kN)
        'truck_neg': float(ws.cell(50, 8).value),          # I51: truck interior -M (kN)
        'tandem_neg': float(ws.cell(50, 9).value),         # J51: tandem interior -M (kN)

        # Impact factor
        'impact': float(ws.cell(25, 6).value),             # G26: IM = 0.25
    }


def write_loads_mct(loads: dict, output_path: str):
    """Xuất file MCT block cho tải trọng (standalone, để kiểm tra)."""
    lines = []
    lines.append('; === LOAD PARAMETERS (from Excel) ===')
    lines.append(f'; TpG(+)           = {loads["tg_pos"]:+.1f} °C')
    lines.append(f'; TpG(-)           = {loads["tg_neg"]:+.1f} °C')
    lines.append(f'; System Temp      = {loads["sys_temp"]:.1f} °C')
    lines.append(f'; Barrier          = {loads["barrier"]:.2f} kN/m2  (first & last top elem)')
    lines.append(f'; Pavement         = {loads["pavement"]:.2f} kN/m   (interior top elems)')
    lines.append(f'; Median Strip     = {loads["median_strip"]:.2f} kN/m2  (not assigned yet)')
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

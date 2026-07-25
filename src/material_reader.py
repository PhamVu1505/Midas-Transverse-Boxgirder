"""
Material Reader - Đọc vật liệu từ Excel và xuất file MCT block.

Input:  data/Midas-Transverse-Boxgirder-analysis.xls (sheet General)
Output: output/material.mct (standalone block, có thể mở kiểm tra)
"""

import os
import xlrd


def _to_float(val, default=0.0):
    """Safely convert Excel value to float."""
    if val is None or val == '':
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def read_material(excel_path: str) -> dict:
    """Đọc thông số vật liệu từ sheet 'General'.

    Returns:
        dict với keys: fc_mpa, Ec_mpa, Ec_kpa, nu, alpha, density, RH
    """
    wb = xlrd.open_workbook(excel_path)
    ws = wb.sheet_by_name('General')

    fc_mpa = _to_float(ws.cell(69, 7).value, 50.0)    # H70: f'c (MPa)
    ec_mpa = _to_float(ws.cell(71, 7).value, 32500.0) # H72: Ec (MPa)
    alpha = _to_float(ws.cell(72, 7).value, 1.08e-5)  # H73: alpha (/°C)
    RH = _to_float(ws.cell(81, 7).value, 80.0)        # H82: relative humidity (%)

    return {
        'fc_mpa': round(fc_mpa, 1),
        'Ec_mpa': round(ec_mpa, 4),
        'Ec_kpa': round(ec_mpa * 1000, 1),
        'nu': 0.2,            # default for concrete
        'alpha': alpha,
        'density': 24.5,      # default kN/m³ for normal-weight concrete
        'RH': round(RH, 1),   # H82: relative humidity (%) for CEB-FIP TDM
    }


def write_material_mct(mat: dict, output_path: str):
    """Xuất file MCT block cho vật liệu."""
    lines = []
    lines.append('; === MATERIAL BLOCK ===')
    lines.append(f'; fc = {mat["fc_mpa"]:.1f} MPa')
    lines.append(f'; Ec = {mat["Ec_mpa"]:.2f} MPa = {mat["Ec_kpa"]:.1f} kN/m2')
    lines.append(f'; nu = {mat["nu"]}')
    lines.append(f'; alpha = {mat["alpha"]} /°C')
    lines.append(f'; density = {mat["density"]} kN/m3')
    lines.append(f'; RH = {mat["RH"]:.0f} %')
    lines.append('')
    lines.append('*MATERIAL    ; Material')
    lines.append('; iMAT, TYPE, MNAME, SPHEAT, HEATCO, PLAST, TUNIT, bMASS, DAMPRATIO, [DATA1]           ; STEEL, CONC, USER')
    lines.append(f'    1, CONC , BoxGirder         , 0, 0, , C, NO, 0.05, 2, '
                 f' {mat["Ec_kpa"]:.4e},   {mat["nu"]},  {mat["alpha"]:.4e},  {mat["density"]},     0')
    lines.append('')
    lines.append('*MATL-COLOR')
    lines.append('; iMAT, W_R, W_G, W_B, HF_R, HF_G, HF_B, HE_R, HE_G, HE_B, bBLEND, FACT')
    lines.append('    1, 255,   0,   0,    0, 255,   0,    0,   0, 255,  NO, 0.5')
    lines.append('')
    fc_int = int(round(mat['fc_mpa']))
    fc_kpa = int(round(mat['fc_mpa'] * 1000))
    rh = int(round(mat['RH']))
    lines.append('*TDM-TYPE    ; Time Dependent Material')
    # CEB-FIP params: fc(kPa), RH(%), notional size h=1m, cement NR, ts=3 day, reserved 0
    lines.append(f'   NAME=C{fc_int}, CEB, {fc_kpa}, {rh}, 1, NR, 3, 0')
    lines.append('')
    lines.append('*TDM-LINK    ; Time Dependent Material Link')
    lines.append('; iMAT, TDM-TYPE1(CREEP/SHRINKAGE), TDM-TYPE2(ELASTICITY)')
    lines.append(f'    1, C{fc_int}, ')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return output_path


if __name__ == '__main__':
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    excel_path = os.path.join(base, 'data', 'Midas-Transverse-Boxgirder-analysis.xls')
    output_path = os.path.join(base, 'output', 'material.mct')

    mat = read_material(excel_path)
    write_material_mct(mat, output_path)

    print(f'Material properties:')
    print(f'  fc    = {mat["fc_mpa"]:.1f} MPa')
    print(f'  Ec    = {mat["Ec_mpa"]:.2f} MPa ({mat["Ec_kpa"]:.4e} kN/m2)')
    print(f'  nu    = {mat["nu"]}')
    print(f'  alpha = {mat["alpha"]} /°C')
    print(f'  gamma = {mat["density"]} kN/m3')
    print(f'  RH    = {mat["RH"]:.0f} %')
    print(f'  -> {output_path}')

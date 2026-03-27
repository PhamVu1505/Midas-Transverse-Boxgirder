"""
Material Reader - Đọc vật liệu từ Excel và xuất file MCT block.

Input:  data/Midas-Transverse-Boxgirder-analysis.xls (sheet General)
Output: output/material.mct (standalone block, có thể mở kiểm tra)
"""

import os
import xlrd


def read_material(excel_path: str) -> dict:
    """Đọc thông số vật liệu từ sheet 'General'.

    Returns:
        dict với keys: Ec_mpa, Ec_kpa, nu, alpha, density
    """
    wb = xlrd.open_workbook(excel_path)
    ws = wb.sheet_by_name('General')

    ec_mpa = ws.cell(71, 7).value    # H72: Ec (MPa)
    alpha = ws.cell(72, 7).value     # H73: alpha (/°C)

    return {
        'Ec_mpa': round(ec_mpa, 4),
        'Ec_kpa': round(ec_mpa * 1000, 1),
        'nu': 0.2,
        'alpha': alpha,
        'density': 24.5,
    }


def write_material_mct(mat: dict, output_path: str):
    """Xuất file MCT block cho vật liệu."""
    lines = []
    lines.append('; === MATERIAL BLOCK ===')
    lines.append(f'; Ec = {mat["Ec_mpa"]:.2f} MPa = {mat["Ec_kpa"]:.1f} kN/m2')
    lines.append(f'; nu = {mat["nu"]}')
    lines.append(f'; alpha = {mat["alpha"]} /°C')
    lines.append(f'; density = {mat["density"]} kN/m3')
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
    lines.append('*TDM-TYPE    ; Time Dependent Material')
    lines.append('   NAME=C50, CEB, 50000, 85, 1, NR, 3, 0')
    lines.append('')
    lines.append('*TDM-LINK    ; Time Dependent Material Link')
    lines.append('; iMAT, TDM-TYPE1(CREEP/SHRINKAGE), TDM-TYPE2(ELASTICITY)')
    lines.append('    1, C50, ')

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
    print(f'  Ec    = {mat["Ec_mpa"]:.2f} MPa ({mat["Ec_kpa"]:.4e} kN/m2)')
    print(f'  nu    = {mat["nu"]}')
    print(f'  alpha = {mat["alpha"]} /°C')
    print(f'  gamma = {mat["density"]} kN/m3')
    print(f'  -> {output_path}')

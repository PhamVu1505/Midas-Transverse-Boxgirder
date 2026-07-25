"""
PT Property Reader - Đọc thông số cáp DƯL ngang từ Excel sheet 'General' A83:K97.

Layout (xls 0-indexed: row 82 = Excel row 83):
    Row  82: RH inserted at H82 (read by material_reader)
    Row  83: Prestressing steel header
    Row  85 (idx 84): Tensile strength    fpu   1860 MPa
    Row  86 (idx 85): Yield strength      fpy   1674 MPa
    Row  87 (idx 86): Modulus             Ep    197000 MPa
    Row  88 (idx 87): Friction coef       mu    0.25 1/rad
    Row  89 (idx 88): Wobble factor       K     6.6e-7 1/mm
    Row  90 (idx 89): Strand diameter     Dp    15.2 mm
    Row  91 (idx 90): Strand area         Aps   140 mm2
    Row  92 (idx 91): # strands           np    5
    Row  93 (idx 92): Tendon area         Ap    700 mm2
    Row  94 (idx 93): Jacking stress      fpj   1395 MPa
    Row  95 (idx 94): Jacking force       Pj    976.5 kN
    Row  96 (idx 95): Anchor set          Δ     0.006 m
    Row  97 (idx 96): Duct DIA            Dduct 66 mm

Cột giá trị: H (idx 7).
"""

import xlrd

from .geometry import TendonProperty


def read_pt_properties(excel_path: str) -> TendonProperty:
    """Đọc thông số PT từ sheet 'General'."""
    wb = xlrd.open_workbook(excel_path)
    ws = wb.sheet_by_name('General')

    def _v(row_idx, col_idx=7):
        val = ws.cell(row_idx, col_idx).value
        if val is None or val == '':
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    fpu       = _v(84)
    fpy       = _v(85)
    Ep        = _v(86)
    mu        = _v(87)
    K         = _v(88)
    Dp        = _v(89)
    Aps       = _v(90)
    n_strands = int(_v(91))
    Ap        = _v(92)
    fpj       = _v(93)
    Pj        = _v(94)
    anchor    = _v(95)
    duct      = _v(96)

    return TendonProperty(
        fpu=fpu, fpy=fpy, Ep=Ep,
        mu=mu, K=K,
        Dp=Dp, Aps=Aps, n_strands=n_strands, Ap=Ap,
        fpj=fpj, Pj=Pj,
        anchor_set=anchor, duct_dia=duct,
    )


if __name__ == '__main__':
    import os
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    xls = os.path.join(base, 'data', 'Midas-Transverse-Boxgirder-analysis.xls')
    p = read_pt_properties(xls)
    print(f'fpu       = {p.fpu} MPa')
    print(f'fpy       = {p.fpy} MPa')
    print(f'Ep        = {p.Ep} MPa')
    print(f'mu        = {p.mu} 1/rad')
    print(f'K         = {p.K} 1/mm')
    print(f'Dp        = {p.Dp} mm')
    print(f'Aps       = {p.Aps} mm2')
    print(f'n_strands = {p.n_strands}')
    print(f'Ap        = {p.Ap} mm2')
    print(f'fpj       = {p.fpj} MPa')
    print(f'Pj        = {p.Pj} kN')
    print(f'anchor    = {p.anchor_set} m')
    print(f'duct_dia  = {p.duct_dia} mm')

"""
PT Property Reader - Đọc thông số cáp DƯL ngang từ Excel sheet 'General' A82:K96.

Layout (xls 0-indexed: row 81 = Excel row 82):
    Row 84 (idx 83): Tensile strength    fpu  1860 MPa
    Row 85 (idx 84): Yield strength      fpy  1674 MPa
    Row 86 (idx 85): Modulus             Ep   197000 MPa
    Row 87 (idx 86): Friction coef       mu   0.25 1/rad
    Row 88 (idx 87): Wobble factor       K    6.6e-7 1/mm
    Row 89 (idx 88): Strand diameter     Dp   15.2 mm
    Row 90 (idx 89): Strand area         Aps  140 mm2
    Row 91 (idx 90): # strands           np   5
    Row 92 (idx 91): Tendon area         Ap   700 mm2
    Row 93 (idx 92): Jacking stress      fpj  1395 MPa
    Row 94 (idx 93): Jacking force       Pj   976.5 kN
    Row 95 (idx 94): Anchor set          Δ    0.006 m
    Row 96 (idx 95): Duct DIA            Dduct 66 mm

Cột giá trị: H (idx 7) — kiểm chứng từ refer.
"""

import xlrd

from .geometry import TendonProperty


def read_pt_properties(excel_path: str) -> TendonProperty:
    """Đọc thông số PT từ sheet 'General'."""
    wb = xlrd.open_workbook(excel_path)
    ws = wb.sheet_by_name('General')

    def _v(row_idx, col_idx=7):
        return float(ws.cell(row_idx, col_idx).value)

    fpu       = _v(83)
    fpy       = _v(84)
    Ep        = _v(85)
    mu        = _v(86)
    K         = _v(87)
    Dp        = _v(88)
    Aps       = _v(89)
    n_strands = int(_v(90))
    Ap        = _v(91)
    fpj       = _v(92)
    Pj        = _v(93)
    anchor    = _v(94)
    duct      = _v(95)

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

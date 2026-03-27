"""
Load Calculator - Tính tải trọng thay đổi theo mặt cắt.

Các tải phụ thuộc H:
- WS (gió kết cấu): áp lực gió × chiều cao bụng
- WL (gió trên xe): moment phụ thuộc H

Các tải cố định (không đổi giữa các mặt cắt):
- Barrier, Pavement, Median Strip
- Temperature gradient (AASHTO Zone 3)
"""

from .geometry import CrossSectionGeometry, LoadParameters


# Hằng số (từ S16 reference)
WS_PRESSURE = 3.664 / 3.2      # kN/m² (áp lực gió tiêu chuẩn)
WS_NODAL_FX_FIXED = -4.91      # kN (gió trên lan can, không đổi theo H)
WS_NODAL_MY_REF = -3.29        # kN.m tại H=3.2m
WL_NODAL_FX_FIXED = -1.5       # kN (1.5 kN/m × 1m strip)
WL_NODAL_MY_REF = -2.7         # kN.m tại H=3.2m
H_REF = 3.2                    # Chiều cao mặt cắt reference (S16)

BARRIER_LOAD = -35.5            # kN/m
PAVEMENT_LOAD = -1.84           # kN/m (γ_asphalt × t_asphalt × 1m)
MEDIAN_LOAD = -19.14            # kN/m


def compute_loads(geo: CrossSectionGeometry) -> LoadParameters:
    """Tính tải trọng cho mặt cắt dựa trên chiều cao H.

    Args:
        geo: Thông số hình học mặt cắt

    Returns:
        LoadParameters chứa tất cả tải trọng
    """
    H = geo.H

    # Wind on Structure (WS)
    ws_beam_intensity = round(-WS_PRESSURE * H, 3)
    ws_nodal_fx = WS_NODAL_FX_FIXED
    ws_nodal_my = round(WS_NODAL_MY_REF * H / H_REF, 2)

    # Wind on Live Load (WL)
    wl_nodal_fx = WL_NODAL_FX_FIXED
    wl_nodal_my = round(WL_NODAL_MY_REF * H / H_REF, 2)

    return LoadParameters(
        ws_beam_intensity=ws_beam_intensity,
        ws_nodal_fx=ws_nodal_fx,
        ws_nodal_my=ws_nodal_my,
        wl_nodal_fx=wl_nodal_fx,
        wl_nodal_my=wl_nodal_my,
        barrier_load=BARRIER_LOAD,
        pavement_load=PAVEMENT_LOAD,
        median_load=MEDIAN_LOAD,
    )

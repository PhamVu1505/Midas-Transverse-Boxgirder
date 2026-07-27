"""
Geometry data classes - Cấu trúc dữ liệu hình học mặt cắt.
"""

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class CrossSectionGeometry:
    """Toàn bộ thông số hình học của một mặt cắt ngang box girder.

    Hệ tọa độ MCT: X ngang (tâm=0), Z đứng (Z=0 đáy, Z=H đỉnh).
    """
    name: str  # Tên mặt cắt, VD: "S16"

    # --- Kích thước tổng thể ---
    H: float            # Chiều cao mặt cắt (m)
    B_total: float      # Tổng chiều rộng bản mặt cầu (m), VD: 16.34
    B_box_top: float    # Chiều rộng hộp tại đỉnh (tâm web trái → tâm web phải) (m)
    B_box_bot: float    # Chiều rộng hộp tại đáy (m), hẹp hơn do web nghiêng

    # --- Chiều dày bản trên ---
    t_top_tip: float        # Chiều dày bản trên tại mép cánh hẫng (m), VD: 0.25
    t_top_at_web: float     # Chiều dày bản trên tại vị trí web (haunch) (m), VD: 0.65
    t_top_center: float     # Chiều dày bản trên tại giữa hộp (m), VD: 0.30

    # --- Chiều dày bản đáy ---
    t_bot_center: float     # Chiều dày bản đáy tại giữa (m)
    t_bot_at_web: float     # Chiều dày bản đáy tại haunch gần web (m)

    # --- Chiều dày bụng ---
    t_web_top: float        # Chiều dày bụng tại đỉnh (m)
    t_web_bot: float        # Chiều dày bụng tại đáy (m)

    # --- Cantilever ---
    cant_left: float        # Chiều dài cánh hẫng trái (m)
    cant_right: float       # Chiều dài cánh hẫng phải (m)

    # --- OUTPOLY vertices (8 đỉnh, hệ DXF: Y=0 top, Y<0 down) ---
    outpoly: List[Tuple[float, float]] = field(default_factory=list)

    # --- INPOLY vertices (10 đỉnh) ---
    inpoly: List[Tuple[float, float]] = field(default_factory=list)
    inpoly_right: List[Tuple[float, float]] = field(default_factory=list)  # twin_box only
    section_type: str = 'single'  # 'single' | 'twin_box'

    # --- PT cables (auto-detected từ layer DXF dạng PT-<LOC>-<N>) ---
    # Mỗi entry: (layer_name, [(x_dxf, y_dxf), ...])
    pt_cables: List[Tuple[str, List[Tuple[float, float]]]] = field(default_factory=list)


@dataclass
class Tendon:
    """Cáp DƯL ngang (đã transform sang hệ MCT element-local).

    profile_points lưu (X_along_elem, Z_offset) cho mỗi vertex DXF.
    """
    name: str                                      # "PT-TOP-1" (= layer name)
    location: str                                  # "TOP" | "BOT" | "WEB-L" | "WEB-R"
    index: int                                     # 1, 2, 3...
    profile_points: List[Tuple[float, float]] = field(default_factory=list)
    elem_list: str = ''                            # "101to124"
    first_elem: int = 0                            # ELEMENT routing line ref

    # Đường cáp trong hệ MCT TOÀN CỤC (x tính từ tim, z tính từ đáy), đã rời rạc
    # hoá cung bulge. Dành cho khung xem: dựng ngược từ `profile_points` không ra
    # được vì mỗi vị trí cáp có quy ước element-local riêng (TOP đo từ mặt bản,
    # BOT đo từ mặt bản đáy, WEB đo theo phương đứng).
    path_mct: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class TendonProperty:
    """Thông số chung của hệ cáp DƯL (đọc từ Excel sheet General A82:K96)."""
    fpu: float          # Tensile strength (MPa)
    fpy: float          # Yield strength (MPa)
    Ep: float           # Modulus (MPa)
    mu: float           # Friction coef (1/rad)
    K: float            # Wobble factor (1/mm)
    Dp: float           # Strand diameter (mm)
    Aps: float          # Strand area (mm²)
    n_strands: int      # # strands per cable
    Ap: float           # Tendon area = Aps * n_strands (mm²)
    fpj: float          # Jacking stress (MPa)
    Pj: float           # Jacking force (kN)
    anchor_set: float   # Δ (m)
    duct_dia: float     # Dduct (mm)


@dataclass
class LoadParameters:
    """Thông số tải trọng thay đổi theo mặt cắt."""
    # --- Tải gió trên kết cấu (WS) ---
    ws_beam_intensity: float    # Cường độ gió trên bụng (kN/m)
    ws_nodal_fx: float          # Lực nút FX tại mép (kN)
    ws_nodal_my: float          # Moment MY tại mép (kN.m)

    # --- Tải gió trên xe (WL) ---
    wl_nodal_fx: float          # Lực WL FX (kN)
    wl_nodal_my: float          # Moment WL MY (kN.m)

    # --- Lan can, lớp phủ, dải phân cách ---
    barrier_load: float         # kN/m
    pavement_load: float        # kN/m
    median_load: float          # kN/m

    # --- Gradient nhiệt ---
    tg_pos: float = 23.0        # Gradient nhiệt (+) °C
    tg_neg: float = -7.0        # Gradient nhiệt (-) °C
    system_temp: float = 20.0   # Nhiệt độ đồng đều °C

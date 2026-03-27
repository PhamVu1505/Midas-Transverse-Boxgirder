"""
Assembler - Ghép các MCT blocks thành file hoàn chỉnh.

Pipeline: DXF → Geometry → Nodes → Elements → Sections → Loads → MCT
"""

from .geometry import CrossSectionGeometry, LoadParameters
from .dxf_reader import read_dxf
from .node_generator import generate_all_nodes
from .section_builder import build_all_sections
from .load_calculator import compute_loads
from .svg_export import export_svg
from . import mct_writer


def assemble_mct(geo: CrossSectionGeometry, loads: LoadParameters,
                 nodes: dict, sections: list) -> str:
    """Ghép toàn bộ MCT blocks thành chuỗi hoàn chỉnh.

    Args:
        geo: CrossSectionGeometry
        loads: LoadParameters
        nodes: dict from generate_all_nodes()
        sections: list of SectionDefinition from build_all_sections()

    Returns:
        Chuỗi MCT hoàn chỉnh, sẵn sàng ghi file
    """
    blocks = [
        # Header
        mct_writer.write_header(geo),
        mct_writer.write_unit(),
        mct_writer.write_structype(),
        mct_writer.write_rebar_code(),

        # Geometry
        mct_writer.write_nodes(nodes),
        mct_writer.write_elements(),
        mct_writer.write_groups(),
        mct_writer.write_boundary_group(),
        mct_writer.write_load_group(),

        # Material
        mct_writer.write_material(),
        mct_writer.write_tdm(),
        mct_writer.write_elem_depmatl(geo),

        # Sections
        mct_writer.write_sections(sections),
        mct_writer.write_sect_color(),

        # Load cases
        mct_writer.write_stld_cases(),
        mct_writer.write_constraints(),
        mct_writer.write_selfweight(),
        mct_writer.write_thermal_gradient_pos(loads),
        mct_writer.write_system_temperature(loads),
        mct_writer.write_wind_structure(loads),
        mct_writer.write_barrier(loads),
        mct_writer.write_pavement(loads),
        mct_writer.write_median_strip(loads),
        mct_writer.write_thermal_gradient_neg(loads),
        mct_writer.write_wind_live(loads),

        # Moving load
        mct_writer.write_moving_load_code(),
        mct_writer.write_traffic_lanes(),
        mct_writer.write_vehicles(),
        mct_writer.write_vehicle_classes(),
        mct_writer.write_moving_load_cases(),

        # Combinations
        mct_writer.write_load_combinations(),
        mct_writer.write_lc_color(),

        # Control & footer
        mct_writer.write_move_ctrl(),
        mct_writer.write_dgn_matl(),
        mct_writer.write_enddata(),
    ]

    return '\n'.join(blocks)


def generate_from_dxf(dxf_path: str, output_path: str = None) -> str:
    """Pipeline chính: DXF → MCT file.

    Args:
        dxf_path: Đường dẫn file DXF
        output_path: Đường dẫn output (optional, tự tạo nếu không chỉ định)

    Returns:
        Đường dẫn file MCT đã tạo
    """
    import os

    # Step 1: Read DXF
    print(f"[1/5] Đọc file DXF: {dxf_path}")
    geo = read_dxf(dxf_path)
    print(f"       {geo.name}: H={geo.H}m, B={geo.B_total}m, B_box_top={geo.B_box_top}m")
    print(f"       t_top: tip={geo.t_top_tip}m, web={geo.t_top_at_web}m, center={geo.t_top_center}m")
    print(f"       t_bot: center={geo.t_bot_center}m, web={geo.t_bot_at_web}m")
    print(f"       t_web: top={geo.t_web_top}m, bot={geo.t_web_bot}m")

    # Step 2: Generate nodes
    print(f"[2/5] Tạo 50 nodes...")
    nodes = generate_all_nodes(geo)
    n_total = sum(len(v) for v in nodes.values())
    print(f"       {n_total} nodes: bottom={len(nodes['bottom'])}, "
          f"web_L={len(nodes['web_left'])}, web_R={len(nodes['web_right'])}, "
          f"top={len(nodes['top'])}")

    # Step 3: Build sections
    print(f"[3/5] Tạo 50 sections...")
    sections = build_all_sections(geo, nodes)
    n_tapered = sum(1 for s in sections if s.is_tapered)
    n_psc = len(sections) - n_tapered
    print(f"       {len(sections)} sections: {n_psc} PSC + {n_tapered} TAPERED")

    # Step 4: Compute loads
    print(f"[4/5] Tính tải trọng...")
    loads = compute_loads(geo)
    print(f"       WS beam: {loads.ws_beam_intensity} kN/m")

    # Step 5: Assemble MCT
    print(f"[5/5] Ghép file MCT...")
    mct_content = assemble_mct(geo, loads, nodes, sections)

    # Write file
    if output_path is None:
        output_path = os.path.splitext(dxf_path)[0] + '.mct'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(mct_content)

    n_lines = mct_content.count('\n')
    print(f"  -> {output_path} ({len(mct_content)} bytes, {n_lines} lines)")

    # Export SVG visualization
    svg_path = os.path.splitext(output_path)[0] + '.svg'
    export_svg(geo, nodes, svg_path)
    print(f"  -> {svg_path} (SVG visualization)")

    return output_path

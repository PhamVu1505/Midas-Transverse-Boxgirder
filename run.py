"""
Entry point - Pipeline phân tích khung ngang dầm hộp.

Commands:
    python run.py generate input/dxf/S20.dxf              # 1 file → output/S20/
    python run.py generate input/dxf/                      # all DXF in folder
    python run.py results  output/S20/                     # parse Beam Force → check table + Excel
    python run.py results  output/                         # batch all subfolders
"""

import argparse
import os
import sys
import glob

import ezdxf

from src.dxf_reader import _get_polyline_vertices, read_pt_cables
from src.frame_builder import build_frame
from src.load_reader import read_loads
from src.mct_frame_writer import write_mct
from src.pt_property_reader import read_pt_properties
from src.result_reader import (parse_beam_force, _build_element_thickness,
                               _classify_check_elements, extract_check_points,
                               format_check_table)


EXCEL_PATH = os.path.join(os.path.dirname(__file__),
                          'data', 'Midas-Transverse-Boxgirder-analysis.xls')


# ─────────────────────────────────────────────
# Generate: DXF → MCT + SVG
# ─────────────────────────────────────────────

def _generate_one(dxf_path: str, output_dir: str, include_pt: bool = None):
    """Generate MCT + SVG for one DXF file into output_dir/name/.

    include_pt: True/False/None (None = auto-detect from DXF layers).
    """
    name = os.path.splitext(os.path.basename(dxf_path))[0]
    section_dir = os.path.join(output_dir, name)
    os.makedirs(section_dir, exist_ok=True)

    print(f'[{name}] Reading DXF: {dxf_path}')
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    outpoly = _get_polyline_vertices(msp, 'OUTPOLY')
    inpoly = _get_polyline_vertices(msp, 'INPOLY')
    pt_cables = read_pt_cables(msp) if include_pt is not False else []

    excel = EXCEL_PATH if os.path.exists(EXCEL_PATH) else None
    if not excel:
        print(f'[{name}] WARNING: Excel not found at {EXCEL_PATH}')
        print(f'[{name}] WARNING: using fallback d_L=d_R=0.4 m and skipping all load blocks')
    ld = read_loads(excel) if excel else None
    d_L = ld['d_L'] if ld else 0.4
    d_R = ld['d_R'] if ld else 0.4

    print(f'[{name}] Building frame (d_L={d_L:.3f}, d_R={d_R:.3f})...')
    frame = build_frame(outpoly, inpoly, d_L=d_L, d_R=d_R)

    pt_props = read_pt_properties(excel) if (excel and pt_cables) else None
    if pt_cables:
        print(f'[{name}] PT cables detected: {[n for n, _ in pt_cables]}')

    print(f'[{name}] Writing MCT...')
    mct_text, topo = write_mct(frame, name, excel,
                               pt_cables=pt_cables, pt_props=pt_props,
                               include_pt=include_pt)

    mct_path = os.path.join(section_dir, f'{name}_frame.mct')
    with open(mct_path, 'w', encoding='utf-8') as f:
        f.write(mct_text)

    # SVG
    from src.svg_export import export_frame_svg
    svg_path = os.path.join(section_dir, f'{name}_frame.svg')
    try:
        export_frame_svg(outpoly, inpoly, svg_path, name)
    except Exception:
        pass

    n_elem = len(topo['elements'])
    print(f'[{name}] Done: {n_elem} elements -> {mct_path}')
    return section_dir


def cmd_generate(args):
    """Handle 'generate' command."""
    paths = args.input
    output_dir = args.output_dir
    include_pt = False if getattr(args, 'no_pt', False) else None

    dxf_files = []
    for p in paths:
        if os.path.isdir(p):
            dxf_files.extend(sorted(glob.glob(os.path.join(p, '*.dxf'))))
        elif os.path.isfile(p) and p.lower().endswith('.dxf'):
            dxf_files.append(p)
        else:
            print(f'  [WARN] Skipping: {p}')

    if not dxf_files:
        print('No DXF files found.')
        return

    print(f'Generating {len(dxf_files)} section(s)...\n')
    for dxf_path in dxf_files:
        try:
            _generate_one(dxf_path, output_dir, include_pt=include_pt)
        except Exception as e:
            print(f'  [ERROR] {dxf_path}: {e}')
            import traceback
            traceback.print_exc()
        print()

    print(f'All outputs in: {os.path.abspath(output_dir)}')


# ─────────────────────────────────────────────
# Results: Beam Force XLS → check table + Excel
# ─────────────────────────────────────────────

def _find_beam_force(section_dir: str) -> str:
    """Find Beam Force XLS in section directory."""
    pattern = os.path.join(section_dir, 'Beam Force*.xls')
    files = glob.glob(pattern)
    if files:
        return files[0]
    return None


def _find_dxf_for_section(name: str) -> str:
    """Find DXF file for a section name."""
    base = os.path.dirname(os.path.abspath(__file__))
    dxf_dir = os.path.join(base, 'input', 'dxf')
    path = os.path.join(dxf_dir, f'{name}.dxf')
    if os.path.exists(path):
        return path
    return None


def _process_results(section_dir: str):
    """Process results for one section."""
    name = os.path.basename(section_dir.rstrip('/\\'))

    # Find Beam Force XLS
    xls_path = _find_beam_force(section_dir)
    if not xls_path:
        print(f'[{name}] No Beam Force XLS found in {section_dir}')
        return None

    # Find DXF to rebuild topology
    dxf_path = _find_dxf_for_section(name)
    if not dxf_path:
        print(f'[{name}] No DXF file found for section {name}')
        return None

    print(f'[{name}] Parsing: {os.path.basename(xls_path)}')

    # Build topology
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    excel = EXCEL_PATH if os.path.exists(EXCEL_PATH) else None
    if not excel:
        print(f'[{name}] WARNING: Excel not found, using fallback d_L=d_R=0.4 m')
    ld = read_loads(excel) if excel else None
    d_L = ld['d_L'] if ld else 0.4
    d_R = ld['d_R'] if ld else 0.4
    frame = build_frame(
        _get_polyline_vertices(msp, 'OUTPOLY'),
        _get_polyline_vertices(msp, 'INPOLY'),
        d_L=d_L, d_R=d_R)
    _, topo = write_mct(frame, name, excel)

    # Parse beam force
    results = parse_beam_force(xls_path)
    result_elems = set(r['elem'] for r in results)
    mct_elems = set(eid for eid, _, _, _ in topo['elements'])

    if result_elems != mct_elems:
        print(f'[{name}] ERROR: Element mismatch!')
        print(f'        MCT: {len(mct_elems)} elems, Results: {len(result_elems)} elems')
        diff1 = sorted(mct_elems - result_elems)
        diff2 = sorted(result_elems - mct_elems)
        if diff1:
            print(f'        In MCT but not results: {diff1}')
        if diff2:
            print(f'        In results but not MCT: {diff2}')
        return None

    print(f'[{name}] {len(results)} records, {len(result_elems)} elements — match OK')

    # Build check points
    thick_map = _build_element_thickness(topo['elements'], topo['sections'])

    top_eids = list(range(topo['eid_top_start'], topo['eid_top_end'] + 1))
    bot_eids = list(range(topo['e_bot_first'], topo['e_bot_last'] + 1))
    wL_eids = list(range(topo['eid_wL_start'], topo['eid_wL_end'] + 1))
    wR_eids = list(range(topo['eid_wR_start'], topo['eid_wR_end'] + 1))

    check_elems = _classify_check_elements(
        topo['top_ids'], top_eids,
        topo['wL_insert_idx'], topo['wR_insert_idx'],
        topo['bot_ids'], bot_eids, wL_eids, wR_eids,
        topo['eid_top_start'])

    check_points = extract_check_points(results, check_elems, thick_map)

    # Print table
    table = format_check_table(name, check_points)
    print()
    print(table)
    print()

    # Save text table
    txt_path = os.path.join(section_dir, f'{name}_check.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(table)
    print(f'[{name}] Saved: {txt_path}')

    # Export Excel
    xlsx_path = os.path.join(section_dir, f'{name}_check.xlsx')
    _export_excel(name, check_points, xlsx_path)
    print(f'[{name}] Saved: {xlsx_path}')

    return check_points


def _export_excel(section_name: str, check_points: dict, xlsx_path: str):
    """Export check points to Excel file."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    except ImportError:
        print(f'  [WARN] openpyxl not installed, skipping Excel export')
        print(f'         Install: pip install openpyxl')
        return

    wb = Workbook()
    ws = wb.active
    ws.title = 'Check Points'

    points = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    labels = ['Center +', 'Haunch M-', 'Haunch M+', 'Out Side',
              'Center', 'Haunch', 'Mid->upper', 'Mid->lower']
    groups = ['Top slab', '', '', '', 'Bottom slab', '', 'Web', '']

    # Styles
    bold = Font(bold=True)
    center = Alignment(horizontal='center', vertical='center')
    right = Alignment(horizontal='right', vertical='center')
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin'))
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')
    group_fill = PatternFill(start_color='D9E2F3', end_color='D9E2F3', fill_type='solid')

    # Title
    ws.merge_cells('A1:I1')
    ws['A1'] = f'{section_name} — Check Points'
    ws['A1'].font = Font(bold=True, size=14)

    # Row 3: Header (Check Point letters)
    row = 3
    ws.cell(row, 1, '').border = thin_border
    for j, p in enumerate(points):
        cell = ws.cell(row, j + 2, p)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = thin_border

    # Row 4: Groups
    row = 4
    ws.cell(row, 1, '').border = thin_border
    for j, g in enumerate(groups):
        cell = ws.cell(row, j + 2, g)
        cell.font = bold
        cell.fill = group_fill
        cell.alignment = center
        cell.border = thin_border

    # Row 5: Labels
    row = 5
    ws.cell(row, 1, '').border = thin_border
    for j, lbl in enumerate(labels):
        cell = ws.cell(row, j + 2, lbl)
        cell.alignment = center
        cell.border = thin_border

    # Data rows
    data_rows = [
        ('Depth h (mm)', 'h', '{:.0f}'),
        ('Strength Mu (kN.m)', 'Mu', '{:.2f}'),
        ('  -> element', 'Mu_ref', '{}'),
        ('Strength Vu (kN)', 'Vu', '{:.2f}'),
        ('  -> element', 'Vu_ref', '{}'),
        ('Service Mser (kN.m)', 'Mser', '{:.2f}'),
        ('  -> element', 'Mser_ref', '{}'),
    ]

    for i, (label, key, fmt) in enumerate(data_rows):
        row = 6 + i
        cell = ws.cell(row, 1, label)
        cell.font = bold if not label.startswith(' ') else Font()
        cell.border = thin_border

        for j, p in enumerate(points):
            val = check_points[p][key]
            if isinstance(val, str):
                cell = ws.cell(row, j + 2, val)
                cell.alignment = center
            else:
                cell = ws.cell(row, j + 2, val)
                cell.number_format = '#,##0.00' if '.' in fmt else '#,##0'
                cell.alignment = right
            cell.border = thin_border

    # Column widths
    ws.column_dimensions['A'].width = 24
    for j in range(8):
        col_letter = chr(ord('B') + j)
        ws.column_dimensions[col_letter].width = 14

    wb.save(xlsx_path)


def cmd_results(args):
    """Handle 'results' command."""
    paths = args.input
    all_results = {}

    for p in paths:
        p = p.rstrip('/\\')
        if os.path.isdir(p):
            # Check if this dir contains Beam Force XLS directly
            if _find_beam_force(p):
                cp = _process_results(p)
                if cp:
                    all_results[os.path.basename(p)] = cp
                print()

            # Also scan subdirectories
            subdirs = sorted([d for d in os.listdir(p)
                              if os.path.isdir(os.path.join(p, d))])
            for sub in subdirs:
                sub_path = os.path.join(p, sub)
                if _find_beam_force(sub_path):
                    cp = _process_results(sub_path)
                    if cp:
                        all_results[sub] = cp
                    print()
        else:
            print(f'  [WARN] Not a directory: {p}')

    if len(all_results) > 1:
        print(f'\n{"="*60}')
        print(f'Summary: {len(all_results)} sections processed')
        print(f'{"="*60}')

    if not all_results:
        print('No Beam Force results found.')
        print('Place "Beam Force_*.xls" in the section output folder.')


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Transverse Frame Analysis Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python run.py generate input/dxf/S20.dxf          # 1 section
  python run.py generate input/dxf/                  # all DXF files
  python run.py results  output/S20/                 # 1 section results
  python run.py results  output/                     # all sections
""")

    subparsers = parser.add_subparsers(dest='command', help='Command')

    # generate
    gen_parser = subparsers.add_parser('generate', help='DXF → MCT + SVG')
    gen_parser.add_argument('input', nargs='+', help='DXF file(s) or directory')
    gen_parser.add_argument('-d', '--output-dir', default='output',
                           help='Output root directory (default: output)')
    gen_parser.add_argument('--no-pt', action='store_true',
                           help='Skip PT tendon detection even if DXF has PT-* layers')

    # results
    res_parser = subparsers.add_parser('results', help='Beam Force → check table + Excel')
    res_parser.add_argument('input', nargs='+',
                           help='Section output folder(s) or parent directory')

    args = parser.parse_args()

    if args.command == 'generate':
        cmd_generate(args)
    elif args.command == 'results':
        cmd_results(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

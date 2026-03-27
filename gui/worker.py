"""Background workers for Generate and Results processing."""

import os
import glob

import ezdxf
from PyQt6.QtCore import QThread, pyqtSignal

from src.dxf_reader import _get_polyline_vertices
from src.frame_builder import build_frame
from src.mct_frame_writer import write_mct
from src.svg_export import export_frame_svg
from src.result_reader import (parse_beam_force, _build_element_thickness,
                               _classify_check_elements, extract_check_points)


DXF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'input', 'dxf')


class GenerateWorker(QThread):
    """Generate MCT + SVG from DXF files."""
    log = pyqtSignal(str)
    section_done = pyqtSignal(str, str)  # name, svg_path
    finished_all = pyqtSignal(int)       # count

    def __init__(self, dxf_paths: list, output_dir: str, excel_path: str = None):
        super().__init__()
        self.dxf_paths = dxf_paths
        self.output_dir = output_dir
        self.excel_path = excel_path

    def run(self):
        count = 0
        excel = self.excel_path if self.excel_path and os.path.exists(self.excel_path) else None

        for dxf_path in self.dxf_paths:
            name = os.path.splitext(os.path.basename(dxf_path))[0]
            section_dir = os.path.join(self.output_dir, name)
            os.makedirs(section_dir, exist_ok=True)

            try:
                self.log.emit(f'[{name}] Reading DXF...')
                doc = ezdxf.readfile(dxf_path)
                msp = doc.modelspace()
                outpoly = _get_polyline_vertices(msp, 'OUTPOLY')
                inpoly = _get_polyline_vertices(msp, 'INPOLY')

                self.log.emit(f'[{name}] Building frame...')
                frame = build_frame(outpoly, inpoly)

                self.log.emit(f'[{name}] Writing MCT...')
                mct_text, topo = write_mct(frame, name, excel)
                mct_path = os.path.join(section_dir, f'{name}_frame.mct')
                with open(mct_path, 'w', encoding='utf-8') as f:
                    f.write(mct_text)

                svg_path = os.path.join(section_dir, f'{name}_frame.svg')
                try:
                    export_frame_svg(outpoly, inpoly, svg_path, name)
                except Exception:
                    svg_path = ''

                n_elem = len(topo['elements'])
                self.log.emit(f'[{name}] Done: {n_elem} elements -> {mct_path}')
                self.section_done.emit(name, svg_path)
                count += 1

            except Exception as e:
                self.log.emit(f'[{name}] ERROR: {e}')

        self.finished_all.emit(count)


class ResultsWorker(QThread):
    """Process Beam Force results for sections."""
    log = pyqtSignal(str)
    section_done = pyqtSignal(str, dict)  # name, check_points
    finished_all = pyqtSignal(int)

    def __init__(self, section_dirs: list):
        super().__init__()
        self.section_dirs = section_dirs

    def run(self):
        count = 0
        excel = None  # Results pipeline doesn't need Excel (only topo needed)

        for section_dir in self.section_dirs:
            name = os.path.basename(section_dir.rstrip('/\\'))

            # Find Beam Force XLS
            xls_files = glob.glob(os.path.join(section_dir, 'Beam Force*.xls'))
            if not xls_files:
                continue
            xls_path = xls_files[0]

            # Find DXF
            dxf_path = os.path.join(DXF_DIR, f'{name}.dxf')
            if not os.path.exists(dxf_path):
                self.log.emit(f'[{name}] No DXF found')
                continue

            try:
                self.log.emit(f'[{name}] Parsing: {os.path.basename(xls_path)}')

                doc = ezdxf.readfile(dxf_path)
                msp = doc.modelspace()
                frame = build_frame(
                    _get_polyline_vertices(msp, 'OUTPOLY'),
                    _get_polyline_vertices(msp, 'INPOLY'))
                _, topo = write_mct(frame, name, excel)

                results = parse_beam_force(xls_path)
                result_elems = set(r['elem'] for r in results)
                mct_elems = set(eid for eid, _, _, _ in topo['elements'])

                if result_elems != mct_elems:
                    self.log.emit(f'[{name}] ERROR: Element mismatch! '
                                  f'MCT={len(mct_elems)}, Results={len(result_elems)}')
                    continue

                self.log.emit(f'[{name}] {len(results)} records, {len(result_elems)} elements — OK')

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

                # Save text + Excel
                from src.result_reader import format_check_table
                txt_path = os.path.join(section_dir, f'{name}_check.txt')
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(format_check_table(name, check_points))
                self.log.emit(f'[{name}] Saved: {txt_path}')

                from run import _export_excel
                xlsx_path = os.path.join(section_dir, f'{name}_check.xlsx')
                _export_excel(name, check_points, xlsx_path)
                self.log.emit(f'[{name}] Saved: {xlsx_path}')

                self.section_done.emit(name, check_points)
                count += 1

            except Exception as e:
                self.log.emit(f'[{name}] ERROR: {e}')

        self.finished_all.emit(count)

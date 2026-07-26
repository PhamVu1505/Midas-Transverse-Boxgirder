"""Background workers for Generate and Results processing."""

import json
import os
import traceback

import ezdxf
from PyQt6.QtCore import QThread, pyqtSignal

from src.dxf_reader import _get_polyline_vertices, read_inpolys, read_pt_cables, section_type_from_inpolys
from src.frame_builder import build_frame
from src.load_reader import read_loads
from src.input_reader import source_line
from src.mct_frame_writer import write_mct
from src.pt_property_reader import read_pt_properties
from src.svg_export import export_frame_svg
from src.result_reader import (parse_beam_force, _build_element_thickness,
                               _classify_check_elements, extract_check_points)


class GenerateWorker(QThread):
    """Generate MCT + SVG from DXF files."""
    log = pyqtSignal(str)
    section_done = pyqtSignal(str, str)  # name, svg_path
    finished_all = pyqtSignal(int)       # count

    def __init__(self, dxf_paths: list, output_dir: str, excel_path: str = None,
                 include_pt: bool = None):
        super().__init__()
        self.dxf_paths = dxf_paths
        self.output_dir = output_dir
        self.excel_path = excel_path
        self.include_pt = include_pt    # True/False/None (None = auto)

    def run(self):
        count = 0
        excel = self.excel_path if self.excel_path and os.path.exists(self.excel_path) else None
        if not excel:
            self.log.emit('WARNING: Excel not found — using fallback d_L=d_R=0.4 m and skipping load blocks')
        else:
            self.log.emit(source_line(excel))
        ld = read_loads(excel) if excel else None
        d_L = ld['d_L'] if ld else 0.4
        d_R = ld['d_R'] if ld else 0.4

        for dxf_path in self.dxf_paths:
            name = os.path.splitext(os.path.basename(dxf_path))[0]
            section_dir = os.path.join(self.output_dir, name)
            os.makedirs(section_dir, exist_ok=True)

            try:
                self.log.emit(f'[{name}] Reading DXF...')
                doc = ezdxf.readfile(dxf_path)
                msp = doc.modelspace()
                outpoly = _get_polyline_vertices(msp, 'OUTPOLY')
                inpolys = read_inpolys(msp)
                stype = section_type_from_inpolys(inpolys)
                inpoly = inpolys if stype == 'twin_box' else inpolys[0]
                pt_cables = read_pt_cables(msp) if self.include_pt is not False else []
                if pt_cables:
                    layer_names = ', '.join(n for n, _ in pt_cables)
                    self.log.emit(f'[{name}] PT cables: {layer_names}')

                self.log.emit(f'[{name}] Building frame ({stype}, d_L={d_L:.3f}, d_R={d_R:.3f})...')
                frame = build_frame(outpoly, inpoly, d_L=d_L, d_R=d_R)

                pt_props = read_pt_properties(excel) if (excel and pt_cables) else None

                self.log.emit(f'[{name}] Writing MCT...')
                mct_text, topo = write_mct(frame, name, excel,
                                           pt_cables=pt_cables, pt_props=pt_props,
                                           include_pt=self.include_pt)
                mct_path = os.path.join(section_dir, f'{name}_frame.mct')
                with open(mct_path, 'w', encoding='utf-8') as f:
                    f.write(mct_text)

                # Save topology for Results step (element IDs, sections, ranges)
                topo_path = os.path.join(section_dir, f'{name}_topo.json')
                with open(topo_path, 'w', encoding='utf-8') as f:
                    json.dump(topo, f, indent=2)

                svg_path = os.path.join(section_dir, f'{name}_frame.svg')
                try:
                    export_frame_svg(outpoly, inpoly, svg_path, name, section_type=stype)
                except Exception:
                    svg_path = ''

                n_elem = len(topo['elements'])
                self.log.emit(f'[{name}] Done: {n_elem} elements -> {mct_path}')
                self.section_done.emit(name, svg_path)
                count += 1

            except Exception as e:
                err_msg = f'[{name}] ERROR: {str(e)}\n{traceback.format_exc()}'
                self.log.emit(err_msg)

        self.finished_all.emit(count)


class ResultsWorker(QThread):
    """Process Beam Force results matched with MCT topology files."""
    log = pyqtSignal(str)
    section_done = pyqtSignal(str, dict)       # name, check_points
    error_mismatch = pyqtSignal(str, int, int, str)  # name, mct_count, result_count, bf_path
    finished_all = pyqtSignal(int)             # count

    def __init__(self, pairs: list, output_dir: str):
        super().__init__()
        self.pairs = pairs          # [(name, bf_path, topo_path), ...]
        self.output_dir = output_dir
        self._retries = []          # [(name, new_bf_path, topo_path)]

    def run(self):
        count = 0
        for name, bf_path, topo_path in self.pairs:
            ok = self._process_one(name, bf_path, topo_path)
            if ok:
                count += 1

        # Process any retries queued via retry_section()
        while self._retries:
            retry_name, retry_bf, retry_topo = self._retries.pop(0)
            ok = self._process_one(retry_name, retry_bf, retry_topo)
            if ok:
                count += 1

        self.finished_all.emit(count)

    def _process_one(self, name, bf_path, topo_path):
        """Process a single section. Returns True on success."""
        section_dir = os.path.join(self.output_dir, name)
        os.makedirs(section_dir, exist_ok=True)

        try:
            self.log.emit(f'[{name}] Loading topology: {os.path.basename(topo_path)}')
            with open(topo_path, 'r', encoding='utf-8') as f:
                topo = json.load(f)

            # Convert JSON lists back to tuples for compatibility
            topo['elements'] = [tuple(e) for e in topo['elements']]
            topo['sections'] = [tuple(s) for s in topo['sections']]

            self.log.emit(f'[{name}] Parsing: {os.path.basename(bf_path)}')
            results = parse_beam_force(bf_path)
            result_elems = set(r['elem'] for r in results)
            mct_elems = set(eid for eid, _, _, _ in topo['elements'])

            if result_elems != mct_elems:
                self.log.emit(f'[{name}] Element mismatch: '
                              f'MCT={len(mct_elems)}, Results={len(result_elems)}')
                self.error_mismatch.emit(name, len(mct_elems),
                                         len(result_elems), bf_path)
                return False

            self.log.emit(f'[{name}] {len(results)} records, '
                          f'{len(result_elems)} elements — OK')

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

            # Save text report
            from src.result_reader import format_check_table
            txt_path = os.path.join(section_dir, f'{name}_check.txt')
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(format_check_table(name, check_points))
            self.log.emit(f'[{name}] Saved: {txt_path}')

            # Save Excel report
            from run import _export_excel
            xlsx_path = os.path.join(section_dir, f'{name}_check.xlsx')
            _export_excel(name, check_points, xlsx_path)
            self.log.emit(f'[{name}] Saved: {xlsx_path}')

            self.section_done.emit(name, check_points)
            return True

        except Exception as e:
            err_msg = f'[{name}] ERROR: {str(e)}\n{traceback.format_exc()}'
            self.log.emit(err_msg)
            return False

    def retry_section(self, name, new_bf_path):
        """Queue a section for retry with a different Beam Force file."""
        topo_path = None
        for n, _, tp in self.pairs:
            if n == name:
                topo_path = tp
                break
        if topo_path:
            self._retries.append((name, new_bf_path, topo_path))

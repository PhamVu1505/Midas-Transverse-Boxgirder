"""Background workers for Generate and Results processing."""

import json
import os
import traceback

import ezdxf
from PyQt6.QtCore import QThread, pyqtSignal

from src.dxf_reader import (_get_polyline_vertices, read_inpolys, read_pt_cables,
                            scan_pt_layers, section_type_from_inpolys)
from src.frame_builder import build_frame
from src.load_reader import read_loads
from src.input_reader import source_line
from src.mct_frame_writer import write_mct
from src.pt_property_reader import read_pt_properties
from src.svg_export import export_frame_svg
from src.result_reader import (parse_beam_force, _build_element_thickness,
                               classify_check_elements, extract_check_points)


class GenerateWorker(QThread):
    """Sinh MCT + SVG từ danh sách công việc.

    Mỗi job là một dict {name, dxf, excel, include_pt} — template đọc theo TỪNG
    mặt cắt, vì các mặt cắt khác số sườn hoặc khác bề rộng dùng template khác nhau.
    """
    log = pyqtSignal(str)
    section_done = pyqtSignal(str, str)      # name, svg_path
    section_info = pyqtSignal(str, dict)     # name, thông tin ghi vào project
    section_error = pyqtSignal(str, str)     # name, thông báo lỗi
    finished_all = pyqtSignal(int)

    def __init__(self, jobs: list, output_dir: str, con_can=None):
        super().__init__()
        self.jobs = jobs
        self.output_dir = output_dir
        # `con_can(tên) -> bool`: mặt cắt còn nằm trong project không. Người gọi
        # giữ project, worker thì không — nên hỏi ngược ra thay vì để worker
        # ôm thêm một tham chiếu tới thứ nó không sở hữu.
        self.con_can = con_can

    def xin_dung(self):
        """Xin dừng tác vụ này.

        Không dùng `requestInterruption()` một mình được: Qt bỏ qua nó khi
        luồng CHƯA chạy, mà cơ chế dừng thì không nên phụ thuộc trạng thái
        luồng — nhất là khi test gọi thẳng `run()`. Cờ riêng luôn đúng, cờ
        Qt giữ lại cho các đường khác của Qt.
        """
        self._xin_dung = True
        self.requestInterruption()

    def _nen_dung(self) -> bool:
        if getattr(self, "_xin_dung", False):
            return True
        return self.isInterruptionRequested()

    def run(self):
        count = 0
        seen_excel = set()

        for job in self.jobs:
            # Huỷ HỢP TÁC, xét giữa hai mặt cắt. Cắt ngang lúc đang ghi MCT thì
            # để lại một file dở dang trên đĩa mà không ai biết là dở.
            if self._nen_dung():
                self.log.emit(f'■ Đã dừng theo yêu cầu — xong {count}/'
                              f'{len(self.jobs)} mặt cắt.')
                break

            name = job['name']

            # Mặt cắt bị bỏ khỏi project GIỮA lượt chạy thì đừng làm nữa.
            #
            # Trước đây vẫn tạo đủ `.mct`, `_topo.json`, `.svg` cho nó; kết quả
            # không ghi được vào project (mặt cắt đâu còn) nên chuyện đó diễn ra
            # hoàn toàn im lặng, chỉ để lại một thư mục mồ côi, mà câu tổng kết
            # vẫn đếm nó là một mặt cắt đã tạo.
            if self.con_can is not None and not self.con_can(name):
                self.log.emit(f'[{name}] Bỏ qua — mặt cắt đã bị bỏ khỏi project '
                              f'trong lúc chạy.')
                continue

            dxf_path = job['dxf']
            excel = job.get('excel') or None
            include_pt = job.get('include_pt', True)
            include_pt = None if include_pt else False

            section_dir = os.path.join(self.output_dir, name)
            os.makedirs(section_dir, exist_ok=True)

            try:
                # Đã CHỌN template mà không tìm thấy file là LỖI, không phải lý
                # do để lặng lẽ đổi sang chế độ "không template".
                #
                # Bản cũ gán `excel = None` rồi đi tiếp, nên MCT sinh ra không
                # có một khối tải trọng, vật liệu hay tổ hợp nào — mà mặt cắt
                # vẫn sang "Đã tạo MCT" và dấu hiệu duy nhất là một dòng vàng
                # giữa nhật ký. File ấy nạp vào Midas vẫn giải xong và vẫn xuất
                # ra Beam Force hợp lệ nhưng rỗng ruột: đúng chuyện đã xảy ra
                # với `output/S10`. Dự án đã chốt luật "thiếu khoá trong
                # template thì báo lỗi, không tự điền mặc định" — thiếu CẢ
                # template lại càng phải theo luật ấy.
                if excel and not os.path.exists(excel):
                    raise FileNotFoundError(
                        f'Không tìm thấy template số liệu đã gán:\n{excel}\n'
                        f'Gán lại template cho mặt cắt này, hoặc bỏ gán nếu '
                        f'chỉ muốn dựng hình.')

                if excel and excel not in seen_excel:
                    seen_excel.add(excel)
                    self.log.emit(source_line(excel))
                elif not excel:
                    self.log.emit(f'[{name}] WARNING: chưa có template số liệu — '
                                  f'bỏ qua toàn bộ khối tải trọng và vật liệu')

                self.log.emit(f'[{name}] Đọc DXF: {os.path.basename(dxf_path)}')
                doc = ezdxf.readfile(dxf_path)
                msp = doc.modelspace()
                outpoly = _get_polyline_vertices(msp, 'OUTPOLY')
                inpolys = read_inpolys(msp)
                stype = section_type_from_inpolys(inpolys)
                inpoly = inpolys if stype == 'twin_box' else inpolys[0]
                pt_cables = read_pt_cables(msp) if include_pt is not False else []
                if include_pt is not False:
                    diag = scan_pt_layers(msp)
                    if pt_cables:
                        self.log.emit(f'[{name}] Cáp DƯL: '
                                      + ', '.join(n for n, _ in pt_cables))
                    else:
                        self.log.emit(f'[{name}] Không tìm thấy cáp DƯL nào '
                                      f'(layer đúng quy ước: PT-TOP-1, PT-BOT-1, '
                                      f'PT-WEB-L-1, PT-WEB-R-1)')
                    # Layer trông giống cáp mà không dùng được — nói rõ lý do,
                    # trước đây bỏ qua im lặng nên không ai biết vì sao thiếu cáp.
                    for lay, why in diag['suspect'].items():
                        self.log.emit(f'[{name}] WARNING: bỏ qua layer '
                                      f'{lay!r} — {why}')

                ld = read_loads(excel) if excel else None
                d_L = ld['d_L'] if ld else 0.4
                d_R = ld['d_R'] if ld else 0.4

                self.log.emit(f'[{name}] Dựng khung ({stype}, '
                              f'd_L={d_L:.3f}, d_R={d_R:.3f})…')
                frame = build_frame(outpoly, inpoly, d_L=d_L, d_R=d_R)

                pt_props = read_pt_properties(excel) if (excel and pt_cables) else None

                self.log.emit(f'[{name}] Ghi MCT…')
                mct_text, topo = write_mct(frame, name, excel,
                                           pt_cables=pt_cables, pt_props=pt_props,
                                           include_pt=include_pt,
                                           supports=job.get('supports') or None,
                                           pt_jacking=job.get('pt_jacking', 'begin'))
                mct_path = os.path.join(section_dir, f'{name}_frame.mct')
                with open(mct_path, 'w', encoding='utf-8') as f:
                    f.write(mct_text)

                topo_path = os.path.join(section_dir, f'{name}_topo.json')
                with open(topo_path, 'w', encoding='utf-8') as f:
                    json.dump(topo, f, indent=2)

                svg_path = os.path.join(section_dir, f'{name}_frame.svg')
                try:
                    export_frame_svg(outpoly, inpoly, svg_path, name,
                                     section_type=stype)
                except Exception:
                    svg_path = ''

                for w in topo.get('pt_warnings', []):
                    self.log.emit(f'[{name}] WARNING: {w}')
                # Tổ hợp trỏ tới trường hợp tải không tồn tại → Midas báo
                # "load name ((null)) does not exist" lúc import. Nói ở đây.
                for w in topo.get('combo_warnings', []):
                    self.log.emit(f'[{name}] LỖI TỔ HỢP: {w}')
                # Hoạt tải trong template tính theo dải tương đương của MỘT mặt
                # cắt cụ thể — dùng lại cho mặt cắt khác thì tải sai, mà sai về
                # phía thiếu thì không có gì khác lộ ra.
                if ld:
                    from src.input_reader import read_inputs
                    from src.input_check import frame_metrics, check_template
                    try:
                        for w in check_template(read_inputs(excel),
                                                frame_metrics(topo), name):
                            self.log.emit(
                                f'[{name}] {"WARNING: " if w["level"] == "warn" else ""}'
                                f'{w["text"]}')
                    except Exception as e:
                        self.log.emit(f'[{name}] không đối chiếu được số liệu '
                                      f'đầu vào với hình học — {e}')

                n_elem = len(topo['elements'])
                n_node = sum(len(topo.get(k, []))
                             for k in ('top_ids', 'bot_ids', 'wL_ids',
                                       'wC_ids', 'wR_ids'))
                self.log.emit(f'[{name}] Xong: {n_elem} phần tử -> {mct_path}')
                self.section_info.emit(name, {
                    'mct': mct_path, 'topo': topo_path, 'section_type': stype,
                    'n_nodes': n_node, 'n_elems': n_elem,
                    'pt_cables': [n for n, _ in pt_cables],
                })
                self.section_done.emit(name, svg_path)
                count += 1

            except Exception as e:
                self.log.emit(f'[{name}] ERROR: {e}')
                self.log.emit(traceback.format_exc())
                self.section_error.emit(name, str(e))

        self.finished_all.emit(count)


class ResultsWorker(QThread):
    """Process Beam Force results matched with MCT topology files."""
    log = pyqtSignal(str)
    section_done = pyqtSignal(str, dict)       # name, check_points
    # Bao nội lực để vẽ biểu đồ — tách khỏi `section_done` cho khỏi đổi chữ ký
    # tín hiệu cũ; ai không cần thì không nối.
    envelope_done = pyqtSignal(str, dict)      # name, envelope
    error_mismatch = pyqtSignal(str, int, int, str)  # name, mct_count, result_count, bf_path
    finished_all = pyqtSignal(int)             # count

    def __init__(self, pairs: list, output_dir: str):
        super().__init__()
        self.pairs = pairs          # [(name, bf_path, topo_path), ...]
        self.output_dir = output_dir
        self._retries = []          # [(name, new_bf_path, topo_path)]

    def xin_dung(self):
        """Xin dừng tác vụ này.

        Không dùng `requestInterruption()` một mình được: Qt bỏ qua nó khi
        luồng CHƯA chạy, mà cơ chế dừng thì không nên phụ thuộc trạng thái
        luồng — nhất là khi test gọi thẳng `run()`. Cờ riêng luôn đúng, cờ
        Qt giữ lại cho các đường khác của Qt.
        """
        self._xin_dung = True
        self.requestInterruption()

    def _nen_dung(self) -> bool:
        if getattr(self, "_xin_dung", False):
            return True
        return self.isInterruptionRequested()

    def run(self):
        count = 0
        for name, bf_path, topo_path in self.pairs:
            if self._nen_dung():
                self.log.emit(f'■ Đã dừng theo yêu cầu — xong {count}/'
                              f'{len(self.pairs)} mặt cắt.')
                break
            ok = self._process_one(name, bf_path, topo_path)
            if ok:
                count += 1

        # Process any retries queued via retry_section()
        while self._retries and not self._nen_dung():
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
            self.log.emit(f'[{name}] Đọc topo: {os.path.basename(topo_path)}')
            with open(topo_path, 'r', encoding='utf-8') as f:
                topo = json.load(f)

            # Convert JSON lists back to tuples for compatibility
            topo['elements'] = [tuple(e) for e in topo['elements']]
            topo['sections'] = [tuple(s) for s in topo['sections']]

            self.log.emit(f'[{name}] Đọc: {os.path.basename(bf_path)}')
            # Nói rõ đã đọc mấy sheet: Midas tách bảng khi vượt giới hạn dòng,
            # đọc thiếu sheet thì bảng vẫn ra đủ nên không tự lộ.
            bf_report = []
            results = parse_beam_force(bf_path, report=bf_report)
            for line in bf_report:
                self.log.emit(f'[{name}] {line}')
            result_elems = set(r['elem'] for r in results)
            mct_elems = set(eid for eid, _, _, _ in topo['elements'])

            if result_elems != mct_elems:
                self.log.emit(f'[{name}] Lệch số phần tử: '
                              f'MCT có {len(mct_elems)}, kết quả có {len(result_elems)}')
                self.error_mismatch.emit(name, len(mct_elems),
                                         len(result_elems), bf_path)
                return False

            self.log.emit(f'[{name}] {len(results)} records, '
                          f'{len(result_elems)} elements — OK')

            thick_map = _build_element_thickness(topo['elements'], topo['sections'])
            check_elems = classify_check_elements(topo)

            check_points = extract_check_points(results, check_elems, thick_map)

            from gui.force_diagram import build_envelope
            self.envelope_done.emit(name, build_envelope(results))

            # Nội lực đã tính xong và ĐÚNG. Ghi báo cáo ra đĩa là việc phụ, nên
            # nó không được quyền vứt bỏ kết quả.
            #
            # Trước đây hai lệnh ghi nằm thẳng trong `try` lớn, nên chỉ cần
            # Excel đang mở `<tên>_check.xlsx` là `PermissionError` nhảy xuống
            # `except`, `section_done` không bao giờ phát, và cả mặt cắt mất
            # sạch kết quả — thẻ Kiểm toán báo "chưa có nội lực", còn thông
            # điệp người dùng nhận được là một traceback Python.
            from src.result_reader import format_check_table
            from run import _export_excel

            def ghi(duong_dan, viet):
                try:
                    viet(duong_dan)
                    self.log.emit(f'[{name}] Đã ghi: {duong_dan}')
                except PermissionError:
                    self.log.emit(
                        f'[{name}] WARNING: không ghi được {os.path.basename(duong_dan)}'
                        f' — tệp đang được mở ở chương trình khác (thường là Excel).'
                        f' Đóng tệp rồi xử lý lại. Kết quả vẫn dùng được.')
                except Exception as loi:
                    self.log.emit(
                        f'[{name}] WARNING: không ghi được '
                        f'{os.path.basename(duong_dan)} — {loi}')

            def _viet_txt(p):
                with open(p, 'w', encoding='utf-8') as f:
                    f.write(format_check_table(name, check_points))

            ghi(os.path.join(section_dir, f'{name}_check.txt'), _viet_txt)
            ghi(os.path.join(section_dir, f'{name}_check.xlsx'),
                lambda p: _export_excel(name, check_points, p))

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

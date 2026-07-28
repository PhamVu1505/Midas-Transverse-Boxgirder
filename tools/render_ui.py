"""
Xuất ảnh TOÀN BỘ giao diện ra `docs/ui-snapshots/` bằng một lệnh.

    python tools/render_ui.py                # đủ bộ
    python tools/render_ui.py --list         # xem có những cảnh nào
    python tools/render_ui.py --only check   # chỉ cảnh tên chứa "check"
    python tools/render_ui.py --out /tmp/x   # đổi thư mục ra

Vì sao có công cụ này
─────────────────────
Lỗi bố cục Qt **không có traceback**: nút bị cắt chữ, bảng chỉ hiện một dòng,
`minimumSizeHint` của một trang kéo cả vùng trung tâm rộng ra — tất cả chỉ lộ ra
khi nhìn. Nên mỗi lần sửa giao diện lại phải dựng một đoạn script nháp để chụp
màn hình, và phiên làm việc sau lại dựng lại từ đầu.

Đây là bản dùng chung của đám script nháp đó: dựng project mẫu từ dữ liệu thật
trong `output/`, đi qua mọi thẻ, hai bảng màu, cả mặt cắt một hộp lẫn hai hộp,
rồi ghi ảnh ra đĩa. Mở thư mục ảnh là thấy ngay hiện trạng, không phải đọc lại
code hay viết lại harness.

Nguyên tắc
──────────
* **Không đụng vào thiết lập đã lưu của người dùng.** `MainWindow.set_theme()`
  ghi thẳng vào `QSettings`; ở đây `Prefs.save` bị vô hiệu trong lúc chạy nên
  bảng màu, vị trí cửa sổ và project gần đây của VuPQ giữ nguyên.
* **Chạy được cả khi chưa có Beam Force.** Mặt cắt nào chưa có file kết quả thì
  dựng nội lực GIẢ để còn nhìn được bố cục — ảnh đó có hậu tố `-demo` và công cụ
  nói rõ trên màn hình. Đừng lấy số trong ảnh `-demo` ra dùng.
"""

import argparse
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

OUT_DIR = os.path.join('docs', 'ui-snapshots')
WIN = (1500, 950)          # cỡ cửa sổ khi chụp toàn cảnh
PANEL = (1560, 980)        # cỡ khi chụp riêng một panel (rộng hơn, không dock)

# Tên file Beam Force hay gặp trong output/<mặt cắt>/. Cố ý KHÔNG nhận
# '<tên mặt cắt>.xls' — thư mục kết quả của Midas đầy file .xls khác, đoán bừa
# thì công cụ đọc nhầm rồi báo lỗi khó hiểu.
BF_NAMES = ('Beam Force.xls', 'Beam Force.xlsx',
            'Beam Force_{name}.xls', 'Beam Force_{name}.xlsx')


# ─────────────────────────────────────────────────────────────
# Số liệu
# ─────────────────────────────────────────────────────────────

def discover(output_dir='output'):
    """[(tên, đường dẫn topo, đường dẫn Beam Force hoặc '')] sắp theo tên."""
    found = []
    if not os.path.isdir(output_dir):
        return found
    for name in sorted(os.listdir(output_dir)):
        topo = os.path.join(output_dir, name, f'{name}_topo.json')
        if not os.path.exists(topo):
            continue
        bf = ''
        for pat in BF_NAMES:
            cand = os.path.join(output_dir, name, pat.format(name=name))
            if os.path.exists(cand):
                bf = cand
                break
        found.append((name, topo, bf))
    return found


def load_topo(path):
    with open(path, encoding='utf-8') as f:
        topo = json.load(f)
    topo['elements'] = [tuple(e) for e in topo['elements']]
    topo['sections'] = [tuple(s) for s in topo.get('sections') or []]
    return topo


def real_forces(topo, bf_path):
    """(check_points, envelope) đọc từ file Beam Force thật."""
    from src.result_reader import (parse_beam_force, _build_element_thickness,
                                   classify_check_elements, extract_check_points)
    from gui.force_diagram import build_envelope
    recs = parse_beam_force(bf_path)
    thick = _build_element_thickness(topo['elements'], topo['sections'])
    cps = extract_check_points(recs, classify_check_elements(topo), thick)
    return cps, build_envelope(recs)


def fake_forces(topo):
    """Nội lực GIẢ, chỉ để nhìn bố cục khi mặt cắt chưa có Beam Force.

    Cố ý không giống số thật: biên độ hình sin theo số hiệu phần tử. Ảnh dựng từ
    đây mang hậu tố `-demo`.
    """
    from src.result_reader import classify_check_elements, order_points
    pts = order_points(classify_check_elements(topo).keys())
    cps = {p: {'h': 300 + 40 * i, 'Mu': 90.0 + 7 * i, 'Vu': 120.0 + 5 * i,
               'Mser': 70.0 + 5 * i, 'Mu_ref': f'J{i} · e{i}',
               'Vu_ref': f'I{i} · e{i}', 'Mser_ref': f'J{i} · e{i}'}
           for i, p in enumerate(pts)}
    env = {}
    for e in topo['elements']:
        eid = e[0]
        v = 200.0 * math.sin(eid * 0.35)
        ends = {'str_My': (v - 60, v + 60), 'str_Vz': (v / 2 - 30, v / 2 + 30),
                'ser_My': (v * .7 - 40, v * .7 + 40),
                'ser_Vz': (v / 3 - 20, v / 3 + 20)}
        env[eid] = {'I': dict(ends), 'J': dict(ends)}
    return cps, env


# Cốt thép mẫu để bảng kiểm toán có số mà vẽ. KHÔNG phải cốt thép thiết kế.
DEMO_BARS = {'A': 16, 'B': 16, 'C': 16, 'D': 16,
             'E': 19, 'F': 19, 'G': 25, 'H': 25}


def demo_rebars(points):
    return {p: {'dia': float(DEMO_BARS.get(p[0], 16)), 'spacing': 150.0,
                'cover': 65.0, 'Av': 0.0, 'Av_spacing': 0.0,
                'dp': 0.0, 'pt_spacing': 1000.0}
            for p in points}


# ─────────────────────────────────────────────────────────────
# Cửa sổ
# ─────────────────────────────────────────────────────────────

def build_window(sections, theme_key):
    """MainWindow đã nạp project và đặt bảng màu, KHÔNG ghi vào QSettings."""
    from src.project import Project, Section, GENERATED
    from gui.prefs import Prefs
    from gui.main_window import MainWindow

    # Vô hiệu hoá việc lưu thiết lập: công cụ chỉ được đọc, không được sửa
    # bảng màu / project gần đây của người dùng.
    Prefs.save = lambda self, settings: None

    w = MainWindow()
    w.prefs.theme = theme_key
    w.t = w.prefs.tokens()
    w._push_theme()
    w._sync_theme_menu()

    p = Project()
    p.name = 'Ảnh giao diện'
    p.output_dir = 'output'
    p.template = os.path.join('data', 'Midas-Transverse-Boxgirder-analysis.xls')
    for name, topo_path, bf, topo in sections:
        n_elem = len(topo['elements'])
        n_node = sum(len(topo.get(k, []))
                     for k in ('top_ids', 'bot_ids', 'wL_ids', 'wC_ids', 'wR_ids'))
        p.sections.append(Section(
            name=name, dxf=os.path.join('input', f'{name}.dxf'),
            topo=topo_path, beam_force=bf,
            mct=os.path.join('output', name, f'{name}_frame.mct'),
            n_nodes=n_node, n_elems=n_elem, status=GENERATED,
            rebars=demo_rebars(list(DEMO_BARS))))
    w._apply_project(p)
    w.resize(*WIN)
    w.show()
    return w


def feed_results(w, sections):
    """Bơm nội lực vào ResultsTab như thể vừa bấm "Xử lý tất cả"."""
    used_fake = []
    for name, _topo_path, bf, topo in sections:
        if bf:
            try:
                cps, env = real_forces(topo, bf)
            except Exception as e:                      # file hỏng, sai cột…
                print(f'  ! {name}: không đọc được Beam Force ({e}) — dùng số giả')
                cps, env = fake_forces(topo)
                used_fake.append(name)
        else:
            cps, env = fake_forces(topo)
            used_fake.append(name)
        w.res_tab.all_results[name] = cps
        w.res_tab.all_env[name] = env
        w.res_tab.section_combo.addItem(name)
    return used_fake


# ─────────────────────────────────────────────────────────────
# Cảnh chụp
# ─────────────────────────────────────────────────────────────

def scenes(app, w, sections, save):
    """Đi qua từng cảnh và gọi save(tên, widget, …, sec=mặt cắt đang hiện).

    `sec` phải đúng mặt cắt trong ảnh — hậu tố `-demo` bám theo nó. Ghi nhầm là
    đánh dấu một ảnh số THẬT thành số giả, tệ hơn cả không đánh dấu.
    """
    names = [s[0] for s in sections]
    # Mặt cắt chính: ưu tiên cái đã có Beam Force thật để ảnh dùng số thật
    single = next((n for n, _t, b, _o in sections if b), names[0])
    twin = next((n for n, _t, _b, topo in sections
                 if len(topo.get('wC_ids') or []) > 0), None)

    def step():
        app.processEvents()

    # ── thẻ Model ──
    w.panel.section_selected.emit(single)
    w.tabbar.setCurrentIndex(0)
    step()
    save('01_model', w, sec=single)

    w.tabbar.setCurrentIndex(1)
    step()
    save('02_section_shape', w, sec=single)

    # ── thẻ Results table ──
    w.tabbar.setCurrentIndex(3)
    w.res_tab.section_combo.setCurrentText(single)
    step()
    save('03_results', w, sec=single)

    for i, label in enumerate(
            [w.res_tab.diag_combo.itemText(i)
             for i in range(w.res_tab.diag_combo.count())]):
        w.res_tab.diag_combo.setCurrentText(label)
        step()
        save(f'04_diagram_{i + 1}', w.res_tab.forces, panel=(760, 460),
             sec=single)

    if twin:
        w.res_tab.section_combo.setCurrentText(twin)
        step()
        save('05_results_twin', w, sec=twin)
        w.res_tab.section_combo.setCurrentText(single)
        step()

    # ── thẻ Kiểm toán mặt cắt ──
    w.tabbar.setCurrentIndex(4)
    w.check_tab.cb_sec.setCurrentText(single)
    step()
    w.check_tab.run_check()
    step()
    save('06_check', w, sec=single)
    save('07_check_panel', w.check_tab, panel=PANEL, sec=single)

    if twin:
        w.check_tab.cb_sec.setCurrentText(twin)
        step()
        w.check_tab.run_check()
        step()
        save('08_check_twin', w.check_tab, panel=PANEL, sec=twin)

    # ── có kể đến cáp DƯL (mặc định là KHÔNG) ──
    w.check_tab.cb_sec.setCurrentText(single)
    w.check_tab.chk_pt.setChecked(True)
    step()
    w.check_tab.run_check()
    step()
    save('09_check_with_pt', w.check_tab, panel=PANEL, sec=single)
    w.check_tab.chk_pt.setChecked(False)
    step()

    # ── nguồn MCT ──
    w.tabbar.setCurrentIndex(5)
    step()
    save('10_mct_source', w, sec=single)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('--out', default=OUT_DIR, help=f'thư mục ra (mặc định {OUT_DIR})')
    ap.add_argument('--only', default='', help='chỉ chụp cảnh có tên chứa chuỗi này')
    ap.add_argument('--themes', default='light,dark',
                    help='bảng màu, ngăn bằng dấu phẩy (light/dark/contrast)')
    ap.add_argument('--list', action='store_true', help='liệt kê cảnh rồi thoát')
    args = ap.parse_args()

    found = discover()
    if not found:
        print('Không thấy mặt cắt nào đã tạo MCT trong output/ — '
              'chạy pipeline trước rồi quay lại.')
        return 1
    sections = [(n, t, b, load_topo(t)) for n, t, b in found]
    print(f'Mặt cắt: ' + ' · '.join(
        f'{n}{"" if b else " (chưa có Beam Force)"}' for n, _t, b, _o in sections))

    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv[:1])

    os.makedirs(args.out, exist_ok=True)
    written = []

    for theme_key in [t.strip() for t in args.themes.split(',') if t.strip()]:
        w = build_window(sections, theme_key)
        fake = feed_results(w, sections)
        if fake:
            print(f'  · nội lực GIẢ cho: {", ".join(fake)} — ảnh có hậu tố -demo')

        def save(name, widget, panel=None, sec=None):
            if args.only and args.only.lower() not in name.lower():
                return
            if panel:
                widget.resize(*panel)
            # Vẽ lại HẲN trước khi chụp: chỉ `processEvents()` thì đôi khi
            # `grab()` bắt được khung hình dở dang.
            # (Ba dòng chữ chồng nhau ở thanh trạng thái thì KHÔNG phải do chụp
            #  — đó là thông điệp tạm của QStatusBar vẽ đè lên widget, đã sửa
            #  bằng lớp `StatusBar` trong gui/main_window.py.)
            app.processEvents()
            widget.repaint()
            app.processEvents()
            suffix = '-demo' if sec in fake else ''
            path = os.path.join(args.out, f'{name}_{theme_key}{suffix}.png')
            widget.grab().save(path)
            written.append(path)
            if args.list:
                print(f'  {name}')

        if args.list:
            scenes(app, w, sections, save)
            break
        scenes(app, w, sections, save)
        w.hide()

    print(f'Đã ghi {len(written)} ảnh vào {args.out}')
    for p in written:
        print(f'  {p}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

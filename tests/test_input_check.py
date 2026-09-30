"""Đối chiếu số liệu template với hình học + tuỳ chọn căng cáp.

Chạy:
    pytest tests/test_input_check.py -v

Hai thứ được khoá ở đây:

1. **Suy ngược S/X phải tự kiểm chứng.** `+M` và `−M` là hai công thức khác hẳn
   nhau; nếu cùng ra một `S` thì chắc chắn đã suy đúng. Bài kiểm dựng tải bánh
   từ một `S` biết trước rồi đòi suy lại đúng con số đó.

2. **Mặc định không đổi một byte nào của MCT.** `pt_jacking='begin'` phải cho ra
   đúng dòng `*TDN-PRESTRESS` như bản trước khi có tuỳ chọn này.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.input_check import (CHECK_TEMPLATE, P_TANDEM, P_TRUCK,
                             check_shared_template, check_template,
                             frame_metrics, live_load_compare,
                             live_load_derivation, live_load_from_geometry,
                             strip_width, strip_width_axles,
                             strip_width_tandem, template_strip_geometry)
from src.mct_frame_writer import _write_tendon_prestress_block

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _excel_truck(E):
    """Ô `F44:F46` của sheet Load, chép nguyên văn: `=IF(E>4300,(E+4300)/2,E)`.

    Viết lại độc lập ở đây, không gọi `strip_width_axles`, để bài kiểm so mã
    với **công thức Excel** chứ không so mã với chính nó.
    """
    return (E + 4300.0) / 2.0 if E > 4300.0 else E


def _template(S, X, im=0.33):
    """Bộ số liệu hoạt tải sinh ra từ một S và X biết trước — đúng mạch Excel."""
    E = strip_width(S=S)
    E_can = strip_width(X=X)
    return {
        'impact': im,
        'truck_can': P_TRUCK * (1 + im) / _excel_truck(E_can) * 1000.0,
        'truck_pos': P_TRUCK * (1 + im) / _excel_truck(E['pos']) * 1000.0,
        'truck_neg': P_TRUCK * (1 + im) / _excel_truck(E['neg']) * 1000.0,
    }


def _metrics(S_centre, cant, t_web=0.5, B=16000.0):
    return {
        'B': B, 'n_webs': 2,
        'spans_centre': [S_centre],
        'spans_clear': [S_centre - t_web * 1000.0],
        'cantilever_left': cant, 'cantilever_right': cant,
    }


# ─────────────────────────────────────────────────────────────
# Suy ngược S / X
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize('S,X', [(6468.0, 3632.0), (8450.0, 3945.0),
                                 (5550.0, 3375.0)])
def test_invert_strip_geometry(S, X):
    g = template_strip_geometry(_template(S, X))
    assert g['consistent'], g
    assert abs(g['S'] - S) < 0.5, g
    assert abs(g['X'] - X) < 0.5, g
    # hai công thức độc lập phải trùng nhau — đây mới là phần tự kiểm chứng
    assert abs(g['S_pos'] - g['S_neg']) < 0.5, g


def test_inconsistent_template_is_not_checked():
    """Sheet Load không lập theo dải tương đương thì im lặng, không báo bừa."""
    d = _template(6468.0, 3632.0)
    d['truck_neg'] *= 1.5           # phá quan hệ giữa hai công thức
    g = template_strip_geometry(d)
    assert not g['consistent']
    notes = check_template(d, _metrics(8450.0, 3945.0), 'X')
    assert [n['level'] for n in notes] == ['info']
    assert 'không đối chiếu được' in notes[0]['text']


def test_missing_keys_returns_empty():
    assert template_strip_geometry({}) == {}
    assert check_template({}, _metrics(8450.0, 3945.0)) == []
    assert check_template(_template(6468.0, 3632.0), {}) == []


# ─────────────────────────────────────────────────────────────
# Đối chiếu
# ─────────────────────────────────────────────────────────────

def test_matching_template_is_silent():
    """Template lập cho đúng mặt cắt này thì không được kêu gì."""
    d = _template(8000.0, 3900.0)
    # S=8000 nằm giữa thông thuỷ 7500 và tim–tim 8000 → coi là khớp
    assert check_template(d, _metrics(8000.0, 3900.0), 'S1') == []


def test_smaller_span_is_flagged_unsafe():
    """Mặt cắt có S NHỎ hơn template ⇒ dải rộng hơn thực tế ⇒ tải THIẾU."""
    d = _template(6468.0, 3632.0)
    notes = check_template(d, _metrics(5550.0, 3375.0), 'S20')
    assert any(n['level'] == 'warn' and 'KHÔNG an toàn' in n['text']
               for n in notes), notes


def test_larger_span_is_only_informative():
    """Mặt cắt có S LỚN hơn thì tải dư — thiên về an toàn, chỉ ghi chú."""
    d = _template(6468.0, 3632.0)
    notes = check_template(d, _metrics(8450.0, 3945.0), 'S1')
    assert notes and all(n['level'] == 'info' for n in notes), notes
    assert any('thiên về an toàn' in n['text'] for n in notes)


def test_S_is_compared_to_web_centreline():
    """`S` đo TIM–TIM (TCVN 11823-4 Đ.4.6.2.1), không phải thông thuỷ.

    Template khai đúng trị thông thuỷ (tim–tim trừ một bề dày sườn) thì vẫn phải
    báo: bản đầu chấp nhận cả dải nên ca này lọt lưới.
    """
    m = _metrics(8000.0, 3900.0, t_web=0.5)      # tim–tim 8000, thông thuỷ 7500
    notes = check_template(_template(7500.0, 3900.0), m, 'S1')
    assert any('S (sheet Load)' in n['text'] for n in notes), notes
    # trị thông thuỷ vẫn được in kèm để người dùng nhận ra vì sao lệch
    assert any('thông thuỷ 7500' in n['text'] for n in notes), notes


def test_multi_web_compares_shortest_span():
    """Nhiều bụng thì so với nhịp NGẮN NHẤT — nhịp dễ thiếu tải nhất."""
    m = _metrics(9000.0, 3900.0)
    m['spans_centre'] = [9000.0, 5000.0]
    m['spans_clear'] = [8500.0, 4500.0]
    m['n_webs'] = 3
    notes = check_template(_template(9000.0, 3900.0), m, 'V2')
    assert any(n['level'] == 'warn' and 'KHÔNG an toàn' in n['text']
               for n in notes), notes


def test_warnings_say_check_the_template():
    d = _template(6468.0, 3632.0)
    notes = check_template(d, _metrics(5550.0, 3375.0), 'S20')
    assert notes and all(CHECK_TEMPLATE in n['text'] for n in notes), notes


def test_barrier_wider_than_cantilever():
    d = dict(_template(8000.0, 3900.0), d_L=4.5, d_R=0.35)
    notes = check_template(d, _metrics(8000.0, 3900.0), 'S1')
    assert any('lan can' in n['text'] and n['level'] == 'warn' for n in notes)


def test_shared_template_same_geometry_is_silent():
    e = [{'name': 'a', 'template': 't.xls', 'metrics': _metrics(8000.0, 3900.0)},
         {'name': 'b', 'template': 't.xls', 'metrics': _metrics(8000.0, 3900.0)}]
    assert check_shared_template(e) == []


def test_shared_template_different_geometry_warns():
    e = [{'name': 'a', 'template': 't.xls', 'metrics': _metrics(8000.0, 3900.0)},
         {'name': 'b', 'template': 't.xls', 'metrics': _metrics(5500.0, 3300.0)}]
    out = check_shared_template(e)
    assert len(out) == 1 and out[0]['level'] == 'warn'
    assert 'a' in out[0]['text'] and 'b' in out[0]['text']
    assert CHECK_TEMPLATE in out[0]['text']


def test_one_section_per_template_is_silent():
    e = [{'name': 'a', 'template': 't1.xls', 'metrics': _metrics(8000.0, 3900.0)},
         {'name': 'b', 'template': 't2.xls', 'metrics': _metrics(5500.0, 3300.0)}]
    assert check_shared_template(e) == []


# ─────────────────────────────────────────────────────────────
# Hai lối trình bày, một phép tính
# ─────────────────────────────────────────────────────────────
#
# Cảnh báo hoạt tải xuất hiện ở hai nơi: câu văn trong nhật ký/hộp thoại, và
# bảng hai cột ở dock Properties. Hai nơi phải nói **cùng một con số** — bản đầu
# suýt có hai bản sao của cùng công thức tỉ số, mà lệch nhau thì chẳng có gì lộ
# ra: người dùng đọc dock thấy 8%, đọc log thấy 12%, và không ai đối chiếu.

@pytest.mark.parametrize('S_tpl,X_tpl,S_that,X_that', [
    (6468.0, 3632.0, 5550.0, 3375.0),    # S20 — thiếu cả hai
    (6468.0, 3632.0, 6977.0, 3279.0),    # S10 — chỉ thiếu cánh hẫng
    (6468.0, 3632.0, 8450.0, 3945.0),    # S1  — dư cả hai
])
def test_dock_va_nhat_ky_noi_cung_mot_con_so(S_tpl, X_tpl, S_that, X_that):
    d = _template(S_tpl, X_tpl)
    m = _metrics(S_that, X_that)
    cmp = live_load_compare(d, m)
    notes = check_template(d, m, 'X')
    assert cmp, 'template lập theo dải tương đương mà không đối chiếu được'

    for key, tu_khoa in (('S', 'ô S (sheet Load)'), ('X', 'ô X (sheet Load)')):
        c = cmp[key]
        cau = [n for n in notes if tu_khoa in n['text']]
        if not c['off']:
            assert not cau, f'{key} khớp mà nhật ký vẫn kêu: {cau}'
            continue
        assert len(cau) == 1, f'{key} lệch mà nhật ký nói {len(cau)} lần'

        # Cùng chiều: `unsafe` của dock ⇔ chữ THIẾU của nhật ký ⇔ mức warn
        assert c['unsafe'] == ('THIẾU' in cau[0]['text']), key
        assert cau[0]['level'] == ('warn' if c['unsafe'] else 'info'), key

        # Cùng con số: phần trăm dock tính ra phải là phần trăm trong câu
        pct = ((c['ratio'] - 1) if c['unsafe'] else (1 / c['ratio'] - 1)) * 100
        assert f'{pct:.0f}%' in cau[0]['text'], (
            f'{key}: dock ra {pct:.0f}%, nhật ký ghi {cau[0]["text"]!r}')


def test_template_khong_theo_dai_tuong_duong_thi_khong_so_sanh():
    """Không suy ngược được thì trả rỗng, chứ không đoán bừa một tỉ số."""
    d = _template(6468.0, 3632.0)
    d['truck_neg'] *= 2.0                      # hai công thức cho hai S khác nhau
    assert live_load_compare(d, _metrics(5550.0, 3375.0)) == {}
    assert live_load_compare({}, _metrics(5550.0, 3375.0)) == {}
    assert live_load_compare(_template(6468.0, 3632.0), {}) == {}


def test_nhieu_nhip_lay_nhip_ngan_nhat_va_dung_thong_thuy_cua_no():
    """`clear` phải là thông thuỷ của ĐÚNG nhịp được đem so, không phải nhịp đầu.

    Mặt cắt nhiều bụng so với nhịp ngắn nhất (dải hẹp nhất ⇒ tải bánh lớn nhất).
    Lấy `spans_clear[0]` thì dock in thông thuỷ của một nhịp khác — con số vô
    nghĩa đặt ngay cạnh con số đang bị nghi là gõ nhầm.
    """
    m = {'B': 24000.0, 'n_webs': 3,
         'spans_centre': [9000.0, 5550.0], 'spans_clear': [8500.0, 5050.0],
         'cantilever_left': 3375.0, 'cantilever_right': 3375.0}
    c = live_load_compare(_template(6468.0, 3632.0), m)['S']
    assert c['real'] == 5550.0
    assert c['clear'] == 5050.0
    assert c['unsafe'] is True


# ─────────────────────────────────────────────────────────────
# Hình học đọc từ frame hay topo đều phải ra một kết quả
# ─────────────────────────────────────────────────────────────

def test_metrics_from_frame_and_topo_agree():
    import ezdxf
    from src.dxf_reader import (_get_polyline_vertices, read_inpolys,
                                section_type_from_inpolys)
    from src.frame_builder import build_frame
    from src.mct_frame_writer import write_mct

    dxf = os.path.join(ROOT, 'input', 'dxf', 'S16.dxf')
    if not os.path.exists(dxf):
        pytest.skip('thiếu DXF mẫu')
    msp = ezdxf.readfile(dxf).modelspace()
    out = _get_polyline_vertices(msp, 'OUTPOLY')
    ins = read_inpolys(msp)
    assert section_type_from_inpolys(ins) == 'single'
    frame = build_frame(out, ins[0], d_L=0.35, d_R=0.35)
    _, topo = write_mct(frame, 'S16')

    a, b = frame_metrics(frame), frame_metrics(topo)
    assert a and b
    for k in ('B', 'n_webs', 'cantilever_left', 'cantilever_right'):
        assert a[k] == pytest.approx(b[k], abs=1e-6), k
    assert a['spans_centre'] == pytest.approx(b['spans_centre'], abs=1e-6)


# ─────────────────────────────────────────────────────────────
# Toạ độ ô của đường lui (legacy)
# ─────────────────────────────────────────────────────────────

TEMPLATE = os.path.join(ROOT, 'data', 'Midas-Transverse-Boxgirder-analysis.xls')


def test_legacy_cells_match_input_sheet():
    """Đường lui phải đọc ra ĐÚNG số liệu như sheet INPUT.

    Từng có người chèn một dòng trống vào dòng 10 sheet `Load`, làm 20/21 khoá
    của sheet đó đọc trúng ô của khoá bên cạnh (`d_L` ra 35,5 thay vì 0,35 m).
    Không ai thấy vì sheet `INPUT` mới là nguồn chính — đường lui chỉ chạy khi
    file không có sheet `INPUT`, và lúc đó thì im lặng ra số sai.
    """
    from src.input_reader import crosscheck
    if not os.path.exists(TEMPLATE):
        pytest.skip('thiếu template mẫu')
    bad = crosscheck(TEMPLATE)
    assert not bad, ('toạ độ ô legacy lệch: '
                     + ', '.join(f'{k} ({addr})' for k, _a, _b, addr in bad))


def test_every_legacy_cell_is_readable():
    """Không khoá nào được rơi vào ô trống hay ô tiêu đề.

    `crosscheck` cũ nuốt `InputError` nên 8 khoá hỏng kiểu này không hiện ra —
    bảng báo 12 trong khi thực tế hỏng 20.
    """
    from src.input_reader import (SPEC, _Book, _cast, InputError)
    if not os.path.exists(TEMPLATE):
        pytest.skip('thiếu template mẫu')
    book = _Book(TEMPLATE)
    unreadable = []
    for key, sh, r, c, kind, _u, _d in SPEC:
        if sh not in book.sheets:
            continue
        try:
            _cast(book.cell(sh, r, c), kind, key)
        except InputError:
            unreadable.append(f'{key} ({sh}!R{r + 1}C{c + 1})')
    assert not unreadable, 'ô legacy không đọc được: ' + ', '.join(unreadable)


def test_crosscheck_reports_unreadable_cell():
    """Ô không đọc được phải bị BÁO, không được bỏ qua trong im lặng."""
    import src.input_reader as ir
    if not os.path.exists(TEMPLATE):
        pytest.skip('thiếu template mẫu')
    key, sh, r, c, kind, u, dsc = ir.SPEC_BY_KEY['d_L']
    saved = list(ir.SPEC)
    try:
        # trỏ `d_L` vào một ô chắc chắn trống
        ir.SPEC[:] = [(key, sh, 5000, c, kind, u, dsc) if s[0] == 'd_L' else s
                      for s in saved]
        bad = ir.crosscheck(TEMPLATE)
        assert any(k == 'd_L' and b is None for k, _a, b, _addr in bad), bad
    finally:
        ir.SPEC[:] = saved


# ─────────────────────────────────────────────────────────────
# Căng cáp
# ─────────────────────────────────────────────────────────────

class _Prop:
    fpj = 1395.0


class _Tdn:
    name = 'PT-TOP-1'


def test_jacking_default_matches_old_output():
    """Mặc định phải ra ĐÚNG dòng của bản chưa có tuỳ chọn này."""
    blocks = []
    _write_tendon_prestress_block(blocks, [_Tdn()], _Prop())
    assert ' PT-TOP-1, STRESS, BEGIN, 1.395e+06, 0, 0, Load' in blocks


def test_jacking_both_ends():
    blocks = []
    _write_tendon_prestress_block(blocks, [_Tdn()], _Prop(), 'both')
    assert ' PT-TOP-1, STRESS, BOTH, 1.395e+06, 1.395e+06, 0, Load' in blocks


def test_jacking_unknown_falls_back_to_one_end():
    blocks = []
    _write_tendon_prestress_block(blocks, [_Tdn()], _Prop(), 'linh tinh')
    assert ' PT-TOP-1, STRESS, BEGIN, 1.395e+06, 0, 0, Load' in blocks


def test_project_round_trip_keeps_jacking(tmp_path):
    from src.project import Project, Section
    p = Project(sections=[Section(name='S1', dxf='a.dxf')])
    assert p.find('S1').pt_jacking == 'begin'
    p.set_pt_jacking('S1', 'both')
    p.set_pt_jacking('S1', 'bậy')            # giá trị lạ thì bỏ qua
    assert p.find('S1').pt_jacking == 'both'
    path = p.save(str(tmp_path / 'x.mtbproj'))
    assert Project.load(path).find('S1').pt_jacking == 'both'


def test_old_project_file_defaults_to_one_end(tmp_path):
    """File .mtbproj cũ không có khoá này — phải lui về căng một đầu."""
    import json
    from src.project import Project
    path = tmp_path / 'old.mtbproj'
    path.write_text(json.dumps({
        'format': 1, 'name': 'P', 'output_dir': 'output', 'template': '',
        'sections': [{'name': 'S1', 'dxf': 'a.dxf'}],
    }), encoding='utf-8')
    assert Project.load(str(path)).find('S1').pt_jacking == 'begin'


# ─────────────────────────────────────────────────────────────
# Chiều XUÔI: app tự tính sáu trị tải bánh từ hình học mặt cắt
#
# Sáu trị `truck_*`/`tandem_*` không phải số liệu người dùng gõ — chúng là kết
# quả tính từ `S`, `X`, `IM`. Ba điều được khoá ở đây:
#
#   1. Chiều xuôi tái lập ĐÚNG sáu ô của template thật (lệch ≤ 1e-9), tức công
#      thức trong app và mạch tính trong Excel là một.
#   2. Xuôi rồi nghịch lại ra đúng `S`/`X` đã vào — hai chiều nằm cùng file thì
#      không được phép lệch nhau.
#   3. Cờ TẮT cho ra MCT trùng khít từng byte; cờ BẬT chỉ đổi đúng các con số
#      tải bánh và thêm khối chú thích mạch tính.
# ─────────────────────────────────────────────────────────────

def test_xuoi_tai_lap_dung_sau_o_cua_template_that():
    """Tính từ `S`/`X` mà template dùng phải ra đúng sáu ô Excel.

    Đây là căn cứ cho phép app thôi đọc sáu ô đó. Không có phép kiểm này thì
    "app tự tính" chỉ là một công thức khác, không phải cùng một công thức.
    """
    from src.input_reader import read_inputs
    if not os.path.exists(TEMPLATE):
        pytest.skip('thiếu template')
    d = read_inputs(TEMPLATE, strict=False)
    tpl = template_strip_geometry(d)
    assert tpl and tpl['consistent']

    auto = live_load_from_geometry(
        _metrics(tpl['S'], tpl['X']), d['impact'])
    assert auto
    for k, v in auto['loads'].items():
        assert v == pytest.approx(float(d[k]), abs=1e-9), k


@pytest.mark.parametrize('S,X', [(6468.0, 3632.0), (5550.0, 3375.0),
                                 (8650.0, 3845.0), (16311.0, 3834.0)])
def test_xuoi_roi_nghich_lai_ra_dung_S_va_X(S, X):
    """Hai chiều phải gặp nhau, nếu không thì dock và MCT nói hai chuyện."""
    auto = live_load_from_geometry(_metrics(S, X), 0.33)
    back = template_strip_geometry({**auto['loads'], 'impact': auto['im']})
    assert back['consistent']
    assert back['S'] == pytest.approx(S, abs=1e-6)
    assert back['X'] == pytest.approx(X, abs=1e-6)


def test_xe_hai_truc_dung_dai_rong_hon_xe_tai():
    """`E_tandem = (E_truck + 1200)/2` — sheet Load không ghi, phải truy ngược.

    Lấy nhầm `E_truck` cho xe hai trục thì tải xe hai trục sai theo, mà nó là
    xe TRỘI ở mọi vị trí (xem mục *Hoạt tải* trong CLAUDE.md) — tức sai đúng
    con số đang quyết định kết quả.
    """
    assert strip_width_tandem(2000.0) == pytest.approx(1600.0)
    auto = live_load_from_geometry(_metrics(6468.0, 3632.0), 0.33)
    E_pos = strip_width(S=6468.0)['pos']
    assert auto['loads']['tandem_pos'] == pytest.approx(
        P_TANDEM * 1.33 * 1000.0 / ((E_pos + 1200.0) / 2.0), abs=1e-9)
    # KHÔNG được bằng trị tính bằng E của xe tải
    assert auto['loads']['tandem_pos'] != pytest.approx(
        P_TANDEM * 1.33 * 1000.0 / E_pos, abs=1e-3)


@pytest.mark.parametrize('S,X', [(8450.0, 3945.0), (8650.0, 3845.0),
                                 (16311.0, 4503.0), (6468.0, 3632.0)])
def test_xe_tai_dung_luat_cu_ly_truc_4300_nhu_excel(S, X):
    """Dải rộng hơn 4300 mm thì xe tải lấy `(E + 4300)/2` — ô `F44:F46`.

    Bản đầu bỏ quên luật này. Phép "tái lập đúng sáu ô Excel" không bắt được vì
    cả ba dải của template mẫu (S = 6468) đều hẹp hơn 4300 mm, nên bộ tham số ở
    đây cố ý gồm mặt cắt THẬT có dải vượt: S1, S16 (`+M`), và một nhịp dài
    vượt cả ở `−M`. Thiếu luật thì tải xe tải `+M` của S16 thiếu 11,5%.
    """
    auto = live_load_from_geometry(_metrics(S, X), 0.33)
    ref = _template(S, X)
    for k in ('truck_can', 'truck_pos', 'truck_neg'):
        assert auto['loads'][k] == pytest.approx(ref[k], abs=1e-9), k
    # và dải vượt 4300 thì thực sự có ăn (không phải trùng hợp E < 4300)
    if S > 6700:
        E_pos = strip_width(S=S)['pos']
        assert E_pos > 4300
        assert auto['loads']['truck_pos'] > P_TRUCK * 1.33 * 1000.0 / E_pos * 1.05


def test_luat_cu_ly_truc_hien_ra_trong_mach_tinh():
    """Người thẩm tra phải thấy luật đã ăn vào dải nào, không phải tự so."""
    auto = live_load_from_geometry(_metrics(8650.0, 3845.0), 0.33)
    txt = '\n'.join(live_load_derivation(auto))
    assert '(E + 4300)/2' in txt
    E_pos = strip_width(S=8650.0)['pos']
    assert f'+M {E_pos:.0f} -> {strip_width_axles(E_pos, 4300.0):.0f} mm' in txt
    hep = live_load_from_geometry(_metrics(5550.0, 3375.0), 0.33)
    assert 'khong dai nao vuot' in '\n'.join(live_load_derivation(hep))


def test_nhieu_nhip_va_hai_canh_hang_lech_thi_lay_ben_ngan():
    """Dải hẹp nhất cho tải bánh lớn nhất — chiều thiên về an toàn."""
    m = {'B': 20000.0, 'n_webs': 3,
         'spans_centre': [8000.0, 5000.0], 'spans_clear': [7500.0, 4500.0],
         'cantilever_left': 4000.0, 'cantilever_right': 3000.0}
    auto = live_load_from_geometry(m, 0.33)
    assert auto['S'] == pytest.approx(5000.0)
    assert auto['X'] == pytest.approx(3000.0)


def test_thieu_du_lieu_thi_khong_doan():
    """Không có hình học thì trả rỗng, tuyệt đối không lấy trị mặc định."""
    assert live_load_from_geometry({}, 0.33) == {}
    assert live_load_from_geometry(None, 0.33) == {}
    assert live_load_from_geometry(_metrics(6468.0, 3632.0), None) == {}
    assert live_load_from_geometry({'spans_centre': [0.0],
                                    'cantilever_left': 1.0,
                                    'cantilever_right': 1.0}, 0.33) == {}
    assert live_load_derivation({}) == []


def _mct_hai_luot(dxf_rel):
    """Sinh MCT cho một DXF hai lượt: cờ tắt và cờ bật."""
    import ezdxf
    from src.dxf_reader import (_get_polyline_vertices, read_inpolys,
                                section_type_from_inpolys)
    from src.frame_builder import build_frame, build_twin_frame
    from src.input_reader import read_loads
    from src.mct_frame_writer import write_mct

    dxf = os.path.join(ROOT, dxf_rel)
    if not (os.path.exists(dxf) and os.path.exists(TEMPLATE)):
        pytest.skip(f'thiếu {dxf_rel} hoặc template')
    msp = ezdxf.readfile(dxf).modelspace()
    out = _get_polyline_vertices(msp, 'OUTPOLY')
    ins = read_inpolys(msp)
    ld = read_loads(TEMPLATE)
    if section_type_from_inpolys(ins) == 'twin_box':
        args = (out, ins[0], ins[1])
        build = build_twin_frame
    else:
        args = (out, ins[0])
        build = build_frame
    frame = build(*args, d_L=ld['d_L'], d_R=ld['d_R'])
    name = os.path.splitext(os.path.basename(dxf))[0]
    tat, topo_tat = write_mct(frame, name, TEMPLATE)
    bat, topo_bat = write_mct(frame, name, TEMPLATE, auto_live_load=True)
    return frame, tat, bat, topo_tat, topo_bat


@pytest.mark.parametrize('dxf_rel', ['input/dxf/S16.dxf',
                                     'data/TP_BL/S1_V2.dxf'])
def test_mac_dinh_la_TAT_va_van_ghi_tri_cua_template(dxf_rel):
    """Mặc định phải giữ nguyên hành vi cũ — cả nhánh một hộp và hai hộp.

    `auto_live_load` đổi tải bánh của MỌI mặt cắt, kể cả những mặt cắt đã chạy
    trọn chu trình QA trên Midas thật. Mặc định bật là đổi kết quả sau lưng
    người dùng, nên hai thứ được khoá: gọi không truyền cờ phải **giống từng
    byte** gọi với `False`, và con số ghi ra phải là con số của **template**,
    không phải trị tính từ hình học.
    """
    from src.input_reader import read_inputs
    frame, tat, _, topo_tat, _ = _mct_hai_luot(dxf_rel)

    from src.mct_frame_writer import write_mct
    name = os.path.splitext(os.path.basename(dxf_rel))[0]
    khong_truyen_co, _ = write_mct(frame, name, TEMPLATE)
    voi_False, _ = write_mct(frame, name, TEMPLATE, auto_live_load=False)
    assert khong_truyen_co == tat == voi_False
    assert topo_tat['live_load'] == {'source': 'template'}

    d = read_inputs(TEMPLATE, strict=False)
    auto = live_load_from_geometry(frame_metrics(frame), d['impact'])
    for k in auto['loads']:
        assert f'{float(d[k]):.4f}' in tat, k          # trị template CÓ mặt
        if abs(auto['loads'][k] - float(d[k])) > 0.001:
            assert f'{auto["loads"][k]:.4f}' not in tat, k   # trị tính KHÔNG


@pytest.mark.parametrize('dxf_rel', ['input/dxf/S16.dxf',
                                     'data/TP_BL/S1_V2.dxf'])
def test_co_bat_thi_chi_doi_con_so_tai_banh(dxf_rel):
    """Bật cờ chỉ được đổi các con số trong `*VEHICLE` + thêm chú thích.

    Đổi thêm bất cứ dòng nào khác nghĩa là phép thay thế đã lọt sang chỗ khác —
    và MCT thì Midas mới chối, không phải `pytest`.
    """
    frame, tat, bat, _, topo_bat = _mct_hai_luot(dxf_rel)
    auto = live_load_from_geometry(frame_metrics(frame),
                                  topo_bat['live_load']['im'])
    assert auto

    only_tat = [l for l in tat.splitlines() if l not in bat.splitlines()]
    only_bat = [l for l in bat.splitlines() if l not in tat.splitlines()]
    # mọi dòng MỚI là chú thích mạch tính hoặc dòng số của *VEHICLE
    for l in only_bat:
        assert l.startswith(';') or l.strip()[0].isdigit(), l
    for l in only_tat:
        assert l.strip() and l.strip()[0].isdigit(), l

    # mạch tính phải có mặt, đủ cả ba công thức bề rộng dải
    assert 'TCVN 11823-4 D.6.2.1.3' in bat
    for ct in ('1140 + 0.833X', '660 + 0.55S', '1220 + 0.25S',
               '(E_truck + 1200)/2'):
        assert ct in bat, ct

    # và con số ghi ra phải đúng bằng trị tính từ hình học
    for k, v in auto['loads'].items():
        assert f'{v:.4f}' in bat, k
    assert topo_bat['live_load']['source'] == 'geometry'


def test_co_bat_thi_hai_chieu_bao_khong_con_lech():
    """Sau khi app tự tính, phép đối chiếu template phải báo KHỚP.

    Đây là chỗ hai chiều bắt tay nhau: `live_load_compare` suy ngược từ sáu trị
    vừa ghi và phải tìm lại đúng `S`/`X` của chính mặt cắt đó. Lệch nghĩa là
    một trong hai chiều sai, mà không phép kiểm nào khác nhìn thấy.
    """
    frame, _, _, _, topo_bat = _mct_hai_luot('input/dxf/S16.dxf')
    m = frame_metrics(frame)
    auto = live_load_from_geometry(m, topo_bat['live_load']['im'])
    cmp = live_load_compare({**auto['loads'], 'impact': auto['im']}, m)
    assert cmp
    assert cmp['S']['off'] is False and cmp['X']['off'] is False
    assert cmp['S']['ratio'] == pytest.approx(1.0, abs=1e-9)
    assert cmp['X']['ratio'] == pytest.approx(1.0, abs=1e-9)


def test_su_that_ve_template_chung_van_con_do():
    """Template chung khai S = 6468 mm, không khớp mặt cắt nào.

    Con số cụ thể được khoá lại vì nó là căn cứ của cả việc này: S20 thiếu tới
    13,6% tải bánh, còn S16 dư 22%. Template đổi thì bài kiểm này đỏ, và đó
    đúng là lúc phải đọc lại mục *Bỏ template Excel* trong CLAUDE.md.
    """
    from src.input_reader import read_inputs
    if not os.path.exists(TEMPLATE):
        pytest.skip('thiếu template')
    d = read_inputs(TEMPLATE, strict=False)
    tpl = template_strip_geometry(d)
    assert tpl['S'] == pytest.approx(6468.0, abs=1.0)
    assert tpl['X'] == pytest.approx(3632.0, abs=1.0)

    # S20: nhịp 5550 mm — dải HẸP hơn template ⇒ tải bánh phải LỚN hơn
    s20 = live_load_from_geometry(_metrics(5550.0, 3375.0), d['impact'])
    assert s20['loads']['truck_pos'] > float(d['truck_pos'])
    ty_le = s20['loads']['truck_pos'] / float(d['truck_pos'])
    assert ty_le == pytest.approx(1.136, abs=0.005)


def test_project_luu_va_nap_lai_nguon_tai_banh(tmp_path):
    """Lựa chọn phương pháp phải đi theo file `.mtbproj`.

    Nó ở mức PROJECT chứ không mức mặt cắt: một hồ sơ trộn hai phương pháp
    giữa các mặt cắt thì người thẩm tra không có cách nào biết mặt cắt nào
    theo đường nào.
    """
    from src.project import Project, Section
    p = Project(sections=[Section(name='S1', dxf='a.dxf')])
    assert p.auto_live_load is False
    assert p.set_auto_live_load(True) == 0        # chưa mặt cắt nào có kết quả
    assert p.auto_live_load is True
    path = p.save(str(tmp_path / 'x.mtbproj'))
    assert Project.load(path).auto_live_load is True


def test_file_project_cu_lui_ve_duong_template(tmp_path):
    """File `.mtbproj` cũ không có khoá này — phải lui về đường template.

    Đó đúng là cách nó đã sinh ra kết quả đang lưu trong file ấy; lui về đường
    khác là nói sai về chính số liệu đang mở.
    """
    import json
    from src.project import Project
    path = tmp_path / 'old.mtbproj'
    path.write_text(json.dumps({
        'format': 1, 'name': 'P', 'output_dir': 'output', 'template': '',
        'sections': [{'name': 'S1', 'dxf': 'a.dxf'}],
    }), encoding='utf-8')
    assert Project.load(str(path)).auto_live_load is False


def test_doi_nguon_tai_banh_thi_ket_qua_cu_thanh_lac_hau():
    """Đổi trị này đổi tải bánh của MỌI mặt cắt, tức đổi nội lực.

    Mặt cắt đã có Beam Force thì bảng nội lực và bảng kiểm toán đang hiện
    thuộc về một mô hình khác — đúng khuôn lỗi `Section.stale` sinh ra để
    chặn. Ba chiều được khoá: có kết quả thì bị đánh dấu · chưa có kết quả thì
    không · chọn lại đúng trị đang dùng KHÔNG phải là thay đổi.
    """
    from src.project import Project, Section
    p = Project(sections=[
        Section(name='co_kq', dxf='a.dxf', beam_force='bf.xls'),
        Section(name='chua_giai', dxf='b.dxf'),
    ])
    assert p.set_auto_live_load(True) == 1
    assert 'tải bánh' in p.find('co_kq').stale
    assert p.find('chua_giai').stale == ''

    assert p.set_auto_live_load(True) == 0        # chọn lại: không đổi gì
    assert p.set_auto_live_load(False) == 1      # tắt lại cũng là đổi

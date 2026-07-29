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

from src.input_check import (P_TRUCK, check_shared_template, check_template,
                             frame_metrics, strip_width,
                             template_strip_geometry)
from src.mct_frame_writer import _write_tendon_prestress_block

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _template(S, X, im=0.33):
    """Bộ số liệu hoạt tải sinh ra từ một S và X biết trước."""
    E = strip_width(S=S)
    E_can = strip_width(X=X)
    return {
        'impact': im,
        'truck_can': P_TRUCK * (1 + im) / E_can * 1000.0,
        'truck_pos': P_TRUCK * (1 + im) / E['pos'] * 1000.0,
        'truck_neg': P_TRUCK * (1 + im) / E['neg'] * 1000.0,
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


def test_one_section_per_template_is_silent():
    e = [{'name': 'a', 'template': 't1.xls', 'metrics': _metrics(8000.0, 3900.0)},
         {'name': 'b', 'template': 't2.xls', 'metrics': _metrics(5500.0, 3300.0)}]
    assert check_shared_template(e) == []


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

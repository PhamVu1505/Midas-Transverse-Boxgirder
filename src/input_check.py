"""
Đối chiếu số liệu template với hình học mặt cắt.

Vì sao cần
──────────
Một template Excel dùng chung cho nhiều DXF là chuyện bình thường — vật liệu,
gió, nhiệt độ thì mặt cắt nào cũng như nhau. Nhưng **hoạt tải thì không**: sheet
`Load` mục 2.3 dùng phương pháp dải tương đương, mà bề rộng dải phụ thuộc thẳng
vào hình học của đúng mặt cắt đó:

    cánh hẫng   E = 1140 + 0,833·X
    giữa (+M)   E = 660  + 0,55·S
    giữa (−M)   E = 1220 + 0,25·S

`S` = cự ly sườn, `X` = khoảng cách từ tải tới gối. Tải bánh trên một mét dài là
`P(1+IM)/E`, nên **E nhỏ đi thì tải lớn lên**. Dùng template của mặt cắt có `S`
lớn cho mặt cắt có `S` nhỏ là ra tải **thiếu** — sai về phía không an toàn, và
không có gì trong quy trình hiện nay báo cho biết.

Suy ngược `S` và `X` của template
─────────────────────────────────
Không đọc ô `Load!G39/G40`: toạ độ ô cứng là thứ vừa lệch nguyên một dòng ở
`input_reader.SPEC` (có người chèn thêm một dòng vào sheet `Load`), và template
khác thì bố cục sheet lại khác nữa. Thay vào đó
suy ngược từ chính các khóa **bắt buộc** (`truck_can`, `truck_pos`, `truck_neg`,
`impact`) — cách này **tự kiểm chứng**: `+M` và `−M` là hai công thức khác hẳn
nhau, nếu cùng ra một `S` thì chắc chắn đã suy đúng, còn lệch nhau thì template
không lập theo phương pháp này và ta bỏ qua thay vì báo bừa.

`S` và `X` đo tới **TIM SƯỜN**
─────────────────────────────
Quy phạm định nghĩa `S` là cự ly **tim–tim của các bộ phận đỡ** (TCVN 11823-4
Điều 4.6.2.1), nên đây là quy ước dùng để đối chiếu, không phải khoảng thông
thuỷ giữa hai mặt sườn. `X` cũng đo từ mép bản tới **tim sườn ngoài**.

Chốt một quy ước như vậy làm phép kiểm **chặt hơn** so với bản đầu (chấp nhận cả
một dải từ thông thuỷ tới tim–tim rồi chỉ báo khi nằm ngoài cả hai): mỗi mặt cắt
giờ có đúng một trị số để so, nên template khai lệch là lộ ra ngay. Trị thông
thuỷ vẫn được in kèm trong thông báo, vì chênh lệch đúng bằng một bề dày sườn
thường chính là lý do người lập template gõ nhầm.
"""

import json
import os

# Nửa trục thiết kế HL93 — TCVN 11823-3 Điều 3.6.1.2 (kN)
P_TRUCK = 72.5      # nửa trục 145 kN của xe tải

# Câu mở đầu chung cho mọi cảnh báo về số liệu template. Đặt ngay đầu dòng để
# quét mắt qua cửa sổ Messages là thấy ngay việc phải làm, không phải đọc hết
# câu mới hiểu là đang nói về file Excel chứ không phải về bản vẽ.
CHECK_TEMPLATE = 'KIỂM TRA SỐ LIỆU FILE TEMPLATE'

# Lệch quá ngần này thì báo. Bề rộng dải chỉ phụ thuộc S theo hệ số 0,55 (+M) và
# 0,25 (−M) nên lệch S vài phần trăm gần như không đổi kết quả — ngưỡng đặt thấp
# quá thì cảnh báo kêu suốt và mất tác dụng.
TOL_REL = 0.05
TOL_ABS_MM = 100.0


# ─────────────────────────────────────────────────────────────
# Hình học thật của mặt cắt, đọc từ topo đã dựng
# ─────────────────────────────────────────────────────────────

def frame_metrics(source: dict) -> dict:
    """Cự ly sườn và cánh hẫng đo trên chính mô hình đã dựng.

    Nhận **cả hai** dạng:
      · `topo` đã ghi ra đĩa — bụng nằm ở `wL_nodes` / `wC_nodes` / `wR_nodes`
        (cùng quy ước với `result_reader`);
      · `frame` vừa ra khỏi `build_frame` / `build_twin_frame` — bụng nằm ở
        `web_left` / `web_center` / `web_right`, mỗi cái một dict có `nodes`.

    Nhận được dạng thứ hai thì hộp thoại hỏi-trước-khi-tạo không phải chạy hết
    `write_mct` chỉ để lấy hai con số hình học.

    Đơn vị trả về là **mm** (mô hình dùng m) cho khớp với số liệu trong sheet
    Load, vốn ghi bằng mm.

    Returns:
        {'B', 'n_webs', 'spans_centre', 'spans_clear', 'cantilever_left',
         'cantilever_right'} — rỗng nếu thiếu dữ liệu.
    """
    tops = source.get('top_nodes')
    if tops is None:
        tops = (source.get('top_slab') or {}).get('nodes')
    if not tops:
        return {}
    topo = source

    def xz(n):
        if isinstance(n, dict):
            return float(n['x']), float(n['z']), float(n.get('thickness') or 0)
        return float(n[0]), float(n[1]), 0.0

    webs = []
    for key, alt in (('wL_nodes', 'web_left'), ('wC_nodes', 'web_center'),
                     ('wR_nodes', 'web_right')):
        nodes = topo.get(key) or (topo.get(alt) or {}).get('nodes') or []
        if not nodes:
            continue
        vals = [xz(n) for n in nodes]
        top = max(vals, key=lambda v: v[1])       # đỉnh bụng = chỗ giao bản mặt
        webs.append({'x': top[0], 't': top[2]})
    webs.sort(key=lambda w: w['x'])
    if len(webs) < 2:
        return {}

    xs = [xz(n)[0] for n in tops]
    edge_l, edge_r = min(xs), max(xs)

    spans_centre, spans_clear = [], []
    for a, b in zip(webs, webs[1:]):
        d = (b['x'] - a['x']) * 1000.0
        spans_centre.append(d)
        spans_clear.append(d - (a['t'] + b['t']) / 2 * 1000.0)

    return {
        'B': (edge_r - edge_l) * 1000.0,
        'n_webs': len(webs),
        'spans_centre': spans_centre,
        'spans_clear': spans_clear,
        'cantilever_left': (webs[0]['x'] - edge_l) * 1000.0,
        'cantilever_right': (edge_r - webs[-1]['x']) * 1000.0,
    }


# ─────────────────────────────────────────────────────────────
# Suy ngược S và X mà template đã dùng
# ─────────────────────────────────────────────────────────────

def template_strip_geometry(data: dict) -> dict:
    """`S` và `X` mà sheet Load đã dùng, suy ngược từ tải bánh xe.

    Returns:
        {'S', 'X', 'S_pos', 'S_neg', 'consistent'} (mm), hoặc {} nếu thiếu khóa.
        `consistent=False` nghĩa là hai công thức cho hai `S` khác nhau —
        template không lập theo phương pháp dải tương đương, đừng đối chiếu.
    """
    try:
        im = float(data['impact'])
        can = float(data['truck_can'])
        pos = float(data['truck_pos'])
        neg = float(data['truck_neg'])
    except (KeyError, TypeError, ValueError):
        return {}
    if min(can, pos, neg) <= 0:
        return {}

    def E(load):                       # kN/m → mm
        return P_TRUCK * (1.0 + im) / load * 1000.0

    X = (E(can) - 1140.0) / 0.833
    S_pos = (E(pos) - 660.0) / 0.55
    S_neg = (E(neg) - 1220.0) / 0.25

    consistent = abs(S_pos - S_neg) <= max(TOL_ABS_MM, TOL_REL * abs(S_pos))
    return {
        'S': (S_pos + S_neg) / 2.0,
        'S_pos': S_pos,
        'S_neg': S_neg,
        'X': X,
        'consistent': consistent,
    }


def strip_width(S=None, X=None):
    """Bề rộng dải tương đương (mm) theo TCVN 11823-4 Bảng 1."""
    if X is not None:
        return 1140.0 + 0.833 * X
    return {'pos': 660.0 + 0.55 * S, 'neg': 1220.0 + 0.25 * S}


def live_load_compare(data: dict, metrics: dict) -> dict:
    """Đối chiếu dải tương đương của template với hình học — dạng SỐ, không phải câu.

    `check_template` gói kết quả này thành câu cho nhật ký và hộp thoại; dock
    Properties dựng nó thành bảng hai cột ngay cạnh mấy ô hoạt tải mà nó nói
    tới. Hai lối trình bày, nhưng **phép tính chỉ viết một lần** — hai bản sao
    của cùng một công thức tỉ số thì lệch nhau lúc nào cũng không ai thấy.

    Returns:
        {} khi thiếu số liệu, hoặc khi template không lập theo phương pháp dải
        tương đương (hai công thức cho hai `S` khác nhau). Ngược lại mỗi tham
        số một khối::

            {'S': {'tpl', 'real', 'clear', 'spans', 'ratio', 'unsafe', 'off'},
             'X': {'tpl', 'real', 'left', 'right', 'ratio', 'unsafe', 'off'}}

        `ratio` = E_template / E_mặt_cắt — lớn hơn 1 nghĩa là dải rộng hơn thực
        tế, tức tải bánh **thiếu**. `off` = lệch quá dung sai, mới đáng báo.
    """
    tpl = template_strip_geometry(data)
    if not tpl or not metrics or not tpl['consistent']:
        return {}

    # Nhịp NGẮN NHẤT cho dải hẹp nhất, tức tải bánh lớn nhất — đó là nhịp dễ bị
    # template làm cho thiếu tải nhất.
    centre, clear = metrics['spans_centre'], metrics['spans_clear']
    S_real = min(centre)
    e_t, e_r = strip_width(S=tpl['S']), strip_width(S=S_real)
    S = {
        'tpl': tpl['S'], 'real': S_real,
        'clear': clear[centre.index(S_real)], 'spans': list(centre),
        'ratio': max(e_t['pos'] / e_r['pos'], e_t['neg'] / e_r['neg']),
        'unsafe': e_t['pos'] > e_r['pos'] or e_t['neg'] > e_r['neg'],
        'off': abs(tpl['S'] - S_real) > max(TOL_ABS_MM, TOL_REL * S_real),
    }

    cl, cr = metrics['cantilever_left'], metrics['cantilever_right']
    X_real = min(cl, cr)
    x_t, x_r = strip_width(X=tpl['X']), strip_width(X=X_real)
    X = {
        'tpl': tpl['X'], 'real': X_real, 'left': cl, 'right': cr,
        'ratio': x_t / x_r, 'unsafe': x_t > x_r,
        'off': abs(tpl['X'] - X_real) > max(TOL_ABS_MM, TOL_REL * X_real),
    }
    return {'S': S, 'X': X}


def section_metrics(dxf=None, topo=None, excel=None) -> dict:
    """Hình học dải của MỘT mặt cắt — đọc `topo.json` nếu có, không thì dựng từ DXF.

    Dựng lại từ DXF tốn hơn đọc JSON nhưng vẫn chỉ vài chục mili giây, và đó
    đúng là lúc cần đối chiếu nhất: mặt cắt vừa thêm mà vớ nhầm template thì
    chưa có `topo` nào để đọc.

    DXF hỏng thì trả `{}` chứ không ném — chỗ gọi là hộp thoại và dock
    Properties, còn việc báo lỗi bản vẽ cho tử tế là việc của bước sinh MCT.
    """
    if topo and os.path.exists(topo):
        try:
            with open(topo, encoding='utf-8') as f:
                return frame_metrics(json.load(f))
        except Exception:
            pass
    if not dxf or not os.path.exists(dxf):
        return {}
    try:
        import ezdxf
        from .dxf_reader import (_get_polyline_vertices, read_inpolys,
                                 section_type_from_inpolys)
        from .frame_builder import build_frame, build_twin_frame
        from .load_reader import read_loads
        msp = ezdxf.readfile(dxf).modelspace()
        out = _get_polyline_vertices(msp, 'OUTPOLY')
        ins = read_inpolys(msp)
        ld = read_loads(excel) if (excel and os.path.exists(excel)) else None
        d_L = ld['d_L'] if ld else 0.4
        d_R = ld['d_R'] if ld else 0.4
        if section_type_from_inpolys(ins) == 'twin_box':
            frame = build_twin_frame(out, ins[0], ins[1], d_L=d_L, d_R=d_R)
        else:
            frame = build_frame(out, ins[0], d_L=d_L, d_R=d_R)
        return frame_metrics(frame)
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────
# Đối chiếu
# ─────────────────────────────────────────────────────────────

def check_template(data: dict, metrics: dict, name: str = '') -> list:
    """So số liệu hoạt tải của template với hình học mặt cắt.

    Returns:
        list các dict {'level': 'warn'|'info', 'text': str}. Rỗng = không có gì
        đáng nói.
    """
    out = []
    if not metrics or not data:
        return out
    tpl = template_strip_geometry(data)
    if not tpl:
        return out
    tag = f'{name}: ' if name else ''
    if not tpl['consistent']:
        out.append({'level': 'info', 'text': (
            f'{tag}không đối chiếu được hoạt tải — hai công thức dải tương đương '
            f'của template cho S khác nhau ({tpl["S_pos"]:.0f} và '
            f'{tpl["S_neg"]:.0f} mm), có vẻ sheet Load không lập theo phương '
            f'pháp dải tương đương.')})
        return out

    cmp = live_load_compare(data, metrics)

    # ── Cự ly sườn ──
    centre, clear = metrics['spans_centre'], metrics['spans_clear']
    s = cmp['S']
    if s['off']:
        real = (f'{centre[0]:.0f} mm (tim–tim; thông thuỷ {clear[0]:.0f} mm)'
                if len(centre) == 1 else
                f'{min(centre):.0f}…{max(centre):.0f} mm tim–tim '
                f'cho {len(centre)} nhịp')
        # E nhỏ hơn ⇒ tải bánh lớn hơn ⇒ thiên về an toàn
        hq = (f'tải bánh đang THIẾU khoảng {(s["ratio"] - 1) * 100:.0f}% — '
              f'sai về phía KHÔNG an toàn' if s['unsafe'] else
              f'tải bánh đang dư khoảng {(1 / s["ratio"] - 1) * 100:.0f}% — '
              f'thiên về an toàn')
        out.append({'level': 'warn' if s['unsafe'] else 'info', 'text': (
            f'{tag}{CHECK_TEMPLATE} — ô S (sheet Load) đang khai '
            f'{s["tpl"]:.0f} mm, cự ly sườn của mặt cắt này là {real}. {hq}.')})

    # ── Cánh hẫng ──
    # `X` đo từ mép bản tới TIM sườn ngoài, cùng quy ước với `S`.
    x = cmp['X']
    if x['off']:
        hq = (f'tải bánh trên cánh hẫng đang THIẾU khoảng '
              f'{(x["ratio"] - 1) * 100:.0f}% — sai về phía KHÔNG an toàn'
              if x['unsafe'] else
              f'tải bánh trên cánh hẫng dư khoảng '
              f'{(1 / x["ratio"] - 1) * 100:.0f}%')
        span = (f'{x["left"]:.0f} mm' if abs(x['left'] - x['right']) < 1 else
                f'{min(x["left"], x["right"]):.0f}…'
                f'{max(x["left"], x["right"]):.0f} mm')
        out.append({'level': 'warn' if x['unsafe'] else 'info', 'text': (
            f'{tag}{CHECK_TEMPLATE} — ô X (sheet Load) đang khai '
            f'{x["tpl"]:.0f} mm, cánh hẫng tới tim sườn của mặt cắt này là '
            f'{span}. {hq}.')})

    # ── Bề rộng đoạn lan can không được vượt cánh hẫng ──
    for key, cant, side in (('d_L', x['left'], 'trái'),
                            ('d_R', x['right'], 'phải')):
        try:
            d_mm = float(data[key]) * 1000.0
        except (KeyError, TypeError, ValueError):
            continue
        if d_mm > cant:
            out.append({'level': 'warn', 'text': (
                f'{tag}{CHECK_TEMPLATE} — bề rộng đoạn lan can {key} = '
                f'{d_mm:.0f} mm lớn hơn cánh hẫng {side} ({cant:.0f} mm), '
                f'tĩnh tải lan can đang đặt ra ngoài mặt cắt.')})
    return out


def check_shared_template(entries: list) -> list:
    """Cảnh báo khi nhiều mặt cắt hình học khác nhau dùng CHUNG một template.

    Args:
        entries: [{'name', 'template', 'metrics'}] — `metrics` từ `frame_metrics`.

    Returns:
        list dict {'level', 'text'} như `check_template`.
    """
    groups = {}
    for e in entries:
        if e.get('metrics') and e.get('template'):
            groups.setdefault(e['template'], []).append(e)

    out = []
    for tpl, members in groups.items():
        if len(members) < 2:
            continue
        rows, differ = [], False
        ref = members[0]['metrics']
        for m in members:
            g = m['metrics']
            rows.append(f'  · {m["name"]}: B {g["B"]:.0f} · {g["n_webs"]} bụng · '
                        f'S {g["spans_centre"][0]:.0f} (tim–tim) · '
                        f'hẫng {g["cantilever_left"]:.0f}/'
                        f'{g["cantilever_right"]:.0f} mm')
            if (g['n_webs'] != ref['n_webs']
                    or abs(g['B'] - ref['B']) > TOL_ABS_MM
                    or abs(g['spans_centre'][0] - ref['spans_centre'][0]) > TOL_ABS_MM
                    or abs(g['cantilever_left'] - ref['cantilever_left']) > TOL_ABS_MM):
                differ = True
        if differ:
            out.append({'level': 'warn', 'text': (
                f'{CHECK_TEMPLATE} — {len(members)} mặt cắt dùng chung template '
                f'{os.path.basename(tpl)} nhưng hình học khác nhau — hoạt tải và '
                f'tĩnh tải lan can trong template chỉ đúng cho MỘT mặt cắt:\n'
                + '\n'.join(rows))})
    return out

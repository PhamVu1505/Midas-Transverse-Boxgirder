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
Không đọc ô `Load!G39/G40`: toạ độ ô cứng chính là thứ đã lệch 12 dòng ở
`input_reader._KEYS`, và template khác thì bố cục sheet lại khác. Thay vào đó
suy ngược từ chính các khóa **bắt buộc** (`truck_can`, `truck_pos`, `truck_neg`,
`impact`) — cách này **tự kiểm chứng**: `+M` và `−M` là hai công thức khác hẳn
nhau, nếu cùng ra một `S` thì chắc chắn đã suy đúng, còn lệch nhau thì template
không lập theo phương pháp này và ta bỏ qua thay vì báo bừa.

Không đối chiếu `S` theo một quy ước duy nhất
─────────────────────────────────────────────
Sheet Excel không ghi `S` đo tim–tim sườn hay thông thuỷ giữa hai sườn, mà hai
trị số này chênh nhau đúng bằng một bề dày sườn. Nên hàm trả về **cả hai** và
chỉ báo động khi trị số của template nằm ngoài **cả hai**, cộng thêm dung sai.
Đoán bừa một quy ước thì cảnh báo sai chỗ, mà cảnh báo sai vài lần là người dùng
thôi đọc nó.
"""

# Nửa trục thiết kế HL93 — TCVN 11823-3 Điều 3.6.1.2 (kN)
P_TRUCK = 72.5      # nửa trục 145 kN của xe tải
P_TANDEM = 55.0     # nửa trục 110 kN của xe hai trục

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


# ─────────────────────────────────────────────────────────────
# Đối chiếu
# ─────────────────────────────────────────────────────────────

def _off(value, lo, hi):
    """Độ lệch của `value` so với khoảng [lo, hi]; 0 nghĩa là nằm trong."""
    lo, hi = min(lo, hi), max(lo, hi)
    if value < lo:
        return value - lo
    if value > hi:
        return value - hi
    return 0.0


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

    # ── Cự ly sườn ──
    centre, clear = metrics['spans_centre'], metrics['spans_clear']
    lo, hi = min(clear), max(centre)
    d = _off(tpl['S'], lo, hi)
    if abs(d) > max(TOL_ABS_MM, TOL_REL * max(lo, 1.0)):
        real = (f'{centre[0]:.0f} mm (tim–tim) / {clear[0]:.0f} mm (thông thuỷ)'
                if len(centre) == 1 else
                f'{lo:.0f}…{hi:.0f} mm cho {len(centre)} nhịp')
        # E nhỏ hơn ⇒ tải bánh lớn hơn ⇒ thiên về an toàn
        e_tpl = strip_width(S=tpl['S'])
        e_real = strip_width(S=(lo + hi) / 2.0)
        unsafe = e_tpl['pos'] > e_real['pos'] or e_tpl['neg'] > e_real['neg']
        ratio = max(e_tpl['pos'] / e_real['pos'], e_tpl['neg'] / e_real['neg'])
        hq = (f'tải bánh đang THIẾU khoảng {(ratio - 1) * 100:.0f}% — '
              f'sai về phía KHÔNG an toàn' if unsafe else
              f'tải bánh đang dư khoảng {(1 / ratio - 1) * 100:.0f}% — '
              f'thiên về an toàn')
        out.append({'level': 'warn' if unsafe else 'info', 'text': (
            f'{tag}hoạt tải trong template tính cho cự ly sườn S ≈ '
            f'{tpl["S"]:.0f} mm, mặt cắt này là {real}. {hq}.')})

    # ── Cánh hẫng ──
    cl, cr = metrics['cantilever_left'], metrics['cantilever_right']
    d = _off(tpl['X'], min(cl, cr), max(cl, cr))
    if abs(d) > max(TOL_ABS_MM, TOL_REL * max(min(cl, cr), 1.0)):
        e_tpl = strip_width(X=tpl['X'])
        e_real = strip_width(X=(cl + cr) / 2.0)
        unsafe = e_tpl > e_real
        ratio = e_tpl / e_real
        hq = (f'tải bánh trên cánh hẫng đang THIẾU khoảng '
              f'{(ratio - 1) * 100:.0f}% — sai về phía KHÔNG an toàn'
              if unsafe else
              f'tải bánh trên cánh hẫng dư khoảng {(1 / ratio - 1) * 100:.0f}%')
        span = (f'{cl:.0f} mm' if abs(cl - cr) < 1 else
                f'{min(cl, cr):.0f}…{max(cl, cr):.0f} mm')
        out.append({'level': 'warn' if unsafe else 'info', 'text': (
            f'{tag}hoạt tải cánh hẫng trong template tính cho X ≈ '
            f'{tpl["X"]:.0f} mm, cánh hẫng của mặt cắt này là {span}. {hq}.')})

    # ── Bề rộng đoạn lan can không được vượt cánh hẫng ──
    for key, cant, side in (('d_L', cl, 'trái'), ('d_R', cr, 'phải')):
        try:
            d_mm = float(data[key]) * 1000.0
        except (KeyError, TypeError, ValueError):
            continue
        if d_mm > cant:
            out.append({'level': 'warn', 'text': (
                f'{tag}bề rộng đoạn lan can {key} = {d_mm:.0f} mm lớn hơn cánh '
                f'hẫng {side} ({cant:.0f} mm) — tĩnh tải lan can đang đặt ra '
                f'ngoài mặt cắt.')})
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
                        f'S {g["spans_centre"][0]:.0f} · '
                        f'hẫng {g["cantilever_left"]:.0f}/'
                        f'{g["cantilever_right"]:.0f} mm')
            if (g['n_webs'] != ref['n_webs']
                    or abs(g['B'] - ref['B']) > TOL_ABS_MM
                    or abs(g['spans_centre'][0] - ref['spans_centre'][0]) > TOL_ABS_MM
                    or abs(g['cantilever_left'] - ref['cantilever_left']) > TOL_ABS_MM):
                differ = True
        if differ:
            import os
            out.append({'level': 'warn', 'text': (
                f'{len(members)} mặt cắt dùng chung template '
                f'{os.path.basename(tpl)} nhưng hình học khác nhau — hoạt tải và '
                f'tĩnh tải lan can trong template chỉ đúng cho MỘT mặt cắt:\n'
                + '\n'.join(rows))})
    return out

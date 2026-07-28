"""
Nhận diện cáp dự ứng lực tại từng mặt cắt kiểm toán, đọc thẳng từ `topo`.

Vì sao cần: bảng kiểm toán có ô `dp` (khoảng cách từ thớ nén ngoài cùng đến
trọng tâm cáp). Bắt người dùng tự tra rồi gõ vào tám cột là vừa mất công vừa dễ
gõ nhầm sang bộ phận **không có cáp** — mặt cắt điển hình chỉ căng cáp ngang ở
bản mặt, còn bản đáy và bụng thì không.

Cách làm: `topo['tendons'][].path_mct` đã là đường cáp trong hệ toạ độ MCT
(mét, gốc X ở tim, gốc Z ở đáy) — cùng hệ với node của khung. Nội suy cao độ
cáp tại vị trí điểm kiểm toán rồi quy về `dp` theo phía chịu nén, mà phía chịu
nén thì suy từ **dấu của Mu**.

Không tự đoán diện tích cáp: `Ap` trên một mét dài phụ thuộc cự ly cáp dọc cầu,
mà mặt cắt ngang không mang thông tin đó. Ở đây chỉ trả `has_pt` và `dp`.
"""

from .result_reader import check_point_marks

# Điểm kiểm toán → bộ phận. Điểm phân giải ('A1', 'G2'…) tra theo chữ cái đầu.
ZONE_OF_POINT = {'A': 'TOP', 'B': 'TOP', 'C': 'TOP', 'D': 'TOP',
                 'E': 'BOT', 'F': 'BOT', 'G': 'WEB', 'H': 'WEB'}


def _zone_of_location(loc: str) -> str:
    loc = (loc or '').upper()
    if loc.startswith('TOP'):
        return 'TOP'
    if loc.startswith('BOT'):
        return 'BOT'
    return 'WEB'


def _interp(path, key, want, other):
    """Nội suy thành phần `other` của đường gấp khúc tại `key = want`.

    path là [[x, z], …]; key/other là chỉ số 0 hoặc 1. Ngoài phạm vi thì lấy giá
    trị ở đầu gần nhất — cáp không kéo dài tới đó, nhưng cao độ ở mút vẫn là ước
    lượng hợp lý hơn là bỏ trắng.
    """
    pts = [p for p in path if len(p) >= 2]
    if not pts:
        return None
    pts = sorted(pts, key=lambda p: p[key])
    if want <= pts[0][key]:
        return pts[0][other]
    if want >= pts[-1][key]:
        return pts[-1][other]
    for a, b in zip(pts, pts[1:]):
        if a[key] <= want <= b[key]:
            span = b[key] - a[key]
            if abs(span) < 1e-12:
                return a[other]
            t = (want - a[key]) / span
            return a[other] + t * (b[other] - a[other])
    return pts[-1][other]


def detect(topo: dict, check_points: dict = None) -> dict:
    """{tên điểm: {'has_pt': bool, 'dp': mm, 'zone': str, 'cables': [tên]}}.

    `dp` = 0 khi bộ phận đó không có cáp, hoặc khi thiếu chiều cao tiết diện.
    """
    check_points = check_points or {}
    marks = check_point_marks(topo)

    zones = {}
    for t in topo.get('tendons') or []:
        path = t.get('path_mct') or []
        if len(path) < 2:
            continue
        zones.setdefault(_zone_of_location(t.get('location')), []).append(
            (t.get('name') or '', path))

    out = {}
    for name, mk in marks.items():
        zone = ZONE_OF_POINT.get(name[0], 'WEB')
        cables = zones.get(zone) or []
        cp = check_points.get(name) or {}
        h = float(cp.get('h') or 0.0)
        rec = {'has_pt': bool(cables), 'dp': 0.0, 'zone': zone,
               'cables': [c[0] for c in cables]}
        out[name] = rec
        if not cables or h <= 0:
            continue

        sagging = float(cp.get('Mu') or 0.0) >= 0.0
        if mk['dir'] == 'v':
            # Bản nằm ngang. Node của bản mặt nằm trên MẶT TRÊN (lệch tâm CT),
            # node bản đáy nằm trên MẶT DƯỚI (lệch tâm CB) — nên `mk['z']` chính
            # là một trong hai mặt bê tông, đo thẳng từ đó ra.
            zs = [_interp(p, 0, mk['x'], 1) for _, p in cables]
            zs = [z for z in zs if z is not None]
            if not zs:
                continue
            z_pt = sum(zs) / len(zs)
            if zone == 'TOP':
                d_top = (mk['z'] - z_pt) * 1000.0     # cáp nằm dưới mặt trên
                dp = d_top if sagging else h - d_top
            else:
                d_bot = (z_pt - mk['z']) * 1000.0     # cáp nằm trên mặt dưới
                dp = h - d_bot if sagging else d_bot
        else:
            # Bụng thẳng đứng, node ở TRỌNG TÂM (lệch tâm CC) nên mép bê tông
            # cách node h/2 về mỗi phía.
            xs = [_interp(p, 1, mk['z'], 0) for _, p in cables]
            xs = [x for x in xs if x is not None]
            if not xs:
                continue
            off = (sum(xs) / len(xs) - mk['x']) * 1000.0
            dp = h / 2.0 + (off if sagging else -off)

        rec['dp'] = round(min(max(dp, 0.0), h), 1)
    return out

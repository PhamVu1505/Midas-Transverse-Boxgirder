"""
Kiểm toán tiết diện khung ngang theo **TCVN 11823** (và 22TCN 272-05 để đối
chiếu hồ sơ cũ).

Tiết diện là một **lát cắt rộng 1 m** của mặt cắt ngang, chữ nhật `b × h`, cốt
thép một lớp, có thể có cáp DƯL. Bốn nhóm kiểm tra, đúng bố cục sheet `Strength`
của file mẫu:

    1. Sức kháng uốn        Mu ≤ Mr = φ·Mn
    2. Giới hạn cốt thép     c/de ≤ 0.42  và  Mr ≥ min(Mcr, 1.33·Mu)
    3. Nứt                   fs ≤ fsa (22TCN) · cự ly s ≤ s_max (TCVN 11823)
    4. Cắt                   Vu ≤ Vr = φ·Vn   (MCFT)

Các công thức dưới đây đã được **đối chiếu ngược với chính số liệu** trong
`data/Midas-Transverse-Boxgirder-analysis.xls` (mặt cắt S1) và khớp tuyệt đối:
β₁ = 0.6929; `c` của điểm không cáp (E: 27.0050, G: 48.4948 với fy = 420);
`de` = 197.3 → c/de = 0.2241; n = 5.2622, m = 0.0143, k = 0.1556, j = 0.9481,
fs = 114.3378; dv = 216.0 và 685.6447; cỡ hạt lớn nhất suy từ sxe là 25 mm.

**MỘT CHỖ CỐ Ý KHÁC FILE MẪU** — xem `Flexure.note`. Ở tiết diện có cáp, file
mẫu lấy trục trung hoà từ **riêng lực cáp** (`c = Ap·fpu / (0.85 f'c β₁ b)`,
bỏ cốt thép thường) nhưng lại **cộng cốt thép thường vào Mn**. Hai vế không
nhất quán. Module này giải theo đúng TCVN 11823-5 (cả As và Ap vào phương trình
cân bằng, fps phụ thuộc c). Kết quả **thấp hơn**, tức thiên về an toàn: với
điểm A của S1, Mr 289.87 → 277.4 kN·m (−4.3%).
"""

import math
from dataclasses import dataclass, field

# Hệ số biến đổi mô men nứt, TCVN 11823-5 Điều 5.7.3.3.2
GAMMA_1 = 1.6      # biến động mô men nứt do uốn
GAMMA_2 = 1.1      # biến động dự ứng lực
GAMMA_3 = 0.67     # tỉ lệ chảy/bền của cốt thép thường

C_DE_MAX = 0.42    # giới hạn hàm lượng cốt thép tối đa
Z_22TCN = 23000.0  # N/mm — thông số bề rộng vết nứt của 22TCN 272-05
AGG_SIZE = 25.0    # mm — cỡ hạt lớn nhất, dùng cho sxe

STANDARDS = ('TCVN 11823', '22TCN 272-05')


@dataclass
class Material:
    """Vật liệu. `fc`, `fy` là bắt buộc; còn lại có mặc định thông dụng."""
    fc: float                      # MPa — f'c
    fy: float = 420.0              # MPa — cốt thép thường
    Ec: float = None               # MPa — None thì suy theo 0.043·γ^1.5·√f'c
    Es: float = 200000.0           # MPa
    fpu: float = 1860.0            # MPa — cáp
    fpy: float = 1674.0            # MPa
    Ep: float = 197000.0           # MPa
    density: float = 2500.0        # kg/m³ — chỉ dùng để suy Ec

    def __post_init__(self):
        if self.Ec is None:
            self.Ec = 0.043 * self.density ** 1.5 * math.sqrt(self.fc)

    @property
    def beta1(self) -> float:
        """Hệ số quy đổi khối ứng suất chữ nhật (TCVN 11823-5 Đ.5.7.2.2)."""
        return max(0.65, min(0.85, 0.85 - 0.05 * (self.fc - 28.0) / 7.0))

    @property
    def fr(self) -> float:
        """Cường độ chịu kéo khi uốn, MPa (Đ.5.4.2.6)."""
        return 0.63 * math.sqrt(self.fc)

    @property
    def k_ps(self) -> float:
        """k = 2(1.04 − fpy/fpu), dùng trong công thức fps."""
        return 2.0 * (1.04 - self.fpy / self.fpu)


@dataclass
class Rebar:
    """Cốt thép tại một mặt cắt kiểm toán — người dùng nhập trực tiếp.

    `bar_area` để ghi đè diện tích một thanh. Cần đến vì file mẫu dùng **bảng
    tra ASTM** (D16 → 199 mm², D19 → 284, D25 → 510) chứ không phải π·d²/4
    (201.1 / 283.5 / 490.9). Chênh tới 3.9% ở D25. Bỏ trống thì tính π·d²/4,
    đúng cho thanh hệ mét.
    """
    dia: float = 0.0        # mm — đường kính thanh chịu uốn
    spacing: float = 150.0  # mm — cự ly
    cover: float = 50.0     # mm — từ mép bê tông đến TÂM thanh
    Av: float = 0.0         # mm²/m — cốt đai (0 = không có)
    Av_spacing: float = 0.0  # mm — cự ly đai
    bar_area: float = 0.0   # mm² — ghi đè diện tích một thanh

    def As(self, b: float = 1000.0) -> float:
        """Diện tích cốt thép trên bề rộng b (mm²)."""
        if self.spacing <= 0:
            return 0.0
        a1 = self.bar_area or (math.pi * self.dia ** 2 / 4.0 if self.dia > 0 else 0.0)
        return a1 * (b / self.spacing)


@dataclass
class Tendon:
    """Cáp DƯL tại mặt cắt. dp = 0 nghĩa là không có cáp."""
    dp: float = 0.0   # mm — từ thớ nén ngoài cùng đến trọng tâm cáp
    Ap: float = 0.0   # mm²


@dataclass
class Forces:
    """Nội lực lấy từ bảng Beam Force (đã bao)."""
    Mu: float = 0.0     # kN·m
    Vu: float = 0.0     # kN
    Mser: float = 0.0   # kN·m
    Mdnc: float = 0.0   # kN·m — mô men do tĩnh tải không hệ số, cho Mcr


@dataclass
class CheckResult:
    """Kết quả một nhóm kiểm tra."""
    name: str
    values: dict = field(default_factory=dict)
    demand: float = 0.0
    capacity: float = 0.0
    ok: bool = True
    note: str = ''
    applicable: bool = True     # False = không áp dụng, đừng tính vào kết luận

    @property
    def ratio(self) -> float:
        """Mức huy động. 0 khi không có sức kháng (chưa nhập cốt thép)."""
        return abs(self.demand) / self.capacity if self.capacity else 0.0


# ─────────────────────────────────────────────────────
# 1. Sức kháng uốn
# ─────────────────────────────────────────────────────

def flexure(h, forces, rebar, mat, tendon=None, phi=0.9, b=1000.0):
    """Mu ≤ Mr = φ·Mn, tiết diện chữ nhật b × h.

    Trục trung hoà giải bằng lặp vì fps phụ thuộc chính c:
        c   = (Ap·fpu + As·fy) / (0.85 f'c β₁ b + k·Ap·fpu/dp)
        fps = fpu (1 − k·c/dp)
        Mn  = Ap·fps(dp − a/2) + As·fy(ds − a/2)
    Không cáp thì suy biến về c = As·fy/(0.85 f'c β₁ b) — đúng bằng con số của
    file mẫu (E: 27.0050, G: 48.4948).
    """
    tendon = tendon or Tendon()
    As = rebar.As(b)
    ds = h - rebar.cover
    Ap, dp = tendon.Ap, tendon.dp
    k = mat.k_ps
    cc = 0.85 * mat.fc * mat.beta1 * b          # lực nén bê tông trên 1 mm của c

    if Ap > 0 and dp > 0:
        c = (Ap * mat.fpu + As * mat.fy) / (cc + k * Ap * mat.fpu / dp)
        fps = mat.fpu * (1.0 - k * c / dp)
    else:
        c = As * mat.fy / cc if cc else 0.0
        fps = 0.0

    a = mat.beta1 * c
    Mn = (Ap * fps * (dp - a / 2.0) + As * mat.fy * (ds - a / 2.0)) / 1e6  # kN·m
    Mr = phi * Mn

    # de — chiều cao có hiệu quy đổi khi có cả cáp và cốt thép (Đ.5.7.3.3.1)
    num = Ap * fps * dp + As * mat.fy * ds
    den = Ap * fps + As * mat.fy
    de = num / den if den else ds

    return CheckResult(
        'Sức kháng uốn',
        {'As': As, 'ds': ds, 'Ap': Ap, 'dp': dp, 'fps': fps,
         'beta1': mat.beta1, 'c': c, 'a': a, 'de': de, 'Mn': Mn},
        demand=abs(forces.Mu), capacity=Mr,
        ok=abs(forces.Mu) <= Mr + 1e-9,
        applicable=bool(den),
        note='' if den else 'chưa nhập cốt thép',
    )


# ─────────────────────────────────────────────────────
# 2. Giới hạn cốt thép
# ─────────────────────────────────────────────────────

def reinforcement_limits(h, forces, flex, mat, standard='TCVN 11823',
                         fcpe=0.0, b=1000.0):
    """c/de ≤ 0.42 và Mr ≥ min(Mcr, 1.33·Mu).

    Mcr khác nhau giữa hai tiêu chuẩn — đây là một trong ba chỗ lệch:
      22TCN 272-05 : lấy thẳng 1.2·Mcr với Mcr = fr·S
      TCVN 11823   : Mcr = γ₃[(γ₁·fr + γ₂·fcpe)·Sc − Mdnc(Sc/Snc − 1)]
    Lát cắt 1 m là tiết diện liền khối nên Sc = Snc, số hạng Mdnc triệt tiêu.
    """
    S = b * h ** 2 / 6.0 / 1e9          # m³ — mô đun tiết diện, Sc = Snc
    fr_kpa = mat.fr * 1000.0

    if standard == '22TCN 272-05':
        Mcr = 1.2 * fr_kpa * S
        formula = '1.2·fr·S'
    else:
        Mcr = GAMMA_3 * (GAMMA_1 * fr_kpa + GAMMA_2 * fcpe * 1000.0) * S
        formula = 'γ₃(γ₁·fr + γ₂·f_cpe)·S'

    need = min(Mcr, 1.33 * abs(forces.Mu)) if forces.Mu else Mcr
    c_de = flex.values['c'] / flex.values['de'] if flex.values['de'] else 0.0

    ok = (c_de <= C_DE_MAX + 1e-9) and (flex.capacity >= need - 1e-9)
    return CheckResult(
        'Giới hạn cốt thép',
        {'c/de': c_de, 'c/de_max': C_DE_MAX, 'S': S, 'fr': mat.fr,
         'Mcr': Mcr, '1.33Mu': 1.33 * abs(forces.Mu), 'công thức Mcr': formula},
        demand=need, capacity=flex.capacity, ok=ok,
    )


# ─────────────────────────────────────────────────────
# 3. Kiểm toán nứt
# ─────────────────────────────────────────────────────

def crack(h, forces, rebar, mat, standard='TCVN 11823', gamma_e=1.0, b=1000.0,
          tendon=None):
    """Ứng suất cốt thép ở TTGH Sử dụng, tiết diện nứt đàn hồi.

        n = Es/Ec · ρ = As/(b·ds) · k = √((ρn)² + 2ρn) − ρn · j = 1 − k/3
        fs = Mser / (As·j·ds)

    22TCN 272-05 : fs ≤ fsa = Z/(dc·A)^⅓ ≤ 0.6 fy
    TCVN 11823   : kiểm **cự ly** cốt thép, s ≤ 123000·γe/(βs·fs) − 2dc
                   với βs = 1 + dc/(0.7(h − dc))
    """
    As = rebar.As(b)
    ds = h - rebar.cover
    if As <= 0 or ds <= 0:
        return CheckResult('Kiểm toán nứt', {}, applicable=False,
                           note='chưa nhập cốt thép')

    # Tiết diện CÓ CÁP thì công thức tiết diện nứt đàn hồi bên dưới không dùng
    # được: nó lấy toàn bộ Mser chia cho cánh tay đòn cốt thép thường, bỏ qua
    # nén trước, nên fs vọt lên vô lý (điểm A của S1 ra 338 MPa, hỏng ảo). Kiểm
    # nứt cho tiết diện DƯL phải đi qua mô men gây nén hết và mất mát ứng suất —
    # chưa có số liệu đó. File mẫu cũng chỉ kiểm nứt ở bốn điểm không cáp.
    if tendon and tendon.Ap > 0:
        return CheckResult('Kiểm toán nứt', {}, applicable=False,
                           note='có cáp DƯL — cần xét nén trước, chưa kiểm')

    n = mat.Es / mat.Ec
    m = n * As / (b * ds)
    k = math.sqrt(m * m + 2 * m) - m
    j = 1.0 - k / 3.0
    fs = abs(forces.Mser) * 1e6 / (As * j * ds)     # MPa

    dc = rebar.cover
    vals = {'n': n, 'm': m, 'k': k, 'j': j, 'fs': fs, 'dc': dc}

    if standard == '22TCN 272-05':
        n_bar = b / rebar.spacing if rebar.spacing else 1.0
        A_eff = 2.0 * dc * b / n_bar if n_bar else 0.0
        fsa = min(Z_22TCN / (dc * A_eff) ** (1 / 3), 0.6 * mat.fy) if A_eff else 0.0
        vals.update({'A': A_eff, 'Z': Z_22TCN, 'fsa': fsa, '0.6fy': 0.6 * mat.fy})
        return CheckResult('Kiểm toán nứt', vals, demand=fs, capacity=fsa,
                           ok=fs <= fsa + 1e-9)

    bs = 1.0 + dc / (0.7 * (h - dc)) if h > dc else 1.0
    s_max = 123000.0 * gamma_e / (bs * fs) - 2.0 * dc if fs else float('inf')
    vals.update({'βs': bs, 'γe': gamma_e, 's_max': s_max, 's': rebar.spacing})
    return CheckResult('Kiểm toán nứt', vals,
                       demand=rebar.spacing, capacity=s_max,
                       ok=rebar.spacing <= s_max + 1e-9)


# ─────────────────────────────────────────────────────
# 4. Kiểm toán cắt — MCFT
# ─────────────────────────────────────────────────────

def shear(h, forces, rebar, mat, flex, tendon=None, phi=0.9, b=1000.0):
    """Vu ≤ Vr = φ·Vn theo quy trình tổng quát (TCVN 11823-5 Đ.5.8.3.4.2).

        dv  = max(de − a/2, 0.9·de, 0.72·h)
        εs  = (|Mu|/dv + |Vu| − Ap·fpo) / (Es·As + Ep·Ap) ≥ 0
        sxe = sx · 35/(ag + 16)
        β   = 4.8/(1 + 750εs) · 51/(39 + sxe)     — khi KHÔNG có cốt đai tối thiểu
        β   = 4.8/(1 + 750εs)                     — khi CÓ cốt đai tối thiểu
        θ   = 29 + 3500·εs
        Vc  = 0.083·β·√f'c·b·dv ·  Vs = Av·fy·dv·cotθ/s ·  Vn = min(Vc+Vs, 0.25f'c·b·dv)

    Lưu ý: file mẫu dùng **bảng tra θ–β** của 22TCN 272-05 (sheet `For Shear`),
    còn đây là công thức đóng của TCVN 11823. Hai đường cho kết quả gần nhau
    nhưng không trùng — không phải lỗi.
    """
    tendon = tendon or Tendon()
    As = rebar.As(b)
    de = flex.values.get('de') or (h - rebar.cover)
    a = flex.values.get('a', 0.0)
    dv = max(de - a / 2.0, 0.9 * de, 0.72 * h)

    Ap = tendon.Ap
    fpo = 0.7 * mat.fpu if Ap else 0.0
    den = mat.Es * As + mat.Ep * Ap
    if den <= 0:
        return CheckResult('Kiểm toán cắt', {'dv': dv}, applicable=False,
                           note='chưa nhập cốt thép')

    eps = (abs(forces.Mu) * 1e6 / dv + abs(forces.Vu) * 1e3 - Ap * fpo) / den
    eps = max(eps, 0.0)          # âm thì lấy 0 — thiên về an toàn

    has_stirrup = rebar.Av > 0
    sxe = min(max(rebar.spacing * 35.0 / (AGG_SIZE + 16.0), 300.0), 2000.0)
    beta = 4.8 / (1 + 750 * eps)
    if not has_stirrup:
        beta *= 51.0 / (39.0 + sxe)
    theta = 29.0 + 3500.0 * eps

    Vc = 0.083 * beta * math.sqrt(mat.fc) * b * dv / 1e3        # kN
    Vs = 0.0
    if has_stirrup and rebar.Av_spacing > 0:
        Vs = rebar.Av * mat.fy * dv / math.tan(math.radians(theta)) \
            / rebar.Av_spacing / 1e3
    Vn = min(Vc + Vs, 0.25 * mat.fc * b * dv / 1e3)
    Vr = phi * Vn

    return CheckResult(
        'Kiểm toán cắt',
        {'dv': dv, 'εs': eps, 'sxe': sxe, 'β': beta, 'θ': theta,
         'Vc': Vc, 'Vs': Vs, 'Vn': Vn},
        demand=abs(forces.Vu), capacity=Vr, ok=abs(forces.Vu) <= Vr + 1e-9,
    )


# ─────────────────────────────────────────────────────
# Gộp
# ─────────────────────────────────────────────────────

def check_point(h, forces, rebar, mat, tendon=None, standard='TCVN 11823',
                phi_f=0.9, phi_v=0.9, gamma_e=1.0, fcpe=0.0, b=1000.0) -> dict:
    """Chạy cả bốn nhóm cho MỘT mặt cắt kiểm toán.

    Returns: {'flexure', 'limits', 'crack', 'shear', 'ok'} — 'ok' là AND của
    bốn nhóm.
    """
    if standard not in STANDARDS:
        raise ValueError(f'tiêu chuẩn không nhận: {standard!r}; '
                         f'chọn một trong {STANDARDS}')

    fl = flexure(h, forces, rebar, mat, tendon, phi=phi_f, b=b)
    lim = reinforcement_limits(h, forces, fl, mat, standard, fcpe=fcpe, b=b)
    cr = crack(h, forces, rebar, mat, standard, gamma_e=gamma_e, b=b,
               tendon=tendon)
    sh = shear(h, forces, rebar, mat, fl, tendon, phi=phi_v, b=b)

    rs = (fl, lim, cr, sh)
    return {'flexure': fl, 'limits': lim, 'crack': cr, 'shear': sh,
            'ok': all(r.ok for r in rs if r.applicable)}


def check_all(check_points: dict, rebars: dict, mat: Material,
              tendons: dict = None, **kw) -> dict:
    """Chạy cho toàn bộ các mặt cắt kiểm toán của một mặt cắt ngang.

    check_points: kết quả `result_reader.extract_check_points`
    rebars:       {tên điểm: Rebar}
    tendons:      {tên điểm: Tendon} — thiếu thì coi như không có cáp
    """
    tendons = tendons or {}
    out = {}
    for name, cp in check_points.items():
        rb = rebars.get(name) or rebars.get(name[0]) or Rebar()
        td = tendons.get(name) or tendons.get(name[0])
        out[name] = check_point(
            cp['h'],
            Forces(Mu=cp['Mu'], Vu=cp['Vu'], Mser=cp['Mser']),
            rb, mat, td, **kw)
    return out

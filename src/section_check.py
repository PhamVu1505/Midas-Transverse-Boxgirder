"""
Kiểm toán tiết diện khung ngang theo **TCVN 11823** (và 22TCN 272-05 để đối
chiếu hồ sơ cũ).

Tiết diện là một **lát cắt rộng 1 m** của mặt cắt ngang, chữ nhật `b × h`, cốt
thép một lớp, có thể có cáp DƯL. Bốn nhóm kiểm tra:

    1. Sức kháng uốn        Mu ≤ Mr = φ·Mn                     (Đ.7.3.2)
    2. Giới hạn cốt thép     Mr ≥ min(Mcr, 1.33·Mu)             (Đ.7.3.3)
       + phân loại tiết diện theo biến dạng kéo thực εt         (Đ.7.2.1)
    3. Nứt                   s ≤ 123000γe/(βs·fss) − 2dc        (Đ.7.3.4)
    4. Cắt                   Vu ≤ Vr = φ·Vn, MCFT               (Đ.8.3.3, 8.3.4.2)

**Nguồn công thức: bản chính thức TCVN 11823-5:2017** ở
`H:\VUPQ\Tai_lieu_ky_thuat_TieuChuan\Tieu_chuan_thiet_ke_cau_TCVN11823`
(192 trang, md5 2f416af8c590). Số điều và số phương trình ghi ngay tại từng hàm.

**Đối chiếu số:** điểm E của S1 trong sheet `Strength` khớp tuyệt đối cả 11 đại
lượng (lệch 0.0000): As 1893.3333 · c 27.0050 · a 18.7106 · Mr 490.7022 ·
c/de 0.0389 · n 5.2622 · m 0.0143 · k 0.1556 · j 0.9481 · fs 114.3378 ·
dv 685.6447. Bảng 5 nội suy lại đúng θ/β của bốn điểm A, B, E, G tới 4 chữ số.

**Ba chỗ cố ý khác file mẫu** (đều ghi lý do tại chỗ):
  1. Tiết diện có cáp: file mẫu lấy trục trung hoà từ riêng lực cáp nhưng lại
     cộng cốt thép thường vào Mn — hai vế không nhất quán. Đây giải đúng Đ.7.3.2.
     Mr điểm A 289.87 → 278.31 (−4.0%), thiên về an toàn.
  2. Diện tích thanh mặc định π·d²/4 (thanh hệ mét), file mẫu dùng bảng tra ASTM.
     Có `Rebar.bar_area` để ghi đè khi cần so số.
  3. Kiểm nứt bỏ qua khi tiết diện có cáp (chưa xét nén trước) hoặc khi ứng suất
     kéo chưa tới 80% fr (Đ.7.3.4 chỉ yêu cầu kiểm khi vượt ngưỡng đó).

**φ = 0.90 cho MỌI tiết diện.** Đ.5.4.2.1 cho phép φ = 1.00 với tiết diện dự
ứng lực khống chế kéo, nhưng VuPQ chốt giữ 0.90 — thiên về an toàn, sức kháng
uốn thấp hơn 11%. Đừng tự nâng lên.

"""

import math
from dataclasses import dataclass, field

# Hệ số biến đổi mô men nứt, TCVN 11823-5 Điều 5.7.3.3.2
GAMMA_1 = 1.6      # biến động mô men nứt do uốn
GAMMA_2 = 1.1      # biến động dự ứng lực
GAMMA_3 = 0.67     # tỉ lệ chảy/bền của cốt thép thường

C_DE_MAX = 0.42    # giới hạn hàm lượng cốt thép tối đa — CHỈ của 22TCN 272-05
Z_22TCN = 23000.0  # N/mm — thông số bề rộng vết nứt của 22TCN 272-05
AGG_SIZE = 25.0    # mm — cỡ hạt lớn nhất, dùng cho sxe
EPS_C = 0.003      # biến dạng nén giới hạn của bê tông (Đ.7.2.1)
EPS_CL = 0.002     # giới hạn biến dạng khống chế NÉN (thép cấp 420 và mọi cáp)
EPS_TL = 0.005     # giới hạn biến dạng khống chế KÉO (fy ≤ 520 và mọi cáp)
PHI_COMPRESSION = 0.75   # hệ số sức kháng của mặt cắt khống chế nén
CRACK_TRIGGER = 0.80     # chỉ kiểm nứt khi ứng suất kéo > 80% fr (Đ.7.3.4)

STANDARDS = ('TCVN 11823', '22TCN 272-05')

# Hai phương pháp tổng quát của Điều 8.3.4.2, TCVN cho dùng ngang hàng:
#   'bảng'     — phương pháp (b): tra Bảng 4/Bảng 5, nội suy hai chiều, lặp θ.
#                Đây là cách file mẫu dùng; đã đối chiếu khớp 4 chữ số thập phân.
#   'công thức' — phương pháp (a): công thức đóng pt. 77–79.
# Hai phương pháp lệch nhau RẤT nhiều ở tiết diện vùng nén: (a) chặn εs ≥ 0 nên
# β ≤ 4.8 rồi còn nhân hệ số kích thước 51/(39+sxe) với sxe ≥ 294 → β ≈ 0.7;
# Bảng 5 cho εx xuống −0.20×10⁻³ với β tới 6.36. Mặc định dùng 'bảng'.
SHEAR_METHODS = ('bảng', 'công thức')


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
    """Mr ≥ min(Mcr, 1.33·Mu), cộng giới hạn cốt thép tối đa theo từng tiêu chuẩn.

    **Cốt thép tối đa — hai tiêu chuẩn khác hẳn nhau:**

    22TCN 272-05 có điều kiện `c/de ≤ 0.42`. **TCVN 11823 KHÔNG có điều kiện
    này** — đã soi cả 192 trang bản chính thức TCVN 11823-5:2017, chuỗi "0,42"
    không xuất hiện ở đâu. Thay vào đó Điều 7.2.1 phân loại mặt cắt theo biến
    dạng kéo thực `εt` (khống chế nén `εt ≤ 0.002`, khống chế kéo `εt ≥ 0.005`)
    và Điều 5.4.2.1 cho hệ số sức kháng thay đổi theo đó. Việc phân loại nằm ở
    `tension_control()`.

    **Cốt thép tối thiểu (Đ.7.3.3):**
      22TCN 272-05 : Mr ≥ min(1.2·Mcr, 1.33·Mu) với Mcr = fr·S
      TCVN 11823   : Mcr = γ₃[(γ₁·fr + γ₂·fcpe)·Sc − Mdnc(Sc/Snc − 1)]
    Lát cắt 1 m là tiết diện liền khối nên Sc = Snc, số hạng Mdnc triệt tiêu.
    """
    S = b * h ** 2 / 6.0 / 1e9          # m³ — mô đun tiết diện, Sc = Snc
    fr_kpa = mat.fr * 1000.0
    vals = {'S': S, 'fr': mat.fr}

    if standard == '22TCN 272-05':
        Mcr = 1.2 * fr_kpa * S
        vals['công thức Mcr'] = '1.2·fr·S'
        c_de = flex.values['c'] / flex.values['de'] if flex.values['de'] else 0.0
        vals.update({'c/de': c_de, 'c/de_max': C_DE_MAX})
        max_ok = c_de <= C_DE_MAX + 1e-9
    else:
        Mcr = GAMMA_3 * (GAMMA_1 * fr_kpa + GAMMA_2 * fcpe * 1000.0) * S
        vals['công thức Mcr'] = 'γ₃(γ₁·fr + γ₂·f_cpe)·S'
        max_ok = True           # TCVN không có giới hạn c/de; xem tension_control()

    need = min(Mcr, 1.33 * abs(forces.Mu)) if forces.Mu else Mcr
    vals.update({'Mcr': Mcr, '1.33Mu': 1.33 * abs(forces.Mu)})

    return CheckResult(
        'Giới hạn cốt thép', vals,
        demand=need, capacity=flex.capacity,
        ok=max_ok and flex.capacity >= need - 1e-9,
    )


def tension_control(h, flex, rebar, mat, tendon=None, phi_cap=0.9) -> dict:
    """Phân loại mặt cắt theo biến dạng kéo thực (TCVN 11823-5 Đ.7.2.1).

        εt = εc·(dt − c)/c   với εc = 0.003, dt = thớ cốt thép chịu kéo xa nhất

    Đ.5.4.2.1 cho hệ số sức kháng uốn: khống chế kéo thì 0.90 (BTCT thường) hoặc
    **1.00** (BTCT dự ứng lực); khống chế nén thì 0.75; ở giữa nội suy tuyến
    tính từ 0.75 lên giá trị khống chế kéo.

    `phi_cap` chặn trên giá trị khống chế kéo. **VuPQ chốt giữ 0.90 kể cả cho
    tiết diện dự ứng lực** thay vì lấy 1.00 theo tiêu chuẩn — thiên về an toàn,
    sức kháng uốn thấp hơn 11%. Đừng tự nâng lên 1.00.
    """
    tendon = tendon or Tendon()
    c = flex.values.get('c', 0.0)
    dt = max(h - rebar.cover, tendon.dp or 0.0)
    if c <= 0 or dt <= 0:
        return {'εt': None, 'loại': 'chưa nhập cốt thép', 'φ': phi_cap}

    eps_t = EPS_C * (dt - c) / c
    if eps_t >= EPS_TL:
        kind, phi = 'khống chế kéo', phi_cap
    elif eps_t <= EPS_CL:
        kind, phi = 'khống chế nén', PHI_COMPRESSION
    else:
        t = (eps_t - EPS_CL) / (EPS_TL - EPS_CL)
        kind = 'vùng chuyển tiếp'
        phi = PHI_COMPRESSION + t * (phi_cap - PHI_COMPRESSION)
    return {'εt': eps_t, 'loại': kind, 'φ': phi, 'dt': dt}


# ─────────────────────────────────────────────────────
# 3. Kiểm toán nứt
# ─────────────────────────────────────────────────────

def crack(h, forces, rebar, mat, standard='TCVN 11823', gamma_e=1.0, b=1000.0,
          tendon=None, skip_if_uncracked=True):
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

    # Đ.7.3.4 chỉ kiểm nứt khi ứng suất kéo ở TTGH Sử dụng vượt 80% cường độ
    # chịu kéo do uốn. Dưới ngưỡng đó tiết diện chưa nứt, không có gì để kiểm.
    f_ten = abs(forces.Mser) * 1e6 / (b * h * h / 6.0)      # MPa, tiết diện nguyên
    if skip_if_uncracked and f_ten <= CRACK_TRIGGER * mat.fr:
        return CheckResult(
            'Kiểm toán nứt',
            {'f_kéo': f_ten, 'ngưỡng': CRACK_TRIGGER * mat.fr},
            applicable=False,
            note=f'ứng suất kéo {f_ten:.2f} ≤ 80% fr = '
                 f'{CRACK_TRIGGER * mat.fr:.2f} MPa — chưa nứt')

    n = mat.Es / mat.Ec
    m = n * As / (b * ds)
    k = math.sqrt(m * m + 2 * m) - m
    j = 1.0 - k / 3.0
    fs = abs(forces.Mser) * 1e6 / (As * j * ds)     # MPa
    # Đ.7.3.4: fss dùng trong công thức cự ly không vượt quá 0.60 fy
    fss = min(fs, 0.60 * mat.fy)

    dc = rebar.cover
    vals = {'n': n, 'm': m, 'k': k, 'j': j, 'fs': fs, 'fss': fss,
            '0.6fy': 0.60 * mat.fy, 'dc': dc, 'f_kéo': f_ten}

    if standard == '22TCN 272-05':
        n_bar = b / rebar.spacing if rebar.spacing else 1.0
        A_eff = 2.0 * dc * b / n_bar if n_bar else 0.0
        fsa = min(Z_22TCN / (dc * A_eff) ** (1 / 3), 0.6 * mat.fy) if A_eff else 0.0
        vals.update({'A': A_eff, 'Z': Z_22TCN, 'fsa': fsa, '0.6fy': 0.6 * mat.fy})
        return CheckResult('Kiểm toán nứt', vals, demand=fs, capacity=fsa,
                           ok=fs <= fsa + 1e-9)

    bs = 1.0 + dc / (0.7 * (h - dc)) if h > dc else 1.0
    s_max = 123000.0 * gamma_e / (bs * fss) - 2.0 * dc if fss else float('inf')
    vals.update({'βs': bs, 'γe': gamma_e, 's_max': s_max, 's': rebar.spacing})
    return CheckResult('Kiểm toán nứt', vals,
                       demand=rebar.spacing, capacity=s_max,
                       ok=rebar.spacing <= s_max + 1e-9)


# ─────────────────────────────────────────────────────
# 4. Kiểm toán cắt — MCFT
# ─────────────────────────────────────────────────────
# Bảng 4 và Bảng 5 của TCVN 11823-5:2017 (trang 70), gõ từ bản chính thức ở
# H:\VUPQ\Tai_lieu_ky_thuat\01_TieuChuan. Cột là εx×1000; hàng là vu/f'c
# (Bảng 4) hoặc sxe mm (Bảng 5). Mỗi ô là (θ°, β).
#
# Bảng 4 đối chiếu verbatim với engine đã dùng thật của kcpd
# (Modeling_Bridge_by_RM/kcpd/t150_pilecap_check.py, port từ Cal_KCPD) — khớp.
# Bảng 5 đối chiếu bằng cách nội suy lại chính bốn điểm của file mẫu S1 và khớp
# tới 4 chữ số thập phân: A 26.2870/5.2427 so với 26.2869/5.2427; B, E, G tương
# tự. Đó là bằng chứng file mẫu dùng phương pháp (b) của TCVN hiện hành, không
# phải quy phạm cũ.
_EX_T4 = [-0.20, -0.10, -0.05, 0.0, 0.125, 0.25, 0.50, 0.75, 1.00]
_VU_T4 = [0.075, 0.100, 0.125, 0.150, 0.175, 0.200, 0.225, 0.250]
_T4 = {
    0.075: [(22.3, 6.32), (20.4, 4.75), (21.0, 4.10), (21.8, 3.75), (24.3, 3.24),
            (26.6, 2.94), (30.5, 2.59), (33.7, 2.38), (36.4, 2.23)],
    0.100: [(18.1, 3.79), (20.4, 3.38), (21.4, 3.24), (22.5, 3.14), (24.9, 2.91),
            (27.1, 2.75), (30.8, 2.50), (34.0, 2.32), (36.7, 2.18)],
    0.125: [(19.9, 3.18), (21.9, 2.99), (22.8, 2.94), (23.7, 2.87), (25.9, 2.74),
            (27.9, 2.62), (31.4, 2.42), (34.4, 2.26), (37.0, 2.13)],
    0.150: [(21.6, 2.88), (23.3, 2.79), (24.2, 2.78), (25.0, 2.72), (26.9, 2.60),
            (28.8, 2.52), (32.1, 2.36), (34.9, 2.21), (37.3, 2.08)],
    0.175: [(23.2, 2.73), (24.7, 2.66), (25.5, 2.65), (26.2, 2.60), (28.0, 2.52),
            (29.7, 2.44), (32.7, 2.28), (35.2, 2.14), (36.8, 1.96)],
    0.200: [(24.7, 2.63), (26.1, 2.59), (26.7, 2.52), (27.4, 2.51), (29.0, 2.43),
            (30.6, 2.37), (32.8, 2.14), (34.5, 1.94), (36.1, 1.79)],
    0.225: [(26.1, 2.53), (27.3, 2.45), (27.9, 2.42), (28.5, 2.40), (30.0, 2.34),
            (30.8, 2.14), (32.3, 1.86), (34.0, 1.73), (35.7, 1.64)],
    0.250: [(27.5, 2.39), (28.6, 2.39), (29.1, 2.33), (29.7, 2.33), (30.6, 2.12),
            (31.3, 1.93), (32.8, 1.70), (34.3, 1.58), (35.8, 1.50)],
}
_EX_T5 = [-0.20, -0.10, -0.05, 0.0, 0.125, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00]
_SXE_T5 = [130, 250, 380, 500, 750, 1000, 1500, 2000]
_T5 = {
    130: [(25.4, 6.36), (25.5, 6.06), (25.9, 5.56), (26.4, 5.15), (27.7, 4.41),
          (28.9, 3.91), (30.9, 3.26), (32.4, 2.86), (33.7, 2.58), (35.6, 2.21), (37.2, 1.96)],
    250: [(27.6, 5.78), (27.6, 5.78), (28.3, 5.38), (29.3, 4.89), (31.6, 4.05),
          (33.5, 3.52), (36.3, 2.88), (38.4, 2.50), (40.1, 2.23), (42.7, 1.88), (44.7, 1.65)],
    380: [(29.5, 5.34), (29.5, 5.34), (29.7, 5.27), (31.1, 4.73), (34.1, 3.82),
          (36.5, 3.28), (39.9, 2.64), (42.4, 2.26), (44.4, 2.01), (47.4, 1.68), (49.7, 1.46)],
    500: [(31.2, 4.99), (31.2, 4.99), (31.2, 4.99), (32.3, 4.61), (36.0, 3.65),
          (38.8, 3.09), (42.7, 2.46), (45.5, 2.09), (47.6, 1.85), (50.9, 1.52), (53.4, 1.31)],
    750: [(34.1, 4.46), (34.1, 4.46), (34.1, 4.46), (34.2, 4.43), (38.9, 3.39),
          (42.3, 2.82), (46.9, 2.19), (50.1, 1.84), (52.6, 1.60), (56.3, 1.30), (59.0, 1.10)],
    1000: [(36.6, 4.06), (36.6, 4.06), (36.6, 4.06), (36.6, 4.06), (41.2, 3.20),
           (45.0, 2.62), (50.2, 2.00), (53.7, 1.66), (56.3, 1.43), (60.2, 1.14), (63.0, 0.95)],
    1500: [(40.8, 3.50), (40.8, 3.50), (40.8, 3.50), (40.8, 3.50), (44.5, 2.92),
           (49.2, 2.32), (55.1, 1.72), (58.9, 1.40), (61.8, 1.18), (65.8, 0.92), (68.6, 0.75)],
    2000: [(44.3, 3.10), (44.3, 3.10), (44.3, 3.10), (44.33, 3.10), (47.1, 2.71),
           (52.3, 2.11), (58.7, 1.52), (62.8, 1.21), (65.7, 1.01), (69.7, 0.76), (72.4, 0.62)],
}


def _bounds(v, arr):
    """Cặp chỉ số kẹp giá trị v trong dãy tăng arr."""
    if v <= arr[0]:
        return 0, 0
    if v >= arr[-1]:
        return len(arr) - 1, len(arr) - 1
    for i in range(len(arr) - 1):
        if arr[i] <= v <= arr[i + 1]:
            return i, i + 1
    return len(arr) - 2, len(arr) - 1


def _interp2(table, rows, cols, row_val, col_val):
    """Nội suy hai chiều (θ, β) trong Bảng 4/Bảng 5."""
    rv = min(max(row_val, rows[0]), rows[-1])
    cv = min(max(col_val, cols[0]), cols[-1])
    j0, j1 = _bounds(rv, rows)
    i0, i1 = _bounds(cv, cols)
    tc = 0.0 if i1 == i0 else (cv - cols[i0]) / (cols[i1] - cols[i0])
    tr = 0.0 if j1 == j0 else (rv - rows[j0]) / (rows[j1] - rows[j0])
    out = []
    for k in (0, 1):
        lo = table[rows[j0]][i0][k] + tc * (table[rows[j0]][i1][k] - table[rows[j0]][i0][k])
        hi = table[rows[j1]][i0][k] + tc * (table[rows[j1]][i1][k] - table[rows[j1]][i0][k])
        out.append(lo + tr * (hi - lo))
    return out[0], out[1]


def av_min(mat, b, spacing):
    """Cốt đai tối thiểu, Đ.8.2.5: Av_min = 0.083·√f'c·bv·s/fy (mm²)."""
    if spacing <= 0:
        return float('inf')
    return 0.083 * math.sqrt(mat.fc) * b * spacing / mat.fy


def shear(h, forces, rebar, mat, flex, tendon=None, phi=0.9, b=1000.0,
          method='bảng'):
    """Vu ≤ Vr = φ·Vn (TCVN 11823-5 Đ.8.3.3 và 8.3.4.2).

        dv  = max(de − a/2, 0.9·de, 0.72·h)          — Đ.8.2.9
        Mu  không lấy nhỏ hơn Vu·dv                   — Đ.8.3.4.2
        Vc  = 0.083·β·√f'c·bv·dv                      — pt. 74
        Vs  = Av·fy·dv·cotθ/s                         — pt. 75
        Vn  = min(Vc + Vs, 0.25·f'c·bv·dv)            — pt. 72 và 73

    β, θ theo một trong hai phương pháp tổng quát mà Đ.8.3.4.2 cho dùng ngang
    hàng — xem `SHEAR_METHODS`. Chọn bảng theo lượng cốt đai so với Av_min: đủ
    thì Bảng 4 (tra theo vu/f'c), thiếu thì Bảng 5 (tra theo sxe).

    Lặp θ vì εx phụ thuộc cotθ: khởi đầu 34.3°, tối đa 20 vòng, hội tụ khi
    |Δθ| < 1e-3 — cùng cách với engine kcpd đã dùng thật cho bệ và mũ trụ.
    """
    if method not in SHEAR_METHODS:
        raise ValueError(f'phương pháp cắt không nhận: {method!r}; '
                         f'chọn một trong {SHEAR_METHODS}')

    tendon = tendon or Tendon()
    As = rebar.As(b)
    de = flex.values.get('de') or (h - rebar.cover)
    a = flex.values.get('a', 0.0)
    dv = max(de - a / 2.0, 0.9 * de, 0.72 * h)

    Ap = tendon.Ap
    fpo = 0.7 * mat.fpu if Ap else 0.0
    den_ax = mat.Es * As + mat.Ep * Ap
    if den_ax <= 0:
        return CheckResult('Kiểm toán cắt', {'dv': dv}, applicable=False,
                           note='chưa nhập cốt thép')

    # Mu không lấy nhỏ hơn Vu·dv (Đ.8.3.4.2)
    Mu_eff = max(abs(forces.Mu) * 1e6, abs(forces.Vu) * 1e3 * dv)   # N·mm
    Vu_N = abs(forces.Vu) * 1e3

    s_stirrup = rebar.Av_spacing or rebar.spacing
    Av_min = av_min(mat, b, s_stirrup)
    enough = rebar.Av >= Av_min

    # sx = giá trị nhỏ hơn của dv hoặc cự ly lớp cốt thép kiểm soát nứt (Đ.8.3.4.2)
    sx = min(dv, s_stirrup)

    if method == 'công thức':
        # Phương pháp (a): pt. 77–79; sxe chặn 294…2000 (pt. 81)
        # pt. 80. Trang 65: âm thì "coi giá trị bằng không HOẶC tính lại với
        # mẫu thức thay bằng (Es·As + Ep·Aps + Ec·Act)". Lấy 0 — chọn thiên về
        # an toàn trong hai cách mà tiêu chuẩn cho.
        eps = max((Mu_eff / dv + Vu_N - Ap * fpo) / den_ax, 0.0)
        eps = min(eps, 6.0e-3)
        sxe = min(max(sx * 35.0 / (AGG_SIZE + 16.0), 294.0), 2000.0)
        beta = 4.8 / (1 + 750 * eps)
        if not enough:
            beta *= 51.0 / (39.0 + sxe)
        theta = 29.0 + 3500.0 * eps
    else:
        # Phương pháp (b): Bảng 4/Bảng 5, lặp θ. pt. 85 chỉ chặn TRÊN 2000 —
        # Bảng 5 có hàng ≤130 nên không có chặn dưới 294 như phương pháp (a).
        sxe = min(sx * 35.0 / (AGG_SIZE + 16.0), 2000.0)
        vu_ratio = Vu_N / (phi * dv * b) / mat.fc
        # Ac = diện tích bê tông phía chịu kéo do uốn; Đ.8.3.4.2 lấy phía chịu
        # kéo bằng NỬA chiều cao mặt cắt chứa vùng kéo (trang 67).
        Ac = 0.5 * h * b
        eps_cap = 0.001 if enough else 0.002        # pt. 82 / pt. 83
        theta, beta, eps = 34.3, 0.0, 0.0
        for _ in range(20):
            cot = 1.0 / math.tan(math.radians(theta))
            num = Mu_eff / dv + 0.5 * Vu_N * cot - Ap * fpo
            # pt. 82 (đủ cốt đai) dùng 2(Es·As + Ep·Ap); pt. 83 (thiếu) dùng
            # (Es·As + Ep·Ap). Giá trị ban đầu không nên vượt eps_cap.
            eps = min(num / ((2.0 if enough else 1.0) * den_ax), eps_cap)
            if eps < 0:
                # pt. 84: âm thì tính lại với mẫu 2(Ec·Ac + Es·As + Ep·Ap).
                # KHÔNG lấy 0 như phương pháp (a) — Đ.8.3.4.2 chỉ định pt. 84.
                eps = num / (2.0 * (mat.Ec * Ac + den_ax))
            if enough:
                th_new, beta = _interp2(_T4, _VU_T4, _EX_T4, vu_ratio, eps * 1000.0)
            else:
                th_new, beta = _interp2(_T5, _SXE_T5, _EX_T5, sxe, eps * 1000.0)
            if abs(th_new - theta) < 1e-3:
                theta = th_new
                break
            theta = th_new

    Vc = 0.083 * beta * math.sqrt(mat.fc) * b * dv / 1e3        # kN
    Vs = 0.0
    if rebar.Av > 0 and s_stirrup > 0:
        Vs = rebar.Av * mat.fy * dv / math.tan(math.radians(theta)) / s_stirrup / 1e3
    Vn = min(Vc + Vs, 0.25 * mat.fc * b * dv / 1e3)
    Vr = phi * Vn

    return CheckResult(
        'Kiểm toán cắt',
        {'dv': dv, 'εx': eps, 'sx': sx, 'sxe': sxe, 'β': beta, 'θ': theta,
         'Av_min': Av_min, 'Vc': Vc, 'Vs': Vs, 'Vn': Vn,
         'phương pháp': method, 'bảng': 'Bảng 4' if enough else 'Bảng 5'},
        demand=abs(forces.Vu), capacity=Vr, ok=abs(forces.Vu) <= Vr + 1e-9,
        note='' if enough else 'cốt đai < Av_min → dùng Bảng 5',
    )


# ─────────────────────────────────────────────────────
# Gộp
# ─────────────────────────────────────────────────────

# KHÔNG còn miễn kiểm cắt cho bản mặt. Bản trước tôi viện điều khoản miễn cho
# bản thiết kế theo dải tương đương — soi lại thì KHÔNG CÓ căn cứ: điều loại trừ
# ở Đ.7.3.4 chỉ nhắc "bản mặt cầu thiết kế theo Điều 7.2 Phần 9", mà điều đó là
# THIẾT KẾ THEO KINH NGHIỆM, không phải phương pháp dải; quét cả AASHTO LRFD
# 2012 (1661 trang) cũng không có câu miễn kiểm cắt cho bản mặt.
#
# Và cũng không cần miễn nữa: dùng Bảng 5 (phương pháp (b), đúng cách file mẫu
# làm) thì bản mặt đạt chính đáng — β ≈ 5.24 thay vì 0.72 của công thức đóng.


def check_point(h, forces, rebar, mat, tendon=None, standard='TCVN 11823',
                phi_f=0.9, phi_v=0.9, gamma_e=1.0, fcpe=0.0, b=1000.0,
                shear_method='bảng') -> dict:
    """Chạy cả bốn nhóm cho MỘT mặt cắt kiểm toán, cộng phân loại tiết diện.

    Returns: {'flexure', 'limits', 'crack', 'shear', 'control', 'ok'} — 'ok' là
    AND của các nhóm **có áp dụng**. 'control' là kết quả `tension_control()`.
    """
    if standard not in STANDARDS:
        raise ValueError(f'tiêu chuẩn không nhận: {standard!r}; '
                         f'chọn một trong {STANDARDS}')

    fl = flexure(h, forces, rebar, mat, tendon, phi=phi_f, b=b)
    lim = reinforcement_limits(h, forces, fl, mat, standard, fcpe=fcpe, b=b)
    cr = crack(h, forces, rebar, mat, standard, gamma_e=gamma_e, b=b,
               tendon=tendon)
    sh = shear(h, forces, rebar, mat, fl, tendon, phi=phi_v, b=b,
               method=shear_method)
    ctrl = tension_control(h, fl, rebar, mat, tendon, phi_cap=phi_f)

    rs = (fl, lim, cr, sh)
    return {'flexure': fl, 'limits': lim, 'crack': cr, 'shear': sh,
            'control': ctrl, 'ok': all(r.ok for r in rs if r.applicable)}


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

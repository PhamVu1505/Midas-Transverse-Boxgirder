"""
Dò đường tự động hoá Midas Civil 2022 — bám vào phiên đang mở, gõ thật, ghi lại bản đồ.

Vì sao có công cụ này
─────────────────────
Midas Civil 2022 **không có đường tự động hoá chính thức nào**. Đã kiểm trên máy:

  · không COM — `MIDAS/Civil.Document` trong registry chỉ có `shell\\open\\command`,
    không CLSID, tức không có automation server
  · không API HTTP — chạy `CVLw.exe /API` thì app mở nhưng không nghe cổng nào;
    cờ đó chỉ có ở bản dựng riêng của MIDAS và ở Civil NX
  · kết quả nằm trong `.CA1/.CA3/.CA6` **nhị phân**; `.OUT` chỉ là nhật ký giải

Nên muốn tự động thì phải lái giao diện. Mà giao diện đổi theo phiên bản Midas,
theo ngôn ngữ, theo độ phân giải — nên **câu trả lời phải sinh lại được bằng một
lệnh**, không nằm rải rác trong đầu người. Đó là việc của file này: trả lời dứt
điểm bảy ẩn số A1–A7 rồi ghi ra `tools/midas_map.json` cho `src/midas_driver.py`
(giai đoạn sau) đọc.

Công cụ **bám vào phiên Midas đang chạy** — không mở, **không bao giờ đóng, không
bao giờ giết tiến trình**. Phiên đó là của người dùng.

Đọc `docs/MIDAS-AUTOMATION.md` để biết câu trả lời hiện tại của từng ẩn số.
"""

import argparse
import ctypes
import hashlib
import json
import os
import shutil
import sys
import time
from ctypes import wintypes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

MIDAS_DIR = r'C:\Program Files\MIDAS\midas Civil 2022'
ALIAS_FILE = os.path.join(MIDAS_DIR, 'User', 'shortcutkey.cmd')
LOP_CHINH = 'MidasGenMainFrmClass'
TEN_CMDLINE = 'CommandLine!'

DOI_CHUNG = os.path.join(ROOT, 'output', 'S1')
MCT_MAU = os.path.join(DOI_CHUNG, 'S1_frame.mct')
BF_MAU = os.path.join(DOI_CHUNG, 'Beam Force.xls')
TOPO_MAU = os.path.join(DOI_CHUNG, 'S1_topo.json')

# Mức trạng thái của mô hình trong Midas. Phép dò khai mức nó cần; bộ chạy đi
# tuần tự TRỐNG → CÓ_MÔ_HÌNH → ĐÃ_GIẢI vì không mở lại Midas được (phiên của
# người dùng), nên không thể dựng lại trạng thái sạch cho từng phép dò như
# `tools/check_gui.py` vẫn làm với cửa sổ Qt.
TRONG, CO_MO_HINH, DA_GIAI, BAT_KY = 'TRỐNG', 'CÓ_MÔ_HÌNH', 'ĐÃ_GIẢI', '—'


# ─────────────────────────────────────────────────────────────
# Tầng ctypes — khám phá và MỌI THỨ ĐỤNG BÀN PHÍM
#
# Vì sao không dùng pywinauto ở tầng này:
#   · duyệt cây một app 442 MB rất chậm và pywinauto có cache riêng, làm sai
#     lệch chính phép đo thời gian mà ẩn số A3 cần
#   · lúc Midas đang giải, message loop bận → `SendMessageW` chặn VÔ HẠN, không
#     traceback, phải giết bằng Task Manager. pywinauto không cho ép
#     `SMTO_ABORTIFHUNG`, còn ở đây thì bắt buộc
#   · né bộ gõ tiếng Việt cần đúng `WM_SETTEXT`, không phải mô phỏng phím
# ─────────────────────────────────────────────────────────────

u32 = ctypes.WinDLL('user32', use_last_error=True)
g32 = ctypes.WinDLL('gdi32', use_last_error=True)
imm = ctypes.WinDLL('imm32', use_last_error=True)

WM_NULL, WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH = 0x0000, 0x000C, 0x000D, 0x000E
WM_KEYDOWN, WM_KEYUP, WM_CHAR, WM_COMMAND = 0x0100, 0x0101, 0x0102, 0x0111
EM_SETSEL, EM_REPLACESEL = 0x00B1, 0x00C2
SMTO_ABORTIFHUNG = 0x0002
VK_RETURN, VK_F5, VK_ESCAPE = 0x0D, 0x74, 0x1B
SW_RESTORE = 9

# Dấu nhắc của ô dòng lệnh Midas. Đây là cách định vị ô lệnh — KHÔNG dùng tiêu
# đề thanh dock `CommandLine!`: tiêu đề đó là caption của khung chứa, `WM_SETTEXT`
# lên nó chỉ đổi tên khung chứ không gõ được chữ nào, mà lại làm chính công cụ
# này mất luôn mốc định vị ở lần chạy sau. Đã dẫm phải một lần.
DAU_NHAC = '>>'

_EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def _pid(hwnd):
    p = wintypes.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
    return p.value


def _lop(hwnd):
    b = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(hwnd, b, 256)
    return b.value


def _rect(hwnd):
    r = wintypes.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right - r.left, r.bottom - r.top)


def phan_hoi(hwnd, timeout_ms=1000) -> bool:
    """Message loop của cửa sổ có rảnh không.

    Đây vừa là phép kiểm "đã sẵn sàng nhận lệnh", vừa có thể chính là tín hiệu
    của ẩn số A3: lúc Midas đang giải thì nó KHÔNG phản hồi.
    """
    kq = ctypes.c_ulong()
    return bool(u32.SendMessageTimeoutW(hwnd, WM_NULL, 0, 0,
                                        SMTO_ABORTIFHUNG, timeout_ms,
                                        ctypes.byref(kq)))


def doc_chu(hwnd, timeout_ms=1000):
    """Chữ trong cửa sổ. Trả None khi app đang bận — đó là DỮ LIỆU, không phải lỗi."""
    n = ctypes.c_ulong()
    if not u32.SendMessageTimeoutW(hwnd, WM_GETTEXTLENGTH, 0, 0,
                                   SMTO_ABORTIFHUNG, timeout_ms, ctypes.byref(n)):
        return None
    b = ctypes.create_unicode_buffer(n.value + 2)
    kq = ctypes.c_ulong()
    if not u32.SendMessageTimeoutW(hwnd, WM_GETTEXT, n.value + 1,
                                   ctypes.cast(b, ctypes.c_void_p),
                                   SMTO_ABORTIFHUNG, timeout_ms, ctypes.byref(kq)):
        return None
    return b.value


def dat_chu(hwnd, s: str, timeout_ms=2000) -> bool:
    """Đặt chữ bằng `WM_SETTEXT` rồi ĐỌC LẠI đối chiếu.

    Không đi qua bàn phím nên bộ gõ tiếng Việt không chạm vào được. Giá trị trả
    về là **cảm biến IME**, không chỉ là kiểm tra cho có: trả False nghĩa là ô
    này không nhận `WM_SETTEXT` (phải đi đường khác) hoặc có thứ gì đó đã sửa
    chuỗi trên đường đi.
    """
    b = ctypes.create_unicode_buffer(s)
    kq = ctypes.c_ulong()
    if not u32.SendMessageTimeoutW(hwnd, WM_SETTEXT, 0,
                                   ctypes.cast(b, ctypes.c_void_p),
                                   SMTO_ABORTIFHUNG, timeout_ms, ctypes.byref(kq)):
        return False
    return doc_chu(hwnd) == s


def go_phim(hwnd, vk, giu_ms=30):
    """Gửi một phím THẲNG vào hwnd — không qua hàng đợi bàn phím hệ thống.

    Nhờ vậy không cướp tiêu điểm của người dùng và bộ gõ không xen vào.
    """
    u32.PostMessageW(hwnd, WM_KEYDOWN, vk, 0)
    time.sleep(giu_ms / 1000.0)
    u32.PostMessageW(hwnd, WM_KEYUP, vk, 0xC0000000)


def go_chu(hwnd, s: str, nhip_ms=5):
    """Gõ từng ký tự bằng `WM_CHAR` — vẫn không qua bàn phím hệ thống."""
    for ch in s:
        u32.PostMessageW(hwnd, WM_CHAR, ord(ch), 0)
        time.sleep(nhip_ms / 1000.0)


def liet_ke_cua_so(pid=None, goc=None) -> list:
    """Danh sách cửa sổ. `goc=None` → cửa sổ mức cao nhất; ngược lại → con của `goc`."""
    ra = []

    def _thu(h, _l):
        if pid is None or _pid(h) == pid:
            ra.append({
                'hwnd': h, 'lop': _lop(h), 'chu': doc_chu(h, 300) or '',
                'hien': bool(u32.IsWindowVisible(h)), 'rect': _rect(h),
                'pid': _pid(h),
            })
        return True

    cb = _EnumProc(_thu)
    if goc is None:
        u32.EnumWindows(cb, 0)
    else:
        u32.EnumChildWindows(goc, cb, 0)
    return ra


def tap_hwnd(pid) -> set:
    """Tập hwnd hiện có của một tiến trình — dùng để phát hiện cửa sổ vừa mọc."""
    ra = set()

    def _thu(h, _l):
        if _pid(h) == pid:
            ra.add(h)
        return True

    u32.EnumWindows(_EnumProc(_thu), 0)
    for h in list(ra):
        u32.EnumChildWindows(h, _EnumProc(_thu), 0)
    return ra


def cua_so_moi(truoc: set, pid, han_s=30, nhip=0.2):
    """Chờ một cửa sổ MỚI mọc ra, trả hwnd của nó.

    Không tìm theo tiêu đề hay lớp: bản Midas khác ngôn ngữ là gãy ngay, còn
    "cửa sổ vừa xuất hiện" thì đúng ở mọi bản. Cũng không `sleep` cứng — máy
    nhanh thì bắt nhầm hộp thoại trước đó, máy chậm thì trượt hẳn.
    """
    het = time.time() + han_s
    while time.time() < het:
        moi = [h for h in tap_hwnd(pid) - truoc if u32.IsWindowVisible(h)]
        # lấy cửa sổ mức cao nhất trong đám mới (hộp thoại), không lấy control con
        for h in moi:
            if _lop(h) in ('#32770',) or u32.GetParent(h) in (0, None):
                return h
        if moi:
            return moi[0]
        time.sleep(nhip)
    return None


def trang_thai_ime(hwnd) -> dict:
    """Trạng thái bộ gõ. CHỈ ĐỌC — không bao giờ tắt hộ người dùng.

    Unikey **không phải IME của Windows**: nó móc bàn phím ở tầng dưới, nên
    `ImmGetOpenStatus` có thể trả 0 dù Unikey đang bật. Vì vậy phải dò cả tiến
    trình. Đây đúng là loại chi tiết mà đoán sai thì kết luận "IME tắt" rồi yên
    tâm dùng mô phỏng phím — và hỏng âm thầm.
    """
    ctx = imm.ImmGetContext(hwnd)
    mo = bool(imm.ImmGetOpenStatus(ctx)) if ctx else False
    if ctx:
        imm.ImmReleaseContext(hwnd, ctx)
    ten = []
    try:
        import subprocess
        r = subprocess.run(['tasklist', '/fo', 'csv', '/nh'],
                           capture_output=True, text=True, timeout=15)
        for d in r.stdout.splitlines():
            t = d.split('","')[0].lstrip('"').lower()
            if 'unikey' in t or 'evkey' in t or 'vietkey' in t:
                ten.append(t)
    except Exception:
        pass
    return {'imm_mo': mo, 'bo_go_dang_chay': ten,
            'nguy_co': bool(mo or ten)}


def chup_cua_so(hwnd, path) -> bool:
    """Ảnh của một cửa sổ (kể cả bị che) qua `PrintWindow`."""
    try:
        from PIL import Image
    except ImportError:
        return False
    _l, _t, w, h = _rect(hwnd)
    if w <= 0 or h <= 0:
        return False
    hdc = u32.GetWindowDC(hwnd)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    g32.SelectObject(mdc, bmp)
    # 2 = PW_RENDERFULLCONTENT: cần cho cửa sổ vẽ bằng DirectComposition
    u32.PrintWindow(hwnd, mdc, 2)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [('biSize', wintypes.DWORD), ('biWidth', wintypes.LONG),
                    ('biHeight', wintypes.LONG), ('biPlanes', wintypes.WORD),
                    ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
                    ('biSizeImage', wintypes.DWORD),
                    ('biXPelsPerMeter', wintypes.LONG),
                    ('biYPelsPerMeter', wintypes.LONG),
                    ('biClrUsed', wintypes.DWORD), ('biClrImportant', wintypes.DWORD)]

    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.biWidth, bi.biHeight = w, -h          # âm = ảnh xuôi từ trên xuống
    bi.biPlanes, bi.biBitCount = 1, 32
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    g32.DeleteObject(bmp)
    g32.DeleteDC(mdc)
    u32.ReleaseDC(hwnd, hdc)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1).convert('RGB').save(path)
    return True


def sha(path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for k in iter(lambda: f.read(65536), b''):
            h.update(k)
    return h.hexdigest()


# ─────────────────────────────────────────────────────────────
# Tầng phiên — bám vào Midas ĐANG chạy
# ─────────────────────────────────────────────────────────────

class LoiDo(Exception):
    """Không trả lời được ẩn số. Khác với 'câu trả lời là không làm được'."""


class Phien:
    def __init__(self):
        self.pid = 0
        self.hwnd = 0
        self.hwnd_cmd = 0        # RichEdit mang dấu nhắc `>>`
        self.hwnd_ket_qua = 0    # RichEdit in kết quả, nằm ngay trên ô lệnh
        self.thu_muc = ''
        self.mct = ''
        self.ban_do = {}
        self.anh = False
        self.cho_sua_alias = False

    # ── tiện ích dùng chung cho các phép dò ──
    def con(self, loc=None) -> list:
        ds = liet_ke_cua_so(self.pid, self.hwnd)
        return [c for c in ds if loc(c)] if loc else ds

    def tieu_de(self):
        return doc_chu(self.hwnd) or ''

    def ghi(self, *khoa_gia_tri):
        """Ghi một phát hiện vào bản đồ: ghi('lenh', 'cach_go', 'WM_SETTEXT')."""
        *khoa, gia_tri = khoa_gia_tri
        d = self.ban_do
        for k in khoa[:-1]:
            d = d.setdefault(k, {})
        d[khoa[-1]] = gia_tri

    def chup(self, ten):
        if not self.anh:
            return ''
        p = os.path.join(ROOT, 'docs', 'midas-probe', f'{ten}.png')
        return p if chup_cua_so(self.hwnd, p) else ''


def bam_vao_midas() -> Phien:
    """Tìm phiên Midas đang mở. KHÔNG mở, KHÔNG đóng.

    Ba điều kiện, thiếu một là chưa sẵn sàng: cửa sổ chính đang hiện · tìm được
    ô `CommandLine!` · message loop rảnh. "Cửa sổ đã hiện" một mình thì chưa đủ
    — Midas hiện khung rồi mới dựng ribbon và dòng lệnh, gửi lệnh vào lúc đó là
    rơi vào hư không mà không báo gì.
    """
    chinh = [c for c in liet_ke_cua_so() if c['lop'] == LOP_CHINH and c['hien']]
    if not chinh:
        raise LoiDo('Không thấy Midas Civil 2022 nào đang mở. '
                    'Hãy mở Midas rồi chạy lại — công cụ này cố tình không tự mở app.')
    if len(chinh) > 1:
        raise LoiDo(f'Có {len(chinh)} cửa sổ Midas đang mở — đóng bớt để khỏi '
                    f'dò nhầm phiên.')

    p = Phien()
    p.hwnd = chinh[0]['hwnd']
    p.pid = chinh[0]['pid']
    if not phan_hoi(p.hwnd, 2000):
        raise LoiDo('Midas đang bận (message loop không phản hồi trong 2 s) — '
                    'đợi nó rảnh rồi chạy lại.')
    if u32.IsIconic(p.hwnd):
        raise LoiDo('Cửa sổ Midas đang thu nhỏ. Hộp thoại và UI Automation cần '
                    'cửa sổ hiện thật; toạ độ lúc thu nhỏ đều là −32000 nên mọi '
                    'phép đo hình học đều vô nghĩa. Khôi phục cửa sổ rồi chạy lại '
                    '(hoặc thêm --khoi-phuc-cua-so).')

    # Ô lệnh = RichEdit mang dấu nhắc `>>`. Định vị theo dấu nhắc chứ không theo
    # caption của khung chứa — xem chú thích ở DAU_NHAC.
    con = liet_ke_cua_so(p.pid, p.hwnd)
    o = [c for c in con
         if c['lop'].startswith('RichEdit') and (c['chu'] or '').startswith(DAU_NHAC)]
    if not o:
        raise LoiDo(
            f'Không thấy ô lệnh (RichEdit mang dấu nhắc {DAU_NHAC!r}). '
            f'Thanh Message Window có thể đang tắt — bật View › Message Window '
            f'rồi chạy lại.')
    p.hwnd_cmd = o[0]['hwnd']

    # Ô kết quả nằm ngay trên ô lệnh, cùng cha, cao hơn hẳn.
    cha = u32.GetParent(p.hwnd_cmd)
    anh_em = [c for c in liet_ke_cua_so(p.pid, cha)
              if c['lop'].startswith('RichEdit') and c['hwnd'] != p.hwnd_cmd]
    p.hwnd_ket_qua = anh_em[0]['hwnd'] if anh_em else 0
    return p


def tao_hop_cat(p: Phien):
    """Thư mục tạm cho mọi thứ Midas sinh ra.

    Midas ghi `.mcb/.CA*/.OUT` **cạnh file mct**. Mở thẳng `output/S1` là đè lên
    dữ liệu đối chứng ngay lần chạy đầu — mà đó chính là thứ dùng để chứng minh
    đường tự động cho ra đúng số.
    """
    p.thu_muc = os.path.join(os.environ.get('TEMP', '.'), 'midas_probe',
                             time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(p.thu_muc, exist_ok=True)
    p.mct = os.path.join(p.thu_muc, 'probe.mct')
    shutil.copy2(MCT_MAU, p.mct)
    return p.thu_muc


def chay_lenh(p: Phien, alias: str) -> bool:
    """Phát một lệnh qua ô dòng lệnh của Midas.

    Chèn bằng `EM_REPLACESEL` chứ không `WM_SETTEXT`: ô lệnh là RichEdit mang
    sẵn dấu nhắc `>>`, đặt đè cả ô sẽ xoá mất dấu nhắc — mà đó vừa là mốc Midas
    dùng, vừa là mốc công cụ này dùng để tìm lại ô ở lần chạy sau.
    """
    if not _chen_cuoi(p.hwnd_cmd, alias):
        return False
    go_phim(p.hwnd_cmd, VK_RETURN)
    time.sleep(0.5)
    return True


def doi_ket_qua(p: Phien, do_mau, han_s=600, nhip=0.5) -> list:
    """Lấy mẫu trạng thái theo nhịp, trả về CẢ BẢNG chứ không chỉ True/False.

    Ẩn số A3 hỏi "biết xong bằng dấu hiệu nào" — câu đó chỉ trả lời được khi
    nhìn diễn biến của nhiều nguồn cùng lúc, không phải bằng một lần kiểm.
    """
    bang, t0 = [], time.time()
    while time.time() - t0 < han_s:
        m = do_mau()
        m['t'] = round(time.time() - t0, 1)
        bang.append(m)
        if m.get('xong'):
            break
        time.sleep(nhip)
    return bang


# ─────────────────────────────────────────────────────────────
# Các phép dò
#
# Hợp đồng giống `kiem_*` của tools/check_gui.py: trả chuỗi ghi chú khi ĐẠT,
# `raise AssertionError('mô tả cụ thể')` khi HỎNG.
#
# QUY TẮC PHÂN ĐỊNH — dễ hiểu ngược nên nói rõ: phép dò HỎNG khi **không trả
# lời được** ẩn số, KHÔNG phải khi câu trả lời là "cách này không làm được".
# Ví dụ: kéo-thả không nạp được MCT nhưng hộp thoại Import ăn → ĐẠT, ghi chú
# "cách (a) trượt, dùng (b)". Cả hai cách đều trượt mới là HỎNG.
# ─────────────────────────────────────────────────────────────

def do_giu_nguyen_doi_chung(p):
    """`output/S1` không được đổi một byte nào.

    Bộ đếm, không phải lời hứa: lời hứa trong chú thích thì không ai kiểm được.
    """
    if not os.path.isdir(DOI_CHUNG):
        raise AssertionError(f'thiếu thư mục đối chứng {DOI_CHUNG}')
    hien = {f: sha(os.path.join(DOI_CHUNG, f))
            for f in sorted(os.listdir(DOI_CHUNG))
            if os.path.isfile(os.path.join(DOI_CHUNG, f))}
    cu = p.ban_do.get('_doi_chung')
    if cu is None:
        p.ban_do['_doi_chung'] = hien
        return f'ghi mốc {len(hien)} file'
    lech = [f for f in set(cu) | set(hien) if cu.get(f) != hien.get(f)]
    if lech:
        raise AssertionError('đối chứng bị sửa: ' + ', '.join(sorted(lech)[:5]))
    return f'{len(hien)} file còn nguyên'


do_giu_nguyen_doi_chung.muc = BAT_KY


def do_bam_vao_phien(p):
    """Bám được vào phiên đang mở và định vị các control gốc."""
    con = p.con()
    p.ghi('cua_so', 'chinh_lop', LOP_CHINH)
    p.ghi('cua_so', 'cmdline_lop', _lop(p.hwnd_cmd))
    p.ghi('cua_so', 'so_control_con', len(con))
    t0 = time.time()
    phan_hoi(p.hwnd, 1000)
    p.ghi('cua_so', 'ms_phan_hoi', int((time.time() - t0) * 1000))
    return (f'PID {p.pid} · hwnd {p.hwnd:#x} · {len(con)} control con · '
            f'ô lệnh lớp {_lop(p.hwnd_cmd)}')


do_bam_vao_phien.muc = BAT_KY


def do_tai_lieu_sach(p):
    """Cổng an toàn: chỉ chạy khi Midas chưa mở mô hình nào của người dùng.

    Import MCT đè lên tài liệu đang mở. Thà dừng và báo còn hơn làm mất việc
    đang dở — mất kiểu đó thì không hoàn lại được.

    Hai tiêu đề được coi là an toàn:
      `[Start Page]` — trang chào lúc mới mở, chưa có tài liệu nào
      `[Untitled]`   — tài liệu mới, chưa đặt tên
    Dấu `*` nghĩa là có thay đổi chưa lưu, kể cả trên tài liệu chưa đặt tên.
    """
    td = p.tieu_de()
    an_toan = ('[Start Page]', '[Untitled]')
    if not any(k in td for k in an_toan):
        raise AssertionError(
            f'Midas đang mở mô hình khác — tiêu đề {td!r}. '
            f'Hãy lưu rồi File › New trước khi dò.')
    if '*' in td:
        raise AssertionError(f'có thay đổi chưa lưu: {td!r}')
    p.ghi('cua_so', 'tieu_de_luc_bat_dau', td)
    return f'{td!r} — không có gì để mất'


do_tai_lieu_sach.muc = BAT_KY


def do_ime(p):
    """Bộ gõ tiếng Việt có đang bật không — quyết định cách gửi chuỗi."""
    tt = trang_thai_ime(p.hwnd_cmd)
    p.ghi('lenh', 'ime_nguy_co', tt['nguy_co'])
    p.ghi('lenh', 'bo_go', tt['bo_go_dang_chay'])
    if tt['nguy_co']:
        return (f'CÓ nguy cơ — {", ".join(tt["bo_go_dang_chay"]) or "IMM đang mở"}'
                f' ⇒ cấm mô phỏng phím, mọi chuỗi đi WM_SETTEXT')
    return 'không thấy bộ gõ nào — vẫn dùng WM_SETTEXT cho chắc'


do_ime.muc = BAT_KY


def do_alias_con_nguyen(p):
    """Alias `RtBF` (bảng Beam Force) phải còn trong file cấu hình của Midas.

    File này người dùng sửa được. Hôm nay có, mai dọn file thì mất — driver
    giai đoạn sau phải kiểm hash chứ không chạy mù.
    """
    if not os.path.exists(ALIAS_FILE):
        raise AssertionError(f'không thấy {ALIAS_FILE}')
    with open(ALIAS_FILE, encoding='utf-8', errors='replace') as f:
        noi_dung = f.read()
    p.ghi('lenh', 'alias_sha', sha(ALIAS_FILE))
    if 'RtBF' not in noi_dung:
        raise AssertionError('mất alias RtBF — bảng Beam Force phải mở bằng đường khác')
    co_perform = 'Perform Analysis' in noi_dung
    p.ghi('lenh', 'alias_beam_force', 'RtBF')
    p.ghi('lenh', 'co_alias_perform', co_perform)
    return (f'RtBF còn · alias Perform Analysis: '
            f'{"có" if co_perform else "KHÔNG (sẽ thử F5 / UIA)"}')


do_alias_con_nguyen.muc = BAT_KY


def _chen_cuoi(hwnd, s: str) -> bool:
    """Chèn chuỗi vào cuối RichEdit bằng `EM_REPLACESEL`.

    Không dùng `WM_SETTEXT` cho ô lệnh: nó **xoá cả dấu nhắc** `>>` mà Midas
    dùng làm mốc, và cũng là mốc định vị của chính công cụ này.
    """
    u32.SendMessageW(hwnd, EM_SETSEL, -1, -1)
    b = ctypes.create_unicode_buffer(s)
    u32.SendMessageW(hwnd, EM_REPLACESEL, 1, ctypes.cast(b, ctypes.c_void_p))
    return (doc_chu(hwnd) or '').endswith(s)


def do_command_line(p):
    """**A1** — gõ vào ô dòng lệnh bằng cách nào thì ăn, và bộ gõ có phá không.

    Thử với `Rd` (Redraw) — lệnh vô hại nhất trong bảng alias.

    Đã dẫm một lần và ghi lại để không ai dẫm nữa: `WM_SETTEXT` lên cửa sổ mang
    caption `CommandLine!` **có vẻ ăn** (đọc lại đúng chữ vừa đặt) nhưng đó chỉ
    là đổi tên khung dock — lệnh không chạy, và công cụ mất luôn mốc định vị.
    Bài học: "đọc lại đúng" chưa phải bằng chứng; phải thấy **tác dụng** ở nơi
    khác, ở đây là ô kết quả ngay trên ô lệnh.
    """
    cach, truoc_kq = {}, doc_chu(p.hwnd_ket_qua) if p.hwnd_ket_qua else ''

    # (a) EM_REPLACESEL — chèn vào cuối, giữ nguyên dấu nhắc
    cach['EM_REPLACESEL'] = _chen_cuoi(p.hwnd_cmd, 'Rd')
    doc_a = doc_chu(p.hwnd_cmd)

    # (b) WM_CHAR — đường ký tự, cũng là đường duy nhất bộ gõ có thể phá
    u32.SendMessageW(p.hwnd_cmd, EM_SETSEL, -1, -1)
    go_chu(p.hwnd_cmd, 'Rd')
    time.sleep(0.2)
    doc_b = doc_chu(p.hwnd_cmd)
    cach['WM_CHAR'] = (doc_b or '').endswith('RdRd') or (doc_b or '') != doc_a

    p.ghi('lenh', 'cach_thu', cach)
    p.ghi('lenh', 'doc_lai_em_replacesel', doc_a)
    p.ghi('lenh', 'doc_lai_wm_char', doc_b)

    an = [k for k, v in cach.items() if v]
    if not an:
        raise AssertionError(
            f'không cách nào chèn được chữ vào ô lệnh — EM_REPLACESEL đọc lại '
            f'{doc_a!r}, WM_CHAR ra {doc_b!r}')
    p.ghi('lenh', 'cach_go', an[0])

    # Dọn ô rồi phát đúng một lệnh, và đòi TÁC DỤNG ở ô kết quả.
    u32.SendMessageW(p.hwnd_cmd, EM_SETSEL, 0, -1)
    b = ctypes.create_unicode_buffer(DAU_NHAC)
    u32.SendMessageW(p.hwnd_cmd, EM_REPLACESEL, 1, ctypes.cast(b, ctypes.c_void_p))
    _chen_cuoi(p.hwnd_cmd, 'Rd')
    go_phim(p.hwnd_cmd, VK_RETURN)
    time.sleep(0.8)
    sau_o = doc_chu(p.hwnd_cmd)
    sau_kq = doc_chu(p.hwnd_ket_qua) if p.hwnd_ket_qua else ''
    p.ghi('lenh', 'o_sau_enter', sau_o)
    p.ghi('lenh', 'ket_qua_doi', sau_kq != truoc_kq)

    if sau_kq == truoc_kq and sau_o == doc_a:
        raise AssertionError(
            f'chèn được chữ nhưng Enter không chạy lệnh — ô vẫn {sau_o!r}, ô '
            f'kết quả không đổi. Cần thử SetFocus rồi SendInput, hoặc gửi '
            f'WM_COMMAND thẳng cho cửa sổ chính.')

    ghi_chu = f'chèn được bằng: {", ".join(an)} · sau Enter ô = {sau_o!r}'
    if sau_kq != truoc_kq:
        ghi_chu += ' · ô kết quả CÓ đổi ⇒ lệnh thật sự chạy'
    return ghi_chu


do_command_line.muc = TRONG


def _uia(p):
    """Cửa sổ chính dưới góc nhìn UI Automation.

    UIA ở đây **nhanh bất ngờ** — 0,2 s để nối, 0,3 s để liệt kê mức 1, khác hẳn
    nỗi lo ban đầu về ribbon BCGPro. Nhưng vẫn giữ nguyên tắc: chỉ hỏi đúng nhánh
    cần, không bao giờ duyệt cả cây.
    """
    from pywinauto import Desktop
    if not getattr(p, '_uia_w', None):
        p._uia_w = Desktop(backend='uia').window(handle=p.hwnd)
    return p._uia_w


def _thanh_ung_dung(p):
    """`ToolBar` không tên ở mức 1 — chứa `Application menu` và `Ribbon Tabs`."""
    for c in _uia(p).children():
        ei = c.element_info
        if ei.control_type == 'ToolBar' and not ei.name.strip():
            return c
    raise AssertionError('không thấy thanh chứa Application menu')


def _bam_chuoi_menu(p, *ten_muc, cho=1.6):
    """Bấm lần lượt một chuỗi mục menu, trả về các hwnd mới mọc ra.

    Dùng `click_input()` chứ không `invoke()`: submenu của BCGPro chỉ bung ra khi
    có thao tác chuột thật — `invoke()` chạy không lỗi nhưng không mở gì, và
    "không lỗi" thì rất dễ bị đọc nhầm thành "đã mở".
    """
    from pywinauto import Desktop
    truoc = tap_hwnd(p.pid)
    goc = _thanh_ung_dung(p)
    muc = [c for c in goc.children() if c.element_info.name == ten_muc[0]]
    if not muc:
        raise AssertionError(f'không thấy {ten_muc[0]!r} trên thanh ứng dụng')
    muc[0].click_input()
    time.sleep(cho)

    for ten in ten_muc[1:]:
        moi = [h for h in tap_hwnd(p.pid) - truoc if u32.IsWindowVisible(h)]
        tim = None
        for h in moi:
            try:
                for k in Desktop(backend='uia').window(handle=h).descendants():
                    if k.element_info.name == ten:
                        tim = k
                        break
            except Exception:
                continue
            if tim:
                break
        if tim is None:
            raise AssertionError(f'không thấy mục {ten!r} sau khi mở '
                                 f'{" › ".join(ten_muc[:ten_muc.index(ten)])}')
        tim.click_input()
        time.sleep(cho)

    return [h for h in tap_hwnd(p.pid) - truoc if u32.IsWindowVisible(h)]


def dong_menu(p, lan=4):
    """Gửi ESC vài lần — không bao giờ để menu mở lại cho người dùng."""
    for _ in range(lan):
        go_phim(p.hwnd, VK_ESCAPE)
        time.sleep(0.3)


def do_nap_mct(p):
    """**A4** — nạp file MCT vào phiên đang mở.

    Đường đã dò ra: `Application menu` › `Import` › `MIDAS/Civil MCT File...`.
    Không đi bằng alias được — hệ alias của Midas chỉ phủ các thẻ ribbon
    (Results, View, Load, Analysis…), **không mục nào trỏ tới menu File**.
    Kéo-thả cũng không: Midas dùng OLE drop target nên bỏ qua `WM_DROPFILES`.

    **Phải `New Project...` trước.** Ở màn hình Start Page, toàn bộ submenu
    Import bị khoá xám — bấm vào không có gì xảy ra và cũng không báo lỗi, nên
    nhìn từ phía mã thì y hệt "đã bấm xong". Chỉ ảnh chụp mới lộ ra. Đây đúng
    loại bẫy mà giai đoạn 0 sinh ra để bắt.
    """
    tao_hop_cat(p)
    p.ghi('nap_mct', 'cach',
          'uia:Application menu › New Project… rồi › Import › MIDAS/Civil MCT File...')

    if '[Untitled]' not in p.tieu_de():
        _bam_chuoi_menu(p, 'Application menu', 'New Project...')
        for _ in range(20):
            time.sleep(0.5)
            if '[Untitled]' in p.tieu_de():
                break
        else:
            dong_menu(p)
            raise AssertionError(f'New Project… không tạo được tài liệu mới — '
                                 f'tiêu đề vẫn {p.tieu_de()!r}')
    truoc_td = p.tieu_de()

    try:
        moi = _bam_chuoi_menu(p, 'Application menu', 'Import',
                              'MIDAS/Civil MCT File...')
    except AssertionError:
        dong_menu(p)
        raise

    hop = [h for h in moi if _lop(h) == '#32770']
    if not hop:
        dong_menu(p)
        raise AssertionError(f'bấm hết chuỗi menu mà không có hộp thoại chọn file; '
                             f'cửa sổ mới: {[hex(h) for h in moi]}')
    h = hop[0]
    p.ghi('nap_mct', 'hop_thoai', doc_chu(h))
    p.chup('nap_mct_hop_thoai')

    # Ô tên file của common dialog. Đặt bằng WM_SETTEXT, không gõ phím: đường dẫn
    # đầy `\`, `_` và chữ hoa — đúng loại chuỗi mà bộ gõ tiếng Việt hay ăn mất.
    o = [c for c in liet_ke_cua_so(p.pid, h)
         if c['lop'] == 'Edit' and c['rect'][2] > 100]
    if not o:
        dong_menu(p)
        raise AssertionError('không thấy ô nhập tên file trong hộp thoại')
    if not dat_chu(o[0]['hwnd'], p.mct):
        dong_menu(p)
        raise AssertionError('đặt đường dẫn vào ô tên file không ăn')
    go_phim(o[0]['hwnd'], VK_RETURN)

    for _ in range(60):
        time.sleep(1)
        td = p.tieu_de()
        if td != truoc_td and '[Start Page]' not in td:
            p.ghi('nap_mct', 'tieu_de_sau_khi_nap', td)
            return f'nạp xong — tiêu đề {td!r}'
    dong_menu(p)
    raise AssertionError(f'60 s sau khi Enter mà tiêu đề vẫn {p.tieu_de()!r}')


do_nap_mct.muc = TRONG


def do_kich_hoat_phan_tich(p):
    """**A2** — Perform Analysis kích hoạt bằng gì.

    Chỉ ĐẠT khi thấy `.OUT` **lớn lên**. "Không thấy báo lỗi" không phải bằng
    chứng — F5 ở nhiều bản Midas là Redraw, bấm xong trông y như đã chạy.
    """
    out = os.path.join(p.thu_muc, 'probe.OUT')
    truoc = os.path.getsize(out) if os.path.exists(out) else -1

    go_phim(p.hwnd, VK_F5)
    time.sleep(3)
    sau = os.path.getsize(out) if os.path.exists(out) else -1
    if sau > truoc:
        p.ghi('phan_tich', 'cach_kich_hoat', 'F5')
        return f'F5 ăn — probe.OUT {truoc} → {sau} byte'

    raise AssertionError(
        f'F5 không làm probe.OUT đổi ({truoc} → {sau}). Cần thử UIA ribbon '
        f'Analysis › Perform, hoặc thêm alias — chạy với --cho-phep-sua-alias.')


do_kich_hoat_phan_tich.muc = CO_MO_HINH


def do_dau_hieu_xong(p):
    """**A3** — biết phân tích đã xong bằng dấu hiệu nào."""
    out = os.path.join(p.thu_muc, 'probe.OUT')

    def mau():
        co = os.path.getsize(out) if os.path.exists(out) else -1
        ca = len([f for f in os.listdir(p.thu_muc) if '.CA' in f.upper()])
        ranh = phan_hoi(p.hwnd, 500)
        return {'out': co, 'ca': ca, 'ranh': ranh, 'td': p.tieu_de()[:40],
                'xong': ranh and ca > 0}

    bang = doi_ket_qua(p, mau, han_s=300)
    p.ghi('phan_tich', 'bang_lay_mau', bang[-12:])
    if not bang or not bang[-1].get('xong'):
        raise AssertionError(f'quá hạn, chưa thấy dấu hiệu xong. Mẫu cuối: {bang[-1] if bang else "—"}')
    p.ghi('phan_tich', 'tin_hieu_xong',
          {'kieu': 'co_file_CA_va_message_loop_ranh', 'giay': bang[-1]['t']})
    return f'xong sau {bang[-1]["t"]} s · {bang[-1]["ca"]} file .CA · {len(bang)} mẫu'


do_dau_hieu_xong.muc = CO_MO_HINH


def _ta_hop_thoai(hwnd) -> dict:
    """Mô tả một hộp thoại. Dùng pywinauto vì đọc mục của SysListView32 liên
    tiến trình phải VirtualAllocEx + ReadProcessMemory từng mục — pywinauto đã
    làm đúng và đã được kiểm nghiệm, viết lại bằng ctypes là tự rước bug."""
    ra = {'hwnd': hwnd, 'lop': _lop(hwnd), 'tieu_de': doc_chu(hwnd) or '',
          'control': []}
    for c in liet_ke_cua_so(_pid(hwnd), hwnd):
        ra['control'].append({'lop': c['lop'], 'chu': c['chu'][:40],
                              'rect': c['rect'], 'hwnd': c['hwnd']})
    return ra


def do_hop_thoai_beam_force(p):
    """**A5** — hộp thoại chọn Load Case của bảng Beam Force."""
    truoc = tap_hwnd(p.pid)
    if not chay_lenh(p, 'RtBF'):
        raise AssertionError('không phát được lệnh RtBF vào ô dòng lệnh')
    h = cua_so_moi(truoc, p.pid, han_s=20)
    if h is None:
        raise AssertionError('gõ RtBF xong không có cửa sổ nào mọc ra')
    ta = _ta_hop_thoai(h)
    p.ghi('xuat', 'hop_thoai_chon_tai', ta['tieu_de'])
    p.ghi('xuat', 'control_chon_tai', ta['control'][:40])
    p.chup('beam_force_hop_thoai')
    lop = sorted({c['lop'] for c in ta['control']})
    return f'{ta["tieu_de"]!r} · {len(ta["control"])} control · lớp: {", ".join(lop[:6])}'


do_hop_thoai_beam_force.muc = DA_GIAI


def do_khong_con_hop_thoai_thua(p):
    """Cuối mỗi mức: danh sách cửa sổ đã về như đầu mức chưa."""
    thua = [h for h in tap_hwnd(p.pid) - p.ban_do.get('_hwnd_dau_muc', set())
            if u32.IsWindowVisible(h) and _lop(h) == '#32770']
    if thua:
        ten = [repr(doc_chu(h) or '') for h in thua[:4]]
        raise AssertionError(f'còn {len(thua)} hộp thoại chưa đóng: {", ".join(ten)}')
    return 'không hộp thoại thừa'


do_khong_con_hop_thoai_thua.muc = BAT_KY


PHEP_DO = [
    do_giu_nguyen_doi_chung,
    do_bam_vao_phien,
    do_tai_lieu_sach,
    do_ime,
    do_alias_con_nguyen,
    do_command_line,
    do_nap_mct,
    do_kich_hoat_phan_tich,
    do_dau_hieu_xong,
    do_hop_thoai_beam_force,
    do_khong_con_hop_thoai_thua,
    do_giu_nguyen_doi_chung,
]


# ─────────────────────────────────────────────────────────────
# Chạy
# ─────────────────────────────────────────────────────────────

def in_cay(p: Phien):
    """`--dump`: in cây cửa sổ, không đụng vào gì."""
    print(f'PID {p.pid} · hwnd chính {p.hwnd:#x} · {p.tieu_de()!r}\n')
    con = p.con()
    print(f'{len(con)} control con — những cái có chữ:')
    for c in con:
        if c['chu']:
            x, y, w, h = c['rect']
            print(f'  {c["lop"]:44s} {w:5d}×{h:<5d} {c["chu"][:46]!r}')
    print('\nThống kê lớp:')
    from collections import Counter
    for ten, n in Counter(c['lop'] for c in con).most_common(15):
        print(f'  {n:5d} × {ten}')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('--only', default='', help='chỉ chạy phép dò có tên chứa chuỗi này')
    ap.add_argument('--list', action='store_true', help='liệt kê phép dò rồi thoát')
    ap.add_argument('--dump', action='store_true', help='chỉ in cây cửa sổ, không đụng gì')
    ap.add_argument('--shot', action='store_true', help='chụp ảnh vào docs/midas-probe/')
    ap.add_argument('--ghi', action='store_true', help='ghi tools/midas_map.json')
    ap.add_argument('--cho-phep-sua-alias', action='store_true',
                    help='cho phép thêm alias vào shortcutkey.cmd (có sao lưu)')
    ap.add_argument('--giu-rac', action='store_true', help='không xoá thư mục tạm')
    ap.add_argument('--khoi-phuc-cua-so', action='store_true',
                    help='khôi phục cửa sổ Midas nếu đang thu nhỏ (sẽ cướp tiêu điểm)')
    args = ap.parse_args()

    if args.list:
        for f in PHEP_DO:
            if f.__name__ in [g.__name__ for g in PHEP_DO[:PHEP_DO.index(f)]]:
                continue
            print(f'  {f.__name__:28s} [{getattr(f, "muc", BAT_KY):10s}] '
                  f'{(f.__doc__ or "").strip().splitlines()[0]}')
        return 0

    if args.khoi_phuc_cua_so:
        for c in liet_ke_cua_so():
            if c['lop'] == LOP_CHINH and u32.IsIconic(c['hwnd']):
                u32.ShowWindow(c['hwnd'], SW_RESTORE)
                time.sleep(1.0)

    try:
        p = bam_vao_midas()
    except LoiDo as e:
        print(f'\n{e}\n')
        return 1

    p.anh = args.shot
    p.cho_sua_alias = args.cho_phep_sua_alias

    if args.dump:
        in_cay(p)
        return 0

    print(f'\nBám vào Midas: PID {p.pid} · {p.tieu_de()!r}')
    p.ban_do['_hwnd_dau_muc'] = tap_hwnd(p.pid)

    chay = [f for f in PHEP_DO if args.only.lower() in f.__name__.lower()]
    if not chay:
        print(f'Không phép dò nào khớp {args.only!r}')
        return 1

    dat = hong = 0
    muc_hien = None
    for f in chay:
        muc = getattr(f, 'muc', BAT_KY)
        if muc != muc_hien and muc != BAT_KY:
            print(f'\n── mức {muc} ' + '─' * (46 - len(muc)))
            muc_hien = muc
        try:
            ghi_chu = f(p) or ''
            dat += 1
            print(f'  ĐẠT   {f.__name__:28s} {ghi_chu}')
        except AssertionError as e:
            hong += 1
            print(f'  HỎNG  {f.__name__:28s} {e}')
            break            # ẩn số sau phụ thuộc ẩn số trước — chạy tiếp là vô nghĩa
        except Exception as e:
            hong += 1
            print(f'  HỎNG  {f.__name__:28s} {type(e).__name__}: {e}')
            import traceback
            traceback.print_exc()
            break

    print(f'\n{dat} đạt · {hong} hỏng')

    ban_do = {k: v for k, v in p.ban_do.items() if not k.startswith('_')}
    print('\n── BẢN ĐỒ ' + '─' * 48)
    print(json.dumps(ban_do, ensure_ascii=False, indent=2)[:3000])
    if args.ghi:
        dich = os.path.join(ROOT, 'tools', 'midas_map.json')
        ban_do['midas'] = {'phien_ban': '2022 (9.0.0)', 'exe': MIDAS_DIR,
                           'ngay_do': time.strftime('%Y-%m-%d %H:%M')}
        with open(dich, 'w', encoding='utf-8') as f:
            json.dump(ban_do, f, ensure_ascii=False, indent=2, sort_keys=True)
        print(f'\nĐã ghi {dich}')
    else:
        print('\n(chạy lại với --ghi để lưu tools/midas_map.json)')

    if p.thu_muc and not args.giu_rac:
        shutil.rmtree(p.thu_muc, ignore_errors=True)
    elif p.thu_muc:
        print(f'Thư mục tạm giữ lại: {p.thu_muc}')

    return 1 if hong else 0


if __name__ == '__main__':
    sys.exit(main())

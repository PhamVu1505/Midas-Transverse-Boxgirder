"""
Điều khiển Midas Civil 2022: nạp MCT → chạy phân tích → xuất Beam Force.

    from src.midas_driver import MidasSession
    with MidasSession.attach() as s:
        s.import_mct(r'output\\S1\\S1_frame.mct')
        s.analyze()
        s.export_beam_force(r'output\\S1\\Beam Force_S1.xls')

Chạy thử một mặt cắt:
    python src/midas_driver.py output/S1/S1_frame.mct

Vì sao lái giao diện chứ không gọi API
──────────────────────────────────────
Midas Civil 2022 **không có** COM (`MIDAS/Civil.Document` trong registry chỉ có
`shell\\open\\command`, không CLSID) và **không có** API HTTP (`CVLw.exe /API`
không mở cổng nào — cờ đó chỉ có ở bản dựng riêng và ở Civil NX). Kết quả nằm
trong `.CA1/.CA3/.CA6` nhị phân, `.OUT` chỉ là nhật ký giải. Nên không còn đường
nào khác ngoài lái giao diện.

Toàn bộ công thức và cạm bẫy: `docs/MIDAS-AUTOMATION.md`.
Bản đồ máy đọc: `tools/midas_map.json`.

Ba ràng buộc, đừng gỡ
─────────────────────
1. **Bám vào phiên đang chạy, không tự mở, KHÔNG BAO GIỜ đóng hay giết Midas.**
   Phiên đó là của người dùng — họ có thể đang mở việc khác trong cùng app.
2. **Từ chối khi tài liệu không sạch.** Import MCT đè lên tài liệu đang mở; mất
   việc chưa lưu thì không hoàn lại được.
3. **Luôn `set_focus()` trước mọi cú bấm chuột.** `click_input()` bấm theo toạ độ
   MÀN HÌNH — Midas nằm dưới thì cú bấm rơi vào cửa sổ khác. Đã có lần bấm trúng
   trình soạn thảo đang mở.
"""

import ctypes
import os
import time
from ctypes import wintypes

LOP_CHINH = 'MidasGenMainFrmClass'
DAU_NHAC = '>>'
# Mốc "đã giải xong" trong file .OUT.
#
# KHÔNG dùng dòng tiêu đề khối — Midas in nó dưới dạng chữ giãn cách
# (`** O V E R A L L   T I M E   L O G   I N   S E C O N D **`), nên tìm chuỗi
# 'OVERALL TIME LOG' thì **không bao giờ khớp**. Đã mất hai lượt chạy 1800 giây
# vì đúng chỗ này, và thông báo lỗi lại đổ cho phân tích chưa xong trong khi nó
# đã xong từ lâu. Dòng dưới đây là chữ thường, luôn là dòng cuối file.
XONG = 'TOTAL ELAPSED TIME'
BIFF8 = bytes.fromhex('d0cf11e0a1b11ae1')

u32 = ctypes.WinDLL('user32', use_last_error=True)

WM_NULL, WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH = 0x0000, 0x000C, 0x000D, 0x000E
WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101
BM_CLICK = 0x00F5
LB_GETCOUNT, LB_GETSELCOUNT = 0x018B, 0x0190
SMTO_ABORTIFHUNG = 0x0002
VK_RETURN, VK_F5, VK_ESCAPE = 0x0D, 0x74, 0x1B

_EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


class MidasError(Exception):
    """Không lái được Midas. Thông điệp phải nói rõ người dùng cần làm gì."""


class _GTI(ctypes.Structure):
    _fields_ = [('cbSize', wintypes.DWORD), ('flags', wintypes.DWORD),
                ('hwndActive', wintypes.HWND), ('hwndFocus', wintypes.HWND),
                ('hwndCapture', wintypes.HWND), ('hwndMenuOwner', wintypes.HWND),
                ('hwndMoveSize', wintypes.HWND), ('hwndCaret', wintypes.HWND),
                ('rcCaret', wintypes.RECT)]


# ─────────────────────────────────────────────────────────────
# Lớp Win32 tối thiểu
#
# Không dùng pywinauto ở tầng này: lúc Midas đang giải thì message loop bận,
# `SendMessageW` chặn VÔ HẠN không traceback, phải giết bằng Task Manager.
# `SendMessageTimeoutW` + `SMTO_ABORTIFHUNG` là bắt buộc, mà pywinauto không cho
# ép cờ đó.
# ─────────────────────────────────────────────────────────────

def _lop(hwnd):
    b = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(hwnd, b, 256)
    return b.value


def _pid(hwnd):
    p = wintypes.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
    return p.value


def _rect(hwnd):
    r = wintypes.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right - r.left, r.bottom - r.top)


def _ranh(hwnd, ms=1000) -> bool:
    kq = ctypes.c_ulong()
    return bool(u32.SendMessageTimeoutW(hwnd, WM_NULL, 0, 0,
                                        SMTO_ABORTIFHUNG, ms, ctypes.byref(kq)))


def _doc(hwnd, ms=1000):
    """Chữ trong cửa sổ; None nghĩa là app đang bận — đó là dữ liệu, không phải lỗi."""
    n = ctypes.c_ulong()
    if not u32.SendMessageTimeoutW(hwnd, WM_GETTEXTLENGTH, 0, 0,
                                   SMTO_ABORTIFHUNG, ms, ctypes.byref(n)):
        return None
    b = ctypes.create_unicode_buffer(n.value + 2)
    kq = ctypes.c_ulong()
    if not u32.SendMessageTimeoutW(hwnd, WM_GETTEXT, n.value + 1,
                                   ctypes.cast(b, ctypes.c_void_p),
                                   SMTO_ABORTIFHUNG, ms, ctypes.byref(kq)):
        return None
    return b.value


def _dat(hwnd, s: str) -> bool:
    """Đặt chữ rồi ĐỌC LẠI đối chiếu.

    Đường dẫn đầy `\\`, `_` và chữ hoa — đúng loại chuỗi mà bộ gõ tiếng Việt hay
    ăn mất nếu đi qua bàn phím. `WM_SETTEXT` không phát sự kiện phím nào nên bộ
    gõ không chạm tới được. Đọc lại là để chắc, không phải cho có.
    """
    b = ctypes.create_unicode_buffer(s)
    kq = ctypes.c_ulong()
    if not u32.SendMessageTimeoutW(hwnd, WM_SETTEXT, 0,
                                   ctypes.cast(b, ctypes.c_void_p),
                                   SMTO_ABORTIFHUNG, 2000, ctypes.byref(kq)):
        return False
    return _doc(hwnd) == s


def _phim(hwnd, vk, giu=0.03):
    u32.PostMessageW(hwnd, WM_KEYDOWN, vk, 0)
    time.sleep(giu)
    u32.PostMessageW(hwnd, WM_KEYUP, vk, 0xC0000000)


def _con(hwnd, pid=None):
    ra = []

    def _t(h, _l):
        if pid is None or _pid(h) == pid:
            ra.append({'hwnd': h, 'lop': _lop(h), 'chu': _doc(h, 300) or '',
                       'rect': _rect(h), 'hien': bool(u32.IsWindowVisible(h))})
        return True

    u32.EnumChildWindows(hwnd, _EnumProc(_t), 0)
    return ra


def _dinh(pid):
    """Mọi hwnd của một tiến trình — để phát hiện cửa sổ vừa mọc."""
    ra = set()

    def _t(h, _l):
        if _pid(h) == pid:
            ra.add(h)
        return True

    u32.EnumWindows(_EnumProc(_t), 0)
    for h in list(ra):
        u32.EnumChildWindows(h, _EnumProc(_t), 0)
    return ra


def _tieu_diem():
    g = _GTI()
    g.cbSize = ctypes.sizeof(_GTI)
    tid = u32.GetWindowThreadProcessId(u32.GetForegroundWindow(), None)
    return g.hwndFocus if u32.GetGUIThreadInfo(tid, ctypes.byref(g)) else 0


# ─────────────────────────────────────────────────────────────

class MidasSession:
    """Một phiên làm việc với Midas ĐANG CHẠY."""

    def __init__(self, hwnd, pid, hwnd_cmd):
        self.hwnd = hwnd
        self.pid = pid
        self.hwnd_cmd = hwnd_cmd
        self._uia = None
        self.log = print

    # ── vòng đời ──
    @classmethod
    def attach(cls) -> 'MidasSession':
        """Bám vào phiên Midas đang mở. Không tự mở app."""
        chinh = []

        def _t(h, _l):
            if u32.IsWindowVisible(h) and _lop(h) == LOP_CHINH:
                chinh.append(h)
            return True

        u32.EnumWindows(_EnumProc(_t), 0)
        if not chinh:
            raise MidasError('Không thấy Midas Civil 2022 nào đang mở. '
                             'Hãy mở Midas rồi chạy lại.')
        if len(chinh) > 1:
            raise MidasError(f'Có {len(chinh)} cửa sổ Midas đang mở — đóng bớt '
                             f'để khỏi lái nhầm phiên.')
        h = chinh[0]
        if u32.IsIconic(h):
            raise MidasError('Cửa sổ Midas đang thu nhỏ. Lúc đó mọi toạ độ đều '
                             'là −32000 nên không lái được — khôi phục rồi chạy lại.')
        if not _ranh(h, 2000):
            raise MidasError('Midas đang bận (không phản hồi trong 2 s) — đợi rồi chạy lại.')

        pid = _pid(h)
        o = [c for c in _con(h, pid)
             if c['lop'].startswith('RichEdit') and (c['chu'] or '').startswith(DAU_NHAC)]
        if not o:
            raise MidasError('Không thấy thanh Message Window (ô lệnh mang dấu '
                             'nhắc ">>") — bật View › Message Window rồi chạy lại.')
        return cls(h, pid, o[0]['hwnd'])

    def __enter__(self):
        return self

    def __exit__(self, *a):
        # KHÔNG đóng Midas. Chỉ dọn menu/hộp thoại do mình mở ra.
        self._esc()
        return False

    # ── tiện ích ──
    @property
    def tieu_de(self) -> str:
        return _doc(self.hwnd) or ''

    def _w(self):
        from pywinauto import Desktop
        if self._uia is None:
            self._uia = Desktop(backend='uia').window(handle=self.hwnd)
        return self._uia

    def _len_truoc(self):
        """Đưa Midas lên tiền cảnh — BẮT BUỘC trước mọi cú bấm chuột."""
        self._w().set_focus()
        time.sleep(0.6)

    def _esc(self, lan=3):
        for _ in range(lan):
            _phim(self.hwnd, VK_ESCAPE)
            time.sleep(0.3)

    def _thanh(self):
        """`ToolBar` không tên ở mức 1 — chứa Application menu và Ribbon Tabs."""
        for c in self._w().children():
            ei = c.element_info
            if ei.control_type == 'ToolBar' and not ei.name.strip():
                return c
        raise MidasError('không thấy thanh ứng dụng (ribbon) — giao diện Midas đã đổi?')

    def _cho_cua_so(self, truoc: set, han=30, lop=None):
        """Chờ cửa sổ MỚI mọc ra.

        Không tìm theo tiêu đề: bản Midas khác ngôn ngữ là gãy ngay. "Cửa sổ vừa
        xuất hiện" thì đúng ở mọi bản. Cũng không `sleep` cứng — máy nhanh thì
        bắt nhầm hộp thoại trước, máy chậm thì trượt.
        """
        het = time.time() + han
        while time.time() < het:
            moi = [h for h in _dinh(self.pid) - truoc if u32.IsWindowVisible(h)]
            if lop:
                moi = [h for h in moi if _lop(h) == lop]
            if moi:
                return moi[0]
            time.sleep(0.2)
        return None

    def _bam_chuoi(self, *ten, cho=1.6):
        """Bấm lần lượt một chuỗi mục menu, trả các hwnd mới mọc.

        `click_input()` chứ không `invoke()`: submenu BCGPro chỉ bung ra khi có
        thao tác chuột thật. `invoke()` chạy không lỗi nhưng không mở gì — mà
        "không lỗi" rất dễ bị đọc nhầm thành "đã mở".
        """
        from pywinauto import Desktop
        truoc = _dinh(self.pid)
        goc = self._thanh()
        m = [c for c in goc.children() if c.element_info.name == ten[0]]
        if not m:
            raise MidasError(f'không thấy {ten[0]!r} trên thanh ứng dụng')
        m[0].click_input()
        time.sleep(cho)

        for t in ten[1:]:
            tim = None
            for h in [x for x in _dinh(self.pid) - truoc if u32.IsWindowVisible(x)]:
                try:
                    for k in Desktop(backend='uia').window(handle=h).descendants():
                        if k.element_info.name == t:
                            tim = k
                            break
                except Exception:
                    continue
                if tim:
                    break
            if tim is None:
                raise MidasError(f'không thấy mục {t!r} trong menu')
            tim.click_input()
            time.sleep(cho)
        return [h for h in _dinh(self.pid) - truoc if u32.IsWindowVisible(h)]

    def _tra_loi_xac_nhan(self, truoc: set) -> bool:
        """Trả lời **Yes** cho hộp xác nhận ghi đè, nếu có.

        Ghi đè một file đã tồn tại làm Windows bật `Confirm Save As`. Hộp này
        **modal**, mà `PostMessage(VK_ESCAPE)` vào cửa sổ chính thì không với tới
        — driver sẽ đứng đợi tới hết thời hạn rồi báo một lỗi hoàn toàn lạc đề
        ("chưa có khối OVERALL TIME LOG"). Đã dẫm đúng một lần, mất 1800 giây.

        Chỉ tự bấm cho hộp có chữ `Confirm`. Hộp lạ thì **chụp tên rồi ném lỗi**:
        bấm mù vào hộp thoại chưa biết là cách nhanh nhất phá mô hình.
        """
        for h in _dinh(self.pid) - truoc:
            if not u32.IsWindowVisible(h) or _lop(h) != '#32770':
                continue
            ten = _doc(h) or ''
            if 'Confirm' not in ten:
                continue
            nut = [c for c in _con(h, self.pid)
                   if c['lop'] == 'Button' and c['chu'].replace('&', '') == 'Yes']
            if not nut:
                raise MidasError(f'hộp {ten!r} không có nút Yes — dừng để khỏi bấm mù')
            u32.SendMessageW(nut[0]['hwnd'], BM_CLICK, 0, 0)
            self.log(f'  trả lời Yes cho {ten!r}')
            time.sleep(1.5)
            return True
        return False

    def _dat_duong_dan(self, hop, path):
        """Điền đường dẫn vào ô tên file của hộp thoại rồi Enter."""
        o = [c for c in _con(hop, self.pid) if c['lop'] == 'Edit' and c['rect'][2] > 100]
        if not o:
            raise MidasError('không thấy ô nhập tên file trong hộp thoại')
        if not _dat(o[0]['hwnd'], path):
            raise MidasError(f'đặt đường dẫn không ăn: {path}')
        _phim(o[0]['hwnd'], VK_RETURN)

    # ── bước 1: nạp MCT ──
    def kiem_tai_lieu_sach(self):
        """Chỉ chạy khi Midas chưa mở mô hình nào của người dùng.

        Import MCT đè lên tài liệu đang mở. Thà dừng và báo còn hơn làm mất việc
        đang dở — mất kiểu đó không hoàn lại được.
        """
        td = self.tieu_de
        if not any(k in td for k in ('[Start Page]', '[Untitled]')):
            raise MidasError(f'Midas đang mở mô hình khác ({td!r}). '
                             f'Hãy lưu rồi File › New trước khi chạy.')
        if '*' in td:
            raise MidasError(f'có thay đổi chưa lưu: {td!r}')

    def import_mct(self, mct: str, han=90):
        """`Application menu › New Project… › Import › MIDAS/Civil MCT File…`

        Phải `New Project` trước: ở màn hình Start Page toàn bộ submenu Import bị
        **khoá xám**, bấm vào không lỗi gì cả — nhìn từ phía mã y hệt đã bấm xong.
        """
        mct = os.path.abspath(mct)
        if not os.path.exists(mct):
            raise MidasError(f'không thấy file MCT: {mct}')
        self.kiem_tai_lieu_sach()
        self._len_truoc()

        if '[Untitled]' not in self.tieu_de:
            self._bam_chuoi('Application menu', 'New Project...')
            for _ in range(20):
                time.sleep(0.5)
                if '[Untitled]' in self.tieu_de:
                    break
            else:
                self._esc()
                raise MidasError('New Project… không tạo được tài liệu mới')

        truoc_td = self.tieu_de
        truoc = _dinh(self.pid)
        try:
            self._bam_chuoi('Application menu', 'Import', 'MIDAS/Civil MCT File...')
        except MidasError:
            self._esc()
            raise
        hop = self._cho_cua_so(truoc, han=10, lop='#32770')
        if hop is None:
            self._esc()
            raise MidasError('không mở được hộp thoại chọn file MCT')
        self._dat_duong_dan(hop, mct)

        for _ in range(han):
            time.sleep(1)
            td = self.tieu_de
            if td != truoc_td and '[Start Page]' not in td:
                self.log(f'  nạp xong: {os.path.basename(mct)}')
                return
        self._esc()
        raise MidasError(f'{han} s sau khi nạp mà tiêu đề vẫn {self.tieu_de!r}')

    # ── bước 2: phân tích ──
    def analyze(self, mcb: str, han=1800):
        """F5. Midas đòi lưu trước → điền đường dẫn `.mcb`, lưu xong nó TỰ giải.

        Biết xong bằng khối `OVERALL TIME LOG` ở cuối file `.OUT` — dấu hiệu theo
        **file**, dứt khoát hơn canh cửa sổ hay đo thời gian. Lúc đang giải thì
        message loop bận nên mọi phép hỏi cửa sổ đều không đáng tin.
        """
        mcb = os.path.abspath(mcb)
        os.makedirs(os.path.dirname(mcb), exist_ok=True)
        out = os.path.splitext(mcb)[0] + '.OUT'
        # Dọn dấu vết lượt trước: `.OUT` cũ làm phép kiểm "đã xong" báo nhầm ngay
        # lập tức, còn `.mcb` cũ thì đẻ ra hộp xác nhận ghi đè.
        for f in (out, mcb):
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass

        # F5 là **phím tắt của ribbon**, nên chỉ ăn khi Midas đang ở tiền cảnh:
        # MFC dịch phím tắt trong vòng lặp thông điệp của cửa sổ đang có tiêu điểm.
        # `PostMessage` vào cửa sổ chính lúc app nằm dưới thì phím rơi vào hư
        # không — không lỗi, không tác dụng, và thông báo lỗi sau đó ("F5 không
        # phải Perform Analysis ở bản này") thì lạc đề hoàn toàn.
        from pywinauto.keyboard import send_keys
        self._len_truoc()
        truoc = _dinh(self.pid)
        send_keys('{F5}')
        hop = self._cho_cua_so(truoc, han=20, lop='#32770')
        if hop is None:
            # thử lại bằng đường thông điệp, phòng khi tiêu điểm nằm ở ô nhập nào đó
            _phim(self.hwnd, VK_F5)
            hop = self._cho_cua_so(truoc, han=15, lop='#32770')
        if hop is None:
            raise MidasError(
                'F5 không bật hộp thoại lưu. Kiểm: Midas có ở tiền cảnh không, '
                'mô hình đã nạp chưa (tiêu đề phải có dấu *), và F5 có đúng là '
                'Perform Analysis ở bản này không.')
        self.log(f'  lưu mô hình: {os.path.basename(mcb)}')
        sau_hop = _dinh(self.pid)
        self._dat_duong_dan(hop, mcb)

        t0 = time.time()
        da_xac_nhan = False
        while time.time() - t0 < han:
            time.sleep(1)
            if not da_xac_nhan:
                da_xac_nhan = self._tra_loi_xac_nhan(sau_hop)
            if os.path.exists(out):
                try:
                    with open(out, encoding='utf-8', errors='replace') as f:
                        if XONG in f.read()[-4000:]:
                            self.log(f'  phân tích xong sau {time.time() - t0:.0f} s')
                            return
                except OSError:
                    pass                      # Midas đang ghi dở — thử lại nhịp sau
        raise MidasError(f'{han} s mà {os.path.basename(out)} chưa có khối {XONG!r}')

    # ── bước 3: xuất Beam Force ──
    def export_beam_force(self, xls: str, han=300):
        """Mở bảng, tick HẾT trường hợp tải, rồi xuất Excel.

        Mắt xích khó nhất của cả quy trình nằm ở đây: danh sách trường hợp tải là
        `ListBox` kiểu `LBS_EXTENDEDSEL` **có ô tick riêng**, và **bôi đen với tick
        là hai chuyện khác nhau** — hộp thoại đọc trạng thái *tick*. Đã thử và đều
        KHÔNG được: `LB_SETSEL(1,-1)`, gửi kèm `LBN_SELCHANGE`, `Ctrl+A`, hay
        bôi đen mà không tick. Tất cả đều làm `LB_GETSELCOUNT` báo đủ 55/55 nhưng
        **bảng ra rỗng** — và file xuất ra vẫn là `.xls` hợp lệ, mở bằng Excel vẫn
        có tiêu đề cột. Hỏng hoàn toàn âm thầm.

        Cách đúng: bôi đen cả dải rồi nhấn **SPACE**.
        """
        from pywinauto import Desktop
        from pywinauto.keyboard import send_keys

        xls = os.path.abspath(xls)
        os.makedirs(os.path.dirname(xls), exist_ok=True)
        if os.path.exists(xls):
            os.remove(xls)

        self._len_truoc()
        goc = self._thanh()
        tabs = [c for c in goc.children() if c.element_info.name == 'Ribbon Tabs'][0]
        [t for t in tabs.children() if t.element_info.name == 'Results'][0].click_input()
        time.sleep(1.5)
        # Nội dung thẻ đang mở nằm ở `ToolBar` mang TÊN THẺ, không phải con của TabItem.
        bang = [c for c in goc.children()
                if c.element_info.control_type == 'ToolBar'
                and c.element_info.name == 'Results']
        if not bang:
            raise MidasError('chọn thẻ Results xong mà ribbon không đổi — '
                             'Midas có ở tiền cảnh không?')
        nhom = [g for g in bang[0].children() if g.element_info.name.strip() == 'Tables'][0]
        rt = [k for k in nhom.children() if k.element_info.name == 'Results Tables'][0]

        truoc = _dinh(self.pid)
        rt.click_input()
        time.sleep(1.8)

        def tim(ten):
            for h in [x for x in _dinh(self.pid) - truoc if u32.IsWindowVisible(x)]:
                try:
                    for k in Desktop(backend='uia').window(handle=h).descendants():
                        if k.element_info.name == ten:
                            return k
                except Exception:
                    pass
            return None

        for ten in ('Beam', 'Force'):
            m = tim(ten)
            if m is None:
                self._esc()
                raise MidasError(f'không thấy mục {ten!r} trong Results Tables')
            m.click_input()
            time.sleep(2.0)

        hop = [c for c in _con(self.hwnd, self.pid)] and \
              [h for h in _dinh(self.pid) if _lop(h) == '#32770' and u32.IsWindowVisible(h)]
        if not hop:
            raise MidasError('không thấy Records Activation Dialog')
        h = hop[0]
        lb = [c for c in _con(h, self.pid)
              if c['lop'] == 'ListBox' and u32.SendMessageW(c['hwnd'], LB_GETCOUNT, 0, 0) > 5]
        if not lb:
            self._esc()
            raise MidasError('không thấy danh sách trường hợp tải')
        lb = max(lb, key=lambda c: u32.SendMessageW(c['hwnd'], LB_GETCOUNT, 0, 0))['hwnd']
        n = u32.SendMessageW(lb, LB_GETCOUNT, 0, 0)

        # Tab cho tới khi tiêu điểm rơi đúng vào danh sách. KHÔNG ghim số lần —
        # đo được 11 lần ở lượt này và 15 ở lượt khác, tuỳ trạng thái hộp thoại.
        u32.SetForegroundWindow(h)
        time.sleep(0.8)
        for i in range(1, 25):
            send_keys('{TAB}')
            time.sleep(0.15)
            if _tieu_diem() == lb:
                break
        else:
            self._esc()
            raise MidasError('Tab 24 lần mà tiêu điểm không vào được danh sách tải')

        send_keys('{HOME}')
        time.sleep(0.3)
        send_keys('+{END}')
        time.sleep(0.9)
        send_keys('{SPACE}')                    # ← tick cả dải đang bôi đen
        time.sleep(1.2)
        chon = u32.SendMessageW(lb, LB_GETSELCOUNT, 0, 0)
        self.log(f'  chọn {chon}/{n} trường hợp tải')

        Desktop(backend='uia').window(handle=h).child_window(
            title='OK', control_type='Button').click_input()
        time.sleep(6.0)

        # Xuất: chuột phải TRÊN BẢNG. Không dùng File › Export — ở đó không có Excel.
        self._len_truoc()
        muc = None
        for xy in ((900, 300), (700, 350), (900, 500)):
            g = _dinh(self.pid)
            from pywinauto import mouse
            mouse.right_click(coords=xy)
            time.sleep(1.6)
            for x in [y for y in _dinh(self.pid) - g if u32.IsWindowVisible(y)]:
                try:
                    for k in Desktop(backend='uia').window(handle=x).descendants():
                        if k.element_info.name == 'Export to Excel...':
                            muc = k
                            break
                except Exception:
                    pass
                if muc:
                    break
            if muc:
                break
            self._esc(2)
        if muc is None:
            raise MidasError('không mở được menu chuột phải trên bảng kết quả')

        truoc = _dinh(self.pid)
        muc.click_input()
        hop = self._cho_cua_so(truoc, han=25, lop='#32770')
        if hop is None:
            raise MidasError('không mở được hộp thoại lưu file Excel')
        self._dat_duong_dan(hop, xls)

        for _ in range(han):
            time.sleep(1)
            if os.path.exists(xls) and os.path.getsize(xls) > 0:
                time.sleep(2)                   # để Midas ghi nốt
                break
        else:
            raise MidasError(f'{han} s mà chưa thấy {os.path.basename(xls)}')

        with open(xls, 'rb') as f:
            if f.read(8) != BIFF8:
                raise MidasError(
                    f'{os.path.basename(xls)} không phải .xls BIFF8 — `xlrd` sẽ '
                    f'không đọc được. Kiểm ô định dạng của hộp thoại lưu.')
        self.log(f'  xuất xong: {os.path.getsize(xls):,} byte')

    # ── kiểm ──
    def kiem_ket_qua(self, xls: str, topo: str = None) -> dict:
        """Đọc lại file vừa xuất bằng CHÍNH bộ đọc của app.

        Bước này không thừa. Ba lần trong lúc dò đường, file xuất ra đúng định
        dạng, đúng tên, đúng chỗ, mở bằng Excel vẫn có tiêu đề cột — mà **0 bản
        ghi**. Chỉ kiểm tới mức "file tồn tại" thì đã báo thành công cả ba lần.
        """
        # Chạy được cả khi import như gói (`from src.midas_driver import …`) lẫn
        # khi chạy thẳng như script (`python src/midas_driver.py`) — lối thứ hai
        # không có gói cha nên import tương đối sẽ nổ.
        try:
            from .result_reader import parse_beam_force
        except ImportError:
            from src.result_reader import parse_beam_force
        kq = parse_beam_force(xls)
        lc = {x['load'] for x in kq}
        thieu = [k for k in ('str_all(max)', 'str_all(min)',
                             'ser_all(max)', 'ser_all(min)') if k not in lc]
        if not kq:
            raise MidasError(f'{os.path.basename(xls)} không có bản ghi nào — '
                             f'bảng kết quả rỗng lúc xuất')
        if thieu:
            raise MidasError(
                f'thiếu tổ hợp {", ".join(thieu)} — bảng kiểm toán sẽ ra toàn '
                f'0.00 mà không một dòng cảnh báo nào')
        ra = {'ban_ghi': len(kq), 'phan_tu': len({x['elem'] for x in kq}),
              'truong_hop_tai': len(lc)}
        if topo and os.path.exists(topo):
            import json
            with open(topo, encoding='utf-8') as f:
                et = {e[0] for e in json.load(f)['elements']}
            ra['khop_topo'] = (et == {x['elem'] for x in kq})
            if not ra['khop_topo']:
                raise MidasError(f'tập phần tử không khớp topo '
                                 f'({len(et)} trong topo, {ra["phan_tu"]} trong file)')
        return ra


def chay_mot_mat_cat(mct: str, xls: str = None, mcb: str = None, log=print) -> dict:
    """Nạp → giải → xuất cho MỘT mặt cắt. Trả thống kê của `kiem_ket_qua`."""
    thu_muc = os.path.dirname(os.path.abspath(mct))
    ten = os.path.basename(thu_muc)
    xls = xls or os.path.join(thu_muc, f'Beam Force_{ten}.xls')
    mcb = mcb or os.path.splitext(os.path.abspath(mct))[0] + '.mcb'
    topo = os.path.join(thu_muc, f'{ten}_topo.json')

    with MidasSession.attach() as s:
        s.log = log
        log(f'[{ten}] nạp MCT…')
        s.import_mct(mct)
        log(f'[{ten}] phân tích…')
        s.analyze(mcb)
        log(f'[{ten}] xuất Beam Force…')
        s.export_beam_force(xls)
        tk = s.kiem_ket_qua(xls, topo)
    log(f'[{ten}] {tk["ban_ghi"]:,} bản ghi · {tk["phan_tu"]} phần tử · '
        f'{tk["truong_hop_tai"]} trường hợp tải')
    return tk


if __name__ == '__main__':
    import argparse
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('mct', help='file MCT cần nạp')
    ap.add_argument('-o', '--out', help='file .xls xuất ra')
    a = ap.parse_args()
    try:
        chay_mot_mat_cat(a.mct, a.out)
    except MidasError as e:
        print(f'\n{e}\n')
        sys.exit(1)

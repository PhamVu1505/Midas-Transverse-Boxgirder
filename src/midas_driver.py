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
3. **Không bao giờ bấm vào một toạ độ đoán trước.** `click_input()` bấm theo toạ
   độ MÀN HÌNH. Ba số ghim cứng cho menu ngữ cảnh từng nằm trọn trên màn hình
   TRÁI trong khi Midas phóng to trên màn hình PHẢI — cú bấm chưa lần nào chạm
   Midas, mà rơi vào trình soạn thảo người dùng đang mở. Mọi cú bấm nay lấy toạ
   độ từ **chính control đích** (`GXWND` cho bảng kết quả, rect của phần tử UIA
   cho ribbon), nên không phụ thuộc màn hình, cỡ cửa sổ hay bố cục thanh công cụ.
   Điểm nằm ngoài khung Midas thì **báo lỗi chứ không bấm**.
4. **`_len_truoc()` phải KIỂM LẠI tiền cảnh, không được tin `set_focus()`.**
   Windows cấm tiến trình nền cướp tiền cảnh và pywinauto nuốt thất bại đó —
   im lặng. Phím lạc từ đúng lỗ hổng này đã mở `Auto-Mesh Planar Area` và
   **đóng Midas của người dùng hai lần**.
"""

import ctypes
import os
import re
import tempfile
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
TEN_HOP_CHON_TAI = 'Records Activation Dialog'

u32 = ctypes.WinDLL('user32', use_last_error=True)

WM_NULL, WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH = 0x0000, 0x000C, 0x000D, 0x000E
WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101
WM_CONTEXTMENU = 0x007B
# Ô lưới của bảng kết quả (Stingray Objective Grid). Đây là ĐÍCH của menu ngữ
# cảnh "Export to Excel..." — bám vào nó thì không còn phải đoán toạ độ.
LOP_LUOI = 'GXWND'
BM_CLICK = 0x00F5
LB_GETCOUNT, LB_GETSELCOUNT = 0x018B, 0x0190
SMTO_ABORTIFHUNG = 0x0002
VK_RETURN, VK_F5, VK_ESCAPE, VK_SPACE = 0x0D, 0x74, 0x1B, 0x20
LB_SETSEL = 0x0185

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

    def _len_truoc(self, han=5):
        """Đưa Midas lên tiền cảnh — BẮT BUỘC trước mọi cú bấm chuột hoặc phím thật.

        **Phải KIỂM LẠI, không được tin `set_focus()`.** Windows không cho một
        tiến trình nền cướp tiền cảnh (`SetForegroundWindow` trả về false và
        pywinauto nuốt luôn), nên `set_focus()` **thất bại âm thầm**. Hệ quả đã
        xảy ra thật: chuỗi phím dành cho hộp thoại rơi vào khung nhìn mô hình,
        mở ra `Auto-Mesh Planar Area`, và một phím lạc trong menu Application
        **đóng luôn Midas của người dùng hai lần**.

        Thà dừng có tên còn hơn bấm vào cửa sổ của người khác — đúng cùng lý lẽ
        với việc không bấm mù ra ngoài khung Midas.
        """
        for i in range(han):
            try:
                self._w().set_focus()
            except Exception:
                pass
            time.sleep(0.6)
            fg = u32.GetForegroundWindow()
            # Đủ điều kiện khi cửa sổ tiền cảnh thuộc chính tiến trình Midas —
            # hộp thoại con của Midas cũng hợp lệ, không riêng cửa sổ chính.
            if fg and _pid(fg) == self.pid:
                return
        raise MidasError(
            'không đưa được Midas lên tiền cảnh sau '
            f'{han} lần — cửa sổ đang ở tiền cảnh thuộc tiến trình khác. '
            'Đừng dùng máy trong lúc driver chạy; bấm vào cửa sổ Midas rồi chạy lại.')

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

    def _chon_the(self, ten: str, lan=6):
        """Chọn một thẻ ribbon, trả về bảng lệnh của nó.

        Phải **thử lại**: cú bấm có ăn nhưng bảng lệnh chỉ xuất hiện sau đó một
        nhịp, mà bản đầu tôi kiểm đúng một lần rồi kết luận "ribbon không đổi —
        Midas có ở tiền cảnh không?". Thông điệp ấy sai chỗ, và cả một loạt 6 mặt
        cắt trượt vì nó. Thực tế đo được: lần 1 thấy `['Quick Access Toolbar',
        'View']`, lần 2 đã có `'Results'`.

        Nội dung thẻ đang mở nằm ở `ToolBar` **mang tên thẻ**, không phải con của
        `TabItem` — nên đây cũng chính là phép kiểm "đã chuyển thẻ chưa".
        """
        for i in range(lan):
            tb = self._thanh()
            co = [c for c in tb.children()
                  if c.element_info.control_type == 'ToolBar'
                  and c.element_info.name == ten]
            if co:
                return co[0]
            tabs = [c for c in tb.children() if c.element_info.name == 'Ribbon Tabs']
            if not tabs:
                raise MidasError('không thấy dải thẻ ribbon')
            t = [x for x in tabs[0].children() if x.element_info.name == ten]
            if not t:
                raise MidasError(f'không thấy thẻ ribbon {ten!r}')
            t[0].click_input()
            time.sleep(1.5)
        raise MidasError(f'{lan} lần bấm thẻ {ten!r} mà bảng lệnh của nó không hiện')

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

    # Hộp thoại BÌNH THƯỜNG của quy trình, không phải sự cố:
    #   `Confirm …`        — hỏi ghi đè, `_tra_loi_xac_nhan` lo
    #   `Perform Analysis` — CỬA SỔ TIẾN TRÌNH GIẢI, hiện suốt lúc Midas tính
    #
    # Cái thứ hai từng làm cả loạt 6 mặt cắt trượt sạch: tôi thêm `_hop_la` làm
    # chốt an toàn, rồi chính nó bắt oan cửa sổ tiến trình và báo "phân tích bị
    # chặn" trong khi phân tích đang chạy bình thường. Thêm chốt mà không biết
    # cái gì là bình thường thì chốt chặn đúng luồng hợp lệ.
    HOP_BINH_THUONG = ('Confirm', 'Perform Analysis')

    def _hop_la(self, truoc: set, bo_qua=HOP_BINH_THUONG):
        """Tiêu đề hộp thoại LẠ vừa mọc ra, hoặc None.

        Gọi trong mọi vòng chờ. Không có nó thì một hộp thoại ngoài dự kiến làm
        driver ngồi đợi tới hết thời hạn rồi báo một lỗi hoàn toàn lạc đề — đã
        mất hai lượt 1800 giây vì đúng chuyện này. Biết tên hộp thì lỗi ra ngay
        và nói đúng chỗ.
        """
        for h in _dinh(self.pid) - truoc:
            if not u32.IsWindowVisible(h) or _lop(h) != '#32770':
                continue
            ten = _doc(h, 500) or ''
            if any(k in ten for k in bo_qua) or not ten:
                continue
            return ten
        return None

    def don_dep(self) -> list:
        """Đóng hộp thoại còn sót, trả tên những cái không đóng được.

        Hai cách, theo thứ tự: bấm **Cancel** nếu có (câu trả lời "không làm gì
        cả"), không thì gửi **ESC thẳng vào hộp thoại đó**.

        **TUYỆT ĐỐI KHÔNG `WM_CLOSE`.** Tôi từng dùng nó trong một script dọn dẹp
        viết vội: gửi vòng lặp cho các hộp thoại thì nó lan tới cửa sổ chính và
        **đóng luôn Midas của người dùng** — đúng cái việc cả module này cấm.
        Luật chỉ ghi trong chú thích thì chính người viết cũng vi phạm được, nên
        nay hàm này là chỗ duy nhất được đóng hộp thoại, và nó không biết
        `WM_CLOSE` là gì.

        Hộp chỉ có OK thì thử ESC; ESC không ăn thì **để nguyên và báo tên** —
        bấm OK có thể thực thi lệnh (đã gặp `Auto-Mesh Planar Area`, bấm OK là
        chia lưới cả mô hình).
        """
        con_lai = []
        for h in list(_dinh(self.pid)):
            if not u32.IsWindowVisible(h) or _lop(h) != '#32770':
                continue
            # Midas có sẵn một `#32770` tên rỗng cỡ 267×20 nằm trong thanh công
            # cụ (khung của mấy ô xoay). Nó là phần cố định của giao diện, không
            # phải hộp thoại sót — coi nó là rác thì `don_dep` báo động giả mãi.
            _x, _y, rw, rh = _rect(h)
            ten = (_doc(h, 500) or '').strip()
            if not ten or rw < 200 or rh < 60:
                continue
            if h == self.hwnd:
                continue                      # không bao giờ đụng cửa sổ chính
            nut = [c for c in _con(h, self.pid)
                   if c['lop'] == 'Button' and c['chu'].replace('&', '') == 'Cancel']
            if nut:
                u32.SendMessageW(nut[0]['hwnd'], BM_CLICK, 0, 0)
                time.sleep(1.0)
            else:
                _phim(h, VK_ESCAPE)           # ESC vào ĐÚNG hộp đó, không phải cửa sổ chính
                time.sleep(1.0)
            if u32.IsWindow(h) and u32.IsWindowVisible(h):
                con_lai.append(ten)
        return con_lai

    def moi_tai_lieu(self, han=25):
        """Về tài liệu trống để chạy mặt cắt tiếp theo.

        Trả lời **No** cho hộp hỏi lưu: mô hình đã được `analyze()` lưu ra `.mcb`
        rồi, thay đổi còn lại chỉ là chuyện hiển thị (mở bảng kết quả).
        """
        if '[Untitled]' in self.tieu_de and '*' not in self.tieu_de:
            return
        self._len_truoc()
        truoc = _dinh(self.pid)
        self._bam_chuoi('Application menu', 'New Project...')
        for _ in range(han):
            time.sleep(0.5)
            for h in _dinh(self.pid) - truoc:
                if not u32.IsWindowVisible(h) or _lop(h) != '#32770':
                    continue
                nut = [c for c in _con(h, self.pid)
                       if c['lop'] == 'Button' and c['chu'].replace('&', '') == 'No']
                if nut:
                    u32.SendMessageW(nut[0]['hwnd'], BM_CLICK, 0, 0)
                    time.sleep(1.5)
            if '[Untitled]' in self.tieu_de and '*' not in self.tieu_de:
                return
        raise MidasError(f'không về được tài liệu trống — tiêu đề {self.tieu_de!r}')

    def _o_luoi(self, han=15):
        """hwnd của ô lưới bảng kết quả — đích của menu ngữ cảnh.

        Lấy cái LỚN NHẤT: Midas dựng vài `GXWND` lồng nhau (khung, thanh tiêu đề
        cột), chỉ cái to nhất mới là vùng dữ liệu nhận menu ngữ cảnh.
        """
        for _ in range(han):
            lu = [c for c in _con(self.hwnd, self.pid)
                  if c['lop'] == LOP_LUOI and c['hien'] and c['rect']
                  and c['rect'][2] > 200 and c['rect'][3] > 200]
            if lu:
                return max(lu, key=lambda c: c['rect'][2] * c['rect'][3])['hwnd']
            time.sleep(1.0)
        raise MidasError(f'không thấy ô lưới bảng kết quả (class {LOP_LUOI!r}) — '
                         f'bảng Beam Force có mở không?')

    def _dat_duong_dan(self, hop, path):
        """Điền đường dẫn vào ô tên file của hộp thoại rồi Enter.

        Có file trùng tên thì **đồng ý ghi đè**: đích đến là sản phẩm của chính
        driver, chạy lại là phải ra bản mới. Hộp hỏi đè không được trả lời thì
        driver đứng im cho tới hết thời hạn rồi báo "không xuất được file" — sai
        chỗ hoàn toàn, mà lại là tình huống thường gặp nhất (chạy lại lần hai).
        """
        o = [c for c in _con(hop, self.pid) if c['lop'] == 'Edit' and c['rect'][2] > 100]
        if not o:
            raise MidasError('không thấy ô nhập tên file trong hộp thoại')
        if not _dat(o[0]['hwnd'], path):
            raise MidasError(f'đặt đường dẫn không ăn: {path}')
        truoc = _dinh(self.pid)
        _phim(o[0]['hwnd'], VK_RETURN)
        self._dong_y_ghi_de(truoc)

    def _dong_y_ghi_de(self, truoc, han=6):
        """Bấm **Yes** cho hộp 'file đã tồn tại — ghi đè?' nếu nó hiện ra.

        Chỉ nhận hộp có nút Yes **và** nút No: đó là dạng của hộp hỏi đè. Hộp lạ
        chỉ có OK thì để nguyên cho `don_dep()` xử — bấm bừa OK có thể là thực thi
        một lệnh (đã gặp `Auto-Mesh Planar Area`).
        """
        for _ in range(han):
            time.sleep(0.5)
            for h in _dinh(self.pid) - truoc:
                if not u32.IsWindowVisible(h) or _lop(h) != '#32770':
                    continue
                nut = {c['chu'].replace('&', ''): c['hwnd']
                       for c in _con(h, self.pid) if c['lop'] == 'Button'}
                if 'Yes' in nut and 'No' in nut:
                    u32.SendMessageW(nut['Yes'], BM_CLICK, 0, 0)
                    self.log('  ghi đè file cũ')
                    time.sleep(1.0)
                    return True
        return False

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
    def analyze(self, mcb: str, han=1800, han_khoi_dong=60, han_im=300):
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

        # Chờ hai chặng, và chặng đầu là chỗ tiết kiệm nhất.
        #
        # Bản trước chỉ có một thời hạn 1800 s cho cả quá trình. Mặt cắt SLT lưu
        # được `.mcb` nhưng phân tích **không hề khởi động** — không `.OUT`, không
        # `.CA*` — thế mà driver ngồi đợi đủ nửa tiếng rồi báo "chưa có chuỗi
        # TOTAL ELAPSED TIME", tức đổ lỗi cho một việc chưa bắt đầu. Cả loạt 6 mặt
        # cắt kéo dài 35 phút chỉ vì một mặt cắt im lặng.
        #
        # Nay: `.OUT` phải **xuất hiện** trong `han_khoi_dong`; Midas rảnh mà file
        # vẫn chưa có thì kết luận ngay là phân tích không chạy. Sau đó mới đo tiếp
        # tới khi xong, và mỗi lần `.OUT` lớn thêm thì gia hạn — mô hình lớn giải
        # lâu vẫn được, còn im lặng thì bị bắt trong một phút.
        t0 = time.time()
        da_xac_nhan = False
        lan_lon = t0
        co_truoc = -1
        while True:
            time.sleep(1)
            if not da_xac_nhan:
                da_xac_nhan = self._tra_loi_xac_nhan(sau_hop)

            la = self._hop_la(sau_hop)
            if la:
                raise MidasError(f'phân tích bị chặn bởi hộp thoại {la!r} — '
                                 f'không tự bấm vì chưa biết hộp này')

            co = os.path.getsize(out) if os.path.exists(out) else -1
            if co > co_truoc:
                co_truoc, lan_lon = co, time.time()
            if co >= 0:
                try:
                    with open(out, encoding='utf-8', errors='replace') as f:
                        if XONG in f.read()[-4000:]:
                            self.log(f'  phân tích xong sau {time.time() - t0:.0f} s')
                            return
                except OSError:
                    pass                      # Midas đang ghi dở — thử lại nhịp sau

            if co < 0 and time.time() - t0 > han_khoi_dong:
                raise MidasError(
                    f'{han_khoi_dong} s sau khi lưu mà {os.path.basename(out)} '
                    f'chưa xuất hiện — phân tích KHÔNG khởi động. Mở Midas xem '
                    f'mô hình có lỗi gì không (thiếu ràng buộc, tổ hợp mồ côi…).')
            if time.time() - lan_lon > han_im:
                raise MidasError(
                    f'{han_im} s không thấy {os.path.basename(out)} lớn thêm '
                    f'(đang {co} byte) — phân tích đứng.')
            if time.time() - t0 > han:
                raise MidasError(f'{han} s mà {os.path.basename(out)} chưa có '
                                 f'chuỗi {XONG!r}')

    # ── bước 3: xuất Beam Force ──
    def export_beam_force(self, xls: str, han=300):
        """Mở bảng, tick HẾT trường hợp tải, rồi xuất Excel.

        Mắt xích khó nhất của cả quy trình nằm ở đây: danh sách trường hợp tải là
        `ListBox` kiểu `LBS_EXTENDEDSEL` **có ô tick riêng**, và **bôi đen với tick
        là hai chuyện khác nhau** — hộp thoại đọc trạng thái *tick*. Đã thử và đều
        KHÔNG được: `LB_SETSEL(1,-1)` một mình, gửi kèm `LBN_SELCHANGE`, hay
        `Ctrl+A`. Tất cả đều làm `LB_GETSELCOUNT` báo đủ 55/55 nhưng **bảng ra
        rỗng** — mà file xuất ra vẫn là `.xls` hợp lệ, mở bằng Excel vẫn có tiêu
        đề cột. Hỏng hoàn toàn âm thầm.

        Cách đúng: **bôi đen cả dải rồi SPACE**, và cả hai đi bằng thông điệp —
        xem chú thích trong thân hàm.
        """
        from pywinauto import Desktop

        xls = os.path.abspath(xls)
        os.makedirs(os.path.dirname(xls), exist_ok=True)
        # Xoá bản cũ để `kiem_ket_qua` không đọc nhầm file của lượt trước khi lượt
        # này xuất hụt. Xoá KHÔNG được thì vẫn đi tiếp: Excel đang mở file là giữ
        # khoá, mà bản trước để `os.remove` ném thẳng `PermissionError` — chạy lại
        # trong lúc còn mở bảng cũ là hỏng ngay từ dòng đầu, chưa kịp làm gì.
        # Trường hợp đó để Midas hỏi đè, `_dong_y_ghi_de()` trả lời Yes.
        if os.path.exists(xls):
            try:
                os.remove(xls)
            except OSError as e:
                self.log(f'  không xoá được bản cũ ({e.strerror}) — sẽ ghi đè')

        def tim(ten, truoc):
            """Soi MỌI cửa sổ nổi của tiến trình, không chỉ cửa sổ vừa mọc.

            Bản trước lọc `_dinh(self.pid) - truoc`, tức chỉ cửa sổ **mới** so với
            lúc trước khi bấm. Cửa sổ menu bung ra của Midas không bị huỷ sau khi
            đóng — nó chỉ bị ẩn rồi hiện lại. Nên lượt chạy đầu trong một phiên đã
            mở menu này trước đó thì `truoc` đã chứa nó, hiệu là rỗng, và driver
            báo "không thấy mục 'Beam'" dù menu đang bung ra ngay trên màn hình.

            Ưu tiên cửa sổ mới rồi mới tới các cửa sổ còn lại — cửa sổ mới gần như
            luôn là cái đúng, nên thường không phải duyệt thêm.

            **Bỏ cửa sổ chính** khỏi danh sách: duyệt UIA trên `MidasGenMainFrmClass`
            mất 30–60 s (ribbon BCGPro), đủ để phá cả cơ chế thử lại bên dưới.

            Tôi đã thử thêm một phép lọc nữa — đòi `k.rectangle()` không rỗng, với
            giả thuyết "mục của menu cũ có khung rỗng nên bấm hụt". Giả thuyết đó
            **sai**: nó loại nhầm cả mục hợp lệ và làm hỏng đúng chặng vốn đang
            chạy được ('Force' không còn tìm thấy). Đã bỏ. Thứ thật sự gỡ được bấm
            hụt là **thử lại cả chặng** ở dưới, và điều đó đã được chứng minh trên
            máy thật chứ không phải suy luận.
            """
            hien = {x for x in _dinh(self.pid)
                    if x != self.hwnd and u32.IsWindowVisible(x)}
            for h in sorted(hien, key=lambda x: x in truoc):
                try:
                    for k in Desktop(backend='uia').window(handle=h).descendants():
                        if k.element_info.name == ten:
                            return k
                except Exception:
                    pass
            return None

        def mo_bang():
            """Ribbon → Results Tables → Beam → Force, trả hwnd hộp chọn tải."""
            self._len_truoc()
            bang = self._chon_the('Results')
            nhom = [g for g in bang.children()
                    if g.element_info.name.strip() == 'Tables'][0]
            rt = [k for k in nhom.children()
                  if k.element_info.name == 'Results Tables'][0]

            truoc = _dinh(self.pid)
            rt.click_input()
            time.sleep(1.8)

            # Submenu cũng cần một nhịp mới bung ra — thử lại thay vì kết luận
            # ngay, cùng lý do như `_chon_the`.
            for ten in ('Beam', 'Force'):
                m = None
                for _ in range(6):
                    m = tim(ten, truoc)
                    if m is not None:
                        break
                    time.sleep(1.0)
                if m is None:
                    raise MidasError(f'không thấy mục {ten!r} trong Results Tables')
                m.click_input()
                time.sleep(2.0)

            # Tìm hộp thoại theo TIÊU ĐỀ, có thử lại.
            #
            # Bản trước lấy `#32770` **đầu tiên** tìm thấy — mà Midas có sẵn một
            # `#32770` cỡ 267×20 nằm trong thanh công cụ, không chứa ListBox nào.
            # Nên driver báo "không thấy danh sách trường hợp tải" ở 3/6 mặt cắt,
            # trong khi hộp thoại thật đang mở ngay đó. Script thử nghiệm chạy
            # đúng chính vì nó lọc theo tiêu đề; driver thì không — hai đường khác
            # nhau ở đúng một dòng.
            for _ in range(10):
                ung = [x for x in _dinh(self.pid)
                       if _lop(x) == '#32770' and u32.IsWindowVisible(x)
                       and (_doc(x, 500) or '').strip() == TEN_HOP_CHON_TAI]
                if ung:
                    return ung[0]
                time.sleep(1.0)
            return None

        # Thử lại CẢ CHẶNG, không chỉ từng bước.
        #
        # Menu bấm hụt thì không có tín hiệu nào ngay tại chỗ — mãi tới lúc chờ
        # hộp thoại mới lộ. Lúc đó menu đã ở trạng thái nửa vời, nên phải ESC cho
        # sạch rồi đi lại từ ribbon; thử lại từng bước nhỏ không gỡ được.
        # Phải bắt CẢ `MidasError` của `mo_bang()`, không chỉ trường hợp trả None.
        # Bấm hụt lộ ra ở hai dạng khác nhau — "không thấy mục 'Force'" (hụt giữa
        # chặng) và "không thấy hộp thoại" (hụt ở bước cuối) — mà bản đầu của vòng
        # này chỉ xử dạng thứ hai, nên dạng thứ nhất thoát thẳng ra ngoài và cơ chế
        # thử lại thành vô dụng đúng lúc cần nó nhất.
        h, loi = None, None
        for lan in range(3):
            if lan:
                self.log(f'  menu bấm hụt ({loi}) — dọn rồi đi lại từ ribbon')
                self._esc(3)
                time.sleep(1.5)
            try:
                h = mo_bang()
                if h is None:
                    loi = 'hộp thoại chọn tải không hiện'
            except MidasError as e:
                h, loi = None, str(e)
            if h is not None:
                break
        if h is None:
            self._esc(3)
            raise MidasError(f'không mở được bảng Beam Force sau 3 lượt điều hướng '
                             f'ribbon — lỗi cuối: {loi or "hộp thoại không hiện"}')

        lb = [c for c in _con(h, self.pid)
              if c['lop'] == 'ListBox' and u32.SendMessageW(c['hwnd'], LB_GETCOUNT, 0, 0) > 5]
        if not lb:
            self._esc()
            raise MidasError('hộp thoại mở nhưng không có danh sách trường hợp tải nào')
        lb = max(lb, key=lambda c: u32.SendMessageW(c['hwnd'], LB_GETCOUNT, 0, 0))['hwnd']
        n = u32.SendMessageW(lb, LB_GETCOUNT, 0, 0)

        # Tick HẾT trường hợp tải — **thuần thông điệp, không một phím thật nào**.
        #
        # Hộp thoại đọc trạng thái *tick*, không đọc *bôi đen*, nên cần đúng hai
        # việc: bôi đen cả dải, rồi một lần Space để tick cả dải đó.
        #   · `LB_SETSEL(1, -1)`        → bôi đen 55/55
        #   · `PostMessage(VK_SPACE)`   → tick, gửi THẲNG vào hwnd của ListBox
        #
        # Bản trước làm bằng phím thật: `SetForegroundWindow` rồi Tab tới 24 lần,
        # `Home`, `Shift+End`, `Space`. Nó chạy được khi thao tác tay ngay trước
        # đó, nhưng **phá sạch một loạt 6 mặt cắt** khi chạy từ tiến trình nền:
        # Windows không cho tiến trình nền chiếm tiền cảnh, `set_focus()` thất bại
        # âm thầm, và 24 cái Tab rơi vào khung nhìn mô hình thành lệnh bất kỳ —
        # lượt đó chúng mở `Auto-Mesh Planar Area`, và một phím lạc khác trong
        # menu Application còn **đóng luôn Midas của người dùng**.
        #
        # `PostMessage` gửi vào một hwnd cụ thể nên không phụ thuộc tiền cảnh và
        # không thể rơi ra ngoài. Đã kiểm: cho ra file trùng MD5 với bản làm tay.
        u32.SendMessageW(lb, LB_SETSEL, 1, -1)
        time.sleep(0.5)
        boi_den = u32.SendMessageW(lb, LB_GETSELCOUNT, 0, 0)
        if boi_den < n:
            self._esc()
            raise MidasError(f'chỉ bôi đen được {boi_den}/{n} trường hợp tải')
        u32.PostMessageW(lb, WM_KEYDOWN, VK_SPACE, 0)
        time.sleep(0.12)
        u32.PostMessageW(lb, WM_KEYUP, VK_SPACE, 0xC0000000)
        time.sleep(1.5)
        self.log(f'  tick {boi_den}/{n} trường hợp tải')

        Desktop(backend='uia').window(handle=h).child_window(
            title='OK', control_type='Button').click_input()
        time.sleep(6.0)

        # Xuất: menu ngữ cảnh TRÊN Ô LƯỚI. Không dùng File › Export — ở đó không
        # có Excel.
        #
        # Đích là hwnd của ô lưới, KHÔNG phải một toạ độ đoán trước.
        #
        # Bản đầu ghim cứng (900,300)/(700,350)/(900,500). Máy VuPQ có hai màn
        # hình 1920×1080 kề nhau và Midas phóng to trên màn hình PHẢI (rect
        # left=1912) — cả ba điểm nằm trọn trên màn hình TRÁI, nên cú chuột phải
        # **chưa một lần nào chạm vào Midas**: nó rơi vào cửa sổ bất kỳ người
        # dùng đang mở bên đó. Driver thì báo "không mở được menu chuột phải"
        # trong khi bảng đang mở ngay trước mặt. `set_focus()` không cứu được:
        # toạ độ tuyệt đối đơn giản nằm ngoài cửa sổ.
        #
        # Bản vá thứ hai suy điểm theo tỉ lệ khung cửa sổ chính. Đúng hơn nhưng
        # vẫn là phỏng đoán bố cục: đổi cỡ Message Window hay bật thêm thanh công
        # cụ là điểm đó rời khỏi bảng.
        #
        # Nay bám thẳng vào control `GXWND` (lưới Stingray) — đó CHÍNH LÀ bảng kết
        # quả, nên không còn khái niệm "đoán chỗ". Kèm theo, thử `WM_CONTEXTMENU`
        # trước: nó là thông điệp gửi vào đúng hwnd, **không đụng tới con trỏ
        # chuột của người dùng** và không phụ thuộc màn hình nào cả.
        self._len_truoc()
        luoi = self._o_luoi()
        gx, gy, gw, gh = _rect(luoi)
        tam = (gx + gw // 2, gy + gh // 2)

        def tim_muc(g):
            for x in [y for y in _dinh(self.pid) - g if u32.IsWindowVisible(y)]:
                try:
                    for k in Desktop(backend='uia').window(handle=x).descendants():
                        if k.element_info.name == 'Export to Excel...':
                            return k
                except Exception:
                    pass
            return None

        muc = None
        # (a) thuần thông điệp — không chạm chuột
        g = _dinh(self.pid)
        u32.PostMessageW(luoi, WM_CONTEXTMENU, luoi,
                         (tam[1] << 16) | (tam[0] & 0xFFFF))
        time.sleep(1.6)
        muc = tim_muc(g)
        if muc is not None:
            self.log('  menu ngữ cảnh: thông điệp (không đụng chuột)')
        if muc is None:
            self.log(f'  menu ngữ cảnh: chuột thật vào tâm ô lưới {tam}')
            self._esc(2)
            # (b) chuột thật, nhưng vào TÂM Ô LƯỚI — vẫn không có số ghim cứng nào
            L, T, W, H = _rect(self.hwnd)
            if not (L <= tam[0] < L + W and T <= tam[1] < T + H):
                raise MidasError(f'tâm ô lưới {tam} nằm ngoài cửa sổ Midas '
                                 f'{(L, T, W, H)} — không bấm mù ra ngoài.')
            from pywinauto import mouse
            for dy in (0, -gh // 4, gh // 4):
                g = _dinh(self.pid)
                mouse.right_click(coords=(tam[0], tam[1] + dy))
                time.sleep(1.6)
                muc = tim_muc(g)
                if muc:
                    break
                self._esc(2)
        if muc is None:
            # Dọn TRƯỚC khi ném lỗi. Bản trước ném thẳng, nên bảng kết quả của
            # mặt cắt hỏng vẫn nằm đó khi mặt cắt sau bắt đầu — và mặt cắt sau
            # hỏng theo ở chỗ khác hẳn ("không thấy Records Activation Dialog"),
            # che mất nguyên nhân thật. Đúng khuôn đã thấy: 1 lỗi thành 2 lỗi.
            self._esc(3)
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


def _duong_dan(mct: str):
    """(tên mặt cắt, thư mục, .mcb, .xls, topo) suy từ đường dẫn MCT."""
    thu_muc = os.path.dirname(os.path.abspath(mct))
    ten = os.path.basename(thu_muc)
    return (ten, thu_muc,
            os.path.splitext(os.path.abspath(mct))[0] + '.mcb',
            os.path.join(thu_muc, f'Beam Force_{ten}.xls'),
            os.path.join(thu_muc, f'{ten}_topo.json'))


def _chay(s: 'MidasSession', mct, xls=None, mcb=None) -> dict:
    """Ba bước trên một phiên đã mở. Dùng chung cho chạy một và chạy loạt."""
    ten, _tm, mcb_md, xls_md, topo = _duong_dan(mct)
    s.log(f'[{ten}] nạp MCT…')
    s.import_mct(mct)
    s.log(f'[{ten}] phân tích…')
    s.analyze(mcb or mcb_md)
    s.log(f'[{ten}] xuất Beam Force…')
    s.export_beam_force(xls or xls_md)
    return s.kiem_ket_qua(xls or xls_md, topo)


def _chuan(p: str) -> str:
    """Đường dẫn chuẩn hoá để so sánh.

    `realpath` chứ không `abspath`: `tempfile.gettempdir()` trả dạng 8.3
    (`C:\\Users\\VUPQ~1.CIT\\...`) khi biến môi trường TEMP mang dạng đó, còn tiêu
    đề Midas luôn là đường dẫn dài. So chuỗi thì hai cái không bao giờ khớp.
    """
    return os.path.normcase(os.path.realpath(p))


def _la_tai_lieu_cua_driver(tieu_de: str, cua_minh=()) -> bool:
    """Tài liệu đang mở có phải do chính driver tạo ra không?

    `moi_tai_lieu()` trả lời **No** cho hộp hỏi lưu, tức nó BỎ thay đổi chưa lưu.
    Với tài liệu driver tự tạo thì vô hại (mô hình đã lưu ra `.mcb`, phần còn lại
    chỉ là chuyện hiển thị), nhưng gọi thẳng nó khi người dùng đang mở mô hình
    của mình thì mất việc không hoàn lại được — nên không được nới `kiem_tai_lieu_sach()`
    một cách chung chung.

    Hai dấu hiệu, đều là dấu hiệu CHẮC CHẮN chứ không phải phỏng đoán:

    1. Đường dẫn nằm dưới thư mục tạm của hệ thống — mọi hộp cát của driver đều ở
       đó, mô hình thật của người dùng thì không.
    2. Đường dẫn **trùng đúng** `.mcb` mà chính lượt chạy này sắp ghi đè (`cua_minh`).
       Chạy driver trên `output/<tên>/` thì tài liệu để lại **cũng là của driver**,
       chỉ khác là không nằm trong thư mục tạm — dấu hiệu (1) một mình bỏ sót đúng
       trường hợp đó, và driver từ chối chính sản phẩm của nó ở lượt chạy ngay sau,
       kèm câu "hãy lưu rồi File › New" hoàn toàn lạc đề. Trùng đúng đường dẫn đích
       thì đằng nào file đó cũng bị ghi đè ở bước `analyze()`, nên mở lại nó không
       làm mất thêm gì.
    """
    m = re.search(r'\[([A-Za-z]:\\[^\]]+)\]', tieu_de)
    if not m:
        return False
    try:
        p = _chuan(m.group(1))
        # Tiêu đề Midas không mang đuôi file; `cua_minh` là các đường dẫn `.mcb`.
        if any(p == _chuan(os.path.splitext(q)[0]) for q in cua_minh):
            return True
        tam = _chuan(tempfile.gettempdir())
        return os.path.commonpath([p, tam]) == tam
    except (ValueError, OSError):
        return False


def chay_mot_mat_cat(mct: str, xls: str = None, mcb: str = None, log=print) -> dict:
    """Nạp → giải → xuất cho MỘT mặt cắt. Trả thống kê của `kiem_ket_qua`."""
    ten = _duong_dan(mct)[0]
    with MidasSession.attach() as s:
        s.log = log
        # Nhánh chạy loạt dọn rồi về tài liệu trống trước mỗi mặt cắt; nhánh chạy
        # một mặt cắt thì không — nên chạy lại đúng một mặt cắt sau một lượt loạt
        # là trượt ngay ở cổng `kiem_tai_lieu_sach()`, vì lý do chẳng liên quan gì
        # tới mặt cắt đó. Chỉ tự dọn khi tài liệu đang mở là của driver.
        if _la_tai_lieu_cua_driver(s.tieu_de, [mcb or _duong_dan(mct)[2]]):
            s.don_dep()
            s.moi_tai_lieu()
        tk = _chay(s, mct, xls, mcb)
    log(f'[{ten}] {tk["ban_ghi"]:,} bản ghi · {tk["phan_tu"]} phần tử · '
        f'{tk["truong_hop_tai"]} trường hợp tải')
    return tk


def chay_nhieu_mat_cat(danh_sach, log=print, on_xong=None, on_loi=None) -> dict:
    """Chạy nhiều mặt cắt liên tiếp trên MỘT phiên Midas.

    **Một mặt cắt lỗi không được dừng cả loạt** — cùng lối với `GenerateWorker`
    của app: mỗi việc bọc `try/except` riêng, lỗi ghi lại rồi đi tiếp. Chạy 6 mặt
    cắt mà cái thứ hai làm sập cả loạt thì người dùng phải ngồi canh, tức là mất
    hết ý nghĩa của việc tự động hoá.

    Giữa hai mặt cắt phải **dọn** (đóng hộp thoại sót) rồi **về tài liệu trống**.
    Bỏ bước đó thì mặt cắt sau gặp cổng `kiem_tai_lieu_sach()` và trượt hàng loạt
    vì một lý do chẳng liên quan gì tới nó.

    `on_xong(tên, thống_kê, xls)` / `on_loi(tên, thông_điệp)` được gọi **ngay sau
    từng mặt cắt**, không phải đợi hết loạt. GUI cần vậy để cập nhật tiến độ và
    gán luôn file Beam Force vào project; nếu chỉ trả kết quả ở cuối thì một loạt
    6 mặt cắt là 6 lần chạy Midas mà thanh tiến độ đứng im từ đầu tới cuối.

    Đây cũng là lý do GUI **gọi thẳng hàm này** chứ không tự viết vòng lặp riêng:
    cổng an toàn `kiem_tai_lieu_sach()` và phần dọn giữa hai mặt cắt chỉ nên có
    một bản. Hai bản là sớm muộn cũng lệch — đúng kiểu `run.py` từng quên ghi
    `topo.json` trong khi nhánh GUI vẫn ghi.

    Returns:
        {'xong': {tên: thống kê}, 'loi': {tên: thông điệp}}
    """
    xong, loi = {}, {}
    # Mọi `.mcb` mà loạt này sẽ ghi — dùng để nhận ra tài liệu do chính driver
    # để lại, kể cả khi nó nằm ở `output/<tên>/` chứ không phải thư mục tạm.
    cua_minh = [_duong_dan(m)[2] for m in danh_sach]
    with MidasSession.attach() as s:
        s.log = log
        for i, mct in enumerate(danh_sach, 1):
            ten = _duong_dan(mct)[0]
            log(f'\n── {i}/{len(danh_sach)}: {ten} ' + '─' * max(0, 44 - len(ten)))
            try:
                s.don_dep()
                # `moi_tai_lieu()` trả lời **No** cho hộp hỏi lưu, tức BỎ thay đổi
                # chưa lưu. Bản trước gọi nó vô điều kiện, kể cả ở mặt cắt ĐẦU —
                # nên chạy loạt lúc người dùng đang mở mô hình sửa dở thì mất việc
                # không hoàn lại được, mà cổng `kiem_tai_lieu_sach()` bị đi vòng
                # hoàn toàn. Chỉ được bỏ thay đổi của tài liệu do chính driver tạo.
                if _la_tai_lieu_cua_driver(s.tieu_de, cua_minh):
                    s.moi_tai_lieu()
                else:
                    s.kiem_tai_lieu_sach()
                tk = _chay(s, mct)
                xong[ten] = tk
                log(f'[{ten}] ĐẠT · {tk["ban_ghi"]:,} bản ghi · '
                    f'{tk["phan_tu"]} phần tử · {tk["truong_hop_tai"]} trường hợp tải')
                if on_xong:
                    on_xong(ten, tk, _duong_dan(mct)[3])
            except MidasError as e:
                loi[ten] = str(e)
                log(f'[{ten}] HỎNG · {e}')
                if on_loi:
                    on_loi(ten, str(e))
            except Exception as e:                 # lỗi lạ cũng không được dừng loạt
                loi[ten] = f'{type(e).__name__}: {e}'
                log(f'[{ten}] HỎNG · {type(e).__name__}: {e}')
                if on_loi:
                    on_loi(ten, f'{type(e).__name__}: {e}')
        sot = s.don_dep()
        if sot:
            log(f'\nCòn hộp thoại không đóng được: {", ".join(sot)}')

    log(f'\n{len(xong)} đạt · {len(loi)} hỏng')
    for ten, tk in xong.items():
        log(f'  ĐẠT   {ten:8s} {tk["ban_ghi"]:>7,} bản ghi · '
            f'{tk["truong_hop_tai"]:2d} trường hợp tải')
    for ten, e in loi.items():
        log(f'  HỎNG  {ten:8s} {e[:80]}')
    return {'xong': xong, 'loi': loi}


if __name__ == '__main__':
    import argparse
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('mct', nargs='+', help='một hoặc nhiều file MCT (hoặc thư mục output)')
    ap.add_argument('-o', '--out', help='file .xls xuất ra (chỉ khi có đúng một MCT)')
    a = ap.parse_args()

    # Nhận cả thư mục: `output/` → mọi <tên>/<tên>_frame.mct bên dưới.
    ds = []
    for p in a.mct:
        if os.path.isdir(p):
            for ten in sorted(os.listdir(p)):
                m = os.path.join(p, ten, f'{ten}_frame.mct')
                if os.path.exists(m):
                    ds.append(m)
        else:
            ds.append(p)
    if not ds:
        print('Không thấy file MCT nào.')
        sys.exit(1)

    try:
        if len(ds) == 1:
            chay_mot_mat_cat(ds[0], a.out)
        else:
            kq = chay_nhieu_mat_cat(ds)
            sys.exit(1 if kq['loi'] else 0)
    except MidasError as e:
        print(f'\n{e}\n')
        sys.exit(1)

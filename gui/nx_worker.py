"""
Kiểm chéo nội lực bằng MIDAS CIVIL NX — chạy ở luồng nền cho thẻ *Kiểm chéo NX*.

Vì sao có lớp này
─────────────────
Cả quy trình đứng trên **một** phép giải: Civil 2022 đọc MCT ta sinh rồi trả nội
lực, và bảng kiểm toán tin con số đó. Cho một bản Midas khác giải lại đúng file
`.mcb` ấy là phép kiểm độc lập rẻ nhất — ba lệnh HTTP, không chạm chuột, ~10 s
một mặt cắt. Lõi đã có sẵn ở `tools/nx_crosscheck.py`; lớp này chỉ đưa nó ra
giao diện.

Lớp này **không** tự viết lại vòng lặp so sánh
──────────────────────────────────────────────
Nó gọi thẳng `tim()` · `mot_mat_cat()` · `dat()` của `tools/nx_crosscheck.py`,
đúng lý do `MidasWorker` gọi `chay_nhieu_mat_cat()`: hai bản của cùng một phép
tính thì sớm muộn cũng lệch nhau, và lệch ở chỗ không ai soi. Ngưỡng đạt/hỏng,
cách chép `.mcb` sang hộp cát, cách phân loại tải cơ bản từ `db/STLD` — tất cả
chỉ được có **một** bản duy nhất, và bản đó là CLI đã chạy thật 4/4 mặt cắt.

Bốn ràng buộc mang từ đường CLI sang
────────────────────────────────────
1. **Không mở, không đóng, không điều khiển NX qua giao diện.** Phiên NX là của
   người dùng; ở đây chỉ đi qua API.
2. `kiem_tai_lieu_sach()` phải chạy **trước** lệnh mở đầu tiên — `doc/OPEN` đè
   lên tài liệu đang mở mà không hỏi gì.
3. Điểm dừng đặt **giữa hai mặt cắt**. Cắt ngang lúc NX đang giải thì để lại
   một tài liệu dở trong phiên của người dùng.
4. Lỗi của `NXError` đã là câu viết sẵn cho người dùng (thiếu MAPI-Key, NX chưa
   mở, tài liệu lạ đang mở) — đưa **nguyên văn** ra nhật ký, đừng bọc thêm.
"""

import traceback

from PyQt6.QtCore import QThread, pyqtSignal


def nap_loi_kiem_cheo():
    """Nạp lõi kiểm chéo, trả `(NX, NXError, loi)` — `loi` là chính module
    `tools/nx_crosscheck.py` (dùng `loi.tim`, `loi.mot_mat_cat`, `loi.dat`).

    Tách riêng vì hai lý do:

    * `requests` chỉ cần cho đường NX. Nạp lười ở đây thì máy thiếu thư viện
      vẫn mở được app, và người dùng nhận một câu giải thích thay vì traceback
      lúc khởi động.
    * `tools/` **không** nằm trong đồ thị phụ thuộc của `run_gui.py`, nên bản
      đóng gói chỉ có `tools.nx_crosscheck` khi `build.bat` kê nó vào
      `--hidden-import`. Thiếu thì lỗi **chỉ lộ ra ở bản `.exe`** — đúng khuôn
      bẫy CLAUDE.md đã ghi cho `requests`. Đường lui đọc thẳng file bên cạnh mã
      nguồn để lúc chạy từ repo thì không phụ thuộc thứ tự `sys.path`.

    Test giả lập lõi bằng cách thay chính hàm này — nhờ vậy phần điều phối
    (thứ tự cổng an toàn, điểm dừng, cách báo lỗi) kiểm được mà không cần NX.
    """
    from src.midas_nx import NX, NXError
    try:
        import tools.nx_crosscheck as loi
    except ImportError:
        import importlib.util
        import os
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'tools', 'nx_crosscheck.py')
        spec = importlib.util.spec_from_file_location('nx_crosscheck', p)
        if spec is None or spec.loader is None:
            raise
        loi = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loi)
    return NX, NXError, loi


class NXWorker(QThread):
    """Giải lại một danh sách `.mcb` bằng NX rồi so với bảng của Civil 2022.

    Mỗi job là `{'ten', 'mcb', 'xls', 'ra'}` — `ra` là thư mục ghi
    `nx_crosscheck_<tên>.json`, đúng chỗ `tools/nx_crosscheck.py` vẫn ghi.
    """
    log = pyqtSignal(str)
    section_done = pyqtSignal(str, dict, bool)   # tên, kết quả, đạt hay không
    section_error = pyqtSignal(str, str)         # tên, thông báo lỗi
    finished_all = pyqtSignal(int, int)          # số đạt, số hỏng

    def __init__(self, jobs: list, cua_minh=(), dung_sai=0.011,
                 dung_sai_bao=0.01):
        super().__init__()
        self.jobs = list(jobs)
        # `(số nút, số phần tử)` của những mô hình app biết chắc là của mình.
        # MAPI **không** có endpoint nào trả tên file đang mở, nên đây là dấu
        # hiệu duy nhất để `kiem_tai_lieu_sach()` phân biệt sản phẩm của lượt
        # trước với mô hình người dùng đang làm dở. App biết sẵn hai con số đó
        # (`Section.n_nodes/n_elems`) nên nói ra, thay vì để lõi phải đoán —
        # cùng lối với `cua_minh_them` của `MidasWorker`.
        self.cua_minh = {tuple(x) for x in cua_minh}
        self.dung_sai = dung_sai
        self.dung_sai_bao = dung_sai_bao

    def xin_dung(self):
        """Xin dừng tác vụ này.

        Không dùng `requestInterruption()` một mình được: Qt bỏ qua nó khi
        luồng CHƯA chạy, mà cơ chế dừng thì không nên phụ thuộc trạng thái
        luồng — nhất là khi test gọi thẳng `run()`. Cờ riêng luôn đúng, cờ
        Qt giữ lại cho các đường khác của Qt.
        """
        self._xin_dung = True
        self.requestInterruption()

    def _nen_dung(self) -> bool:
        if getattr(self, "_xin_dung", False):
            return True
        return self.isInterruptionRequested()

    def run(self):
        try:
            NX, NXError, loi = nap_loi_kiem_cheo()
        except Exception as e:
            self.log.emit(
                f'ERROR: không nạp được phần kiểm chéo NX — {e}. '
                f'Bản đóng gói phải kê "src.midas_nx" và "tools.nx_crosscheck" '
                f'trong hidden-import, và KHÔNG được loại trừ requests/urllib3/'
                f'certifi.')
            self.finished_all.emit(0, len(self.jobs))
            return

        try:
            nx = NX(log=self.log.emit)
            don_vi = nx.song()
            # PHẢI đứng trước lệnh mở đầu tiên: `doc/OPEN` đè lên tài liệu đang
            # mở, không hỏi gì.
            nx.kiem_tai_lieu_sach(self.cua_minh)
        except NXError as e:
            # `NXError` đã mang sẵn câu chỉ đường (mở NX, bấm Apps → API
            # Settings → Connect, đóng tài liệu lạ…). Đưa nguyên văn.
            self.log.emit(f'ERROR: {e}')
            self.finished_all.emit(0, len(self.jobs))
            return
        except Exception as e:
            self.log.emit(f'ERROR: không gọi được API của NX — {e}')
            self.log.emit(traceback.format_exc())
            self.finished_all.emit(0, len(self.jobs))
            return

        self.log.emit(f'NX sẵn sàng · đơn vị {don_vi.get("1", {})}')

        so_dat = so_hong = 0
        for job in self.jobs:
            # Huỷ HỢP TÁC, xét GIỮA hai mặt cắt. Cắt ngang lúc NX đang giải thì
            # để lại một tài liệu dở trong phiên của người dùng, mà ta thì
            # không được phép đóng nó hộ.
            if self._nen_dung():
                self.log.emit(
                    f'■ Đã dừng theo yêu cầu — xong {so_dat + so_hong}/'
                    f'{len(self.jobs)} mặt cắt.')
                break
            ten = job['ten']
            self.log.emit(f'── {ten} · giải lại bằng NX')
            try:
                kq = loi.mot_mat_cat(nx, ten, job['mcb'], job['xls'],
                                     self.dung_sai, self.dung_sai_bao,
                                     job['ra'])
            except NXError as e:
                so_hong += 1
                self.section_error.emit(ten, str(e))
                continue
            except Exception as e:
                so_hong += 1
                self.section_error.emit(ten, str(e))
                self.log.emit(traceback.format_exc())
                continue
            ok = loi.dat(kq)
            so_dat, so_hong = so_dat + bool(ok), so_hong + (not ok)
            self.section_done.emit(ten, dict(kq), bool(ok))

        self.finished_all.emit(so_dat, so_hong)

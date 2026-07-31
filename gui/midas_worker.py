"""
Chạy Midas/Civil từ trong app — bước ③ của quy trình.

**Tính năng này mặc định TẮT, và đó là chủ ý.** Đường ưu tiên vẫn là VuPQ tự mở
Midas rồi tự bấm: driver lái Midas qua chính giao diện của nó (không có COM,
không có API), nên trong lúc chạy nó chiếm ribbon và tiền cảnh — **máy không dùng
được**. Một công cụ giành lấy chuột và bàn phím thì không được phép tự bật.

Bật ở `Tùy chọn → Midas`. Khi tắt, mục menu vẫn hiện nhưng bị khoá, kèm chú thích
chỉ đường — giấu hẳn thì người dùng không biết là có.

Lớp này **không** tự viết lại vòng lặp chạy loạt. Nó gọi
`src.midas_driver.chay_nhieu_mat_cat()` và nhận tín hiệu qua callback, để cổng an
toàn (`kiem_tai_lieu_sach`, dọn giữa hai mặt cắt, nhận diện tài liệu của driver)
chỉ có **một bản duy nhất**. Hai bản là sớm muộn cũng lệch — `run.py` từng quên
ghi `topo.json` suốt nhiều tháng trong khi nhánh GUI vẫn ghi đủ.
"""

import traceback

from PyQt6.QtCore import QThread, pyqtSignal


class MidasWorker(QThread):
    """Nạp MCT → Perform Analysis → xuất Beam Force cho một danh sách mặt cắt.

    Mỗi job là `{'name', 'mct'}`. Tên file Beam Force do driver tự suy từ thư mục
    chứa MCT (`output/<tên>/Beam Force_<tên>.xls`), đúng chỗ tab Kết quả tìm.
    """
    log = pyqtSignal(str)
    section_done = pyqtSignal(str, str, dict)   # name, đường dẫn xls, thống kê
    section_error = pyqtSignal(str, str)        # name, thông báo lỗi
    finished_all = pyqtSignal(int, int)         # số đạt, số hỏng

    def __init__(self, jobs: list, cua_minh_them=()):
        super().__init__()
        self.jobs = jobs
        # `.mcb` của MỌI mặt cắt trong project, kể cả mặt cắt không nằm trong
        # lượt này: sau một lượt chạy, Midas còn giữ tài liệu của mặt cắt cuối,
        # và lượt sau sẽ gặp nó ở cổng an toàn. App biết chắc những file đó do
        # chính nó sinh ra nên nói ra, thay vì để driver phải đoán.
        self.cua_minh_them = list(cua_minh_them)

    def run(self):
        try:
            from src.midas_driver import chay_nhieu_mat_cat
        except Exception as e:
            # pywinauto/comtypes thiếu thì nói thẳng, đừng để traceback thô.
            self.log.emit(f'ERROR: không nạp được driver Midas — {e}')
            self.finished_all.emit(0, len(self.jobs))
            return

        def _xong(ten, tk, xls):
            self.section_done.emit(ten, xls, dict(tk))

        def _loi(ten, msg):
            self.section_error.emit(ten, msg)

        try:
            kq = chay_nhieu_mat_cat([j['mct'] for j in self.jobs],
                                    log=self.log.emit,
                                    on_xong=_xong, on_loi=_loi,
                                    cua_minh_them=self.cua_minh_them)
        except Exception as e:
            # `attach()` ném khi không có Midas, có nhiều cửa sổ, hay tài liệu
            # chưa sạch — đó là thông điệp đã viết sẵn cho người dùng, đưa
            # nguyên văn ra nhật ký chứ đừng bọc thêm.
            self.log.emit(f'ERROR: {e}')
            self.log.emit(traceback.format_exc())
            self.finished_all.emit(0, len(self.jobs))
            return

        self.finished_all.emit(len(kq['xong']), len(kq['loi']))

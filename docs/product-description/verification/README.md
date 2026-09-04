# Kiểm chứng bằng tay

Các tài liệu tính năng được soạn từ mã nguồn và bài test. Thư mục này là quy trình đối chiếu chúng với **sản phẩm chạy thật**, mỗi lần một khẳng định quan sát được.

## Ở đây có gì

| File | Phủ |
| --- | --- |
| [khung-xem.md](khung-xem.md) | `khung-xem/*` |
| quy-trinh.md | `quy-trinh/*` (chưa soạn) |
| kiem-toan.md | `kiem-toan/*` và `so-lieu/*` (chưa soạn) |

Mỗi file có một bảng cho mỗi tài liệu. Mỗi hàng là một mục kiểm, gồm mã cố định (`GOI-07`), mức ưu tiên, thứ cần có, khẳng định kèm liên kết tới đúng mục trong tài liệu, bước dựng, các bước bấm, kết quả trông đợi, và cột Kết quả để người kiểm điền. Mục nào không kiểm bằng tay được thì liệt kê riêng dưới mỗi tài liệu.

Mức ưu tiên: **P1** là sự thật nền tảng, khẳng định mà nhiều tài liệu khác dựa vào, hoặc một lỗi bị nghi. **P2** là khẳng định thường. **P3** là một con số, một màu, một khoảng thời gian.

## Cách chạy một lượt

1. **Dựng bề mặt.** Chạy `python run_gui.py` từ gốc repo. Trạng thái sạch cho một lượt kiểm:
   - Đặt biến môi trường `MTB_DATA_DIR` trỏ tới một thư mục tạm **trước khi mở app**, nếu không lượt kiểm sẽ đốt mất ngày dùng thử của máy và ghi vào `%ProgramData%` thật.
   - Trong *Tuỳ chọn*, đưa về mặc định lần chạy đầu: bảng màu **Sáng**, màu nhấn **Xanh kỹ thuật**, mật độ **Vừa**, cỡ chữ **10pt**. Nhiều mục P3 nói về màu và khoảng cách nên chỉ đúng ở bộ mặc định này.
   - Mở project mẫu, hoặc thêm `input/dxf/S1.dxf` rồi tạo MCT để có một mặt cắt ở trạng thái `generated`.
   - Dọn sau lượt kiểm: xoá thư mục `MTB_DATA_DIR` tạm, và xoá mọi gối tự đặt bằng nút **Mặc định** nếu định chạy lại.

2. **Xác nhận commit.** Mọi tài liệu ghi `Đối chiếu với commit \`{sha}\``. Chạy `git -c safe.directory=H:/VuPQ_Tools/Midas-Transverse-Boxgirder rev-parse --short HEAD`. Khác nhau thì tài liệu đang mô tả một bản khác, và một số mục hỏng sẽ là **trôi phiên bản** chứ không phải lỗi.

3. **Mở tài liệu bên cạnh app.** Đọc mục được liên kết trước mỗi lần kiểm; hàng trong bảng chỉ là bản tóm tắt, khẳng định thật nằm trong tài liệu.

4. **Làm hết P1 trước** trên mọi file, rồi P2, rồi P3.

5. **Ghi `đạt`, `hỏng`, hoặc `tắc`** vào cột Kết quả, kèm ghi chú cho mọi thứ không phải đạt sạch. *Hỏng* là điều tài liệu nói mà sản phẩm không làm. *Tắc* là mục không chạy được (thiếu thiết bị, thiếu file, một mục hỏng trước đó chặn đường).

6. **Ghi mọi mục hỏng vào [`bug-triage.md`](../bug-triage.md).** Đã có mục tương ứng thì thêm dòng **Trạng thái** trích mã mục kiểm; chưa có thì thêm mục mới với mã mục kiểm ở phần *Nêu bởi*. **Một mục hỏng không đương nhiên là lỗi của sản phẩm** — đôi khi tài liệu sai, và bản sửa là sửa tài liệu. Dòng Trạng thái phải nói rõ là bên nào sai.

7. **Khi mọi mục P1 và P2 của một tài liệu đã đạt hoặc đã được ghi nhận**, đổi hàng của nó trong mục *bảng độ phủ* trong [README.md](../README.md) từ `đã soạn` sang `đã kiểm`.

## Thiết bị và điều kiện

- **chuột** — chuột thật có bánh lăn. Bánh lăn của chuột và bàn di cảm ứng **không giống nhau**: bàn di báo cuộn theo quán tính, nên số nấc phóng khác đi. Mọi mục nói về nấc lăn phải chạy bằng chuột thật.
- **bàn phím** — bàn phím vật lý. Chú ý: nhiều phím tắt của khung xem chỉ ăn khi **khung xem đang giữ tiêu điểm**; bấm vào canvas một lần trước khi thử phím.
- **hai màn hình** — vài mục về vị trí cửa sổ chỉ lộ ra khi app mở trên màn hình phụ. Đây cũng là điều kiện đã từng làm lộ một lỗi thật của trình điều khiển Midas.
- **Midas Civil 2022 đang mở** — chỉ cần cho các mục về chạy Midas. Máy không có Civil 2022 thì những mục đó là `tắc`, không phải `hỏng`.
- **file cụ thể** — `input/dxf/S1.dxf` (một hộp), `data/TP_BL/S1_V2.dxf` (hai hộp), `input/dxf/SLT.dxf` (hai hộp, mặt cầu dốc một chiều). Vài mục cần đúng mặt cắt hai hộp vì mặt cắt một hộp không lộ ra hành vi đang xét.
- **hết dùng thử** — không giả lập được bằng tay trong một lượt kiểm. Các mục cần điều kiện này nằm ở phần *Không kiểm bằng tay được*.

## Lái sản phẩm bằng script

App không có console cho người dùng, nhưng **dựng được widget thật trong Python** và phát sự kiện chuột, phím thật vào đó. Cách này tốt cho ba việc:

- dựng trạng thái ban đầu chính xác (nạp đúng một `*_topo.json`, đặt đúng danh sách gối);
- **đọc trạng thái trở lại** sau một tương tác thật, cho những mục mà kết quả trông đợi là một trạng thái chứ không phải một thứ nhìn thấy được;
- đo những con số mà mắt không đọc được, ví dụ điểm mô hình nằm dưới con trỏ trước và sau một nấc lăn.

Đầu vào vẫn phải là **đầu vào thật** ở những mục nói về đầu vào: phát `QMouseEvent` vào widget, đừng gọi thẳng hàm nội bộ — nếu không kết quả nói về việc các hàm gọi nhau thế nào chứ không nói về việc người dùng làm gì.

Script **không** làm được: mọi thứ về diện mạo (màu, khoảng cách, chữ bị cắt) vì widget chạy ẩn không vẽ ra; cảm giác của một cú kéo; thời gian chờ thật của Midas. Ba công cụ sẵn có của dự án chia nhau phần này: `tools/check_gui.py` bấm thật rồi so chữ người dùng đọc được, `tools/audit_gui.py` kích hoạt mọi điều khiển, `tools/render_ui.py` chụp ảnh mọi thẻ để soi bằng mắt.

**Một lượt chạy bằng script không đủ để đánh dấu tài liệu là `đã kiểm`.**

## Kết quả tới nay

Chưa có lượt kiểm tay nào.

Đã chạy **một lượt bằng script** ngày 2026-09-04, đối chiếu commit `ab1e907`, trên `output/S1/S1_topo.json`, dựng `FrameView` thật rồi phát sự kiện chuột thật. Lượt này chạy 4 mục của [khung-xem.md](khung-xem.md) và cho kết quả:

| Mục | Kết quả |
| --- | --- |
| `GOI-01` tắt chế độ giữa lúc kéo | **hỏng** → [B-01](../bug-triage.md#b-01) |
| `GOI-02` bấm node đã có gối | **đạt** (xác nhận đúng điều tài liệu nói: không có phản hồi nào) → [B-06](../bug-triage.md#b-06) |
| `GOI-03` bán kính chạm 14 điểm ảnh | **đạt**, và bác bỏ một khẳng định sai trong bản đầu của tài liệu |
| `XEM-01` phóng quanh con trỏ | **hỏng** → [B-04](../bug-triage.md#b-04) |

Lượt này **không** phủ: bất cứ thứ gì nhìn thấy được (cửa sổ chạy ẩn, không có gì được vẽ ra), cảm giác của cú kéo, thời gian phản hồi, và toàn bộ các mục cần Midas. **Chưa tài liệu nào được đánh dấu `đã kiểm`**, vì đánh dấu như vậy đòi một lượt bấm tay.

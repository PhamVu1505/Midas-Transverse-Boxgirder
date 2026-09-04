# Mô tả sản phẩm — Midas Transverse Boxgirder

Bản mô tả trải nghiệm người dùng của Midas Transverse Boxgirder: người dùng thấy gì, làm được gì, và chính xác thì điều gì xảy ra khi họ làm.

## Mục đích

Từ phía người dùng, phần mềm này là một **máy trạng thái lớn**. Kỹ sư đi qua nó bằng chuột, phím tắt, phím bổ trợ, ô nhập, và những tác vụ chạy nền có thể mất hàng phút. Phần lớn hành vi ấy đang được định nghĩa **ngầm**, nằm rải trong `gui/` (widget, hộp thoại, worker), `src/` (đọc DXF, dựng khung, ghi MCT, kiểm toán) và trong các bài test. Không có chỗ nào nói bằng lời thường rằng: *"người dùng làm X thì điều này xảy ra, và nếu họ làm Y giữa chừng thì điều kia xảy ra."*

Tập tài liệu này là chỗ đó. Nó mô tả toàn bộ trải nghiệm trên **một bề mặt**: cửa sổ chính của app chạy với tuỳ chọn mặc định, một project đang mở.

Người đọc là người cần hiểu hoặc sửa sản phẩm: người thiết kế, người viết mã, người viết tài liệu, người kiểm thử, và bất kỳ ai đang phải quyết định xem một hành vi là **cố ý** hay là **lỗi**. Tài liệu viết từ ngoài vào. Nó mô tả trải nghiệm, không mô tả cách cài đặt.

### Đây không phải là gì

- **Không phải tài liệu API.** Kiến trúc và giao diện lập trình nằm ở `docs/ARCHITECTURE.md` và `CLAUDE.md`.
- **Không tổ chức theo module.** `frame_builder`, `mct_frame_writer`, `result_reader` không có tài liệu riêng. Một hành vi được mô tả đúng một lần, ở nơi người dùng gặp nó.
- **Không phải tài liệu thiết kế kỹ thuật.** Chỗ nào chi tiết kỹ thuật thay đổi điều người dùng trông đợi thì nó nằm trong khối trích dẫn `Ghi chú kỹ thuật:`, và không ở đâu khác.
- **Không phải hướng dẫn sử dụng.** `docs/USER-GUIDE.txt` dạy cách dùng; tập này mô tả hành vi, gồm cả hành vi đáng ngờ.

## Quy ước

- Mô tả trải nghiệm, không mô tả mã. Viết *"Nút Tạo MCT bị khoá cho tới khi mặt cắt có template"*, không viết *"`_sync_actions()` gọi `setEnabled(bool(tpl))`"*.
- Chi tiết kỹ thuật đặt trong khối trích dẫn mở đầu bằng `Ghi chú kỹ thuật:`.
- Tiêu đề viết như câu thường, không viết hoa đầu mỗi từ.
- Dùng từ nhất quán. [Bảng từ](glossary.md) là nguồn sự thật cho các từ như *mặt cắt*, *project*, *tác vụ*, *cổng giấy phép*, *khung xem*, *điểm kiểm toán*, *gán kết quả*.
- Mỗi tài liệu kết thúc bằng mã commit đã đối chiếu và danh sách câu còn để ngỏ.
- Hành vi gây bất ngờ thì nói thẳng là bất ngờ, kèm lý do nếu mã hoặc chú thích có nói. Không làm nhẹ đi.

## Việc phải làm

Mỗi tài liệu mô tả một tính năng. Tính năng có thể lớn (*thẻ Kiểm toán mặt cắt*) hoặc rất nhỏ (*dòng truy vấn dưới khung xem*), nhưng cái nào cũng được mô tả đầy đủ, gồm cả trường hợp biên và tương tác với tính năng khác.

### Khuôn tài liệu

Mọi tài liệu tính năng dùng chung một khuôn tám mục, để so sánh được với nhau và để không bỏ sót gì.

1. **Tóm tắt.** Một đoạn mô tả tính năng ở mức trừu tượng, rồi một hai câu nói nó nằm ở đâu, mở bằng gì, dấu hiệu nào cho biết nó đang hoạt động.
2. **Trường hợp đơn giản.** Đường đi thường gặp, viết thành văn.
3. **Diễn biến tương tác, theo từng sự kiện.** Năm chặng của **một tác vụ trên mặt cắt đang chọn** (xem *Hình dạng tương tác* bên dưới), kèm một sơ đồ trạng thái Mermaid `stateDiagram-v2`.
4. **Biến thể.** Bảng các biến thể, và mỗi biến thể làm gì khi đặt lúc mở so với khi đổi giữa chừng.
5. **Huỷ và ngắt.** Cùng một danh sách trong mọi tài liệu.
6. **Tương tác với phần khác.** Các mối bận tâm xuyên suốt, cùng thứ tự trong mọi tài liệu.
7. **Trường hợp biên.**
8. **Câu còn để ngỏ và việc kiểm chứng.**

**Mục 5 là mục quan trọng nhất.** Hỏi cùng một bộ câu hỏi về ngắt quãng cho *mọi* tính năng chính là cách các lỗ hổng lộ ra khi so sánh.

#### Hình dạng tương tác

Đơn vị tương tác của sản phẩm này là **một tác vụ trên mặt cắt đang chọn**. Nó phủ được cả hai loại thao tác có trong app: cử chỉ chuột trên khung xem (kéo gối, kéo pan) và tác vụ chạy nền dài (tạo MCT, chạy Midas, kiểm toán). Năm chặng, đặt tên theo lời của sản phẩm:

| Chặng | Nghĩa |
| --- | --- |
| **Mở** | Cái gì khởi động tác vụ, đích là gì, cái gì được kiểm trước, cái gì được chụp lại để còn khôi phục |
| **Kết thúc ngay** | Tác vụ kết thúc mà chưa thành việc dài: bấm hụt, không có mặt cắt nào chọn, cổng giấy phép từ chối |
| **Thành việc dài** | Cái gì vượt lằn ranh: worker khởi động, hoặc con trỏ bắt đầu kéo. Cái gì bị chốt lại từ khoảnh khắc đó |
| **Đang chạy** | Cái gì cập nhật liên tục, người dùng còn làm được gì, cái gì bị khoá |
| **Kết thúc** | Cái gì được ghi xuống: file trên đĩa, trạng thái mặt cắt, mục nhật ký. Đường hỏng nếu có |

#### Biến thể (cùng bộ hàng trong mọi tài liệu)

| Biến thể |
| --- |
| Shift |
| Ctrl |
| Alt / Space |
| Trạng thái mặt cắt (`new` · `generated` · `assigned` · `checked` · `error`) |
| Cổng giấy phép (đủ phép · dùng thử · bị chặn · thiếu tính năng) |
| Tuỳ chọn liên quan trong *Tuỳ chọn* |

#### Huỷ và ngắt (cùng bộ hàng, cùng thứ tự, trong mọi tài liệu)

1. Người dùng huỷ dứt khoát: Esc, nút Huỷ, đóng hộp thoại
2. Người dùng làm việc khác giữa chừng: đổi mặt cắt đang chọn, đổi thẻ xem, bật/tắt Sửa gối, mở hộp thoại khác
3. Người dùng đóng cửa sổ hoặc thoát app khi tác vụ đang chạy
4. Môi trường hỏng: Midas không phản hồi, phiên Windows bị khoá, hết chỗ đĩa, mất quyền ghi
5. Đích bị đổi: mặt cắt bị xoá khỏi project, DXF bị sửa hoặc xoá trên đĩa
6. File kết quả bị chiếm: Excel đang mở đúng file app sắp ghi
7. Cổng giấy phép đổi trạng thái giữa chừng: hết dùng thử, danh sách chặn về
8. Nguồn nhập đổi: kéo thả file mới khi đang chạy, mục chuột phải mở phiên thứ hai

Ba họ ngắt quãng chuẩn (người dùng tự huỷ · môi trường hỏng · đích bị đổi) đều có mặt; hai hàng 6 và 7 là đặc thù của sản phẩm này.

#### Mối bận tâm xuyên suốt (cùng thứ tự trong mọi tài liệu)

**Cổng giấy phép.** **Project và trạng thái mặt cắt.** **Số liệu template.** **Nhật ký Messages.** **Thanh bước và thanh trạng thái.** **Bảng màu và tuỳ chọn.** **File trên đĩa.** **Midas bên ngoài.**

### Cách làm

1. Đọc nơi giữ trạng thái tương tác (`gui/frame_view.py`, `gui/main_window.py`, `gui/worker.py`, `src/project.py`).
2. Đọc bài test tương ứng trong `tests/`. `tests/test_regression.py` và `tests/test_input_check.py` gần như là đặc tả chạy được của các trường hợp biên.
3. Soạn tài liệu.
4. Thử chỗ nào còn mơ hồ **trên app chạy thật**. Test trả lời *"cái gì xảy ra"*; app chạy thật trả lời *cảm giác thế nào*, *nhìn thấy gì trong lúc đang chạy*, và *mất bao lâu*.
5. Ghi mã commit đã đối chiếu.

### Kiểm chứng

Lúc soạn thì đọc mã; lúc kiểm chứng thì **nhìn sản phẩm**. Thư mục `verification/` giữ một danh mục cho mỗi cụm tài liệu, mỗi mục là một khẳng định quan sát được, kèm bước dựng, các bước bấm, kết quả trông đợi, mức ưu tiên và thiết bị cần. Một tài liệu chỉ chuyển từ `đã soạn` sang `đã kiểm` khi mọi mục P1 và P2 của nó đã đạt hoặc đã được ghi vào `bug-triage.md`.

Ba công cụ sẵn có của dự án là công cụ kiểm chứng tự động, **không thay được người bấm tay**:

| Công cụ | Trả lời |
| --- | --- |
| `tools/check_gui.py` | Bấm vào thì có đúng không (34 phép kiểm, mỗi phép gắn một lỗi đã xảy ra thật) |
| `tools/audit_gui.py` | Có nút nào chết không (62 điều khiển) |
| `tools/render_ui.py` | Nhìn có ổn không (~26 ảnh) |

### Thứ tự việc

1. **Mẫu: [Sửa gối](khung-xem/sua-goi.md).** Nhỏ, gọn, có một cú kéo thật. Dùng để chốt khuôn, giọng văn và độ sâu.
2. **Nền móng.** Mô hình nhập liệu, project và mặt cắt, khung xem, tác vụ nền, số liệu đầu vào, cổng giấy phép. Mọi tài liệu khác trỏ về đây thay vì nhắc lại.
3. **Vùng khó nhất: tạo MCT và kiểm toán mặt cắt.** Phần lớn thời gian của người dùng nằm ở đây, và các trạng thái chuyền tay nhau nên phải đọc hết trước khi viết bất kỳ tài liệu nào của vùng này.
4. **Phần còn lại**, soạn song song, rồi một lượt soát nhất quán và một lượt kiểm chứng trên toàn bộ.

### Quyết định về phạm vi

- **Bề mặt.** Cửa sổ chính của app, tuỳ chọn mặc định lần chạy đầu (Sáng · Xanh kỹ thuật · mật độ Vừa · 10pt), một project đang mở, giao diện tiếng Việt.
- **Ngoài phạm vi:** công cụ nội bộ `tools/license_admin.py` (không phải sản phẩm giao cho người dùng); `run.py` dòng lệnh (sẽ có tài liệu riêng sau); trình cài đặt.
- **Cửa sổ chuột phải** (`gui/quick_mct.py`) là một bề mặt **thứ hai** nhưng nhỏ và dùng chung worker, nên nó có một tài liệu riêng chứ không phải một repo riêng.
- **Cổng giấy phép** mô tả một lần ở `giay-phep/`, các tài liệu khác chỉ trỏ tới. Nhắc lại ở từng chỗ thì sẽ trôi khỏi nhau.
- **Không đánh số quy tắc.** Đây là tài liệu văn xuôi, không phải đặc tả đánh số. Neo tiêu đề là đủ để trỏ chéo.

## Cấu trúc

```
README.md                     file này
goal.md                       chỉ dẫn thường trực cho người soạn
AGENTS.md, CLAUDE.md          điểm vào cho agent
glossary.md                   bảng từ dùng chung
bug-triage.md                 mọi lỗi bị nghi, gộp trùng, kèm bước tái hiện và quyết định cần

verification/
  README.md                   cách chạy một lượt kiểm tay và ghi kết quả
  khung-xem.md                danh mục cho khung-xem/
  quy-trinh.md                danh mục cho quy-trinh/
  kiem-toan.md                danh mục cho kiem-toan/ và so-lieu/

foundations/
  mo-hinh-nhap-lieu.md        chuột, phím, ngưỡng, phím bổ trợ; cái gì huỷ, hoàn tất, ngắt
  project-va-mat-cat.md       project là gì, mặt cắt là gì, năm trạng thái, nguồn sự thật duy nhất
  khung-xem.md                zoom, pan, fit, lớp, ba chế độ vẽ
  tac-vu-nen.md               tác vụ chạy nền: tiến độ, huỷ, lỗi, cái gì ghi xuống đĩa
  so-lieu-dau-vao.md          template Excel, 40 khoá, sheet INPUT, luật thiếu khoá thì báo lỗi

khung-xem/
  sua-goi.md                  đặt, dời, xoá gối trên bản đáy  ← tài liệu mẫu
  tra-node.md                 rê chuột tra node, dòng truy vấn
  che-do-xem.md               Model · Section shape · Parts
  lop-hien-thi.md             bật tắt lớp vẽ

quy-trinh/
  them-dxf.md                 thêm bản vẽ, kéo thả, xem trước
  tao-mct.md                  sinh MCT, hộp thoại hỏi trước, cảnh báo template
  chay-midas.md               chạy Midas tự động, cổng an toàn
  gan-beam-force.md           gán kết quả nội lực vào mặt cắt
  chuot-phai.md               cửa sổ Tạo file MCT từ Explorer

kiem-toan/
  the-kiem-toan.md            nhập cốt thép, chạy kiểm, đọc bảng
  diem-kiem-toan.md           A–H và các điểm phân giải
  bieu-do-bao.md              biểu đồ bao nội lực
  xuat-excel.md               xuất bảng kiểm toán

so-lieu/
  doi-chieu-template.md       cảnh báo hoạt tải, khối Dải tương đương
  input-data.md               tab Input data ở dock Properties

giay-phep/
  cong-giay-phep.md           đăng ký, kích hoạt, dùng thử, bị chặn
  su-dung.md                  nhật ký sử dụng người dùng xem được

xuyen-suot/
  tuy-chon.md                 bảng màu, mật độ, phông, mặc định
  nhat-ky.md                  Messages, bốn mức, huy hiệu
  thanh-buoc.md               năm bước và thanh trạng thái
  file-tren-dia.md            output/, .mtbproj, ghi đè
```

## Độ phủ

Trạng thái là một trong `chưa bắt đầu`, `đã soạn`, `đã kiểm`.

| Tài liệu | Trạng thái |
| --- | --- |
| glossary.md | đã soạn |
| goal.md | đã soạn |
| bug-triage.md | đã soạn |
| verification/ (3 danh mục) | chưa bắt đầu |
| foundations/mo-hinh-nhap-lieu.md | chưa bắt đầu |
| foundations/project-va-mat-cat.md | chưa bắt đầu |
| foundations/khung-xem.md | chưa bắt đầu |
| foundations/tac-vu-nen.md | chưa bắt đầu |
| foundations/so-lieu-dau-vao.md | chưa bắt đầu |
| khung-xem/sua-goi.md | đã soạn |
| khung-xem/tra-node.md | chưa bắt đầu |
| khung-xem/che-do-xem.md | chưa bắt đầu |
| khung-xem/lop-hien-thi.md | chưa bắt đầu |
| quy-trinh/them-dxf.md | chưa bắt đầu |
| quy-trinh/tao-mct.md | chưa bắt đầu |
| quy-trinh/chay-midas.md | chưa bắt đầu |
| quy-trinh/gan-beam-force.md | chưa bắt đầu |
| quy-trinh/chuot-phai.md | chưa bắt đầu |
| kiem-toan/the-kiem-toan.md | chưa bắt đầu |
| kiem-toan/diem-kiem-toan.md | chưa bắt đầu |
| kiem-toan/bieu-do-bao.md | chưa bắt đầu |
| kiem-toan/xuat-excel.md | chưa bắt đầu |
| so-lieu/doi-chieu-template.md | chưa bắt đầu |
| so-lieu/input-data.md | chưa bắt đầu |
| giay-phep/cong-giay-phep.md | chưa bắt đầu |
| giay-phep/su-dung.md | chưa bắt đầu |
| xuyen-suot/tuy-chon.md | chưa bắt đầu |
| xuyen-suot/nhat-ky.md | chưa bắt đầu |
| xuyen-suot/thanh-buoc.md | chưa bắt đầu |
| xuyen-suot/file-tren-dia.md | chưa bắt đầu |

### Độ phủ soát tương tác

Bảng trên đếm tài liệu đã soạn. Bảng này đếm việc khác: **bề mặt nào đã bị soát
tìm lỗi tương tác** và đưa kết quả vào [bug-triage.md](bug-triage.md). Soát tương
tác đi trước việc soạn tài liệu — nó nói cho người soạn biết chỗ nào sẽ phải viết
*"đáng coi là lỗi hơn là đáng ghi thành tài liệu"*.

Bốn câu hỏi của một lượt soát: thao tác bị ngắt giữa chừng · trạng thái và phản
hồi · trường hợp biên · phím tắt ngoài khung xem.

| Bề mặt | Trạng thái | Mã đã nêu |
| --- | --- | --- |
| Khung xem — sửa gối | đã soát | B-01 · B-02 · B-03 · B-04 · B-06 |
| Tác vụ nền (tạo MCT · xử lý Beam Force · chạy Midas) | đã soát | B-10 · B-11 · B-12 · B-13 · B-14 · B-24 |
| Cây mặt cắt và trạng thái mặt cắt | đã soát | B-08 · B-15 · B-17 · B-18 · B-20 · B-23 |
| Số liệu đầu vào (bản vẽ · template) | đã soát | B-07 · B-09 · B-19 |
| Thẻ Kiểm toán mặt cắt — bảng nhập | đã soát | B-16 |
| Thẻ Results table — bảng và hộp thoại | đã soát | B-12 · B-21 |
| Thanh trạng thái và nhật ký | đã soát | B-22 |
| Cửa sổ chuột phải *Tạo file MCT* | đã soát | B-10 |
| Khung xem — tra node, chế độ xem, lớp hiển thị | chưa soát | — |
| Biểu đồ bao nội lực và sơ đồ điểm kiểm toán | chưa soát | — |
| Hộp thoại *Tuỳ chọn* | chưa soát | — |
| Cổng giấy phép và thẻ *Sử dụng* | chưa soát | — |

Ba chỗ **chưa xác định được** và cần bấm tay trên bản đóng gói: thư mục làm việc
thật của app đã cài (xem [B-19](bug-triage.md#b-19)); hành vi khi ngắt *Chạy
Midas* giữa chừng (cần một phiên Midas thật); và điều gì xảy ra với tiến trình
khi thoát app trong lúc một tác vụ nền còn chạy.

## Tham chiếu

Nguồn sự thật là chính repo này, tại `H:\VuPQ_Tools\Midas-Transverse-Boxgirder`. Các vị trí liên quan:

- `run_gui.py`: điểm vào, dựng cửa sổ, áp theme đã lưu trước khi dựng
- `gui/main_window.py`: vỏ ứng dụng, menu, phím tắt, đồng bộ mặt cắt giữa các thẻ
- `gui/frame_view.py`: **nơi giữ trạng thái tương tác của khung xem** — chuột, phím, zoom, pan, sửa gối
- `gui/pan_zoom.py`: zoom/pan dùng chung của sơ đồ điểm kiểm toán và biểu đồ bao
- `gui/worker.py`, `gui/midas_worker.py`: tác vụ chạy nền
- `src/project.py`: **đối tượng miền** — `Project`, `Section`, năm trạng thái
- `src/input_reader.py`: 40 khoá số liệu đầu vào, hằng `SPEC`
- `src/input_check.py`: đối chiếu template với hình học, `live_load_compare()`
- `src/security/guard.py`: cổng giấy phép duy nhất
- `tests/test_regression.py`, `tests/test_input_check.py`, `tests/test_build_script.py`: bài test đọc được như đặc tả
- `tools/check_gui.py`: mỗi phép kiểm gắn với một lỗi giao diện đã xảy ra thật
- `CLAUDE.md`: tiền sử lỗi và các quyết định đã chốt, kèm lý do

Đối chiếu với commit `ab1e907`.

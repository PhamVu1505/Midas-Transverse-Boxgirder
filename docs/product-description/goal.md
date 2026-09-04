# Chỉ dẫn thường trực cho người soạn

Đây là lời nhắc cho bất kỳ ai — người hay agent — ngồi xuống soạn thêm một tài liệu trong tập này.

## Đọc theo thứ tự

1. `README.md` — nhất là mục *Khuôn tài liệu* và *Quyết định về phạm vi*.
2. `glossary.md` — dùng đúng những từ này.
3. `khung-xem/sua-goi.md` — tài liệu mẫu. Nó chốt độ sâu và giọng văn. Tài liệu của bạn phải sâu ngang nó.
4. Tài liệu nền móng mà tính năng của bạn dựa vào.

Rồi mới đọc mã.

## Việc

Viết đúng một tài liệu, theo đủ tám mục của khuôn, cùng độ sâu với tài liệu mẫu. Một tính năng nhỏ làm cho tử tế rơi vào khoảng 150–200 dòng; tính năng khó nhất khoảng 250–300.

Soạn từ **mã nguồn và bài test**. Rồi thử những chỗ còn mơ hồ **trên app chạy thật**. Bài test trả lời *"cái gì xảy ra"*; app chạy thật trả lời *cảm giác thế nào*, *nhìn thấy gì trong lúc đang chạy*, và *mất bao lâu*.

## Luật viết

- **Mô tả trải nghiệm, không mô tả mã.** Viết *"Nút Tạo MCT bị khoá cho tới khi mặt cắt có template"*, không viết *"`_sync_actions()` gọi `setEnabled()`"*.
- Chi tiết kỹ thuật chỉ đặt trong khối trích dẫn `> Ghi chú kỹ thuật:`, và chỉ khi cơ chế ấy làm ra một kết quả người dùng không đoán được.
- Tiêu đề viết như câu thường.
- Trực tiếp, cụ thể, không rào đón, không giọng quảng cáo.
- **Hành vi gây bất ngờ thì nói thẳng**, kèm lý do nếu mã hoặc chú thích có nói. Nếu trông như lỗi thì viết hẳn *"đáng coi là lỗi hơn là đáng ghi thành tài liệu"* trong mục *Câu còn để ngỏ*, rồi thêm một mục vào `bug-triage.md`.
- Biến thể và ngắt quãng đặt trong **bảng**, chia theo chặng. **Mọi ô đều phải có chữ**, kể cả khi câu trả lời là *"Không có tác dụng."* Ô trống nghĩa là chưa ai hỏi câu đó.
- Trỏ chéo bằng liên kết tương đối thay vì nhắc lại. Tài liệu nền móng **sở hữu** các con số và định nghĩa.
- Mỗi tương tác đúng một sơ đồ Mermaid `stateDiagram-v2`, chỉ gồm những trạng thái người dùng thật sự đi qua.
- Kết bằng mục `## Câu còn để ngỏ và việc kiểm chứng` rồi dòng `Đối chiếu với commit \`{sha}\``.
- **Không sửa mã nguồn sản phẩm.** Ở đây nó là tài liệu tham chiếu chỉ đọc.
- Không xác định được một hành vi từ mã và test thì viết phần xác định được, đẩy phần còn lại vào *Câu còn để ngỏ*, rồi đi tiếp. **Không đoán, không dừng lại.**

## Chuyện đã chốt, đừng suy lại

Những điều dưới đây đã được xác lập. Đừng dẫn lại từ đầu và đừng viết trái với chúng.

**Hình dạng tương tác.** Đơn vị là *một tác vụ trên mặt cắt đang chọn*, năm chặng: **Mở** · **Kết thúc ngay** · **Thành việc dài** · **Đang chạy** · **Kết thúc**. Danh sách ngắt quãng tám hàng và danh sách bận tâm xuyên suốt tám mục là **cố định**, cùng thứ tự, trong mọi tài liệu.

**Chỉ có một mặt cắt đang chọn cho cả app.** Cây mặt cắt, ô chọn của thẻ Results table và thẻ Kiểm toán luôn nói cùng một mặt cắt.

**Project là nguồn sự thật duy nhất** cho danh sách mặt cắt. Không thẻ nào giữ danh sách riêng.

**Sản phẩm không có hoàn tác** ở bất cứ đâu.

**Không một phím bổ trợ nào có tác dụng trong khung xem.** Shift, Ctrl, Alt, Space đều không được đọc. Đây là sự thật đã kiểm chứng, không phải chỗ chưa đọc kỹ. Trong bảng *Biến thể* cứ ghi *"Không có tác dụng."* và trỏ về [B-02](bug-triage.md#b-02).

**Khung xem chính phóng quanh tâm khung, không quanh con trỏ** — khác với sơ đồ điểm kiểm toán và biểu đồ bao. Đã đo: một nấc lăn làm điểm dưới con trỏ trôi 0,67 m. Xem [B-04](bug-triage.md#b-04).

**Gối lưu theo toạ độ X**, không theo số hiệu node, và luôn sinh ra là **con lăn**.

**Cổng giấy phép chỉ chặn ở bốn chỗ**: tạo MCT (F5), chạy Midas (F8), chạy kiểm toán, và cửa sổ chuột phải. Xem mô hình, sửa gối, đọc bảng kết quả đều không qua cổng.

**Ba công cụ kiểm của dự án chạy từ mã nguồn**, nên chúng mù với mọi thứ chỉ xảy ra ở bản đóng gói. Đừng viết rằng một hành vi đã được kiểm chỉ vì `check_gui.py` xanh.

**Thiếu khoá trong template thì phần mềm phải báo lỗi**, không được tự điền mặc định. Mặc định âm thầm từng sinh ra file MCT sai số liệu.

## Khi xong

- Cập nhật bảng độ phủ trong `README.md` thành `đã soạn`.
- Thêm mục vào `bug-triage.md` cho mọi thứ bạn nghi là lỗi, đánh mã `B-NN` tiếp theo. **Không đánh lại số** những mã đã có.
- Báo lại những gì bạn **không** xác định được từ mã và test.

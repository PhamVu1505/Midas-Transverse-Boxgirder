"""
Cửa sổ Hướng dẫn sử dụng.

Bố cục theo lối help của midas Civil và CSI: danh sách chủ đề bên trái, nội dung
bên phải — thay cho việc mở một file .txt bằng trình duyệt. Nội dung tiếng Việt
có dấu, viết theo đúng quy trình thực tế của chương trình.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                             QListWidgetItem, QTextBrowser, QPushButton,
                             QLabel, QFrame, QSplitter)

from .theme import LIGHT, FONT_MONO, FONT_UI


def _topics(t):
    """(tiêu đề, nội dung HTML). Màu lấy từ token nên đổi theme là theo."""
    ink, ink2, ink3 = t['ink'], t['ink_2'], t['ink_3']
    acc, warn, ok = t['accent'], t['warn'], t['ok']
    soft, line = t['accent_soft'], t['border_soft']

    def note(txt, color=acc, bg=None):
        return (f'<table width="100%" cellpadding="8" cellspacing="0"'
                f' style="background:{bg or soft}"><tr>'
                f'<td style="border-left:3px solid {color}">{txt}</td></tr></table>')

    def step(n, title, body):
        return (f'<p><b style="color:{acc}">Bước {n} — {title}</b><br>{body}</p>')

    return [
        ('Tổng quan', f'''
<h2 style="color:{ink}">Chương trình làm gì</h2>
<p>Tự động hóa việc phân tích khung ngang dầm hộp bê tông cốt thép dự ứng lực:
đọc mặt cắt từ file DXF, dựng mô hình khung, xuất file MCT cho Midas/Civil, rồi
đọc kết quả nội lực về lập bảng kiểm toán.</p>

<h3 style="color:{ink}">Quy trình năm bước</h3>
<table cellpadding="6" cellspacing="0" width="100%">
<tr><td width="26"><b style="color:{acc}">1</b></td>
    <td>Thêm các mặt cắt DXF vào project</td></tr>
<tr><td><b style="color:{acc}">2</b></td>
    <td>Tạo file MCT</td></tr>
<tr><td><b style="color:{ink3}">3</b></td>
    <td style="color:{ink2}"><i>Mở MCT trong Midas/Civil và chạy phân tích —
    bước này nằm ngoài chương trình</i></td></tr>
<tr><td><b style="color:{acc}">4</b></td>
    <td>Nạp file Beam Force do Midas xuất ra</td></tr>
<tr><td><b style="color:{acc}">5</b></td>
    <td>Xem bảng kiểm toán và xuất Excel</td></tr>
</table>
<p style="color:{ink2}">Thanh bước ở đầu cửa sổ luôn hiển thị bạn đang ở đâu
trong quy trình. Bước 3 vẽ nét đứt vì phải làm bên Midas.</p>
'''),

        ('Giao diện', f'''
<h2 style="color:{ink}">Các vùng trên màn hình</h2>
<table cellpadding="7" cellspacing="0" width="100%">
<tr style="background:{soft}">
    <td width="150"><b>Panel Project</b><br><span style="color:{ink2}">bên trái</span></td>
    <td>Cây mặt cắt · Thiết lập (template số liệu, thư mục kết quả) ·
        Lớp hiển thị</td></tr>
<tr><td><b>Vùng giữa</b></td>
    <td>Các thẻ chế độ xem: <b>Model</b>, <b>Section shape</b>, <b>Parts</b>,
        <b>Results table</b>, <b>Kiểm toán mặt cắt</b>, <b>MCT source</b></td></tr>
<tr style="background:{soft}">
    <td><b>Panel Properties</b><br><span style="color:{ink2}">bên phải</span></td>
    <td>Thông tin mặt cắt, node đang trỏ, danh sách gối · thẻ
        <b>Input data</b> liệt kê số liệu đọc từ template</td></tr>
<tr><td><b>Messages</b><br><span style="color:{ink2}">dưới đáy</span></td>
    <td>Nhật ký. Dòng vàng là cảnh báo, dòng đỏ là lỗi</td></tr>
</table>

<h3 style="color:{ink}">Ba chế độ xem mặt cắt</h3>
<p><b>Model</b> — hình dạng khung và cách chia phần tử. Mỗi node có một vạch
cắt vuông góc nên đếm được số phần tử bằng mắt.</p>
<p><b>Section shape</b> — vẽ mặt cắt <i>đúng như Midas sẽ dựng</i>: mỗi phần tử
là một dải vuốt côn theo chiều dày hai đầu, theo quy ước lệch tâm
<b>CT</b> (bản mặt treo xuống), <b>CB</b> (bản đáy nhô lên), <b>CC</b> (bụng đối
xứng). Biên bê tông thật từ DXF vẽ nét đứt phía dưới, nên lệch chỗ nào thấy ngay.</p>
<p><b>Parts</b> — tô màu theo bộ phận, dùng khi cần kiểm tra chương trình có
phân loại đúng bản mặt / bụng / bản đáy hay không.</p>

<h3 style="color:{ink}">Xem trước từ DXF</h3>
<p>Mặt cắt vừa thêm mà <i>chưa tạo MCT</i> vẫn hiện hình: chương trình đọc thẳng
biên bê tông và đường cáp DƯL từ DXF rồi vẽ ra, kèm dải nhắc
<span style="color:{warn}"><b>XEM TRƯỚC TỪ DXF</b></span> ở góc trên. Lúc này
chưa có node và phần tử vì chưa chia lưới.</p>
<p>Nhờ vậy bản vẽ sai (thiếu layer, sai đơn vị, cáp đặt lệch chỗ) lộ ra ngay khi
nạp file, không phải chạy hết một lượt tạo MCT mới biết.</p>

<h3 style="color:{ink}">Thao tác trên hình</h3>
<p>Lăn chuột để phóng to thu nhỏ · kéo chuột để di chuyển · phím <b>F</b> hoặc
nút <b>⤢</b> để vừa khung · rê chuột lên node để xem toạ độ và chiều dày.</p>
'''),

        ('Chuẩn bị file DXF', f'''
<h2 style="color:{ink}">Quy ước lớp trong DXF</h2>
<p>Mặt cắt vẽ bằng <b>LWPOLYLINE</b> khép kín, đặt trên các lớp sau:</p>
<table cellpadding="7" cellspacing="0" width="100%">
<tr style="background:{soft}"><td width="130"><code>OUTPOLY</code></td>
    <td>Đường bao ngoài mặt cắt. Bắt buộc, chỉ một đường.</td></tr>
<tr><td><code>INPOLY</code></td>
    <td>Lỗ rỗng bên trong. <b>Một</b> đường cho mặt cắt một hộp,
        <b>hai</b> đường cho mặt cắt hai hộp.</td></tr>
<tr style="background:{soft}"><td><code>PT-&lt;VỊ TRÍ&gt;-&lt;SỐ&gt;</code></td>
    <td>Cáp dự ứng lực, ví dụ <code>PT-TOP-1</code>, <code>PT-BOT-2</code>,
        <code>PT-WEB-L-1</code>. Chương trình tự nhận theo <b>tên lớp</b>.</td></tr>
</table>
{note(f'Mặt cắt <b>ba hộp trở lên chưa hỗ trợ</b>. Nếu file có từ ba đường '
      f'<code>INPOLY</code>, chương trình dừng và báo lỗi rõ ràng chứ không '
      f'âm thầm bỏ sót.', warn, t["warn_bg"])}

<h3 style="color:{ink}">Hệ toạ độ</h3>
<p>Trong DXF: X ngang, Y đứng. Chương trình tự quy về hệ của Midas với X = 0 tại
tim dầm và Z = 0 tại đáy, nên bản vẽ đặt ở đâu trong không gian cũng được.</p>
'''),

        ('Template số liệu', f'''
<h2 style="color:{ink}">Sheet <code>INPUT</code></h2>
<p>Toàn bộ tải trọng, vật liệu và thông số cáp đọc từ <b>một sheet duy nhất</b>
tên <code>INPUT</code>, bố cục khoá – giá trị:</p>
<table cellpadding="6" cellspacing="0" width="100%" style="font-family:{FONT_MONO}">
<tr style="background:{soft}"><td><b>A — khoá</b></td><td><b>B — giá trị</b></td>
    <td><b>C — đơn vị</b></td></tr>
<tr><td>fc</td><td>=General!H70</td><td>MPa</td></tr>
<tr><td>pavement</td><td>=Load!G9</td><td>kN/m</td></tr>
<tr><td>d_L</td><td>=Load!I11</td><td>m</td></tr>
</table>
<p>Chương trình tra theo <b>khoá ở cột A</b>, không theo số dòng. Nhờ vậy chèn
hay xoá dòng ở sheet <code>INPUT</code> lẫn ở các sheet con đều không ảnh hưởng
kết quả — miễn là không đổi tên khoá.</p>

{note(f'<b>Thiếu khoá thì chương trình dừng và báo tên khoá thiếu</b>, không tự '
      f'điền giá trị mặc định. Điền mặc định âm thầm từng làm mô hình xuất ra '
      f'sai số liệu mà không ai biết.')}

<h3 style="color:{ink}">Gán template</h3>
<p>Vào <b>Tệp → Chọn template số liệu</b> để đặt template dùng chung. Muốn một
mặt cắt dùng template khác, bấm chuột phải lên nó trong cây rồi chọn
<b>Gán template số liệu</b> — các mặt cắt cùng số sườn và cùng bề rộng thường
dùng chung được một template.</p>
<p>Kiểm tra trước khi chạy: <b>Công cụ → Kiểm tra template số liệu</b> sẽ liệt
kê cả 40 khoá và đối chiếu với ô gốc bên sheet con, bắt được trường hợp công
thức bị dán thành số cứng.</p>
'''),

        ('Tạo file MCT', f'''
<h2 style="color:{ink}">Các bước</h2>
{step(1, 'Thêm mặt cắt',
      'Bấm <b>Thêm DXF</b> trên thanh công cụ, hoặc <b>Tệp → Thêm cả thư mục '
      'DXF</b> để nạp một lượt. Nhanh nhất là <b>kéo file .dxf (hoặc cả thư '
      'mục) từ Windows Explorer thả vào cửa sổ</b> — thả file .mtbproj thì mở '
      'luôn project đó. Thêm xong mặt cắt hiện hình ngay để kiểm tra bản vẽ.')}
{step(2, 'Chọn template', 'Xem mục <i>Template số liệu</i>.')}
{step(3, 'Đặt thư mục kết quả',
      'Ô <b>Thư mục kết quả</b> trong panel Project. Mỗi mặt cắt sẽ có một thư '
      'mục con riêng.')}
{step(4, 'Tạo MCT',
      'Bấm <b>Tạo MCT toàn bộ</b> (phím <b>F5</b>), hoặc chọn vài mặt cắt trong '
      'cây rồi bấm <b>Shift+F5</b> để chỉ tạo cho những mặt cắt đó.')}

<h3 style="color:{ink}">Chấm trạng thái trong cây</h3>
<table cellpadding="6" cellspacing="0">
<tr><td width="30" style="color:{ink3}">○</td><td>Chưa tạo MCT</td></tr>
<tr><td style="color:{acc}">●</td><td>Đã tạo MCT</td></tr>
<tr><td style="color:{warn}">◐</td><td>Đã gán file Beam Force</td></tr>
<tr><td style="color:{ok}">✓</td><td>Đã kiểm toán xong</td></tr>
<tr><td style="color:{t["err"]}">✕</td><td>Lỗi — xem chi tiết ở Messages</td></tr>
</table>
{note(f'Chưa gán template thì MCT chỉ có hình học, vật liệu và gối; toàn bộ '
      f'khối tải trọng cùng tổ hợp bị bỏ qua. Chương trình ghi rõ điều này vào '
      f'đầu file và vào Messages.', warn, t["warn_bg"])}
'''),

        ('Gối', f'''
<h2 style="color:{ink}">Đặt và sửa gối</h2>
<p>Mặc định chương trình đặt một gối cố định ở đáy bụng trái, một gối di động ở
đáy bụng phải, và với mặt cắt hai hộp thì thêm một gối di động ở đáy vách giữa.</p>

<p>Muốn đổi, bấm nút <b>Sửa gối</b> phía trên khung nhìn. Danh sách gối hiện ở
panel Properties bên phải, mỗi gối một thẻ:</p>
<ul>
<li>Gõ <b>số hiệu node</b> rồi Enter để dời gối sang node khác</li>
<li>Bấm một trong <b>ba nút ký hiệu</b> để đổi loại gối</li>
<li>Nút <b>✕</b> để xoá, <b>＋ Thêm gối</b> để đặt thêm</li>
</ul>
<p>Trên hình vẽ: bấm vào node bản đáy để đặt gối, kéo tam giác để dời, bấm chuột
phải lên tam giác để xoá.</p>

<h3 style="color:{ink}">Ba loại gối</h3>
<table cellpadding="7" cellspacing="0" width="100%">
<tr style="background:{soft}"><td width="130"><b>Gối cố định</b></td>
    <td><code>111000</code> — khoá Dx, Dy, Dz</td></tr>
<tr><td><b>Gối di động</b></td>
    <td><code>011000</code> — khoá Dy, Dz</td></tr>
<tr style="background:{soft}"><td><b>Ngàm</b></td>
    <td><code>111111</code> — khoá cả sáu bậc tự do</td></tr>
</table>
{note('Phương <b>Dy</b> luôn bị khoá. Khung ngang là bài toán phẳng trong mặt '
      'phẳng XZ, nhưng Midas giải trong không gian ba chiều — thiếu ràng buộc '
      'Dy thì báo lỗi ma trận suy biến.')}
<p style="color:{ink2}">Gối lưu theo <b>toạ độ</b> chứ không theo số hiệu node,
nên sửa lại DXF hay đổi kích thước phần tử thì gối vẫn nằm đúng vị trí cũ.</p>
'''),

        ('Đọc kết quả', f'''
<h2 style="color:{ink}">Sau khi chạy Midas</h2>
{step(1, 'Xuất Beam Force',
      'Trong Midas/Civil, xuất bảng nội lực phần tử ra file Excel.')}
{step(2, 'Gán file cho mặt cắt',
      'Sang thẻ <b>Results table</b>, bấm đúp vào dòng của mặt cắt rồi chọn file '
      'Beam Force tương ứng. Hoặc bấm chuột phải lên mặt cắt trong cây và chọn '
      '<b>Gán file Beam Force</b>.')}
{step(3, 'Xử lý',
      'Bấm <b>Xử lý Beam Force</b> (phím <b>F6</b>). Chương trình đối chiếu số '
      'phần tử giữa file kết quả và mô hình; lệch nhau thì báo để chọn lại file.')}

<h3 style="color:{ink}">Tám điểm kiểm toán</h3>
<p>Bảng kết quả cho mô men, lực cắt và chiều cao tiết diện tại tám điểm:
<b>A–D</b> trên bản mặt, <b>E–F</b> trên bản đáy, <b>G–H</b> trên bụng. Hình mặt
cắt phía trên bảng vẽ từ <i>toạ độ DXF thật</i> và chỉ rõ vị trí từng điểm bằng
ký hiệu vết cắt theo quy ước bản vẽ.</p>
<p>Hình này <b>lăn chuột để phóng to thu nhỏ, kéo chuột để di chuyển</b>, bấm đúp
hoặc phím <b>F</b> để vừa khung — như thẻ Model. Kéo thanh chia giữa hình và bảng
để đổi tỉ lệ hai phần.</p>

<h3 style="color:{ink}">Biểu đồ bao nội lực</h3>
<p>Ô bên phải vẽ <b>đường bao mômen hoặc lực cắt</b> lên chính hình khung ngang,
chọn bằng ô <b>Biểu đồ</b>: Cường độ (<code>str_all</code>) hoặc Sử dụng
(<code>ser_all</code>) — đúng hai tổ hợp bao mà bảng bên dưới vẫn tra, nên hình
và bảng luôn nói cùng một con số.</p>
<p>Hai đường bao vẽ chồng: <b style="color:{t["part_top"]}">max</b> và
<b style="color:{t["part_bot"]}">min</b>. Nhìn hình mới thấy được <i>hình dạng</i>
nội lực — chỗ đổi dấu, chỗ vút, chỗ nào lẽ ra phải trơn mà lại gãy khúc (dấu hiệu
chia lưới hoặc gán tải sai). Ô này cũng zoom/pan như ô mặt cắt.</p>
<p style="color:{ink2}">Mặt cắt <b>nhiều hộp</b> có thêm điểm phân giải cho từng
khoang và từng vách — <b>A1, A2…</b> (giữa mỗi khoang bản mặt), <b>E1, E2…</b>
(giữa mỗi khoang bản đáy), <b>G1…Gm</b> và <b>H1…Hm</b> (đầu trên và đầu dưới
mỗi vách). Tám điểm A–H vẫn giữ nguyên ý nghĩa <i>bao</i> để bố trí lưới thép
chung.</p>
'''),

        ('Kiểm toán mặt cắt', f'''
<h2 style="color:{ink}">Kiểm toán tiết diện theo TCVN 11823</h2>
<p>Thẻ <b>Kiểm toán mặt cắt</b> (phím <b>F7</b>) lấy nội lực vừa xử lý ở thẻ
<b>Results table</b>, cộng với cốt thép do người dùng nhập, rồi kiểm bốn nhóm
theo TCVN 11823-5. Tiết diện xét là <b>lát cắt rộng 1 m</b> của mặt cắt ngang.</p>

{step(1, 'Nhập cốt thép',
      'Bảng trên cùng, mỗi cột là một điểm kiểm toán. Nhập đường kính, cự ly, '
      'lớp bảo vệ (tính đến <b>tâm</b> thanh) và cốt đai. '
      'A<sub>s</sub> tự tính. Số liệu lưu vào project theo từng mặt cắt.')}
{step(2, 'Chọn tiêu chuẩn và hệ số',
      "TCVN 11823 hoặc 22TCN 272-05 (để đối chiếu hồ sơ cũ). f'c lấy sẵn từ "
      "template số liệu, sửa được. φ mặc định 0,90 cho cả uốn và cắt.")}
{step(3, 'Bấm Kiểm toán',
      'Bảng dưới chia bốn nhóm, trình bày theo mẫu bảng kiểm toán quen dùng. '
      'Bấm <b>Xuất Excel…</b> để đưa vào hồ sơ.')}

<h3 style="color:{ink}">Cáp dự ứng lực nhận diện tự động</h3>
<p>Hai hàng <b>Cáp d<sub>p</sub></b> và <b>Cự ly cáp @</b> chỉ mở ở những bộ phận
<i>thật sự có cáp trong bản vẽ</i>. Mặt cắt chỉ căng cáp ngang ở bản mặt thì các
cột bản đáy và bụng bị khoá, hiện dấu gạch — không gõ nhầm vào được.</p>
<p>d<sub>p</sub> tính thẳng từ đường cáp trong DXF: nội suy cao độ cáp tại vị trí
điểm kiểm toán rồi đo tới thớ chịu nén (thớ nào chịu nén thì suy từ dấu của
M<sub>u</sub>). Sửa lại được nếu cần.</p>
<p>Diện tích một bó lấy từ template số liệu (khoá <code>Ap</code>). Cự ly cáp theo
phương dọc cầu mặc định <b>1000 mm</b> — đúng bằng giả thiết của mô hình Midas:
khung ngang được dựng thành dải rộng 1 m và cáp trong dải đó mang diện tích của
một bó. Đổi cự ly thì bảng kiểm toán và mô hình nói hai chuyện khác nhau.
A<sub>p</sub> trên 1 m = (diện tích một bó) × 1000 / cự ly.</p>

<h3 style="color:{ink}">Đọc bảng kết quả</h3>
<p>Mỗi nhóm kết thúc bằng hàng <b>hệ số sức kháng / nội lực</b>
(M<sub>r</sub>/M<sub>u</sub>, V<sub>r</sub>/V<sub>u</sub>…) — số càng lớn càng
an toàn. Nền ô nói ngay kết quả:</p>
<table cellpadding="7" cellspacing="0" width="100%">
<tr style="background:{soft}"><td width="150"><b style="color:{ok}">Xanh</b></td>
    <td>hệ số ≥ 1,05 — đạt và còn dư</td></tr>
<tr><td><b style="color:{warn}">Vàng</b></td>
    <td>1,00 ≤ hệ số &lt; 1,05 — đạt nhưng dư chưa tới 5%</td></tr>
<tr style="background:{soft}"><td><b style="color:{t["err"]}">Đỏ</b></td>
    <td>hệ số &lt; 1,00 — không đạt</td></tr>
</table>
<p style="color:{ink2}">Số chữ số thập phân theo đúng bảng kiểm toán mẫu: nội
lực, kích thước, diện tích và ứng suất lấy tròn số; hệ số không thứ nguyên lấy
2–3 chữ số. Ô nào bằng 0 thì hiện dấu gạch cho đỡ rối.</p>

<h3 style="color:{ink}">Bốn nhóm kiểm tra</h3>
<table cellpadding="7" cellspacing="0" width="100%">
<tr style="background:{soft}"><td width="150"><b>Sức kháng uốn</b></td>
    <td>M<sub>u</sub> ≤ M<sub>r</sub> = φM<sub>n</sub> — Điều 7.3.2</td></tr>
<tr><td><b>Giới hạn cốt thép</b></td>
    <td>M<sub>r</sub> ≥ min(M<sub>cr</sub>, 1,33M<sub>u</sub>) — Điều 7.3.3, kèm
        phân loại tiết diện theo biến dạng kéo thực ε<sub>t</sub> (Điều 7.2.1)</td></tr>
<tr style="background:{soft}"><td><b>Nứt</b></td>
    <td>Cự ly cốt thép ở trạng thái giới hạn Sử dụng — Điều 7.3.4</td></tr>
<tr><td><b>Cắt</b></td>
    <td>V<sub>u</sub> ≤ V<sub>r</sub> = φV<sub>n</sub> theo MCFT — Điều 8.3.3
        và 8.3.4.2</td></tr>
</table>

<h3 style="color:{ink}">Hai phương pháp tra θ và β</h3>
<p>Điều 8.3.4.2 cho dùng ngang hàng hai cách. Ô <b>Cắt theo</b> chọn giữa:</p>
<table cellpadding="7" cellspacing="0" width="100%">
<tr style="background:{soft}"><td width="150"><b>bảng</b></td>
    <td>Tra Bảng 4 / Bảng 5, nội suy hai chiều, lặp θ. Mặc định.</td></tr>
<tr><td><b>công thức</b></td>
    <td>Công thức đóng, phương trình 77–79. Cho kết quả <b>chặt hơn nhiều</b> ở
        tiết diện vùng nén vì chặn ε<sub>s</sub> ≥ 0.</td></tr>
</table>

{note('Điều kiện <b>c/d<sub>e</sub> ≤ 0,42</b> chỉ có ở 22TCN 272-05. TCVN 11823 '
      'không có điều kiện này mà phân loại tiết diện theo ε<sub>t</sub>, nên khi '
      'chọn TCVN thì bảng hiện ε<sub>t</sub> thay cho c/d<sub>e</sub>.')}

<p style="color:{ink2}">Kiểm nứt được bỏ qua khi tiết diện có cáp dự ứng lực
(chưa xét nén trước) hoặc khi ứng suất kéo ở trạng thái Sử dụng chưa tới 80%
f<sub>r</sub> — lúc đó tiết diện chưa nứt. Cột nào bỏ qua thì cột đó ghi rõ lý do
ở hàng <i>Ghi chú</i>.</p>
'''),

        ('Tùy chọn giao diện', f'''
<h2 style="color:{ink}">Tùy chọn</h2>
<p>Mở bằng nút <b>⚙</b> cuối thanh công cụ, hoặc <b>Công cụ → Tùy chọn</b>
(<code>Ctrl+,</code>). Bấm <b>mũi tên</b> cạnh nút bánh răng để đổi nhanh bảng
màu mà không cần mở hộp thoại. Thiết lập áp dụng ngay, không phải khởi động lại,
và được nhớ cho lần mở sau.</p>

<h3 style="color:{ink}">Giao diện</h3>
<table cellpadding="7" cellspacing="0" width="100%">
<tr style="background:{soft}"><td width="120"><b>Bảng màu</b></td>
    <td><b>Sáng</b> — mặc định, nền xám lệch xanh kiểu phần mềm kỹ thuật.<br>
        <b>Tối</b> — nền xám than, dùng khi làm việc lâu hoặc phòng thiếu sáng.<br>
        <b>Tương phản cao</b> — nền trắng, chữ đen thuần, viền đậm; hợp khi
        trình chiếu hoặc chụp màn hình đưa vào báo cáo.</td></tr>
<tr><td><b>Màu nhấn</b></td>
    <td>Màu của nút chính, dòng đang chọn và các chi tiết nhấn.</td></tr>
<tr style="background:{soft}"><td><b>Mật độ</b></td>
    <td><b>Chặt</b> cho màn hình nhỏ, <b>Thoáng</b> cho màn hình lớn.</td></tr>
<tr><td><b>Cỡ chữ · Phông</b></td>
    <td>8–14 pt. Ô <i>Xem thử</i> ngay bên dưới đổi theo tức thì.</td></tr>
</table>

<h3 style="color:{ink}">Khung xem</h3>
<p>Chọn những lớp <b>bật sẵn</b> mỗi khi mở một mặt cắt, và chế độ xem mặc định
lúc khởi động. Trong lúc làm việc vẫn bật tắt được ở mục <b>Lớp hiển thị</b>
panel Project.</p>

<h3 style="color:{ink}">Mặc định</h3>
<p>Thư mục kết quả và template số liệu dùng cho <b>project mới</b> — project đã
lưu giữ thiết lập riêng của nó. Cùng chỗ này tắt được việc mở lại project gần
nhất khi khởi động và việc tự chọn mặt cắt vừa thêm.</p>

<p style="color:{ink2}"><b>Khôi phục mặc định</b> đưa mọi mục về ban đầu nhưng
<i>giữ nguyên</i> hai đường dẫn thư mục kết quả và template.</p>
'''),

        ('Phím tắt', f'''
<h2 style="color:{ink}">Phím tắt</h2>
<table cellpadding="7" cellspacing="0" width="100%" >
<tr style="background:{soft}"><td width="130"><code>Ctrl+N</code></td>
    <td>Project mới</td></tr>
<tr><td><code>Ctrl+Shift+O</code></td><td>Mở project</td></tr>
<tr style="background:{soft}"><td><code>Ctrl+S</code></td><td>Lưu project</td></tr>
<tr><td><code>Ctrl+O</code></td><td>Thêm DXF</td></tr>
<tr style="background:{soft}"><td><code>Ctrl+T</code></td>
    <td>Chọn template số liệu</td></tr>
<tr><td><code>F5</code></td><td>Tạo MCT toàn bộ</td></tr>
<tr style="background:{soft}"><td><code>Shift+F5</code></td>
    <td>Tạo MCT cho mặt cắt đang chọn</td></tr>
<tr><td><code>Ctrl+B</code></td><td>Gán file Beam Force</td></tr>
<tr style="background:{soft}"><td><code>F6</code></td><td>Xử lý Beam Force</td></tr>
<tr><td><code>F7</code></td><td>Kiểm toán mặt cắt</td></tr>
<tr style="background:{soft}"><td><code>F</code></td><td>Vừa khung nhìn</td></tr>
<tr><td><code>Ctrl+L</code></td><td>Xoá nhật ký</td></tr>
<tr style="background:{soft}"><td><code>Ctrl+,</code></td><td>Tùy chọn giao diện</td></tr>
<tr><td><code>F1</code></td><td>Mở hướng dẫn này</td></tr>
</table>
'''),

        ('Xử lý sự cố', f'''
<h2 style="color:{ink}">Các lỗi hay gặp</h2>

<p><b style="color:{t["err"]}">Midas báo: The specified load name ((null)) does
not exist</b><br>
File MCT có tổ hợp tải trọng nhưng thiếu trường hợp tải mà tổ hợp đó gọi tới.
Nguyên nhân thường là <b>chưa gán template số liệu</b> khi tạo MCT. Gán template
rồi tạo lại.</p>

<p><b style="color:{t["err"]}">Thiếu số liệu đầu vào — liệt kê tên khoá</b><br>
Sheet <code>INPUT</code> thiếu khoá hoặc ô giá trị đang rỗng. Mở template, điền
đủ rồi chạy lại. Dùng <b>Công cụ → Kiểm tra template số liệu</b> để xem toàn bộ
40 khoá.</p>

<p><b style="color:{warn}">Số phần tử của Beam Force không khớp mô hình</b><br>
File kết quả không phải của mặt cắt này, hoặc mô hình đã được tạo lại sau khi
chạy Midas. Chọn lại đúng file, hoặc chạy lại Midas với MCT mới nhất.</p>

<p><b style="color:{warn}">Mặt cắt cần 1 hoặc 2 INPOLY, tìm thấy N</b><br>
File DXF có số đường lỗ rỗng không hợp lệ. Kiểm tra lớp <code>INPOLY</code>,
xoá các đường thừa hoặc đường vẽ trùng.</p>

<p><b style="color:{warn}">Giá trị trên sheet INPUT lệch so với ô gốc</b><br>
Công thức tham chiếu đã bị dán thành số cứng hoặc trỏ sang workbook khác. Số vẫn
hiện đúng hôm nay nhưng không còn bám theo sheet con nữa. Dán lại công thức.</p>

<p style="color:{ink2}">Mọi lỗi đều ghi đầy đủ ở cửa sổ <b>Messages</b> dưới đáy,
kèm dấu vết ngăn xếp khi cần.</p>
'''),
    ]


class HelpDialog(QDialog):
    def __init__(self, theme: dict = None, parent=None):
        super().__init__(parent)
        self.t = theme or LIGHT
        self.setWindowTitle('Hướng dẫn sử dụng')
        self.resize(940, 660)
        self.setMinimumSize(720, 480)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        head = QLabel('  Midas Transverse Boxgirder — Hướng dẫn sử dụng')
        head.setStyleSheet(
            f'background:{self.t["accent"]};color:#fff;font-size:12pt;'
            f'font-weight:600;padding:11px 14px;')
        lay.addWidget(head)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.topics = QListWidget()
        self.topics.setStyleSheet(
            f'QListWidget{{border:0;background:{self.t["panel_alt"]};'
            f'font-size:10pt;padding:6px 0}}'
            f'QListWidget::item{{padding:8px 14px}}'
            f'QListWidget::item:selected{{background:{self.t["accent_soft"]};'
            f'color:{self.t["accent"]};font-weight:600}}')
        self.topics.setFixedWidth(190)
        split.addWidget(self.topics)

        self.body = QTextBrowser()
        self.body.setOpenExternalLinks(True)
        self.body.setStyleSheet(
            f'QTextBrowser{{border:0;background:{self.t["panel"]};'
            f'padding:6px 18px;font-family:{FONT_UI};font-size:10pt;'
            f'color:{self.t["ink"]}}}')
        split.addWidget(self.body)
        split.setStretchFactor(1, 1)
        lay.addWidget(split, 1)

        bar = QFrame()
        bar.setStyleSheet(f'QFrame{{background:{self.t["panel_alt"]};'
                          f'border-top:1px solid {self.t["border"]}}}')
        h = QHBoxLayout(bar)
        h.setContentsMargins(12, 8, 12, 8)
        h.addStretch()
        close = QPushButton('Đóng')
        close.setProperty('primary', True)
        close.clicked.connect(self.accept)
        h.addWidget(close)
        lay.addWidget(bar)

        self._data = _topics(self.t)
        for title, _ in self._data:
            QListWidgetItem(title, self.topics)
        self.topics.currentRowChanged.connect(self._show)
        self.topics.setCurrentRow(0)

    def _show(self, row):
        if 0 <= row < len(self._data):
            self.body.setHtml(self._data[row][1])
            self.body.verticalScrollBar().setValue(0)

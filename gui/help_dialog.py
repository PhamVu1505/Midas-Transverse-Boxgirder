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
        <b>Results table</b>, <b>MCT source</b></td></tr>
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
      'DXF</b> để nạp một lượt.')}
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
<b>A–D</b> trên bản mặt, <b>E–F</b> trên bản đáy, <b>G–H</b> trên bụng. Sơ đồ bên
cạnh bảng chỉ rõ vị trí từng điểm.</p>
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
<tr><td><code>F</code></td><td>Vừa khung nhìn</td></tr>
<tr style="background:{soft}"><td><code>Ctrl+L</code></td><td>Xoá nhật ký</td></tr>
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

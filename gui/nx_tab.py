"""
Thẻ *Kiểm chéo NX* — cho MIDAS CIVIL NX giải lại chính `.mcb` mà Civil 2022 đã
giải, rồi so từng bản ghi nội lực.

Vì sao cần
──────────
Cả quy trình đứng trên **một** phép giải. Nếu MCT khai sai một chỗ mà Midas vẫn
giải trót lọt thì không gì lộ ra — đúng khuôn lỗi đã gặp thật: `output/S10` từng
mang MCT không có một khối tải nào, Midas vẫn xuất ra `.xls` hợp lệ 6.656 byte
rỗng ruột. Cho một bản Midas **khác** giải lại rồi so là phép kiểm độc lập rẻ
nhất: ba lệnh HTTP, không chạm chuột, ~10 s một mặt cắt.

Đọc bảng thế nào
────────────────
Hai bản Midas **không** buộc phải ra số giống hệt. Bảng của chúng in 2 chữ số
thập phân, và bài toán hoạt tải di động rời rạc hoá đường ảnh hưởng theo cách
riêng của từng bản. Nên hai cột lệch đo bằng **hai thước khác nhau**:

* **Tải cơ bản** (`Self Weight`, `Prestress`, `Barrier`…) là hệ tuyến tính —
  hai bản phải ra **cùng một số**, chỉ cho lệch bằng đơn vị hiển thị (0,011).
  Đây là con số quyết định ĐẠT/HỎNG.
* **Trị số bao** (`Cuong do I(max)`, `ser_all(min)`…) dựng từ đường ảnh hưởng,
  nên đo bằng sai số **tương đối** và **không** tính vào đạt/hỏng — báo để đọc,
  không phải để phán. Dùng chung một thước tuyệt đối thì 3/4 mặt cắt bị gọi là
  hỏng chỉ vì làm tròn.

Toàn bộ phép tính nằm ở `tools/nx_crosscheck.py`; thẻ này chỉ trình bày. Ngưỡng
đạt/hỏng ở đây **không** có ô cho người dùng chỉnh: hai ngưỡng đó rút ra từ phép
đo thật trên bốn mặt cắt, nới ra là phép kiểm thôi kiểm được gì.
"""

import json
import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QAbstractItemView, QHeaderView, QMessageBox)

from .theme import LIGHT

#: Cột của bảng kết quả. Đúng những gì cần để phán và để truy khi hỏng.
#: Tiêu đề để NGẮN, lời giải thích dài nằm ở dải nhắc phía trên và ở tooltip:
#: tiêu đề dài thì chính nó bị cắt cụt ("…ố bao (không tính đạt/hỏ") ngay khi
#: mở dock hai bên, mà lúc đó không còn chỗ nào nói ra điều nó định nói.
COT = ['Mặt cắt', 'Bản ghi 2022', 'Bản ghi NX', 'Ghép được',
       'Tải cơ bản: lệch lớn nhất', 'Trị số bao', 'Kết quả']

CHU_THICH_COT = {
    4: 'Lệch lớn nhất giữa hai bản Midas ở các trường hợp tải TĨNH (đọc từ '
       'db/STLD của chính mô hình). Hệ tuyến tính nên phải trùng tới đơn vị '
       'hiển thị — dung sai 0,011. Đây là con số quyết định ĐẠT/HỎNG.',
    5: 'Lệch TƯƠNG ĐỐI lớn nhất ở các trị số bao (Cuong do I(max), '
       'ser_all(min)…). Bao hoạt tải dựng từ đường ảnh hưởng, mỗi bản Midas '
       'rời rạc hoá một kiểu, nên KHÔNG tính vào đạt/hỏng — báo để đọc.',
}

DAT, HONG, CHUA = 'ĐẠT', 'HỎNG', 'chưa chạy'

#: Ba tệp nguồn (.mct → .mcb → Beam Force) không cùng một mô hình. Không phải
#: ĐẠT, cũng không phải HỎNG: cả hai chữ đó đều là câu về **hai bản Midas**,
#: còn đây là câu về **tệp trên đĩa** — và việc phải làm cũng khác hẳn (sinh
#: lại MCT rồi chạy lại Civil 2022, chứ không phải đi soi khối MCT nào sai).
NGHI = 'KHÔNG KẾT LUẬN'


def hang(kq: dict, ok: bool, cu: bool = False, lac_hau: bool = False,
         nguon=()) -> list:
    """Một hàng của bảng, dạng chuỗi — **không** đụng tới Qt.

    Tách ra khỏi widget để phần trình bày kiểm được bằng `pytest` thường: đây
    là nơi duy nhất quyết định người dùng đọc thấy con số nào, mà lỗi trình bày
    thì không có traceback.

    Số in **đúng như `tools/nx_crosscheck.py` in ra nhật ký** (4 chữ số cho
    lệch tuyệt đối, 2 chữ số phần trăm cho lệch tương đối). Cùng một phép tính
    mà bảng nói 0,01 còn nhật ký nói 0,0100 thì người dùng phải tự đối chiếu —
    đúng lỗi "một phép tính, hai lối trình bày" dự án đã vấp ở cảnh báo hoạt
    tải.
    """
    ghep = f'{kq.get("ghep", 0):,}'
    thua = []
    if kq.get('chi_a'):
        thua.append(f'chỉ 2022: {kq["chi_a"]:,}')
    if kq.get('chi_b'):
        thua.append(f'chỉ NX: {kq["chi_b"]:,}')
    if thua:
        ghep += ' · ' + ' · '.join(thua)

    co_ban = (f'My {kq.get("max_My", 0.0):.4f} kN.m · '
              f'Vz {kq.get("max_Vz", 0.0):.4f} kN')
    if kq.get('qua_dung_sai'):
        co_ban += f' · {kq["qua_dung_sai"]:,} quá dung sai'

    bao = f'{kq.get("max_bao_tuong_doi", 0.0) * 100:.2f}%'
    if kq.get('qua_dung_sai_bao'):
        bao += f' · {kq["qua_dung_sai_bao"]:,} quá ngưỡng'

    # Nguồn không cùng một mô hình thì phép so không đo được điều nó sinh ra
    # để đo, nên KHÔNG được mượn hai chữ ĐẠT/HỎNG. Lý do đi ngay trong ô để
    # người đọc khỏi phải tự so dấu thời gian của ba tệp.
    ket = ((NGHI + ' · ' + ' · '.join(nguon)) if nguon
           else (DAT if ok else HONG))
    if cu:
        # Nói rõ đây là kết quả của LƯỢT TRƯỚC đọc lại từ đĩa, không phải lượt
        # vừa chạy. Không ghi thì mở app hôm sau thấy một bảng toàn ĐẠT và
        # tưởng vừa kiểm xong.
        ket += ' · lần trước'
    if lac_hau:
        # `.mcb` hoặc bảng Beam Force mới hơn kết quả kiểm chéo — tức mô hình
        # đã được dựng lại sau lượt kiểm. Chữ ĐẠT lúc này nói về một mô hình
        # KHÁC. Đây đúng khuôn lỗi `Section.stale` sinh ra để chặn: thà bảo
        # người dùng chạy lại còn hơn để họ tin một con số không còn thuộc về
        # mô hình nào đang có.
        ket += ', mô hình đã đổi'
    return [kq.get('ten', ''), f'{kq.get("n_2022", 0):,}',
            f'{kq.get("n_nx", 0):,}', ghep, co_ban, bao, ket]


class NXTab(QWidget):
    """Danh sách mặt cắt có đủ `.mcb` + Beam Force, và bảng đạt/hỏng."""

    section_selected = pyqtSignal(str)

    def __init__(self, status_bar, project=None, theme=None,
                 require_license=None):
        super().__init__()
        from src.project import Project
        self.status_bar = status_bar
        self.project = project if project is not None else Project()
        self.t = theme or LIGHT
        self.log_area = None
        self.worker = None
        # Cổng giấy phép do cửa sổ chính đưa vào (`MainWindow.require_license`),
        # vì chỉ nó mới mở được hộp thoại Giấy phép. Không có thì tự hỏi `guard`
        # — mặc định phải là HỎI, không phải cho qua: một mặc định "cho qua"
        # biến mọi chỗ quên nối dây thành một lỗ thủng im lặng.
        self._require_license = require_license
        self._viec = []        # [{'ten','mcb','xls','ra'}]
        self._kq = {}          # {tên: (kq, đạt, là kết quả cũ)}
        self._init_ui()

    # ── giao diện ────────────────────────────────────────────
    def _init_ui(self):
        lay = QVBoxLayout(self)

        # Điều kiện chạy đặt ngay trên đầu, không giấu vào tooltip: đây là tính
        # năng duy nhất của app cần một phần mềm KHÁC đang mở và đã bấm Connect,
        # nên không nói trước thì mọi lượt chạy đầu tiên đều hỏng.
        self.lb_hint = QLabel(
            '⚠  <b>MIDAS CIVIL NX phải đang chạy</b> và đã bấm '
            '<b>Apps → API Settings → Connect</b> (NX tự ghi MAPI-Key vào '
            'registry, không phải copy-paste). App <b>không</b> mở, không đóng '
            'và không điều khiển NX qua giao diện — chỉ đi qua API. '
            'Mô hình được chép sang hộp cát rồi mới mở, nên kết quả của '
            'Civil 2022 trong thư mục kết quả không bị ghi đè.<br>'
            'Cột <b>Tải cơ bản</b> là thước phán ĐẠT/HỎNG — tải tĩnh là hệ '
            'tuyến tính nên hai bản Midas phải ra cùng một số. Cột '
            '<b>Trị số bao</b> dựng từ đường ảnh hưởng, mỗi bản rời rạc hoá '
            'một kiểu, nên <b>không</b> tính vào đạt/hỏng — báo để đọc.')
        self.lb_hint.setWordWrap(True)
        self.lb_hint.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(self.lb_hint)

        self.table = QTableWidget(0, len(COT))
        self.table.setHorizontalHeaderLabels(COT)
        for j, chu in CHU_THICH_COT.items():
            self.table.horizontalHeaderItem(j).setToolTip(chu)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        # Mọi cột co theo nội dung, **chỉ** cột "Trị số bao" giãn để nuốt phần
        # thừa. Cho nhiều cột cùng giãn thì chúng chia đều và cột nào cũng cụt
        # ("My 0.0100 kN.m · Vz 0.0100 …"); cho cột cuối giãn thì tổng bề rộng
        # vượt khung và **cột Kết quả — thứ duy nhất bắt buộc phải đọc được —
        # bị đẩy ra ngoài mép phải**. Cả hai đều đã thấy trong ảnh chụp.
        hh = self.table.horizontalHeader()
        for j in range(len(COT)):
            hh.setSectionResizeMode(
                j, QHeaderView.ResizeMode.Stretch if j == 5
                else QHeaderView.ResizeMode.ResizeToContents)
        # Bấm vào một hàng là chọn mặt cắt cho CẢ app — chỉ có MỘT mặt cắt đang
        # chọn, đúng luật đã chốt cho thẻ Results và Kiểm toán.
        self.table.cellClicked.connect(self._on_cell)
        # Hệ số giãn 1: `QTableWidget` kế thừa sizeHint 256×192 của
        # `QAbstractScrollArea`, để 0 thì bảng đứng nguyên 192 px và cắt mất
        # mấy hàng cuối.
        lay.addWidget(self.table, 1)

        row = QHBoxLayout()
        self.lb_sum = QLabel('')
        self.lb_sum.setWordWrap(True)
        row.addWidget(self.lb_sum, 1)
        self.btn_refresh = QPushButton('Làm mới danh sách')
        self.btn_refresh.clicked.connect(self.refresh)
        row.addWidget(self.btn_refresh)
        self.btn_run = QPushButton('Chạy kiểm chéo')
        self.btn_run.setToolTip(
            'Cho NX giải lại các mặt cắt trong bảng rồi so với bảng của '
            'Civil 2022.\nChọn vài hàng để chỉ chạy những mặt cắt đó.')
        self.btn_run.clicked.connect(self.run)
        row.addWidget(self.btn_run)
        lay.addLayout(row)

        self._restyle()

    def _restyle(self):
        self.lb_sum.setStyleSheet(f'color: {self.t["ink_2"]}; font-size: 8pt;')

    def apply_theme(self, theme: dict, size: dict = None):
        self.t = theme
        self._restyle()
        # Màu nền ô nằm trong từng `QTableWidgetItem` — QSS không với tới, phải
        # dựng lại bảng thì ô ĐẠT/HỎNG mới đổi theo bảng màu.
        self._fill()

    def set_log(self, log):
        self.log_area = log

    def set_project(self, project):
        self.project = project
        # Project khác thì kết quả kiểm chéo của project cũ không còn nghĩa gì.
        self._kq.clear()
        self.refresh()

    # ── danh sách việc ───────────────────────────────────────
    def _output_dir(self) -> str:
        return self.project.output_dir or 'output'

    def refresh(self):
        """Dựng lại danh sách mặt cắt có đủ `.mcb` + Beam Force.

        Dùng chính `tim()` của `tools/nx_crosscheck.py` — cùng phép dò với CLI,
        nên thẻ này và dòng lệnh không bao giờ nói hai danh sách khác nhau.
        """
        self._viec = []
        out = self._output_dir()
        loi = self._loi()
        if loi is not None:
            for ten, mcb, xls in loi.tim(out):
                # Tính lại từ tệp đang có chứ không lấy `nguon_lac_hau` đã ghi
                # trong JSON: JSON nói về lúc chạy, còn dòng này phải nói về
                # lúc NHÌN. Sinh lại MCT sau lượt kiểm là lý do mới xuất hiện
                # mà tệp kết quả không thể biết.
                self._viec.append({'ten': ten, 'mcb': mcb, 'xls': xls,
                                   'ra': os.path.join(out, ten),
                                   'nguon': loi.nguon_lac_hau(ten, mcb, xls)})
                if ten not in self._kq:
                    cu = self._doc_ket_qua_cu(out, self._viec[-1], loi)
                    if cu is not None:
                        self._kq[ten] = cu
        self._fill()

    def _loi(self):
        """Module lõi kiểm chéo, hoặc None nếu không nạp được.

        Nạp lười: `requests` chỉ cần cho đường NX, và bản đóng gói phải kê
        `tools.nx_crosscheck` trong hidden-import. Không nạp được thì thẻ vẫn
        mở được và nói rõ vì sao, thay vì ném traceback lúc dựng cửa sổ.
        """
        if getattr(self, '_loi_cache', 'x') == 'x':
            try:
                from .nx_worker import nap_loi_kiem_cheo
                self._loi_cache = nap_loi_kiem_cheo()[2]
            except Exception as e:
                self._loi_cache = None
                self._loi_loi = str(e)
        return self._loi_cache

    def _doc_ket_qua_cu(self, out, v, loi):
        """Kết quả lượt kiểm chéo trước, đọc lại từ `nx_crosscheck_<tên>.json`.

        Một cảnh báo chỉ tồn tại trong khoảnh khắc bấm nút thì hôm sau không
        còn gì nói rằng mặt cắt này chưa bao giờ được kiểm chéo — đúng lỗi đã
        vá ở cảnh báo hoạt tải. Kết quả cũ được ghi rõ là **lần trước**, và
        được đối chiếu dấu thời gian với `.mcb`/`.xls` để biết nó còn nói về
        mô hình đang có hay không.
        """
        ten = v['ten']
        p = os.path.join(out, ten, f'nx_crosscheck_{ten}.json')
        if not os.path.exists(p):
            return None
        try:
            with open(p, encoding='utf-8') as f:
                kq = json.load(f)
            # So dấu thời gian với hai tệp nguồn: tạo lại MCT rồi chạy lại
            # Civil 2022 là kết quả kiểm chéo cũ không còn nói về mô hình đang
            # có nữa.
            t_kq = os.path.getmtime(p)
            lac_hau = any(os.path.exists(f) and os.path.getmtime(f) > t_kq
                          for f in (v['mcb'], v['xls']))
            return dict(kq), bool(loi.dat(kq)), True, lac_hau
        except (OSError, ValueError, KeyError):
            return None

    def _fill(self):
        t = self.table
        t.setRowCount(len(self._viec))
        n_dat = n_hong = n_chua = n_lac = n_nghi = 0
        for i, v in enumerate(self._viec):
            ten = v['ten']
            got = self._kq.get(ten)
            if got is None:
                # Chưa chạy lần nào, nhưng lý do nguồn thì biết được ngay từ
                # dấu thời gian — nói luôn, đừng bắt người dùng chạy 45 giây
                # rồi mới biết phép so đó không dùng được.
                nguon = v.get('nguon') or ()
                cells = [ten, '—', '—', '—', '—', '—',
                         (CHUA + ' · ' + ' · '.join(nguon)) if nguon else CHUA]
                mau = 'warn' if nguon else None
                n_chua += 1
            else:
                kq, ok, cu, lac_hau = got
                nguon = v.get('nguon') or ()
                cells = hang(kq, ok, cu, lac_hau, nguon)
                # Lạc hậu thì tô VÀNG dù kết quả cũ là ĐẠT — xanh lá đọc thành
                # "yên tâm", mà đó chính là điều không được nói ở đây. Nguồn
                # không cùng mô hình cũng vàng, và cùng lý do.
                mau = ('warn' if (lac_hau or nguon)
                       else ('ok' if ok else 'err'))
                n_nghi += bool(nguon)
                n_dat += bool(ok and not lac_hau and not nguon)
                n_hong += bool(not ok and not nguon)
                n_lac += bool(lac_hau)
            for j, s in enumerate(cells):
                it = QTableWidgetItem(s)
                it.setToolTip(s)
                if j == len(COT) - 1 and mau:
                    # Màu lấy từ token — bảng Tối cần nền tối, mã màu cứng thì
                    # đứng yên khi đổi bảng màu và chỉ lộ ra sau khi sang Tối.
                    it.setBackground(QBrush(QColor(self.t[f'{mau}_bg'])))
                    it.setForeground(QBrush(QColor(self.t[mau])))
                t.setItem(i, j, it)
        bits = []
        if n_dat:
            bits.append(f'{n_dat} đạt')
        if n_hong:
            bits.append(f'{n_hong} hỏng')
        if n_nghi:
            bits.append(f'{n_nghi} không kết luận (nguồn khác mô hình)')
        if n_lac:
            bits.append(f'{n_lac} kết quả cũ, mô hình đã đổi')
        if n_chua:
            bits.append(f'{n_chua} chưa chạy')
        if not self._viec:
            # Hỏi cache chứ KHÔNG gọi `_loi()`: `_fill()` chạy ngay lúc dựng
            # cửa sổ (qua `apply_theme`), mà `_loi()` kéo theo `requests` — nạp
            # thư viện của một tính năng chưa ai bấm là làm chậm mọi lần mở app.
            loi_msg = (getattr(self, '_loi_loi', '')
                       if getattr(self, '_loi_cache', 1) is None else '')
            bits = [loi_msg or (
                'Không mặt cắt nào có đủ .mcb và Beam Force trong '
                f'{self._output_dir()} — chạy Midas Civil 2022 (F8) trước.')]
        self.lb_sum.setText(' · '.join(bits))
        self.btn_run.setEnabled(bool(self._viec) and self.worker is None)

    def _on_cell(self, row, _col):
        if 0 <= row < len(self._viec):
            self.section_selected.emit(self._viec[row]['ten'])

    # ── chạy ─────────────────────────────────────────────────
    def _xin_phep(self) -> bool:
        """Cổng giấy phép cho tính năng `'nx'`.

        Đặt ở **chỗ tính**, không phải chỗ mở thẻ: mở thẻ để xem bố cục thì
        không hại gì, cho NX giải lại và ra bảng đạt/hỏng mới là sản phẩm. Đây
        đúng lối `CheckTab.run_check` đang làm, và là lỗi bản đầu của tính năng
        giấy phép đã mắc (cổng đặt ở chỗ mở thẻ nên bấm F5 vẫn chạy tuốt).
        """
        if self._require_license is not None:
            return bool(self._require_license('nx'))
        from src.security import guard
        state = guard.get_runtime_state('nx')
        if state.ready:
            return True
        self.lb_sum.setText(state.message.replace('\n', ' · '))
        QMessageBox.warning(self, 'Chưa được phép', state.message)
        return False

    def _cua_minh(self, viec) -> set:
        """`(số nút, số phần tử)` của những mô hình app biết chắc là của mình.

        MAPI không có endpoint nào trả tên file đang mở, nên `kiem_tai_lieu_sach`
        chỉ nhận diện được bằng hai con số này. Lấy từ project trước — app đã
        ghi sẵn `n_nodes`/`n_elems` lúc sinh MCT nên không phải đoán; mặt cắt
        nào không có trong project thì đọc `topo.json` bên cạnh.

        Phải kê **mọi** mặt cắt chứ không chỉ lượt này: sau một lượt, NX còn giữ
        mô hình của mặt cắt cuối, và lượt sau gặp lại nó ở cổng an toàn — đúng
        lỗi "chạy loạt lần hai bao giờ cũng vấp" đã sửa cho driver Civil 2022.
        """
        ra = {(s.n_nodes, s.n_elems) for s in self.project if s.n_nodes}
        co = {s.name for s in self.project}
        out = self._output_dir()
        for v in viec:
            if v['ten'] in co:
                continue
            p = os.path.join(out, v['ten'], f'{v["ten"]}_topo.json')
            try:
                with open(p, encoding='utf-8') as f:
                    d = json.load(f)
                ids = set()
                for k in ('top_ids', 'bot_ids', 'wL_ids', 'wC_ids', 'wR_ids'):
                    ids |= set(d.get(k) or [])
                ra.add((len(ids), len(d['elements'])))
            except (OSError, KeyError, ValueError):
                pass
        return ra

    def _chon(self) -> list:
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        viec = [self._viec[r] for r in rows if 0 <= r < len(self._viec)]
        return viec or list(self._viec)

    def run(self):
        if self.worker is not None:
            return
        if not self._xin_phep():
            return
        viec = self._chon()
        if not viec:
            return
        if not self._xac_nhan(viec):
            return

        from .nx_worker import NXWorker
        self._log('info', f'Kiểm chéo NX: {len(viec)} mặt cắt')
        self.worker = NXWorker(viec, cua_minh=self._cua_minh(self._viec))
        self.worker.log.connect(self._on_log)
        self.worker.section_done.connect(self._on_done)
        self.worker.section_error.connect(self._on_error)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.start()
        self.btn_run.setEnabled(False)
        self.status_bar.showMessage(
            f'Đang kiểm chéo bằng NX: {len(viec)} mặt cắt…')

    def _xac_nhan(self, viec) -> bool:
        """Hỏi trước khi chạy — vì lệnh sắp tới đụng vào phiên của người dùng.

        `doc/OPEN` **đè lên tài liệu đang mở trong NX, không hỏi gì**.
        `kiem_tai_lieu_sach()` chặn được mô hình lạ, nhưng người dùng vẫn nên
        biết trước rằng cửa sổ NX của họ sắp đổi nội dung. Mặc định là **Huỷ**:
        lỡ tay Enter thì phải là không làm gì.
        """
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle('Kiểm chéo bằng MIDAS CIVIL NX')
        box.setText(f'Sắp cho NX giải lại {len(viec)} mặt cắt.')
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setInformativeText(
            'NX phải đang chạy và đã bấm <b>Connect</b>. App sẽ <b>mở mô hình '
            'trong cửa sổ NX của bạn</b> (bản sao trong hộp cát) — tài liệu '
            'đang mở ở đó sẽ bị thay. Nếu NX đang giữ một mô hình lạ thì app '
            'dừng và báo, không đè lên.<br><br>'
            'Khoảng 10–20 giây mỗi mặt cắt. Chuột và bàn phím <b>không</b> bị '
            'chiếm.')
        canh = [f'{v["ten"]}: {c}' for v in viec for c in (v.get('nguon') or ())]
        if canh:
            # Chạy vẫn được — người dùng có thể muốn xem con số. Nhưng phải
            # biết TRƯỚC rằng kết quả sẽ không kết luận được điều gì, thay vì
            # đọc một bảng HỎNG rồi đi tìm lỗi trong MCT.
            box.setInformativeText(
                box.informativeText() + '<br><br><b>' + str(len(canh)) +
                ' mặt cắt có nguồn không cùng một mô hình</b> — kết quả sẽ '
                'không kết luận được. Sinh lại MCT rồi chạy lại Civil 2022 '
                'trước thì phép so mới có nghĩa.')
        box.setDetailedText('\n'.join(
            [f'{v["ten"]}  ←  {v["mcb"]}' for v in viec] +
            ([''] + canh if canh else [])))
        go = box.addButton('Chạy', QMessageBox.ButtonRole.AcceptRole)
        box.addButton('Huỷ', QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(box.buttons()[-1])
        box.exec()
        return box.clickedButton() is go

    def xin_dung(self):
        if self.worker is not None:
            self.worker.xin_dung()

    # ── tín hiệu từ worker ───────────────────────────────────
    def _log(self, muc, msg):
        if self.log_area is None:
            return
        getattr(self.log_area, {'info': 'info', 'ok': 'success',
                                'warn': 'warning', 'err': 'error'}[muc])(msg)

    def _on_log(self, msg):
        if self.log_area is not None:
            self.log_area.append_auto(msg)

    def _on_done(self, ten, kq, ok):
        # Đếm theo MẶT CẮT đã kiểm chéo xong, không theo số lần bấm nút —
        # cùng lối `generate_tab` đếm `mct`. Thiếu dòng này thì thẻ *Sử dụng*
        # công bố thiếu một loại việc, mà công bố thiếu thì đúng là thứ luật
        # minh bạch của dự án sinh ra để tránh.
        from src.security import usage_log
        usage_log.record('nx')

        self._kq[ten] = (dict(kq), bool(ok), False, False)
        self._fill()
        self.status_bar.showMessage(
            f'{ten}: {DAT if ok else HONG} · ghép {kq.get("ghep", 0):,} bản ghi')

    def _on_error(self, ten, msg):
        # `NXError` đã là câu viết cho người dùng — đưa nguyên văn, đừng gói lại.
        self._log('err', f'[{ten}] {msg}')

    def _on_finished(self, so_dat, so_hong):
        self.worker = None
        self._fill()
        if so_hong:
            self._log('warn', f'Kiểm chéo NX: {so_dat} đạt · {so_hong} hỏng')
        elif so_dat:
            self._log('ok', f'Kiểm chéo NX: {so_dat}/{so_dat} mặt cắt đạt')
        self.status_bar.showMessage(
            f'Kiểm chéo NX xong: {so_dat} đạt · {so_hong} hỏng')

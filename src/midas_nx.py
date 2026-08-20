"""
Client MIDAS CIVIL NX API (MAPI) — mở mô hình, giải, đọc bảng nội lực.

Vì sao có module này
────────────────────
`src/midas_driver.py` điều khiển Midas Civil 2022 bằng **giao diện**: bấm ribbon,
tick ListBox, chờ hộp thoại. Nó chiếm chuột và bàn phím của máy suốt lúc chạy, và
mỗi bước là một cơ hội bấm hụt. Civil NX thì có API REST thật, nên cùng một việc:

    mở mô hình → giải → xuất nội lực

đi hết bằng ba lệnh HTTP, **không chạm chuột**, và nhanh hơn hẳn (S16: 9 s so với
50–70 s qua giao diện).

Dùng để **kiểm chéo**: cùng một `.mcb`, cho hai bản Midas giải rồi so nội lực.
Trên S16 đã đối chiếu đủ 7.656 bản ghi, lệch lớn nhất `My` 0,090 kN·m.

Bốn sự thật phải nhớ
────────────────────
1. **MAPI-Key CHẾT mỗi lần MIDAS khởi động lại.** Lấy lại ở NX: `Apps → API
   Settings → Disconnect → Refresh → Connect → Copy`. Key **không** được để trong
   mã nguồn hay trong thư mục dự án — đọc từ biến `MAPI_KEY` hoặc file
   `%USERPROFILE%\\mapikey.txt`.

2. **"command complete" KHÔNG có nghĩa là xong.** `/doc/IMPORT` trả đúng câu đó
   cho một file `.mct` rồi nạp về **0 nút**. Mọi lệnh làm đổi mô hình ở đây đều
   phải **đọc lại** `db/NODE` để xác nhận, chứ không tin thông báo.

3. **`/doc/OPEN` chỉ nhận `.mcb`**, và tham số là **chuỗi trần** (`{"Argument":
   "C:\\...\\a.mcb"}`), không phải `{"Argument": {"PATH": ...}}`. File `.mct` thì
   `OPEN` báo *Failed to open file* còn `IMPORT` báo complete mà không nạp gì —
   nghĩa là **chưa có đường nạp MCT vào NX qua API**.

4. **`/doc/NEW` xoá trắng tài liệu đang mở.** Phiên NX là của người dùng, nên
   `kiem_tai_lieu_sach()` phải chạy trước, y như luật của `midas_driver`.

Hai kiểu 404 (rất tiện lúc dò đường)
────────────────────────────────────
    "404 Not Found, Please check your request url."  → sai cả NHÓM lệnh
    "404 Not Found"                                  → đúng nhóm, sai TÊN

Nhóm hợp lệ: `db` · `doc` · `post` · `view`. Tên lệnh trong `doc` phải **viết
hoa** (`OPEN`, `NEW`, `ANAL`, `SAVEAS`), còn tên bảng trong `db` thì không phân
biệt hoa thường (`db/unit` và `db/UNIT` như nhau).
"""

import json
import os
import time

import requests

BASE = 'https://moa-engineers.midasit.com:443/civil'

# Nơi tìm MAPI-Key, theo thứ tự. Cố ý KHÔNG có chỗ nào trong thư mục dự án —
# key là bí mật ngắn hạn, lọt vào git là phải xoay lại.
NOI_DE_KEY = [
    ('bien môi trường MAPI_KEY', None),
    ('%MAPI_KEY_FILE%', os.environ.get('MAPI_KEY_FILE') or ''),
    ('%TEMP%\\mapikey.txt', os.path.join(os.environ.get('TEMP', ''), 'mapikey.txt')),
    ('%USERPROFILE%\\mapikey.txt',
     os.path.join(os.environ.get('USERPROFILE', ''), 'mapikey.txt')),
]


class NXError(RuntimeError):
    """Lỗi có tên, để chỗ gọi in thẳng cho người dùng."""


def doc_key() -> str:
    """MAPI-Key, tìm theo `NOI_DE_KEY`. Không thấy thì báo cách lấy."""
    key = (os.environ.get('MAPI_KEY') or '').strip()
    if key:
        return key
    for _ten, p in NOI_DE_KEY:
        if p and os.path.isfile(p):
            k = open(p, encoding='utf-8-sig').read().strip()
            if k:
                return k
    raise NXError(
        'không tìm thấy MAPI-Key. Trong MIDAS CIVIL NX: Apps → API Settings → '
        'Disconnect → Refresh → Connect → Copy, rồi lưu vào '
        '%USERPROFILE%\\mapikey.txt (hoặc đặt biến môi trường MAPI_KEY). '
        'Key CHẾT mỗi lần MIDAS khởi động lại nên phải lấy lại sau mỗi lần mở.')


class NX:
    """Một phiên làm việc với MIDAS CIVIL NX đang chạy.

    Không mở, không đóng NX — phiên là của người dùng, đúng luật của
    `midas_driver`. Chỉ `doc/NEW` và `doc/OPEN` mới làm mất tài liệu đang mở, và
    cả hai đều đi qua `kiem_tai_lieu_sach()`.
    """

    def __init__(self, key: str = None, log=print):
        self.key = key or doc_key()
        self.log = log

    # ── tầng HTTP ────────────────────────────────────────────
    def _goi(self, method, ep, body=None, han=300):
        h = {'MAPI-Key': self.key, 'Content-Type': 'application/json'}
        try:
            r = requests.request(method, f'{BASE}/{ep.lstrip("/")}', headers=h,
                                 json=body if body is not None else {},
                                 timeout=han)
        except requests.RequestException as e:
            raise NXError(f'{method} {ep}: không gọi được API — {e}') from e
        try:
            d = r.json()
        except ValueError:
            raise NXError(f'{method} {ep}: API trả về thứ không phải JSON — '
                          f'{r.text[:200]}')
        if isinstance(d, dict) and 'error' in d:
            msg = (d['error'] or {}).get('message', '')
            if 'not opened' in msg:
                raise NXError('NX chưa mở tài liệu nào')
            raise NXError(f'{method} {ep}: {msg}')
        return d

    def get(self, ep, han=120):
        return self._goi('GET', ep, None, han)

    def post(self, ep, body=None, han=300):
        return self._goi('POST', ep, body, han)

    # ── trạng thái ───────────────────────────────────────────
    def song(self) -> dict:
        """Đơn vị đang đặt trong NX — cũng là phép thử key còn sống không."""
        return self.get('db/UNIT').get('UNIT', {})

    def dem(self) -> tuple:
        """(số nút, số phần tử) của tài liệu đang mở; (0, 0) nếu chưa mở."""
        try:
            n = len(self.get('db/NODE').get('NODE') or {})
            e = len(self.get('db/ELEM').get('ELEM') or {})
        except NXError as e:
            if 'chưa mở tài liệu' in str(e):
                return 0, 0
            raise
        return n, e

    def kiem_tai_lieu_sach(self, cua_minh=()):
        """Dừng nếu NX đang mở một mô hình **không phải của ta**.

        `doc/OPEN` và `doc/NEW` đè lên tài liệu hiện tại **không hỏi gì**. Thà
        dừng và báo còn hơn làm mất việc đang dở của người dùng — cùng một luật
        với `midas_driver.kiem_tai_lieu_sach()`.

        Args:
            cua_minh: tập `(số nút, số phần tử)` của những mô hình lượt chạy này
                sẽ đụng tới. Khớp một trong số đó thì coi là sản phẩm của lượt
                trước và cho đi tiếp.

        Nhận diện bằng số đếm là chỗ **yếu nhất** của module này, và nói rõ ra
        đây: MAPI không có endpoint nào trả tên file đang mở (`db/PROJINFO`,
        `db/FILENAME`… đều 404), nên không có cách nào so đường dẫn như driver
        Civil 2022 vẫn làm. Mô hình của người dùng mà tình cờ đúng cả hai con số
        thì sẽ bị nhận nhầm. Đổi lại, không có phép kiểm này thì **lượt chạy thứ
        hai bao giờ cũng vấp** — đúng lỗi đã xảy ra với `chay_nhieu_mat_cat`.
        """
        n, e = self.dem()
        if not (n or e):
            return
        if (n, e) in set(cua_minh):
            self.log(f'  NX đang giữ mô hình của lượt trước ({n} nút · '
                     f'{e} phần tử) — ghi đè')
            return
        raise NXError(
            f'NX đang mở một mô hình lạ ({n} nút · {e} phần tử). Lệnh sắp chạy '
            f'sẽ đè lên nó. Hãy lưu rồi đóng tài liệu đó trong NX (File › Close), '
            f'sau đó chạy lại.')

    # ── thao tác ─────────────────────────────────────────────
    def mo(self, mcb: str, cho_nut=True):
        """Mở một `.mcb` rồi **đọc lại** để xác nhận đã nạp thật.

        `mcb` phải là đường dẫn tuyệt đối; NX chạy trong tiến trình khác nên
        đường dẫn tương đối là tương đối với thư mục của NX, không phải của ta.
        """
        mcb = os.path.abspath(mcb)
        if not os.path.exists(mcb):
            raise NXError(f'không thấy file: {mcb}')
        if os.path.splitext(mcb)[1].lower() != '.mcb':
            raise NXError(
                f'chỉ mở được .mcb, không mở được {os.path.basename(mcb)}. '
                f'NX không nạp .mct qua API: /doc/IMPORT báo "command complete" '
                f'nhưng nạp về 0 nút.')
        self.post('doc/OPEN', {'Argument': mcb})
        n, e = self.dem()
        # "command complete" không đủ — phải thấy số liệu mới tính là mở được.
        if cho_nut and not n:
            raise NXError(f'mở {os.path.basename(mcb)} xong mà mô hình rỗng '
                          f'(0 nút) — NX không đọc được file này')
        self.log(f'  mở {os.path.basename(mcb)}: {n} nút · {e} phần tử')
        return n, e

    def moi(self):
        """Tài liệu trắng. Gọi `kiem_tai_lieu_sach()` trước nếu chưa chắc."""
        self.post('doc/NEW', {})

    def giai(self, han=3600) -> float:
        """Chạy phân tích. Trả về số giây đã chờ."""
        t0 = time.time()
        self.post('doc/ANAL', {}, han=han)
        d = time.time() - t0
        self.log(f'  phân tích xong sau {d:.0f}s')
        return d

    def noi_luc(self, eids=None, han=900) -> list:
        """Bảng Beam Force, dạng list dict giống `result_reader.parse_beam_force`.

        Chỉ giữ hai đầu I/J: NX trả cả điểm 1/4, 2/4, 3/4 mà bảng kiểm toán
        không dùng tới, và `.xls` của Civil 2022 cũng không xuất.
        """
        if eids is None:
            eids = sorted(int(k) for k in (self.get('db/ELEM').get('ELEM') or {}))
        if not eids:
            raise NXError('mô hình không có phần tử nào')
        d = self.post('post/table', {'Argument': {
            'TABLE_NAME': 'BF', 'TABLE_TYPE': 'BEAMFORCE',
            'NODE_ELEMS': {'KEYS': list(eids)}}}, han=han)
        if 'BF' not in d:
            raise NXError(f'không lấy được bảng Beam Force: '
                          f'{json.dumps(d, ensure_ascii=False)[:200]}')
        head = d['BF'].get('HEAD') or []
        col = {h: i for i, h in enumerate(head)}
        for c in ('Elem', 'Load', 'Part', 'Shear-z', 'Moment-y'):
            if c not in col:
                raise NXError(f'bảng Beam Force thiếu cột {c!r}; có: {head}')

        def so(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        ra = []
        for r in d['BF'].get('DATA') or []:
            part = str(r[col['Part']]).strip()
            if part[:1] not in ('I', 'J'):
                continue
            ra.append({'elem': int(so(r[col['Elem']])),
                       'load': str(r[col['Load']]).strip(),
                       'end': part[0],
                       'Vz': so(r[col['Shear-z']]),
                       'My': so(r[col['Moment-y']])})
        self.log(f'  Beam Force: {len(ra)} bản ghi (I/J)')
        return ra


def la_bao(ten_tai: str, tai_co_ban=None) -> bool:
    """Trường hợp tải này là kết quả DẪN XUẤT (tổ hợp / bao) hay không.

    Args:
        tai_co_ban: tên các trường hợp tải **tĩnh** của chính mô hình, đọc từ
            `db/STLD`. Có nó thì phân loại chắc chắn: tên nào không nằm trong
            đó đều là dẫn xuất.

    Không có `tai_co_ban` thì lui về đoán theo hậu tố `(max)/(min)/(all)` mà
    Midas gắn cho trị số lấy từ đường bao. **Cách đoán này thiếu**: `Cuong do
    III` và `Cuong do IV` là tổ hợp nhưng không có hậu tố (chúng không chứa
    hoạt tải, nên chỉ có một trị số), và đoán nhầm chúng thành tải cơ bản đã
    làm lượt kiểm S1_V2 báo "320 bản ghi tải cơ bản lệch" trong khi cả 22
    trường hợp tải cơ bản thật đều trùng khít.
    """
    if tai_co_ban is not None:
        return ten_tai.strip() not in tai_co_ban
    return ten_tai.strip().lower().endswith(('(max)', '(min)', '(all)'))


def so_sanh(a: list, b: list, dung_sai=0.011, dung_sai_bao=0.01,
            tai_co_ban=None) -> dict:
    """So hai bộ nội lực theo khoá (phần tử, trường hợp tải, đầu I/J).

    **Hai loại trường hợp tải phải đo bằng hai thước khác nhau** — đây là kết
    luận rút ra từ lượt kiểm chéo đầu tiên trên bốn mặt cắt thật:

    Loại nào là "cơ bản" thì đọc từ `db/STLD` của chính mô hình (`tai_co_ban`),
    không đoán theo tên — xem `la_bao()`.

    · **Tải cơ bản** (`Prestress`, `Barrier`, `Self`…): hai bản Midas giải cùng
      một hệ phương trình tuyến tính, nên phải ra **cùng một số**. Chỉ cho phép
      lệch bằng đơn vị hiển thị của bảng (2 chữ số thập phân) → `dung_sai`
      tuyệt đối 0,011. Lệch hơn thế nghĩa là hai bên đang giải hai mô hình
      khác nhau, và đó mới là điều đáng báo.

    · **Trị số BAO** (`Cuong do I(max)`, `ser_all(min)`, `LCB1(max)`…): dựng
      trên bao hoạt tải di động, mà mỗi bản Midas rời rạc hoá đường ảnh hưởng
      theo cách riêng. Đo bằng sai số **tương đối** (`dung_sai_bao`, mặc định
      1%). Đo bằng thước tuyệt đối thì S1_V2 lệch 3,98 kN·m trên trị 64 kN·m
      bị gọi là hỏng, trong khi đó chỉ là 6% của một đại lượng vốn không buộc
      phải trùng.

    Returns:
        {'ghep', 'chi_a', 'chi_b', 'max_My', 'max_Vz', 'max_bao_tuong_doi',
         'qua_dung_sai', 'qua_dung_sai_bao', 'vi_du'}
        `qua_dung_sai` đếm riêng **tải cơ bản** — đó là con số quyết định đạt hỏng.
    """
    def khoa(r):
        return (int(r['elem']), str(r['load']).strip(), str(r['end']).strip())

    A = {khoa(r): r for r in a}
    B = {khoa(r): r for r in b}
    chung = A.keys() & B.keys()
    max_my = max_vz = max_td = 0.0
    qua = qua_bao = 0
    vi_du = []
    for k in sorted(chung):
        dmy = abs(A[k]['My'] - B[k]['My'])
        dvz = abs(A[k]['Vz'] - B[k]['Vz'])
        if la_bao(k[1], tai_co_ban):
            thang = max(abs(A[k]['My']), abs(A[k]['Vz']), 1.0)
            td = max(dmy, dvz) / thang
            max_td = max(max_td, td)
            if td > dung_sai_bao:
                qua_bao += 1
            continue
        max_my, max_vz = max(max_my, dmy), max(max_vz, dvz)
        if dmy > dung_sai or dvz > dung_sai:
            qua += 1
            if len(vi_du) < 10:
                vi_du.append({'khoa': k, 'My': (A[k]['My'], B[k]['My']),
                              'Vz': (A[k]['Vz'], B[k]['Vz'])})
    return {'ghep': len(chung),
            'chi_a': len(A.keys() - B.keys()),
            'chi_b': len(B.keys() - A.keys()),
            'max_My': max_my, 'max_Vz': max_vz,
            'max_bao_tuong_doi': max_td,
            'qua_dung_sai': qua, 'qua_dung_sai_bao': qua_bao, 'vi_du': vi_du}

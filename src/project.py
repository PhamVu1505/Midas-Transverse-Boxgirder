"""
Mô hình project — nguồn sự thật duy nhất cho danh sách mặt cắt.

Vì sao cần
──────────
Trước đây hai nửa quy trình rời nhau: tab Tạo mô hình sinh ra MCT + topo.json,
rồi tab Kiểm toán phải ĐOÁN NGƯỢC xem file Beam Force nào ứng với MCT nào —
`_match_pairs()` dài 60 dòng dò theo tên file và thư mục cha. Toàn bộ thông tin
đó vốn đã biết ngay lúc sinh MCT, chỉ là không có chỗ nào lưu.

`Project` giữ thông tin đó: mỗi `Section` nhớ luôn DXF gốc, template riêng,
MCT/topo đã sinh, file Beam Force được gán và trạng thái hiện tại. Ghi ra file
`.mtbproj` (JSON) nên mở lại phiên sau vẫn còn nguyên.

Template theo từng mặt cắt: các mặt cắt cùng số sườn và cùng bề rộng thì dùng
chung được, nên `Section.template` để rỗng nghĩa là lấy `Project.template`.
"""

import json
import os
from dataclasses import dataclass, field, asdict

FILE_EXT = '.mtbproj'
FORMAT_VERSION = 1

# Trạng thái theo đúng thứ tự quy trình
NEW = 'new'              # đã thêm DXF, chưa sinh MCT
GENERATED = 'generated'  # đã có MCT + topo
ASSIGNED = 'assigned'    # đã gán file Beam Force
CHECKED = 'checked'      # đã ra bảng kiểm toán
ERROR = 'error'

STATUS_LABEL = {
    NEW:       'Chưa tạo MCT',
    GENERATED: 'Đã tạo MCT',
    ASSIGNED:  'Đã gán Beam Force',
    CHECKED:   'Đã kiểm toán',
    ERROR:     'Lỗi',
}
STATUS_ORDER = [NEW, GENERATED, ASSIGNED, CHECKED, ERROR]


def same_inputs(a: str, b: str) -> bool:
    """Hai nguồn số liệu có cho ra CÙNG các con số không.

    Đọc không được bên nào thì coi là KHÁC: không biết chắc là giống thì phải
    nói ra rằng kết quả có thể đã lạc hậu, chứ không im lặng cho qua.
    """
    if not a and not b:
        return True
    try:
        from .input_data import keys
        from .input_reader import read_inputs
        da, db = read_inputs(a, strict=True), read_inputs(b, strict=True)
    except Exception:
        return False
    return all(da.get(k) == db.get(k) for k in keys())


@dataclass
class Section:
    """Một mặt cắt ngang trong project."""
    name: str
    dxf: str
    template: str = ''         # rỗng = dùng template chung của project
    include_pt: bool = True

    mct: str = ''
    topo: str = ''
    beam_force: str = ''
    report: str = ''

    section_type: str = ''     # 'single' | 'twin_box'
    n_nodes: int = 0
    n_elems: int = 0
    pt_cables: list = field(default_factory=list)

    # Gối lưu theo TOẠ ĐỘ X, không theo ID node: đổi target_len hay sửa DXF là
    # ID node đổi hết, còn vị trí gối trên bản đáy thì không. Lúc ghi MCT mới
    # quy về node đáy gần nhất.  [{'x': float, 'kind': 'pin'|'roller'|'fixed'}]
    supports: list = field(default_factory=list)

    # Cốt thép nhập tay cho tab Kiểm toán mặt cắt, khoá theo TÊN ĐIỂM kiểm toán
    # ('A', 'A1', 'E2'…): {'dia', 'spacing', 'cover', 'Av', 'Av_spacing',
    # 'dp', 'Ap'}. Điểm phân giải thiếu số liệu thì `section_check.check_all`
    # tự lui về chữ cái đầu, nên chỉ cần nhập 'A' là A1/A2 dùng theo.
    rebars: dict = field(default_factory=dict)
    # Tuỳ chọn kiểm toán riêng của mặt cắt: tiêu chuẩn, phương pháp cắt, φ, fy…
    check_opts: dict = field(default_factory=dict)

    # Căng cáp một đầu ('begin') hay hai đầu ('both') — vào ô JACKING của
    # *TDN-PRESTRESS. Mặc định 'begin' để MCT của project cũ giống hệt bản trước.
    pt_jacking: str = 'begin'

    status: str = NEW
    note: str = ''

    # Vì sao nội lực đang gán KHÔNG còn khớp mô hình. Rỗng = còn khớp.
    #
    # Đây là loại sai nguy hiểm nhất của phần mềm này: mô hình vẫn chạy, bảng
    # kiểm toán vẫn ra số đẹp, và không có gì trong cả quy trình lộ ra rằng số
    # đó thuộc về một mô hình đã bị thay. Trạng thái `assigned` được giữ
    # nguyên — người dùng không mất đường dẫn Beam Force đã gán — nhưng mọi
    # chỗ hiển thị kết quả phải nói rõ là nó đã lạc hậu.
    stale: str = ''

    def set_supports(self, supports):
        """Đặt danh sách gối, sắp theo X cho danh sách hiển thị ổn định."""
        self.supports = sorted(
            ({'x': round(float(s['x']), 6),
              'kind': s.get('kind', 'roller')} for s in supports or []),
            key=lambda s: s['x'])

    def reset_outputs(self):
        """Xóa kết quả đã sinh — dùng khi DXF hoặc template đổi."""
        self.mct = self.topo = self.report = ''
        self.section_type = ''
        self.n_nodes = self.n_elems = 0
        self.pt_cables = []
        self.status = NEW
        self.note = ''
        # Không còn kết quả nào thì cũng không còn gì lạc hậu.
        self.stale = ''


@dataclass
class Project:
    """Tập hợp mặt cắt + thiết lập chung."""
    name: str = 'Project mới'
    output_dir: str = 'output'
    template: str = ''
    sections: list = field(default_factory=list)

    # Tải bánh: lấy từ template Excel (False) hay app tự tính từ hình học mặt
    # cắt (True). Đặt ở mức project chứ không mức mặt cắt — nó là lựa chọn
    # PHƯƠNG PHÁP, mà một hồ sơ trộn hai phương pháp giữa các mặt cắt thì
    # người thẩm tra không có cách nào biết mặt cắt nào theo đường nào.
    auto_live_load: bool = False

    path: str = ''             # đường dẫn .mtbproj (rỗng = chưa lưu)
    _dirty: bool = False

    # ── truy vấn ──
    def __bool__(self):
        # Có __len__ nên project rỗng sẽ là falsy nếu không định nghĩa __bool__.
        # Một project rỗng vẫn là một project hợp lệ — `x or Project()` từng
        # âm thầm thay thế nó bằng đối tượng mới.
        return True

    def __len__(self):
        return len(self.sections)

    def __iter__(self):
        return iter(self.sections)

    def find(self, name: str):
        for s in self.sections:
            if s.name == name:
                return s
        return None

    def template_for(self, section) -> str:
        """Template hiệu lực của một mặt cắt: riêng nếu có, không thì của project."""
        if isinstance(section, str):
            section = self.find(section)
        if section and section.template:
            return section.template
        return self.template

    def by_status(self, status) -> list:
        return [s for s in self.sections if s.status == status]

    def counts(self) -> dict:
        c = {k: 0 for k in STATUS_ORDER}
        for s in self.sections:
            c[s.status] = c.get(s.status, 0) + 1
        return c

    @property
    def total_elements(self) -> int:
        return sum(s.n_elems for s in self.sections)

    @property
    def dirty(self) -> bool:
        return self._dirty

    def touch(self):
        self._dirty = True

    @property
    def title(self) -> str:
        return os.path.splitext(os.path.basename(self.path))[0] if self.path else self.name

    # ── sửa đổi ──
    def add_dxf(self, dxf_path: str, template: str = '') -> 'Section':
        """Thêm một DXF. Trùng đường dẫn thì trả lại mặt cắt sẵn có."""
        dxf_path = os.path.normpath(dxf_path)
        for s in self.sections:
            if os.path.normpath(s.dxf) == dxf_path:
                return s
        name = os.path.splitext(os.path.basename(dxf_path))[0]
        base, i = name, 2
        while self.find(name):
            name = f'{base}_{i}'
            i += 1
        sec = Section(name=name, dxf=dxf_path, template=template)
        self.sections.append(sec)
        self._dirty = True
        return sec

    def remove(self, name: str) -> bool:
        s = self.find(name)
        if not s:
            return False
        self.sections.remove(s)
        self._dirty = True
        return True

    def set_template(self, name: str, template: str):
        s = self.find(name)
        if s:
            s.template = template
            s.reset_outputs()
            self._dirty = True

    def set_supports(self, name: str, supports):
        s = self.find(name)
        if s:
            truoc = list(s.supports)
            s.set_supports(supports)
            self._dirty = True
            # Sơ đồ gối quyết định nội lực. Đổi nó trên một mặt cắt ĐÃ có kết
            # quả thì bảng nội lực và bảng kiểm toán đang hiện thuộc về một mô
            # hình khác — mà trước đây không có gì nói ra điều đó: trạng thái
            # vẫn `assigned`, hệ số an toàn vẫn ra số đẹp.
            #
            # So sánh trước/sau vì tín hiệu này còn phát cả khi chỉ dựng lại
            # danh sách; đánh dấu vô điều kiện thì cảnh báo kêu suốt và người
            # dùng thôi đọc.
            if truoc != s.supports:
                self.mark_stale(
                    name,
                    'Sơ đồ gối đã đổi sau khi có kết quả — nội lực đang gán '
                    'tính từ sơ đồ gối cũ. Hãy tạo lại MCT và chạy lại Midas.')

    def set_rebars(self, name: str, rebars: dict):
        """Ghi bảng cốt thép của một mặt cắt. Không đụng tới trạng thái quy
        trình: đổi cốt thép chỉ làm bảng kiểm toán cũ hết hiệu lực, còn MCT và
        Beam Force vẫn nguyên."""
        s = self.find(name)
        if s is None:
            return
        s.rebars = {k: dict(v) for k, v in (rebars or {}).items()}
        self._dirty = True

    def set_pt_jacking(self, name: str, jacking: str):
        """Căng một đầu ('begin') hay hai đầu ('both').

        Chỉ đổi ô JACKING trong MCT sắp sinh, không đụng trạng thái quy trình —
        MCT đã sinh vẫn còn đó, người dùng tự tạo lại khi muốn áp thay đổi.
        """
        s = self.find(name)
        if s is None or jacking not in ('begin', 'both'):
            return
        s.pt_jacking = jacking
        self._dirty = True

    def set_auto_live_load(self, bat: bool) -> int:
        """Đổi nguồn tải bánh: template Excel ↔ app tự tính từ hình học.

        Đổi trị này đổi **tải bánh của mọi mặt cắt**, tức đổi nội lực. Mặt cắt
        đã có Beam Force thì bảng nội lực và bảng kiểm toán đang hiện thuộc về
        một mô hình khác — đúng khuôn lỗi mà `Section.stale` sinh ra để chặn, và
        cùng lý do `set_supports` đánh dấu lạc hậu.

        So trước/sau rồi mới đánh dấu: chọn lại đúng trị đang dùng không phải
        là thay đổi, mà cảnh báo kêu vô cớ thì người dùng thôi đọc.

        Returns:
            số mặt cắt vừa bị đánh dấu lạc hậu.
        """
        bat = bool(bat)
        if bat == self.auto_live_load:
            return 0
        self.auto_live_load = bat
        self._dirty = True
        ly_do = ('Nguồn tải bánh đã đổi ('
                 + ('app tự tính từ hình học' if bat else 'template Excel')
                 + ') sau khi có kết quả — nội lực đang gán tính từ tải bánh '
                   'cũ. Hãy tạo lại MCT và chạy lại Midas.')
        return sum(1 for s in self.sections if self.mark_stale(s.name, ly_do))

    def set_shared_template(self, path: str) -> int:
        """Đổi nguồn số liệu CHUNG của project (template Excel hoặc khối `.json`).

        Trước đây ô chọn template gán thẳng `self.template` rồi thôi — đổi nguồn
        số liệu sau khi đã có Beam Force là bảng nội lực thuộc về một bộ số liệu
        khác mà không có gì nói ra. Nay đánh dấu lạc hậu mọi mặt cắt dùng
        template chung.

        So **trị số**, không so đường dẫn: chuyển template Excel sang khối số
        liệu của app (cùng 40 con số) là đổi lối vào, không đổi mô hình — đánh
        dấu lạc hậu lúc đó là bắt người dùng chạy lại Midas vô cớ.

        Returns:
            số mặt cắt vừa bị đánh dấu lạc hậu.
        """
        truoc = self.template
        if os.path.normcase(os.path.abspath(path or '')) == \
                os.path.normcase(os.path.abspath(truoc or '')):
            return 0
        self.template = path
        self._dirty = True
        if same_inputs(truoc, path):
            return 0
        ly_do = ('Nguồn số liệu đầu vào đã đổi (' + os.path.basename(path or '')
                 + ') sau khi có kết quả — nội lực đang gán tính từ số liệu cũ. '
                   'Hãy tạo lại MCT và chạy lại Midas.')
        return sum(1 for s in self.sections
                   if not s.template and self.mark_stale(s.name, ly_do))

    def inputs_edited(self, path: str) -> int:
        """Khối số liệu `path` vừa được sửa TẠI CHỖ — đánh dấu lạc hậu mọi mặt
        cắt đang dùng nó. Chỗ gọi (hộp thoại khai số liệu) đã so trước/sau."""
        key = os.path.normcase(os.path.abspath(path))
        ly_do = ('Số liệu đầu vào (' + os.path.basename(path) + ') đã sửa sau '
                 'khi có kết quả — nội lực đang gán tính từ số liệu cũ. Hãy tạo '
                 'lại MCT và chạy lại Midas.')
        n = 0
        for s in self.sections:
            tpl = self.template_for(s)
            if tpl and os.path.normcase(os.path.abspath(tpl)) == key:
                n += self.mark_stale(s.name, ly_do)
        return n

    def set_check_opts(self, name: str, opts: dict):
        s = self.find(name)
        if s is None:
            return
        s.check_opts = dict(opts or {})
        self._dirty = True

    def set_beam_force(self, name: str, path: str):
        s = self.find(name)
        if s:
            s.beam_force = path
            if s.status in (GENERATED, ASSIGNED):
                s.status = ASSIGNED if path else GENERATED
            # Gán file mới là hết lạc hậu: đây đúng là thao tác chữa nó.
            s.stale = ''
            self._dirty = True

    def record_generated(self, name, mct, topo, section_type,
                         n_nodes, n_elems, pt_cables=None):
        s = self.find(name)
        if not s:
            return
        s.mct, s.topo = mct, topo
        s.section_type = section_type
        s.n_nodes, s.n_elems = n_nodes, n_elems
        s.pt_cables = list(pt_cables or [])
        s.status = ASSIGNED if s.beam_force else GENERATED
        s.note = ''
        if s.beam_force:
            # Mô hình vừa được dựng lại, nhưng file nội lực đang gán là kết quả
            # của LẦN GIẢI TRƯỚC. Trước đây cho về thẳng `assigned` nên bảng
            # kiểm toán vẫn ra số, tính từ một mô hình không còn tồn tại.
            s.stale = ('Mô hình vừa được tạo lại — nội lực đang gán là kết quả '
                       'của lần giải trước. Hãy chạy lại Midas rồi gán lại '
                       'Beam Force.')
        self._dirty = True

    def mark_stale(self, name: str, reason: str) -> bool:
        """Đánh dấu nội lực đang gán không còn khớp mô hình.

        Chỉ có nghĩa khi mặt cắt đã có kết quả — đổi gối trên một mặt cắt chưa
        giải thì không có gì lạc hậu cả.
        """
        s = self.find(name)
        if not s or not s.beam_force:
            return False
        if s.stale == reason:
            return False
        s.stale = reason
        self._dirty = True
        return True

    def record_error(self, name, note):
        s = self.find(name)
        if s:
            s.status = ERROR
            s.note = str(note)[:400]
            self._dirty = True

    def record_checked(self, name, report=''):
        s = self.find(name)
        if s:
            s.status = CHECKED
            s.report = report
            self._dirty = True

    # ── đọc/ghi ──
    def to_dict(self) -> dict:
        return {
            'format': FORMAT_VERSION,
            'name': self.name,
            'output_dir': self.output_dir,
            'template': self.template,
            'auto_live_load': self.auto_live_load,
            'sections': [
                {k: v for k, v in asdict(s).items() if not k.startswith('_')}
                for s in self.sections
            ],
        }

    def save(self, path: str = None) -> str:
        path = path or self.path
        if not path:
            raise ValueError('Chưa có đường dẫn để lưu project')
        if not path.lower().endswith(FILE_EXT):
            path += FILE_EXT
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        self.path = path
        self._dirty = False
        return path

    @classmethod
    def load(cls, path: str) -> 'Project':
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        if d.get('format', 1) > FORMAT_VERSION:
            raise ValueError(
                f'File project tạo bởi phiên bản mới hơn (format {d["format"]}), '
                f'chương trình này chỉ đọc được tới format {FORMAT_VERSION}.')
        fields = {f for f in Section.__dataclass_fields__}
        p = cls(
            name=d.get('name', 'Project'),
            output_dir=d.get('output_dir', 'output'),
            template=d.get('template', ''),
            # File .mtbproj cũ không có khoá này — phải lui về đường template,
            # đúng cách nó đã sinh ra kết quả đang lưu trong file đó.
            auto_live_load=bool(d.get('auto_live_load', False)),
            sections=[Section(**{k: v for k, v in s.items() if k in fields})
                      for s in d.get('sections', [])],
        )
        p.path = path
        p._dirty = False
        return p

    def refresh_status(self):
        """Đối chiếu với đĩa — file bị xóa ngoài app thì hạ trạng thái."""
        for s in self.sections:
            if s.mct and not os.path.exists(s.mct):
                s.reset_outputs()
            elif s.beam_force and not os.path.exists(s.beam_force):
                s.beam_force = ''
                if s.status in (ASSIGNED, CHECKED):
                    s.status = GENERATED

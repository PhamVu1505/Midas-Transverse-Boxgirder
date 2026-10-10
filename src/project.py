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
import time
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

    # Số liệu ĐÃ DÙNG lần tạo MCT gần nhất — xem `Project.gen_fingerprint()`.
    # Như bảng tóm tắt của caldintav: thứ hiển thị là cái đã "Submit", không
    # phải cái đang gõ; lệch nhau thì mặt cắt "cần tạo lại" và nói rõ vì sao.
    # Rỗng = project cũ chưa ghi dấu vân tay → trạng thái "không rõ".
    gen_inputs: dict = field(default_factory=dict)

    status: str = NEW
    note: str = ''

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


@dataclass
class Project:
    """Tập hợp mặt cắt + thiết lập chung."""
    name: str = 'Project mới'
    output_dir: str = 'output'
    template: str = ''
    sections: list = field(default_factory=list)
    # Hệ số tổ hợp tự sửa (T21), chung cho cả project vì tổ hợp theo quy phạm
    # chứ không theo mặt cắt: {tên tổ hợp: [[ANAL, LCNAME, FACT], …]}. Chỉ lưu
    # tổ hợp KHÁC mặc định — xem `mct_frame_writer.combo_overrides_clean()`.
    combos: dict = field(default_factory=dict)

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
            s.set_supports(supports)
            self._dirty = True

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
            self._dirty = True

    # ── dấu vân tay số liệu đầu vào ──
    @staticmethod
    def _file_sig(path):
        if not path:
            return ['', 0]
        try:
            return [os.path.abspath(path), round(os.path.getmtime(path), 1)]
        except OSError:
            return [os.path.abspath(path), 0]

    def gen_fingerprint(self, s, include_pt=None) -> dict:
        """Mọi thứ quyết định nội dung MCT của mặt cắt `s`, ở dạng so được."""
        return {
            'dxf': self._file_sig(s.dxf),
            'template': self._file_sig(self.template_for(s)),
            'include_pt': bool(s.include_pt if include_pt is None else include_pt),
            'pt_jacking': s.pt_jacking,
            'supports': [[round(float(x['x']), 4), x.get('kind', '')]
                         for x in s.supports],
            'combos': json.dumps(self.combos, sort_keys=True),
        }

    _FP_LABEL = {'dxf': 'bản vẽ DXF', 'template': 'template số liệu',
                 'include_pt': 'tuỳ chọn cáp DƯL', 'pt_jacking': 'kiểu căng cáp',
                 'supports': 'gối', 'combos': 'tổ hợp tải trọng'}

    def stale_reasons(self, s, include_pt=None):
        """Vì sao MCT của `s` không còn khớp số liệu hiện tại.

        None = không biết (project cũ, chưa có dấu vân tay) · [] = khớp ·
        [lý do…] = cần tạo lại. Không biết thì nói không biết — báo "cần tạo
        lại" cho mọi project cũ thì cảnh báo kêu suốt và người dùng thôi đọc.
        """
        if not s.mct or not s.gen_inputs:
            return None
        now = self.gen_fingerprint(s, include_pt)
        if include_pt is None:
            now['include_pt'] = s.gen_inputs.get('include_pt', now['include_pt'])
        return [self._FP_LABEL[k] for k in self._FP_LABEL
                if s.gen_inputs.get(k) != now[k]]

    def beam_force_older_than_mct(self, s) -> bool:
        """Beam Force gán từ trước lần tạo MCT gần nhất → là của mô hình cũ."""
        t = (s.gen_inputs or {}).get('time')
        if not (s.beam_force and t and os.path.exists(s.beam_force)):
            return False
        return os.path.getmtime(s.beam_force) < t - 1

    def record_generated(self, name, mct, topo, section_type,
                         n_nodes, n_elems, pt_cables=None, inputs=None):
        s = self.find(name)
        if not s:
            return
        if inputs is not None:
            s.gen_inputs = dict(inputs, time=time.time())
        s.mct, s.topo = mct, topo
        s.section_type = section_type
        s.n_nodes, s.n_elems = n_nodes, n_elems
        s.pt_cables = list(pt_cables or [])
        s.status = ASSIGNED if s.beam_force else GENERATED
        s.note = ''
        self._dirty = True

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
            'combos': self.combos,
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
            combos=d.get('combos') or {},
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

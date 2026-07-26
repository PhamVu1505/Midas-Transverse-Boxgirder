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

    status: str = NEW
    note: str = ''

    def reset_outputs(self):
        """Xóa kết quả đã sinh — dùng khi DXF hoặc template đổi."""
        self.mct = self.topo = self.report = ''
        self.section_type = ''
        self.n_nodes = self.n_elems = 0
        self.pt_cables = []
        self.status = NEW
        self.note = ''

    @property
    def ready_for_check(self) -> bool:
        return bool(self.topo and self.beam_force
                    and os.path.exists(self.topo)
                    and os.path.exists(self.beam_force))


@dataclass
class Project:
    """Tập hợp mặt cắt + thiết lập chung."""
    name: str = 'Project mới'
    output_dir: str = 'output'
    template: str = ''
    sections: list = field(default_factory=list)

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

    def clear_sections(self):
        self.sections = []
        self._dirty = True

    def set_template(self, name: str, template: str):
        s = self.find(name)
        if s:
            s.template = template
            s.reset_outputs()
            self._dirty = True

    def set_beam_force(self, name: str, path: str):
        s = self.find(name)
        if s:
            s.beam_force = path
            if s.status in (GENERATED, ASSIGNED):
                s.status = ASSIGNED if path else GENERATED
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

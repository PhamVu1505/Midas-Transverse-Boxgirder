"""
Kiểm giao diện tự động — dựng cửa sổ thật, bấm thật, rồi đối chiếu.

    python tools/check_gui.py                 # chạy hết, cả hai bảng màu
    python tools/check_gui.py --list          # liệt kê các phép kiểm rồi thoát
    python tools/check_gui.py --only dong_bo  # chỉ chạy phép kiểm có tên chứa chuỗi
    python tools/check_gui.py --themes dark

Vì sao có công cụ này
─────────────────────
`pytest tests/` kiểm được phần tính toán, `tools/render_ui.py` cho *nhìn* thấy
bố cục — nhưng cả hai đều không trả lời được "bấm vào thì có đúng không". Những
lỗi tốn nhiều thời gian nhất của dự án này đều thuộc loại đó:

  · ô "Xem mặt cắt" đổi bảng nhưng dock Properties vẫn đứng ở mặt cắt cũ
  · widget mồ côi giữ nguyên 640×480 mặc định, vẽ đè lên cả dock
  · thông điệp tạm của QStatusBar chồng lên hai nhãn có sẵn
  · mũi tên ô xoay biến mất vì QSS đã đặt border

`pytest` im lặng cả bốn, và ảnh chụp thì phải có người ngồi soi. Ở đây mỗi phép
kiểm gắn với **một lỗi đã xảy ra thật**, nên bộ này lớn dần theo đúng những chỗ
đã từng gãy chứ không phải theo trí tưởng tượng.

Thêm phép kiểm
──────────────
Viết một hàm `def kiem_<tên>(c)` rồi ghi vào `CHECKS`. `c` là `Ctx` — xem lớp đó.
Sai thì `raise AssertionError('mô tả cụ thể')`; trả về chuỗi thì chuỗi đó được in
kèm dòng ĐẠT làm ghi chú. Không cần dọn dẹp: mỗi phép kiểm nhận một cửa sổ mới.
"""

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))


# ─────────────────────────────────────────────────────────────
# Bối cảnh
# ─────────────────────────────────────────────────────────────

class Ctx:
    """Cửa sổ đã nạp project mẫu + vài lối tắt hay dùng.

    `single` / `twin` là tên mặt cắt một hộp và hai hộp có trong project mẫu
    (`twin` có thể là None nếu `output/` chưa có mặt cắt hai hộp nào).
    """

    def __init__(self, app, win, sections, theme):
        self.app = app
        self.w = win
        self.sections = sections
        self.theme = theme
        self.single = self.twin = None
        for name, _t, _b, topo in sections:
            twin = (topo.get('geometry') or {}).get('section_type') == 'twin_box' \
                or bool(topo.get('wC_ids'))
            if twin and not self.twin:
                self.twin = name
            elif not twin and not self.single:
                self.single = name

    def step(self):
        """Cho Qt xử lý hết việc đang chờ rồi vẽ lại — như một nhịp tương tác."""
        self.app.processEvents()
        self.w.repaint()
        self.app.processEvents()

    def pick(self, combo, text):
        """Chọn một mục ĐÚNG như người dùng bấm chuột.

        `setCurrentText` một mình chỉ đổi chữ trong ô; `textActivated` mới là
        tín hiệu mà phần đồng bộ mặt cắt lắng nghe. Kiểm bằng `setCurrentText`
        thôi thì phép kiểm luôn ĐẠT kể cả khi tính năng chưa hề được nối dây.
        """
        combo.setCurrentText(text)
        combo.textActivated.emit(text)
        self.step()

    def props_section(self) -> str:
        """Tên mặt cắt mà dock Properties đang hiển thị."""
        return self.w.props._section


# ─────────────────────────────────────────────────────────────
# Các phép kiểm
# ─────────────────────────────────────────────────────────────

def kiem_dong_bo_mat_cat_tu_results(c):
    """Đổi mặt cắt ở thẻ Results table thì cả app phải đi theo."""
    if not c.twin:
        return 'bỏ qua — project mẫu không có mặt cắt hai hộp'
    c.w.tabbar.setCurrentIndex(3)
    c.pick(c.w.res_tab.section_combo, c.twin)

    tree = c.w.panel.tree.currentItem()
    from PyQt6.QtCore import Qt
    tree_name = tree.data(0, Qt.ItemDataRole.UserRole) if tree else None
    assert tree_name == c.twin, f'cây mặt cắt vẫn ở {tree_name!r}, đợi {c.twin!r}'
    assert c.props_section() == c.twin, \
        f'dock Properties vẫn ở {c.props_section()!r}, đợi {c.twin!r}'
    assert c.twin in c.w.lb_detail.text(), \
        f'thanh trạng thái không nhắc tới {c.twin}: {c.w.lb_detail.text()!r}'
    return f'{c.twin}: cây · dock · thanh trạng thái đều khớp'


def kiem_dong_bo_mat_cat_tu_kiem_toan(c):
    """Đổi mặt cắt ở thẻ Kiểm toán mặt cắt cũng phải kéo theo cả app."""
    if not c.twin:
        return 'bỏ qua — project mẫu không có mặt cắt hai hộp'
    c.w.tabbar.setCurrentIndex(4)
    c.pick(c.w.check_tab.cb_sec, c.twin)
    assert c.props_section() == c.twin, \
        f'dock Properties vẫn ở {c.props_section()!r}, đợi {c.twin!r}'
    return f'{c.twin}: dock đi theo ô "Mặt cắt"'


def kiem_dung_lai_combo_khong_keo_cay(c):
    """Dựng lại danh sách trong combo KHÔNG được làm cây mặt cắt nhảy.

    `refresh()` của thẻ Kiểm toán gọi `clear()` + `addItems()` mỗi lần project
    đổi. Nếu phần đồng bộ nghe `currentTextChanged` thay vì `textActivated` thì
    combo rỗng đi rồi nhảy về tên đầu danh sách sẽ lôi cả cây mặt cắt theo —
    người dùng đang xem S20 bỗng bị ném về S1 sau mỗi lần bấm Tạo MCT.
    """
    if not c.twin:
        return 'bỏ qua — project mẫu không có mặt cắt hai hộp'
    from PyQt6.QtCore import Qt
    c.w.tabbar.setCurrentIndex(4)
    c.pick(c.w.check_tab.cb_sec, c.twin)
    truoc = c.w.panel.tree.currentItem().data(0, Qt.ItemDataRole.UserRole)

    cb = c.w.check_tab.cb_sec
    names = [cb.itemText(i) for i in range(cb.count())]
    cb.clear()                      # đúng thao tác mà refresh() làm
    cb.addItems(names)
    cb.setCurrentText(truoc)
    c.step()

    sau = c.w.panel.tree.currentItem().data(0, Qt.ItemDataRole.UserRole)
    assert sau == truoc, f'cây mặt cắt bị kéo từ {truoc!r} sang {sau!r}'
    return 'dựng lại combo: cây mặt cắt đứng yên'


def kiem_o_cang_cap(c):
    """Ô "Căng cáp" chỉ mở khi mặt cắt có cáp, và ghi được vào project."""
    props = c.w.props
    sec = c.w.project.find(c.single)
    assert sec is not None, f'không tìm thấy mặt cắt {c.single!r}'

    sec.pt_cables = []
    props.show_section(c.single)
    c.step()
    assert not props.cb_jacking.isEnabled(), \
        'mặt cắt không có cáp mà ô Căng cáp vẫn mở — sẽ có người đổi rồi ' \
        'tưởng đã đổi được gì đó'

    sec.pt_cables = ['PT-TOP-1']
    props.show_section(c.single)
    c.step()
    assert props.cb_jacking.isEnabled(), 'mặt cắt có cáp mà ô Căng cáp bị khoá'

    i = props.cb_jacking.findData('both')
    assert i >= 0, 'thiếu mục "Căng hai đầu" trong ô chọn'
    props.cb_jacking.setCurrentIndex(i)
    c.step()
    assert sec.pt_jacking == 'both', \
        f'đổi ô chọn nhưng project vẫn giữ {sec.pt_jacking!r}'
    assert c.w.project.dirty, 'project không được đánh dấu là đã sửa'
    return 'khoá đúng lúc · ghi được vào project'


def kiem_chay_midas_mac_dinh_tat(c):
    """Chạy Midas phải TẮT sẵn, và bước ③ chỉ hết 'ngoài app' khi đã bật."""
    w = c.w

    # ── mặc định: tắt ──
    assert not w.prefs.midas_auto, \
        'chạy Midas tự động đang BẬT SẴN — nó chiếm chuột và bàn phím của người ' \
        'dùng, không được phép tự bật'
    assert not w.a_midas.isEnabled(), \
        'tính năng tắt mà mục "Chạy Midas/Civil" vẫn bấm được'
    assert w.a_midas.isVisible() or w.a_midas.text(), \
        'mục vẫn phải hiện (dù khoá) để người dùng biết là có'
    assert 'Tùy chọn' in w.a_midas.toolTip(), \
        f'chú thích không chỉ đường bật: {w.a_midas.toolTip()!r}'
    assert w.steps.steps[2][2] is True, \
        'chưa bật tự động mà bước ③ đã bỏ dấu "ngoài app"'

    # ── bật lên ──
    w.prefs.midas_auto = True
    w._sync_midas_action()
    c.step()
    assert w.a_midas.isEnabled(), 'đã bật mà mục vẫn bị khoá'
    assert w.steps.steps[2][2] is False, \
        'đã bật tự động mà bước ③ vẫn vẽ nét đứt "ngoài app" — thanh bước nói sai'

    # ── đang chạy thì khoá lại, khỏi chồng hai lượt ──
    w.midas_worker = object()
    w._sync_midas_action()
    c.step()
    assert not w.a_midas.isEnabled(), \
        'đang chạy Midas mà vẫn bấm được lần nữa — hai lượt sẽ giành nhau ribbon'
    w.midas_worker = None
    w.prefs.midas_auto = False
    w._sync_midas_action()
    return 'tắt sẵn · bật thì mở khoá · đang chạy thì khoá lại'


def kiem_tuy_chon_khong_chan_tin_hieu(c):
    """Không widget nào của hộp thoại Tùy chọn bị bỏ quên ở trạng thái chặn tín hiệu.

    `_sync_widgets()` chặn tín hiệu để đổ giá trị vào widget rồi mở lại trong
    `finally`. Bản trước viết danh sách widget **hai lần** — thêm widget mới mà
    chỉ sửa một chỗ thì nó bị chặn **vĩnh viễn**: bấm vào không có gì xảy ra,
    không lỗi, không dấu vết. Đúng chuyện đã xảy ra với hai ô của trang Midas,
    và người dùng là người phát hiện chứ không phải phép kiểm nào.
    """
    from gui.prefs import PreferencesDialog
    d = PreferencesDialog(c.w.prefs, c.w)
    try:
        bi_chan = [n for n in dir(d)
                   if n.startswith(('ck_', 'cb_', 'ed_', 'sl_'))
                   and hasattr(getattr(d, n, None), 'signalsBlocked')
                   and getattr(d, n).signalsBlocked()]
        assert not bi_chan, \
            f'widget còn bị chặn tín hiệu sau _sync_widgets: {bi_chan} — ' \
            f'bấm vào sẽ không có tác dụng gì'

        # Và kiểm cụ thể ô quan trọng nhất: bấm phải ghi được vào Prefs.
        truoc = d.p.midas_auto
        d.ck_midas.setChecked(not truoc)
        c.step()
        assert d.p.midas_auto != truoc, \
            'bấm ô "Cho phép app tự lái Midas/Civil" nhưng Prefs không đổi'
        assert d.ck_midas_confirm.isEnabled() == d.p.midas_auto, \
            'ô con "Hỏi lại trước mỗi lần chạy" không đi theo ô cha'
        return f'{len(list(d._controls()))} widget đều nhận tín hiệu'
    finally:
        d.close()


def kiem_preflight_hoi_truoc_khi_tao(c):
    """Số liệu template lệch hình học thì phải HỎI trước khi tạo MCT."""
    import PyQt6.QtWidgets as QtW
    goc = QtW.QMessageBox
    hien = {}

    class Hop:
        Icon = type('I', (), {'Warning': 0})
        ButtonRole = type('B', (), {'AcceptRole': 0, 'RejectRole': 1})

        def __init__(self, parent=None):
            self._nhan = {}
        def setIcon(self, *a): pass
        def setWindowTitle(self, t): hien['tieu_de'] = t
        def setText(self, t): hien['dong_dau'] = t
        def setInformativeText(self, t): pass
        def setDetailedText(self, t): hien['chi_tiet'] = t
        def addButton(self, nhan, vai):
            o = object()
            self._nhan[vai] = o
            return o
        def setDefaultButton(self, b): pass
        def exec(self): hien['da_hien'] = True
        def clickedButton(self): return self._nhan[hien['bam']]

    try:
        QtW.QMessageBox = Hop
        hien['bam'] = 0                      # bấm "Vẫn tạo"
        secs = list(c.w.project)
        assert c.w.gen_tab.preflight(secs) is True, \
            'bấm "Vẫn tạo" mà preflight vẫn chặn'
        assert hien.get('da_hien'), \
            'template lệch hình học mà không hiện hộp thoại nào — cảnh báo ' \
            'trôi qua một dòng log thì không ai đọc'
        assert 'KIỂM TRA SỐ LIỆU FILE TEMPLATE' in hien.get('chi_tiet', ''), \
            'nội dung cảnh báo không mở đầu bằng câu nhắc sửa template'

        hien['bam'] = 1                      # bấm "Huỷ"
        assert c.w.gen_tab.preflight(secs) is False, \
            'bấm "Huỷ" mà preflight vẫn cho chạy tiếp'
    finally:
        QtW.QMessageBox = goc
    return 'hộp thoại hiện · Vẫn tạo / Huỷ đều đúng'


def kiem_canh_bao_hoat_tai_tra_duoc_bat_ky_luc_nao(c):
    """Dock Properties phải nói được tải bánh của mặt cắt này thiếu hay dư.

    Trước đây cảnh báo hoạt tải **chỉ tồn tại đúng lúc bấm Tạo MCT**: một hộp
    thoại rồi vài dòng trôi trong Messages. Mở lại project hôm sau thì mọi mặt
    cắt đều `assigned`, bảng kiểm toán đầy số, và không còn gì nói rằng tải
    bánh của S10 đang thiếu 8%. VuPQ chốt tự sửa template, nên con số phải tra
    được bất cứ lúc nào chứ không phải chỉ trong khoảnh khắc sinh MCT.
    """
    from src.input_check import live_load_compare, section_metrics
    from src.input_reader import read_inputs

    thay = []
    for s in c.w.project:
        tpl = c.w.project.template_for(s)
        if not (tpl and os.path.exists(tpl)):
            continue
        cmp = live_load_compare(
            read_inputs(tpl, strict=False),
            section_metrics(dxf=s.dxf, topo=s.topo, excel=tpl))
        if not cmp:
            continue
        c.w.panel.select(s.name)
        c.step()
        assert c.props_section() == s.name, 'dock không đi theo mặt cắt được chọn'
        chu = c.w.props.input[1].text()
        assert 'DẢI TƯƠNG ĐƯƠNG' in chu, \
            f'{s.name}: dock không có khối đối chiếu dải tương đương'
        assert f'{cmp["S"]["tpl"]:.0f} mm' in chu, \
            f'{s.name}: dock không in trị S mà template đang khai'

        for key in ('S', 'X'):
            k = cmp[key]
            if k['off'] and k['unsafe']:
                pct = (k['ratio'] - 1) * 100
                assert f'THIẾU {pct:.0f}%' in chu, (
                    f'{s.name}: {key} thiếu {pct:.0f}% mà dock không nói ra — '
                    f'đây đúng là chỗ người dùng đọc để biết phải sửa gì')
                thay.append(f'{s.name}·{key} THIẾU {pct:.0f}%')
    if not thay:
        return 'bỏ qua — không mặt cắt nào trong project mẫu bị thiếu tải'
    return ' · '.join(thay)


def kiem_bat_tat_duoc_tung_dock(c):
    """Ba mục `Xem → Panel…` phải bật/tắt được dock thật.

    `QDockWidget.toggleViewAction()` bị Qt khoá khi dock **không có cờ
    `Closable`**. `_dock()` từng chỉ đặt `Movable | Floatable`, nên cả ba mục
    trong menu Xem xám vĩnh viễn: người dùng không giấu được panel nào, mà menu
    vẫn bày ra ba mục bấm không ăn. Không lỗi, không dấu vết — `pytest` im lặng
    và ảnh chụp cũng không thấy, vì mục xám trông vẫn "bình thường".
    """
    from PyQt6.QtWidgets import QDockWidget
    docks = c.w.findChildren(QDockWidget)
    assert len(docks) >= 3, f'chỉ thấy {len(docks)} dock, đợi 3'
    ten = []
    for d in docks:
        a = d.toggleViewAction()
        assert a.isEnabled(), (
            f'mục bật/tắt dock {d.windowTitle()!r} đang bị khoá — thiếu cờ '
            f'DockWidgetClosable thì Qt khoá luôn toggleViewAction')
        assert d.isVisible(), f'dock {d.windowTitle()!r} không hiện sẵn'
        a.trigger()
        c.step()
        assert not d.isVisible(),             f'bấm mục Xem mà dock {d.windowTitle()!r} vẫn hiện'
        a.trigger()
        c.step()
        assert d.isVisible(),             f'bấm lần hai mà dock {d.windowTitle()!r} không hiện lại'
        ten.append(d.windowTitle())
    return 'ẩn/hiện được: ' + ' · '.join(ten)


def kiem_khong_co_widget_mo_coi(c):
    """Không widget nào được vẽ ngoài layout ở kích thước mặc định.

    `deleteLater()` một mình không gỡ widget khỏi cha, mà đã bị `takeAt` khỏi
    layout thì không ai đặt lại kích thước — nó giữ nguyên 640×480 và vẽ đè lên
    cả dock. Dấu hiệu chắc chắn: widget ĐANG HIỆN mà to hơn hẳn cha nó.
    """
    from PyQt6.QtWidgets import QWidget
    xau = []
    for con in c.w.findChildren(QWidget):
        cha = con.parentWidget()
        if not con.isVisible() or cha is None:
            continue
        if (con.width() > cha.width() + 50) or (con.height() > cha.height() + 50):
            chu = con.text()[:30] if hasattr(con, 'text') else ''
            xau.append(f'{type(con).__name__} {con.width()}×{con.height()} '
                       f'trong {type(cha).__name__} {cha.width()}×{cha.height()}'
                       + (f' [{chu}]' if chu else ''))
    assert not xau, 'widget mồ côi: ' + ' · '.join(xau[:5])
    return f'duyệt {len(c.w.findChildren(QWidget))} widget, không có cái nào tràn cha'


def kiem_thanh_trang_thai_khong_chong_chu(c):
    """`showMessage()` phải chảy vào ô chi tiết, không thành thông điệp tạm.

    `QStatusBar` tự vẽ thông điệp tạm ở nửa trái và **không** ẩn hai nhãn có
    sẵn, nên ba dòng chữ chồng lên nhau thành một đám không đọc nổi.
    """
    from PyQt6.QtWidgets import QStatusBar
    c.w.status.showMessage('THU NGHIEM 123')
    c.step()
    assert c.w.lb_detail.text() == 'THU NGHIEM 123', \
        f'ô chi tiết không nhận được chữ: {c.w.lb_detail.text()!r}'
    tam = QStatusBar.currentMessage(c.w.status)     # bản gốc của Qt
    assert not tam, f'vẫn còn thông điệp tạm của Qt: {tam!r}'
    return 'chữ vào ô chi tiết · Qt không giữ thông điệp tạm nào'


def kiem_huy_hieu_nhat_ky(c):
    """Mỗi mức độ trong Messages phải có huy hiệu là ẢNH, không phải ký tự."""
    from gui.icons import level_image
    thieu = [m for m in ('info', 'ok', 'warn', 'err')
             if level_image(m, c.w.t) is None]
    assert not thieu, f'không dựng được huy hiệu cho: {thieu}'

    log = c.w.log
    log.clear()
    log.warning('thử cảnh báo')
    log.error('thử lỗi')
    c.step()
    assert len(log._badges) == 2, \
        f'chèn 2 mức mà tài liệu chỉ có {len(log._badges)} huy hiệu'
    assert log.counts()['warn'] == 1 and log.counts()['err'] == 1, log.counts()

    # Huy hiệu phải mang màu của bảng màu ĐANG dùng, không phải bảng màu cũ.
    assert any(c.w.t['warn'].lstrip('#') in t for t in log._badges), \
        f'huy hiệu không mang mã màu {c.w.t["warn"]} của bảng màu hiện tại'
    return f'4 mức có ảnh · khoá huy hiệu gồm mã màu ({c.theme})'


def kiem_mui_ten_o_xoay_va_o_xo(c):
    """QSS phải trỏ tới ảnh mũi tên thật cho ô xoay và ô xổ.

    Đặt `border`/`background` lên `QSpinBox`/`QComboBox` là Qt thôi nhờ style
    vẽ mũi tên, mà hai sub-control này **chỉ** nhận `image: url(...)`.
    """
    from gui.theme import build_qss, make_size
    qss = build_qss(c.w.t, make_size(), '')
    for luat in ('QSpinBox::up-arrow', 'QSpinBox::down-arrow',
                 'QComboBox::down-arrow'):
        assert luat in qss, f'QSS thiếu quy tắc {luat}'
        khuc = qss.split(luat, 1)[1][:200]
        assert 'image: url(' in khuc, \
            f'{luat} không trỏ tới ảnh — mũi tên sẽ biến mất'
    return 'ô xoay và ô xổ đều có ảnh mũi tên'


def kiem_moi_the_ve_duoc(c):
    """Mở lần lượt mọi thẻ chế độ xem và vẽ lại — bắt lỗi trong paintEvent.

    Lỗi trong `paintEvent` làm Qt chết cứng cả tiến trình, không traceback.
    Chỉ import được thôi thì chưa chứng minh được gì.
    """
    ten = []
    for i in range(c.w.tabbar.count()):
        c.w.tabbar.setCurrentIndex(i)
        c.step()
        ten.append(c.w.tabbar.tabText(i))
    return 'vẽ được: ' + ' · '.join(ten)


def kiem_cong_giay_phep_chan_dung_cho(c):
    """Không có quyền thì KHÔNG được sinh MCT, và phải nói rõ vì sao.

    Cổng kiểm tra chỉ có nghĩa nếu nó nằm trên đường đi thật. Bản đầu của tính
    năng này đặt cổng ở chỗ mở thẻ chứ không phải chỗ tính, nên bấm F5 vẫn chạy
    tuốt. Phép kiểm bấm đúng đường người dùng đi: gọi require_license rồi xem
    generate có bị chặn không.
    """
    import PyQt6.QtWidgets as QtW
    from src.security import guard

    w = c.w
    goc_warning = QtW.QMessageBox.warning
    goc_open = w.open_license
    da_mo = []
    da_goi_generate = []
    goc_generate = w.gen_tab.generate

    def gia_generate(*a, **k):
        da_goi_generate.append(a)

    class TrangThai:
        ready = False
        message = 'Giấy phép đã bị thu hồi.\nLý do: kiểm thử'
        source = guard.SOURCE_LICENSE
        block = None
        license = None
        trial = None
        path = ''
        def headline(self):
            return 'Chưa kích hoạt'

    try:
        QtW.QMessageBox.warning = staticmethod(lambda *a, **k: None)
        w.open_license = lambda: da_mo.append(1)
        w.gen_tab.generate = gia_generate

        # ── đang dùng thử / có giấy phép: phải cho qua ──
        assert w.require_license('mct') is True,             'đang chạy hợp lệ mà cổng vẫn chặn'
        w.generate_all()
        assert da_goi_generate, 'cổng mở mà generate không được gọi'

        # ── bị chặn: không được sinh MCT ──
        da_goi_generate.clear()
        goc_state = guard.get_runtime_state
        guard.get_runtime_state = lambda feature=None: TrangThai()
        try:
            assert w.require_license('mct') is False,                 'trạng thái không chạy được mà cổng vẫn cho qua'
            w.generate_all()
            assert not da_goi_generate,                 'bị chặn mà generate VẪN chạy — cổng đặt sai chỗ'
            assert da_mo, 'bị chặn mà không mở hộp thoại Giấy phép chỉ đường'
        finally:
            guard.get_runtime_state = goc_state
    finally:
        QtW.QMessageBox.warning = goc_warning
        w.open_license = goc_open
        w.gen_tab.generate = goc_generate
    return 'hợp lệ thì qua · bị chặn thì dừng và mở hộp thoại'


def kiem_moi_loi_vao_tao_mct_deu_qua_cong(c):
    """MỌI đường tới việc sinh MCT phải qua cổng, không riêng F5.

    Lỗi đã xảy ra thật: `generate_requested` của cây mặt cắt nối THẲNG vào
    `gen_tab.generate`, nên bấm chuột phải một mặt cắt rồi chọn *Tạo MCT* là
    sinh được file với giấy phép đã hết hạn hoặc đã bị thu hồi — trong khi F5
    ngay cạnh đó thì bị chặn đúng. Docstring của `require_license` đã cảnh báo
    trước: đặt cổng ở một chỗ rồi tin là đủ thì lối chuột phải sẽ lọt.
    """
    import PyQt6.QtWidgets as QtW
    from src.security import guard

    w = c.w
    ten = c.single or c.twin
    goc_warning = QtW.QMessageBox.warning
    goc_open = w.open_license
    goc_preflight = w.gen_tab.preflight
    goc_state = guard.get_runtime_state
    da_goi = []

    class BiChan:
        ready = False
        message = 'Giấy phép đã bị thu hồi.\nLý do: kiểm thử'
        source = guard.SOURCE_LICENSE
        block = None
        license = None
        trial = None
        path = ''
        def headline(self):
            return 'Chưa kích hoạt'

    try:
        QtW.QMessageBox.warning = staticmethod(lambda *a, **k: None)
        w.open_license = lambda: None

        # Do o CHO BAT DAU LAM VIEC THAT, khong o cho nhan tin hieu. Neu thay
        # `gen_tab.generate` bang ham gia thi phep kiem chi do duoc CACH NOI
        # day: mot ket noi Qt toi bound method da chup ham that luc connect,
        # nen ham gia khong bao gio duoc goi va phep kiem hong vi ly do khac.
        # `preflight` thi ca hai loi noi deu goi toi, va goi qua `self` nen
        # thay duoc luc chay.
        w.gen_tab.preflight = lambda *a, **k: (da_goi.append(a), False)[1]

        # Cong dong: MOI loi vao deu phai dung truoc khi cham toi viec that
        guard.get_runtime_state = lambda feature=None: BiChan()
        try:
            w.generate_all()
            w.panel.generate_requested.emit([ten])
            c.step()
            assert not da_goi, (
                'bị chặn mà việc sinh MCT VẪN khởi động — có lối vào không '
                'qua cổng (F5 hoặc chuột phải trong cây)')
        finally:
            guard.get_runtime_state = goc_state

        # Cong mo: ca hai loi vao phai chay binh thuong, khong bi chan oan
        da_goi.clear()
        w.generate_all()
        c.step()
        assert da_goi, 'cổng mở mà F5 lại không chạy'

        da_goi.clear()
        w.panel.generate_requested.emit([ten])
        c.step()
        assert da_goi, 'cổng mở mà lối chuột phải lại không chạy'
    finally:
        QtW.QMessageBox.warning = goc_warning
        w.open_license = goc_open
        w.gen_tab.preflight = goc_preflight
        guard.get_runtime_state = goc_state
    return 'F5 và lối chuột phải đều qua cổng · mở thì cả hai chạy'


def kiem_chon_nham_tep_khong_giet_app(c):
    """Chọn nhầm một tệp không phải văn bản thì báo lỗi, KHÔNG được abort.

    Bộ lọc của hộp *Nhập từ tệp…* có mục "Tất cả (*.*)", nên chọn nhầm PDF hay
    DOCX là chuyện thường. `UnicodeDecodeError` là `ValueError` chứ không phải
    `OSError`; bắt hụt nó thì PyQt6 không có excepthook và **cả tiến trình bị
    abort** — mà người dùng chưa kích hoạt đang kẹt đúng ở màn hình này, tức
    họ mất luôn đường vào phần mềm.
    """
    import os
    import tempfile
    import PyQt6.QtWidgets as QtW
    from gui.license_dialog import LicenseDialog

    goc_warning = QtW.QMessageBox.warning
    goc_getopen = QtW.QFileDialog.getOpenFileName
    da_bao = []
    tam = os.path.join(tempfile.gettempdir(), 'mtb_tep_nhi_phan.bin')
    with open(tam, 'wb') as f:
        f.write(bytes(range(256)))          # chắc chắn không phải UTF-8

    dlg = LicenseDialog(c.w)
    try:
        QtW.QMessageBox.warning = staticmethod(
            lambda *a, **k: da_bao.append(a[2] if len(a) > 2 else ''))
        QtW.QFileDialog.getOpenFileName = staticmethod(
            lambda *a, **k: (tam, ''))

        dlg._import_license_file()          # trước bản vá: abort cả tiến trình
        c.step()

        assert da_bao, 'chọn nhầm tệp nhị phân mà không báo gì'
        assert dlg.ed_key.text().strip() == '', (
            'tệp rác lại được đổ vào ô mã giấy phép')
    finally:
        QtW.QMessageBox.warning = goc_warning
        QtW.QFileDialog.getOpenFileName = goc_getopen
        dlg.deleteLater()
        try:
            os.remove(tam)
        except OSError:
            pass
    return 'tệp nhị phân → báo lỗi, app còn sống, ô mã vẫn trống'


def kiem_f6_xuat_bang_kiem_toan_qua_cong(c):
    """F6 ghi ra bảng kiểm toán, nên phải qua cổng tính năng 'check'.

    Lỗi đã xảy ra thật: `run.py` gác lệnh tương đương bằng `_gate('check')`,
    còn F6 trong giao diện thì không gác gì. Một giấy phép chỉ mua 'mct' vẫn
    xuất được `<tên>_check.txt` và `<tên>_check.xlsx`, chỉ cần bấm F6 thay vì
    mở thẻ Kiểm toán ngay cạnh — mà thẻ đó thì gác đúng.
    """
    import PyQt6.QtWidgets as QtW
    from src.security import guard

    w = c.w
    goc_warning = QtW.QMessageBox.warning
    goc_open = w.open_license
    goc_process = w.res_tab.process
    goc_state = guard.get_runtime_state
    da_chay = []

    class ThieuTinhNang:
        ready = False
        message = 'Giấy phép này không có tính năng: Kiểm toán tiết diện'
        source = guard.SOURCE_LICENSE
        block = None
        license = None
        trial = None
        path = ''
        def headline(self):
            return 'Thiếu tính năng'

    try:
        QtW.QMessageBox.warning = staticmethod(lambda *a, **k: None)
        w.open_license = lambda: None
        w.res_tab.process = lambda *a, **k: da_chay.append(1)

        guard.get_runtime_state = lambda feature=None: (
            ThieuTinhNang() if feature == 'check' else goc_state(feature))
        try:
            w.process_results()
            c.step()
            assert not da_chay, (
                "thiếu tính năng 'check' mà F6 VẪN xuất bảng kiểm toán")
        finally:
            guard.get_runtime_state = goc_state

        da_chay.clear()
        w.process_results()
        c.step()
        assert da_chay, 'có quyền mà F6 lại không chạy'
    finally:
        QtW.QMessageBox.warning = goc_warning
        w.open_license = goc_open
        w.res_tab.process = goc_process
        guard.get_runtime_state = goc_state
    return "thiếu tính năng thì F6 dừng · có quyền thì chạy"


def kiem_noi_ro_dang_ghi_lai_nhung_gi(c):
    """Người dùng phải xem được ĐÚNG những gì đang bị ghi và gửi đi.

    Phần mềm thả nhịp tim mang mã máy và các con số đếm về cho người cấp phép.
    Đợt gọn giao diện đã bỏ thẻ *Sử dụng* và bỏ luôn phần công bố, khiến
    `usage_log.summary_lines()` thành mã chết và người dùng không còn đường nào
    xem — giấu đi thì đó là theo dõi lén.
    """
    from gui.license_dialog import LicenseDialog
    from src.security import usage_log

    dlg = LicenseDialog(c.w)
    try:
        c.step()
        chu = dlg.lb_su_dung.text()
        assert chu.strip(), 'thẻ Trạng thái không nói gì về số liệu đang ghi'
        assert 'mã máy' in chu, 'không nói rằng mã máy được gửi kèm'
        assert 'Không ghi tên bản vẽ' in chu, (
            'không nói rõ thứ KHÔNG bị ghi — đó mới là điều người dùng lo')
        # Phai lay tu nguon that, khong duoc viet lai thanh van: van xuoi se
        # troi khoi thuc te, con con so thi khong.
        for dong in usage_log.summary_lines():
            assert dong in chu, f'thiếu dòng số liệu thật: {dong!r}'
    finally:
        dlg.deleteLater()
    return 'thẻ Trạng thái công bố đúng số liệu đang được ghi'


def kiem_nhan_giay_phep_doi_mau_theo_bang_mau(c):
    """Nhãn giấy phép ở thanh trạng thái phải lấy màu từ token.

    Đây là khuôn lỗi đã gặp nhiều lần trong dự án: mã màu cứng đứng yên khi đổi
    bảng màu, và chỉ lộ ra khi đã sang bản Tối.
    """
    w = c.w
    assert w.lb_lic.text().strip(), 'thanh trạng thái không nói gì về giấy phép'
    qss = w.lb_lic.styleSheet()
    hop_le = {w.t['ok'], w.t['warn'], w.t['err']}
    assert any(mau.lower() in qss.lower() for mau in hop_le),         f'màu nhãn giấy phép không nằm trong token của bảng màu hiện tại: {qss!r}'
    return f'{w.lb_lic.text()} · màu lấy từ token'


def kiem_o_chuot_phai_khong_noi_doi(c):
    """Ô "menu chuột phải" phải đọc registry thật, không giữ bản sao riêng.

    Giữ trạng thái trong QSettings thì người dùng gỡ mục bằng tay (hoặc cài lại
    máy) là ô tích nói dối. Phép kiểm bật ô, đọc lại registry, rồi trả về đúng
    hiện trạng ban đầu.
    """
    from PyQt6.QtCore import QSettings
    from gui.prefs import Prefs, PreferencesDialog
    from src import shell_integration as shell

    if not shell.available():
        return 'bỏ qua — không phải Windows'

    ban_dau = shell.is_registered()
    dlg = PreferencesDialog(Prefs.load(QSettings('TEDI', 'MidasTransverseBoxgirder')), c.w)
    try:
        assert dlg.ck_shell.isChecked() == ban_dau,             'ô tích không khớp hiện trạng registry lúc mở hộp thoại'
        dlg.ck_shell.setChecked(not ban_dau)
        c.step()
        assert shell.is_registered() == (not ban_dau),             'bấm ô mà registry không đổi theo'
        assert dlg.ck_shell.isChecked() == shell.is_registered(),             'ô tích và registry lệch nhau ngay sau khi bấm'
        assert '--mct' in dlg.lb_shell.text() or not shell.is_registered(),             'đang bật mà chú thích không cho xem lệnh đã đăng ký'
    finally:
        dlg.ck_shell.setChecked(ban_dau)
        dlg.deleteLater()
        if shell.is_registered() != ban_dau:
            shell.register() if ban_dau else shell.unregister()
    return f'đọc/ghi thẳng registry (hiện trạng giữ nguyên: {ban_dau})'


CHECKS = [
    kiem_moi_the_ve_duoc,
    kiem_dong_bo_mat_cat_tu_results,
    kiem_dong_bo_mat_cat_tu_kiem_toan,
    kiem_dung_lai_combo_khong_keo_cay,
    kiem_o_cang_cap,
    kiem_chay_midas_mac_dinh_tat,
    kiem_tuy_chon_khong_chan_tin_hieu,
    kiem_preflight_hoi_truoc_khi_tao,
    kiem_canh_bao_hoat_tai_tra_duoc_bat_ky_luc_nao,
    kiem_bat_tat_duoc_tung_dock,
    kiem_khong_co_widget_mo_coi,
    kiem_thanh_trang_thai_khong_chong_chu,
    kiem_huy_hieu_nhat_ky,
    kiem_mui_ten_o_xoay_va_o_xo,
    kiem_cong_giay_phep_chan_dung_cho,
    kiem_moi_loi_vao_tao_mct_deu_qua_cong,
    kiem_chon_nham_tep_khong_giet_app,
    kiem_f6_xuat_bang_kiem_toan_qua_cong,
    kiem_noi_ro_dang_ghi_lai_nhung_gi,
    kiem_nhan_giay_phep_doi_mau_theo_bang_mau,
    kiem_o_chuot_phai_khong_noi_doi,
]


# ─────────────────────────────────────────────────────────────
# Chạy
# ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('--only', default='', help='chỉ chạy phép kiểm có tên chứa chuỗi này')
    ap.add_argument('--themes', default='light,dark', help='bảng màu, ngăn bằng dấu phẩy')
    ap.add_argument('--list', action='store_true', help='liệt kê phép kiểm rồi thoát')
    args = ap.parse_args()

    if args.list:
        for f in CHECKS:
            print(f'  {f.__name__:38s} {(f.__doc__ or "").strip().splitlines()[0]}')
        return 0

    import render_ui as R

    found = R.discover()
    if not found:
        print('Không thấy mặt cắt nào đã tạo MCT trong output/ — '
              'chạy pipeline trước rồi quay lại.')
        return 1
    sections = [(n, t, b, R.load_topo(t)) for n, t, b in found]

    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv[:1])

    chay = [f for f in CHECKS if args.only.lower() in f.__name__.lower()]
    if not chay:
        print(f'Không phép kiểm nào khớp {args.only!r}')
        return 1

    dat = hong = 0
    for theme in [t.strip() for t in args.themes.split(',') if t.strip()]:
        print(f'\n── bảng màu {theme} ' + '─' * 46)
        for f in chay:
            # Cửa sổ MỚI cho từng phép kiểm: phép kiểm trước đổi mặt cắt đang
            # chọn, bật/tắt ô, ghi vào project — để dùng chung thì thứ tự chạy
            # âm thầm quyết định kết quả.
            w = R.build_window(sections, theme)
            R.feed_results(w, sections)
            c = Ctx(app, w, sections, theme)
            c.step()
            try:
                ghi_chu = f(c) or ''
                dat += 1
                print(f'  ĐẠT   {f.__name__:38s} {ghi_chu}')
            except Exception as e:
                hong += 1
                print(f'  HỎNG  {f.__name__:38s} {e}')
                if not isinstance(e, AssertionError):
                    import traceback
                    traceback.print_exc()
            finally:
                w.hide()
                w.deleteLater()
                app.processEvents()

    print(f'\n{dat} đạt · {hong} hỏng')
    return 1 if hong else 0


if __name__ == '__main__':
    sys.exit(main())

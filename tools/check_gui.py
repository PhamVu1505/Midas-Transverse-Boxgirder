"""
Kiểm giao diện tự động — dựng cửa sổ thật, bấm thật, rồi đối chiếu.

    python tools/check_gui.py                 # chạy hết
    python tools/check_gui.py --list          # liệt kê các phép kiểm rồi thoát
    python tools/check_gui.py --only dong_bo  # chỉ chạy phép kiểm có tên chứa chuỗi

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
        assert 'Dải tương đương' in chu, \
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


def kiem_qss_khong_dung_dieu_khien_native(c):
    """Không QSS nào được chạm vào nút, ô nhập, ô tích… — để Windows tự vẽ.

    Chỉ một thuộc tính hộp (`border`/`background`/`padding`/`margin`) trên một
    điều khiển là Qt thôi nhờ style native vẽ nó. Bản v1.3–v1.4.1 phủ QSS lên
    mọi thứ rồi phải tự dựng lại mũi tên ô xoay, dấu tích, độ nổi của nút — mà
    vẫn thua bản Windows vẽ (VuPQ chốt bỏ, 2026-10-10). Soát ba đường QSS có thể
    lọt vào: QSS của app · QSS nội tuyến trên chính điều khiển · QSS không bộ
    chọn đặt trên khung cha (nó lan xuống mọi con).
    """
    import re
    from PyQt6.QtWidgets import QWidget
    from gui.theme import NATIVE_CONTROLS
    hop = re.compile(r'\b(border|background|padding|margin)\b')
    loai = tuple(getattr(__import__('PyQt6.QtWidgets', fromlist=['x']), n)
                 for n in NATIVE_CONTROLS)

    def ten_trong(qss):
        return [n for n in NATIVE_CONTROLS if re.search(rf'\b{n}\b', qss)]

    loi = []
    app_qss = c.app.styleSheet()
    if ten_trong(app_qss):
        loi.append(f'QSS của app nhắc tới {ten_trong(app_qss)}')
    # Cả hai hộp thoại riêng: chúng không phải con của cửa sổ chính
    from gui.prefs import PreferencesDialog
    from gui.help_dialog import HelpDialog
    hop_thoai = [PreferencesDialog(c.w.prefs, c.w), HelpDialog(c.w.t, c.w)]
    ws = [c.w, *c.w.findChildren(QWidget)]
    for d in hop_thoai:
        ws += [d, *d.findChildren(QWidget)]
    for w in ws:
        q = w.styleSheet()
        if not q:
            continue
        ten = type(w).__name__ + (f'#{w.objectName()}' if w.objectName() else '')
        if ten_trong(q):
            loi.append(f'{ten}: QSS nhắm vào {ten_trong(q)}')
        elif isinstance(w, loai) and hop.search(q):
            loi.append(f'{ten}: QSS có thuộc tính hộp — {q[:60]!r}')
        elif '{' not in q and hop.search(q) and any(
                isinstance(k, loai) for k in w.findChildren(QWidget)):
            loi.append(f'{ten}: QSS không bộ chọn lan xuống điều khiển con — {q[:60]!r}')
    assert not loi, ' · '.join(loi[:5]) + (f' … (+{len(loi) - 5})' if len(loi) > 5 else '')
    for d in hop_thoai:
        d.deleteLater()
    return f'soát {len(ws)} widget + QSS của app · style {c.app.style().metaObject().className()}'


def kiem_mot_phong_mot_co_khong_nghieng(c):
    """Một phông, một cỡ, không in nghiêng — kiểu chữ theo caldintav.

    VuPQ chốt 2026-10-10 (docs/UI-CALDINTAV.md): caldintav dùng đúng một phông,
    một cỡ, chữ đậm chỉ cho tiêu đề nhóm, gần như không in nghiêng. Bản trước
    rải 8 pt / 9 pt / 12 pt / Consolas / chữ nghiêng khắp nơi. Soát chữ người
    dùng thực sự đọc: phông của từng widget, cùng `font-size` / `font-family` /
    `<i>` lọt vào nội dung hay QSS của nhãn. Ngoại lệ có tên: thẻ MCT source
    (phông đơn cách) và chú giải nổi trên hình vẽ (nhỏ hơn đúng 1 pt).
    """
    import re
    from PyQt6.QtWidgets import QWidget, QLabel
    from gui.prefs import PreferencesDialog
    from gui.help_dialog import HelpDialog
    goc = c.app.font()
    ngoai_le = {c.w.mct_view, *c.w.mct_view.findChildren(QWidget), c.w.viewer.legend}
    hop_thoai = [PreferencesDialog(c.w.prefs, c.w), HelpDialog(c.w.t, c.w)]
    ws = [c.w, *c.w.findChildren(QWidget)]
    for d in hop_thoai:
        ws += [d, *d.findChildren(QWidget)]
    cam = re.compile(r'font-size|font-family|font-style|<i>|<tt>', re.I)
    loi = []
    for w in ws:
        if w in ngoai_le:
            continue
        f = w.font()
        ten = type(w).__name__ + (f'#{w.objectName()}' if w.objectName() else '')
        if isinstance(w, QLabel):
            ten += f' {w.text()[:24]!r}'
        if f.italic():
            loi.append(f'{ten}: in nghiêng')
        if f.family() != goc.family():
            loi.append(f'{ten}: phông {f.family()!r}')
        if abs(f.pointSizeF() - goc.pointSizeF()) > 0.01:
            loi.append(f'{ten}: cỡ {f.pointSizeF():g} pt (chung {goc.pointSizeF():g})')
        noi_dung = w.styleSheet() + (w.text() if isinstance(w, QLabel) else '')
        if cam.search(noi_dung):
            loi.append(f'{ten}: {cam.search(noi_dung).group(0)!r} trong nội dung/QSS')
    for d in hop_thoai:
        d.deleteLater()

    # Chữ VẼ bằng QPainter (thanh bước, khung xem, biểu đồ, tiêu đề cột) không
    # nằm trong font() của widget nào: chặn QPainter.setFont rồi vẽ lại mọi thẻ.
    from PyQt6.QtGui import QPainter
    da_ve = []
    goc_set = QPainter.setFont

    def ghi(painter, font):
        da_ve.append((font.family(), font.pointSizeF(), font.italic()))
        return goc_set(painter, font)
    QPainter.setFont = ghi
    try:
        for i in range(c.w.tabbar.count()):
            c.w.tabbar.setCurrentIndex(i)
            c.step()
            c.w.repaint()
    finally:
        QPainter.setFont = goc_set
    co_cho_phep = {round(goc.pointSizeF(), 2), round(goc.pointSizeF() - 1, 2)}
    for fam, pt, nghieng in set(da_ve):
        if nghieng:
            loi.append(f'QPainter vẽ chữ nghiêng ({fam} {pt:g} pt)')
        if fam != goc.family():
            loi.append(f'QPainter vẽ phông {fam!r}')
        # huy hiệu điểm kiểm toán (A, A1…) co theo vòng tròn — ký hiệu bản vẽ
        if round(pt, 2) not in co_cho_phep and pt > goc.pointSizeF():
            loi.append(f'QPainter vẽ cỡ {pt:g} pt')

    assert not loi, ' · '.join(loi[:5]) + (f' … (+{len(loi) - 5})' if len(loi) > 5 else '')
    return (f'soát {len(ws)} widget + {len(set(da_ve))} kiểu chữ QPainter · '
            f'{goc.family()} {goc.pointSizeF():g} pt')


def kiem_nut_zoom_doc_duoc(c):
    """Nút zoom của khung xem phải hiện icon đủ lớn, không bị bóp thành chấm.

    Bản v1.4.1 dùng ký tự `− + ⤢` (máy thiếu glyph `⤢` thì ra vạch chéo) và QSS
    padding chung ăn hết chỗ của icon. Đo trên **điểm ảnh đã vẽ**.
    """
    # "điểm tối" chứ không so đúng mã màu mực: nét 1,35 px được khử răng cưa,
    # dấu − nằm trên nửa điểm ảnh nên không điểm nào mang đúng màu 'ink'.
    def gan(q):
        return q.lightness() < 128
    rong = []
    for b, ic in c.w.viewer._zoom_btns:
        bi = b.grab().toImage()
        xs = [x for x in range(bi.width()) for y in range(bi.height())
              if gan(bi.pixelColor(x, y))]
        rong.append((max(xs) - min(xs) + 1) if xs else 0)
        assert rong[-1] >= 8, f'icon {ic!r} chỉ rộng {rong[-1]} px — bị bóp thành chấm'
    return 'icon rộng ' + ' · '.join(f'{r} px' for r in rong)


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
    kiem_qss_khong_dung_dieu_khien_native,
    kiem_nut_zoom_doc_duoc,
    kiem_mot_phong_mot_co_khong_nghieng,
]


# ─────────────────────────────────────────────────────────────
# Chạy
# ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('--only', default='', help='chỉ chạy phép kiểm có tên chứa chuỗi này')
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
    print()
    for f in chay:
        # Cửa sổ MỚI cho từng phép kiểm: phép kiểm trước đổi mặt cắt đang
        # chọn, bật/tắt ô, ghi vào project — để dùng chung thì thứ tự chạy
        # âm thầm quyết định kết quả.
        w = R.build_window(sections)
        R.feed_results(w, sections)
        c = Ctx(app, w, sections, 'light')
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

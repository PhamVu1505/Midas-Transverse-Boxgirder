"""Mục chuột phải "Tạo file MCT" và đường chạy nhanh.

Chạy:
    pytest tests/test_shell_menu.py -v

Ba câu được khoá ở đây:

1. **Lệnh đăng ký phải mang đúng cờ --mct và tham số %1.** Sai một chữ thì mục
   menu vẫn hiện, bấm vào vẫn mở phần mềm — nhưng mở cả app thay vì tạo MCT, và
   không có gì báo là sai.
2. **Đăng ký rồi gỡ phải sạch.** Bỏ sót khoá con là menu chuột phải của người
   dùng còn một mục chết trỏ vào đường dẫn không tồn tại.
3. **Thư mục kết quả không bao giờ được là đường dẫn tương đối.** Mở từ
   Explorer thì thư mục làm việc là chỗ nào cũng có thể; 'output' sẽ mọc ra ở
   nơi không ai tìm lại được.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import shell_integration as shell

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='chỉ có trên Windows')


def test_lenh_dang_ky_mang_dung_co(tmp_path):
    cmd = shell._command_line('"%1"')
    assert '--mct' in cmd
    assert cmd.rstrip().endswith('"%1"')
    program, prefix = shell.app_command()
    assert cmd.startswith(f'"{program}"')
    if not getattr(sys, 'frozen', False):
        # Chạy từ mã nguồn: phải là pythonw, không thì mỗi lần bấm menu lại
        # nháy một cửa sổ console đen giữa màn hình.
        assert program.lower().endswith(('pythonw.exe', 'python.exe'))
        assert prefix and prefix[0].endswith('run_gui.py')


def test_dang_ky_roi_go_thi_sach():
    da_co = shell.is_registered()
    lenh_cu = shell.registered_command()
    try:
        shell.register()
        assert shell.is_registered()
        assert '--mct' in shell.registered_command()
        shell.unregister()
        assert not shell.is_registered()
        assert shell.registered_command() == ''
    finally:
        # Trả lại đúng hiện trạng của máy đang chạy test.
        if da_co:
            shell.register()
        elif shell.is_registered():
            shell.unregister()
        if da_co and lenh_cu:
            assert shell.is_registered()


def test_quet_dxf_trong_thu_muc(tmp_path):
    (tmp_path / 'a.dxf').write_text('x', encoding='utf-8')
    (tmp_path / 'B.DXF').write_text('x', encoding='utf-8')
    (tmp_path / 'c.dwg').write_text('x', encoding='utf-8')
    # KHÔNG đặt tên thư mục con là 'con': CON là tên thiết bị dành riêng của
    # Windows, mkdir ném NotADirectoryError.
    (tmp_path / 'thumuccon').mkdir()
    (tmp_path / 'thumuccon' / 'd.dxf').write_text('x', encoding='utf-8')

    found = [os.path.basename(p) for p in shell.dxf_files_in(str(tmp_path))]
    assert found == ['B.DXF', 'a.dxf']          # không đệ quy, không lấy .dwg


def test_thu_muc_khong_ton_tai_thi_tra_rong():
    assert shell.dxf_files_in(r'Z:\khong-co-o-nay') == []


# ── đường chạy nhanh ──────────────────────────────────────────────────────

def test_thu_muc_ket_qua_khong_bao_gio_tuong_doi(tmp_path):
    from gui.quick_mct import default_output_for

    class P:
        output_dir = 'output'                   # tương đối — phải bị bỏ qua
        template = ''

    dxf = tmp_path / 'banve' / 'S1.dxf'
    dxf.parent.mkdir()
    dxf.write_text('x', encoding='utf-8')
    assert default_output_for([str(dxf)], P()) == str(dxf.parent)

    P.output_dir = str(tmp_path / 'ket-qua')    # tuyệt đối — phải được dùng
    assert default_output_for([str(dxf)], P()) == str(tmp_path / 'ket-qua')


def test_template_lui_ve_ban_cua_kho(tmp_path):
    from gui.quick_mct import default_template, _REPO_TEMPLATE

    class P:
        template = str(tmp_path / 'khong-co.xls')

    assert default_template(P()) == (_REPO_TEMPLATE
                                     if os.path.exists(_REPO_TEMPLATE) else '')
    real = tmp_path / 'co-that.xls'
    real.write_text('x', encoding='utf-8')
    P.template = str(real)
    assert default_template(P()) == str(real)


def test_doc_tham_so_dong_lenh(tmp_path):
    import run_gui

    args = run_gui._parse_args(['--mct', 'a.dxf', 'b.dxf'])
    assert args['mct'] == ['a.dxf', 'b.dxf']
    assert not args['register'] and not args['unregister']

    assert run_gui._parse_args(['--dang-ky-chuot-phai'])['register']
    assert run_gui._parse_args(['--go-chuot-phai'])['unregister']
    assert run_gui._parse_args([])['mct'] == []


def test_mo_rong_muc_tieu_nhan_ca_file_lan_thu_muc(tmp_path):
    import run_gui

    (tmp_path / 'x.dxf').write_text('x', encoding='utf-8')
    (tmp_path / 'y.dxf').write_text('x', encoding='utf-8')
    (tmp_path / 'z.txt').write_text('x', encoding='utf-8')

    paths = run_gui._expand_targets([str(tmp_path)])
    assert sorted(os.path.basename(p) for p in paths) == ['x.dxf', 'y.dxf']

    one = run_gui._expand_targets([str(tmp_path / 'x.dxf')])
    assert [os.path.basename(p) for p in one] == ['x.dxf']

    assert run_gui._expand_targets([str(tmp_path / 'z.txt')]) == []

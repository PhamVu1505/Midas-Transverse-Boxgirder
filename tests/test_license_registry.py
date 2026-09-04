"""Sổ cấp phép — luật gộp nhịp tim.

Chạy:
    pytest tests/test_license_registry.py -v

Sổ là thứ **duy nhất** người cấp phép nhìn vào để biết ai đang dùng và ai đã
can thiệp. Nhịp tim thì do máy khách gửi lên, tức là dữ liệu **không tin được**.
Ba luật dưới đây là chỗ hai điều đó gặp nhau:

* **Số đếm chỉ tăng.** Xoá `usage.json` ở máy khách rồi đồng bộ tiếp không được
  làm mất lịch sử đã thu. Ghi đè thẳng thì chỉ cần xoá một tệp là xoá sạch sổ.
* **Số nhỏ đi là có can thiệp** — kể cả khi khoá **biến mất hẳn** khỏi nhịp tim,
  vì xoá `usage.json` cho ra đúng dấu vết đó.
* **Danh tính không tự mất.** Máy đã gỡ giấy phép vẫn thả nhịp tim, và nhịp tim
  đó không còn `customer`/`license_id`/`expires_at`. Ghi đè bằng chuỗi rỗng thì
  đúng những máy cần truy lại là những máy trắng thông tin nhất.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

from license_registry import LicenseRegistry           # noqa: E402

MAY = '00AA438C-BF49-4C7E-AC68-CB3EE5658BBC'   # da chuan hoa


@pytest.fixture
def so(tmp_path):
    return LicenseRegistry(tmp_path / 'so.sqlite3')


def _may(so_) -> dict:
    rows = [r for r in so_.list_machines() if r.machine_id == MAY]
    assert rows, 'không thấy máy trong sổ'
    r = rows[0]
    return {'customer': r.customer, 'license_id': r.license_id,
            'expires_at': r.expires_at, 'tampered': r.tampered,
            'counters': r.counters}


def test_so_dem_chi_tang_va_giam_thi_bi_danh_dau(so):
    so.record_machine({
        'machine_id': MAY, 'customer': 'VuPQ', 'license_id': 'L-01',
        'expires_at': '2027-01-01', 'first_seen': '2026-01-01',
        'last_seen': '2026-06-01', 'counters': {'sessions': 40, 'mct': 12},
    })
    assert _may(so)['counters']['mct'] == 12

    # May khach xoa usage.json roi tha nhip tim moi: so nho di
    so.record_machine({
        'machine_id': MAY, 'customer': 'VuPQ', 'license_id': 'L-01',
        'expires_at': '2027-01-01', 'first_seen': '2026-05-01',
        'last_seen': '2026-07-01', 'counters': {'sessions': 1, 'mct': 0},
    })
    m = _may(so)
    assert m['counters']['mct'] == 12, 'lịch sử đã thu bị ghi đè mất'
    assert m['counters']['sessions'] == 40
    assert m['tampered'], 'số nhỏ đi mà không đánh dấu là có can thiệp'


def test_khoa_bien_mat_han_cung_la_can_thiep(so):
    """Nhánh dễ lọt nhất: khoá không nhỏ đi, mà **không còn** trong nhịp tim."""
    so.record_machine({
        'machine_id': MAY, 'customer': 'VuPQ',
        'last_seen': '2026-06-01', 'counters': {'sessions': 5, 'mct': 30},
    })
    # 'mct' bien mat han; 'sessions' van tang binh thuong
    so.record_machine({
        'machine_id': MAY, 'customer': 'VuPQ',
        'last_seen': '2026-07-01', 'counters': {'sessions': 6},
    })
    m = _may(so)
    assert m['counters']['mct'] == 30, 'khoá biến mất thì số cũ cũng mất theo'
    assert m['tampered'], (
        'khoá biến mất hẳn khỏi nhịp tim mà không bị đánh dấu — đây đúng là '
        'dấu vết của việc xoá usage.json')


def test_danh_tinh_khong_bi_xoa_trang_boi_nhip_tim_rong(so):
    so.record_machine({
        'machine_id': MAY, 'machine_label': 'PC-VUPQ\\admin',
        'customer': 'VuPQ', 'license_id': 'L-01', 'expires_at': '2027-01-01',
        'last_seen': '2026-06-01', 'counters': {'sessions': 3},
    })
    # May da go giay phep: nhip tim khong con thong tin giay phep nua
    so.record_machine({
        'machine_id': MAY, 'last_seen': '2026-08-01',
        'counters': {'sessions': 9},
    })
    m = _may(so)
    assert m['customer'] == 'VuPQ', 'tên khách hàng bị xoá trắng'
    assert m['license_id'] == 'L-01', 'mã giấy phép bị xoá trắng'
    assert m['expires_at'] == '2027-01-01', 'hạn bị xoá trắng'
    assert m['counters']['sessions'] == 9, 'số vẫn phải cập nhật bình thường'


def test_mot_nhip_tim_hong_khong_lam_do_ca_lo(so):
    """`NaN` là JSON hợp lệ với nhiều bộ ghi, mà `int(nan)` ném ValueError."""
    so.record_machine({
        'machine_id': MAY, 'customer': 'VuPQ', 'last_seen': '2026-06-01',
        'counters': {'sessions': 4, 'hong': float('nan'),
                     'vo_cuc': float('inf')},
    })
    m = _may(so)
    assert m['counters']['sessions'] == 4
    assert 'hong' not in m['counters'] and 'vo_cuc' not in m['counters']

"""Giấy phép, dùng thử, nhật ký sử dụng, điểm hẹn và cổng kiểm tra.

Chạy:
    pytest tests/test_license.py -v

Mỗi bài ở đây khoá một câu **phải đúng thì hệ thống mới có nghĩa**:

* Chữ ký sai, sai máy, hết hạn, thiếu tính năng — **từng cái một** phải chặn.
  Bốn điều kiện mà chỉ kiểm ba thì cái thứ tư là cửa mở.
* **Không đọc được mã máy thì THẤT BẠI ĐÓNG.** Đường lui theo tên máy từng làm
  một giấy phép chạy được trên mọi máy.
* **Mất điểm hẹn KHÔNG chặn.** Người dùng ở công trường không phải chịu hậu quả
  của một ổ mạng.
* **Dùng thử không cứu một tính năng chưa mua** — nếu không thì gói Basic tự
  nhiên thành gói đủ trong 7 ngày.

Mọi bài đều trỏ MTB_* vào thư mục tạm: không bài nào được đụng vào giấy phép
thật hay sổ dùng thử thật của máy đang chạy test.
"""

import json
import os
import sys
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.security import checkpoint, guard, license_manager as lm, signing
from src.security import trial, usage_log
from src.security.hwid import UNBOUND_MACHINE_ID, normalize_machine_id
from src.security.keys import PUBLIC_KEYS

MACHINE = '00AA438C-BF49-4C7E-AC68-CB3EE5658BBC'
OTHER = '11111111-2222-3333-4444-555555555555'


# ── nền ───────────────────────────────────────────────────────────────────

@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Cách li hoàn toàn: giấy phép, dùng thử, nhật ký, điểm hẹn đều vào tmp."""
    monkeypatch.setenv('MTB_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('MTB_LICENSE_FILE', str(tmp_path / 'mtb.runtime'))
    monkeypatch.setenv('MTB_TRIAL_FILE', str(tmp_path / 'trial.runtime'))
    monkeypatch.setenv('MTB_USAGE_FILE', str(tmp_path / 'usage.json'))
    monkeypatch.setenv('MTB_CHECKPOINT', str(tmp_path / 'diemhen'))
    monkeypatch.delenv('MTB_DEV_BYPASS', raising=False)
    monkeypatch.setattr('src.security.hwid.get_machine_id', lambda: MACHINE)
    monkeypatch.setattr('src.security.license_manager.get_machine_id', lambda: MACHINE)
    monkeypatch.setattr('src.security.trial.get_machine_id', lambda: MACHINE)
    monkeypatch.setattr('src.security.usage_log.get_machine_id', lambda: MACHINE)
    monkeypatch.setattr('src.security.checkpoint.get_machine_id', lambda: MACHINE)
    return tmp_path


@pytest.fixture(scope='module')
def key():
    try:
        return signing.load_private_key()
    except signing.SignatureError:
        pytest.skip('Máy này không có khoá riêng (secrets/) — bỏ qua.')


def make(key, *, machine=MACHINE, days=180, features=None, **kw):
    return lm.generate_license(machine, lm.default_expiry(days),
                               customer=kw.pop('customer', 'Kiểm thử'),
                               features=features, private_key=key, **kw)


# ── chữ ký và bốn điều kiện ───────────────────────────────────────────────

def test_giay_phep_hop_le_thi_qua(sandbox, key):
    token, info = make(key)
    got = lm.verify_license_token(token)
    assert got.machine_id == MACHINE
    assert got.license_id == info.license_id
    assert got.has_feature('mct') and got.has_feature('nx')


def test_sua_mot_ky_tu_la_hong_chu_ky(sandbox, key):
    token, _ = make(key)
    head, payload, sig = token.rsplit('.', 2)[0], token.split('.')[2], token.split('.')[3]
    # đổi đúng một ký tự trong phần nội dung
    broken = f"{head}.{payload[:-1]}{'A' if payload[-1] != 'A' else 'B'}.{sig}"
    with pytest.raises(lm.LicenseError):
        lm.verify_license_token(broken)


def test_sai_may_thi_chan(sandbox, key):
    token, _ = make(key, machine=OTHER)
    with pytest.raises(lm.LicenseError, match='không khớp máy'):
        lm.verify_license_token(token)


def test_het_han_thi_chan(sandbox, key):
    token, _ = make(key, days=-1)
    with pytest.raises(lm.LicenseError, match='hết hạn'):
        lm.verify_license_token(token)


def test_thieu_tinh_nang_thi_chan(sandbox, key):
    token, _ = make(key, features=['check'])
    lm.verify_license_token(token, feature='check')          # có thì qua
    with pytest.raises(lm.LicenseError, match='chưa mở tính năng'):
        lm.verify_license_token(token, feature='mct')


def test_khong_doc_duoc_ma_may_thi_that_bai_dong(sandbox, key, monkeypatch):
    """Đường lui theo tên máy/hostname là cửa mở — phải chối, không được nhận.

    Bản đầu của dự án tham chiếu từng lui về biến môi trường tên máy; khi đó
    một giấy phép cấp cho máy A khớp luôn trên máy B cùng tên.
    """
    token, _ = make(key)
    monkeypatch.setattr('src.security.license_manager.get_machine_id',
                        lambda: UNBOUND_MACHINE_ID)
    with pytest.raises(lm.LicenseError, match='không khớp máy'):
        lm.verify_license_token(token)


def test_van_tay_khoa_cong_khai_duoc_ghim():
    """Đổi modulus dưới cùng một key_id là làm hỏng mọi bản đã phát hành.

    Bài này đổ khi ai đó sửa keys.py — và đó là chủ ý: phải sửa cả con số dưới
    đây, tức phải dừng lại một nhịp mà đọc luật trong keys.py.
    """
    assert set(PUBLIC_KEYS) == {'mtb-v1'}
    assert signing.key_fingerprint('mtb-v1') == (
        'e1d320ab56aceaec527b9dbb9a965ecfb930bfcb3ca3481d3e9c39da0d987170')


def test_inspect_van_doc_duoc_noi_dung_khi_bi_choi(sandbox, key):
    """Chối thì phải nói vì sao — kèm nội dung, để người dùng biết đường sửa."""
    token, _ = make(key, machine=OTHER)
    st = lm.inspect_license_token(token)
    assert not st.ok
    assert st.info is not None and st.info.machine_id == OTHER


def test_ghi_va_doc_lai_giay_phep(sandbox, key):
    token, _ = make(key)
    written = lm.save_license(token)
    assert written
    st = lm.get_license_status()
    assert st.ok and st.info.machine_id == MACHINE
    lm.remove_license()
    assert not lm.get_license_status().ok


# ── dùng thử ──────────────────────────────────────────────────────────────

def test_dung_thu_7_ngay(sandbox):
    st = trial.get_trial_status()
    assert st.active and st.days_left == trial.TRIAL_DAYS
    assert not trial.get_trial_status(date.today() + timedelta(days=7)).active
    assert trial.get_trial_status(date.today() + timedelta(days=3)).days_left == 4


def test_lui_dong_ho_thi_khoa(sandbox):
    trial.get_trial_status()
    st = trial.get_trial_status(date.today() - timedelta(days=5))
    assert not st.active and st.tampered


def test_sua_ban_ghi_dung_thu_thi_khoa_chu_khong_bat_dau_lai(sandbox):
    trial.get_trial_status()
    path = tuple(trial._trial_paths())[0]
    raw = json.loads(path.read_text(encoding='utf-8'))
    raw['started_at'] = '2099-01-01'          # cố kéo dài hạn dùng thử
    path.write_text(json.dumps(raw), encoding='utf-8')
    st = trial.get_trial_status()
    assert not st.active and st.tampered


def test_ban_ghi_dung_thu_cua_may_khac_khong_dung_duoc(sandbox, monkeypatch):
    trial.get_trial_status()
    monkeypatch.setattr('src.security.trial.get_machine_id', lambda: OTHER)
    st = trial.get_trial_status()
    assert not st.active and st.tampered


def test_xem_truoc_khong_ghi_so(sandbox):
    """Truyền `now` là để XEM. Nếu lượt xem cũng ghi 'lần chạy gần nhất' thì
    xem thử ngày mai xong, hôm nay chính máy đó bị coi là lùi đồng hồ."""
    trial.get_trial_status()
    path = tuple(trial._trial_paths())[0]
    before = path.read_text(encoding='utf-8')
    trial.get_trial_status(date.today() + timedelta(days=3))
    assert path.read_text(encoding='utf-8') == before


# ── nhật ký sử dụng ───────────────────────────────────────────────────────

def test_dem_dung_so_luot(sandbox):
    usage_log.start_session('1.5.0')
    usage_log.record('mct', 6)
    usage_log.record('midas')
    snap = usage_log.load()
    assert snap.counters == {'sessions': 1, 'mct': 6, 'midas': 1}
    assert snap.app_version == '1.5.0'
    assert sum(snap.months.values()) == 8


def test_sua_tay_nhat_ky_thi_lo(sandbox):
    usage_log.record('mct', 2)
    path = tuple(usage_log._usage_paths())[0]
    raw = json.loads(path.read_text(encoding='utf-8'))
    raw['counters']['mct'] = 0
    path.write_text(json.dumps(raw), encoding='utf-8')
    assert usage_log.load().tampered


def test_bao_cao_su_dung_xuat_duoc(sandbox, tmp_path, key):
    usage_log.record('mct', 3)
    token, info = make(key)
    out = usage_log.export_report(tmp_path / 'bc.mtbusage', info)
    data = json.loads(out.read_text(encoding='utf-8'))
    assert data['kind'] == 'usage-report'
    assert data['usage']['counters']['mct'] == 3
    assert data['license']['license_id'] == info.license_id


# ── điểm hẹn ──────────────────────────────────────────────────────────────

def test_nhip_tim_ghi_ra_va_doc_lai(sandbox, key):
    usage_log.record('mct', 4)
    token, info = make(key, checkpoint=str(sandbox / 'diemhen'))
    result = checkpoint.sync(info, app_version='1.5.0')
    assert result.ok and result.heartbeat_written
    beats = checkpoint.read_heartbeats(sandbox / 'diemhen')
    assert len(beats) == 1
    assert beats[0]['machine_id'] == MACHINE
    assert beats[0]['counters']['mct'] == 4


def test_danh_sach_chan_theo_may_va_theo_giay_phep(sandbox, key):
    token, info = make(key, checkpoint=str(sandbox / 'diemhen'))
    root = sandbox / 'diemhen'

    checkpoint.publish_blocklist(root, [{'machine_id': MACHINE,
                                         'reason': 'Hết hợp đồng'}], key)
    checkpoint.sync(info)
    assert checkpoint.check_blocked(info).blocked
    assert 'Hết hợp đồng' in checkpoint.check_blocked(info).reason

    checkpoint.publish_blocklist(root, [{'license_id': info.license_id,
                                         'reason': 'Thu hồi'}], key)
    checkpoint.sync(info)
    assert checkpoint.check_blocked(info).blocked

    checkpoint.publish_blocklist(root, [{'machine_id': OTHER, 'reason': 'x'}], key)
    checkpoint.sync(info)
    assert not checkpoint.check_blocked(info).blocked


def test_danh_sach_chan_gia_thi_khong_an(sandbox, key):
    """Chỉ chữ ký của người cấp mới chặn được. Không thì ai cũng chặn được ai."""
    root = sandbox / 'diemhen'
    root.mkdir(parents=True, exist_ok=True)
    (root / checkpoint.BLOCKLIST_NAME).write_text(
        'MTBBL1.mtb-v1.eyJlbnRyaWVzIjpbXX0.AAAA', encoding='utf-8')
    token, info = make(key, checkpoint=str(root))
    checkpoint.sync(info)
    assert not checkpoint.check_blocked(info).blocked
    assert checkpoint.cached_blocklist() is None


def test_mat_diem_hen_thi_khong_chan(sandbox, key, monkeypatch):
    """Ổ mạng chết KHÔNG được biến thành phần mềm chết."""
    monkeypatch.setenv('MTB_CHECKPOINT', 'Z:/khong-co-o-nay/diemhen')
    token, info = make(key)
    result = checkpoint.sync(info)
    assert result.configured and not result.ok
    assert not checkpoint.check_blocked(info).blocked


def test_bo_danh_sach_chan_thi_may_chay_lai_duoc(sandbox, key):
    root = sandbox / 'diemhen'
    token, info = make(key, checkpoint=str(root))
    checkpoint.publish_blocklist(root, [{'machine_id': MACHINE, 'reason': 'x'}], key)
    checkpoint.sync(info)
    assert checkpoint.check_blocked(info).blocked
    (root / checkpoint.BLOCKLIST_NAME).unlink()
    checkpoint.sync(info)
    assert not checkpoint.check_blocked(info).blocked


# ── cổng kiểm tra ─────────────────────────────────────────────────────────

def test_thu_tu_cong_giay_phep_truoc_dung_thu(sandbox, key):
    assert guard.get_runtime_state().source == guard.SOURCE_TRIAL
    token, _ = make(key)
    lm.save_license(token)
    state = guard.get_runtime_state()
    assert state.ready and state.source == guard.SOURCE_LICENSE


def test_dung_thu_khong_cuu_tinh_nang_chua_mua(sandbox, key):
    token, _ = make(key, features=['check'])
    lm.save_license(token)
    state = guard.get_runtime_state('mct')
    assert not state.ready
    assert 'chưa mở tính năng' in state.message
    assert state.source == guard.SOURCE_LICENSE      # không lui về dùng thử


def test_bi_chan_thi_giay_phep_con_han_cung_khong_chay(sandbox, key):
    token, info = make(key, checkpoint=str(sandbox / 'diemhen'))
    lm.save_license(token)
    checkpoint.publish_blocklist(sandbox / 'diemhen',
                                 [{'machine_id': MACHINE, 'reason': 'Nghỉ việc'}], key)
    checkpoint.sync(info)
    state = guard.get_runtime_state()
    assert not state.ready and state.blocked
    assert 'Nghỉ việc' in state.message
    with pytest.raises(guard.RuntimeGateError):
        guard.require_app_ready()


def test_het_dung_thu_va_khong_giay_phep_thi_dung(sandbox):
    path = tuple(trial._trial_paths())[0]
    trial.get_trial_status()
    raw = json.loads(path.read_text(encoding='utf-8'))
    old = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    raw['started_at'] = raw['last_seen'] = old
    raw['sig'] = trial._sign({k: v for k, v in raw.items() if k != 'sig'}, MACHINE)
    path.write_text(json.dumps(raw), encoding='utf-8')
    state = guard.get_runtime_state()
    assert not state.ready
    assert 'dùng thử' in state.message


def test_cua_dev_khong_lot_vao_ban_dong_goi(sandbox, monkeypatch):
    monkeypatch.setenv('MTB_DEV_BYPASS', '1')
    assert guard.dev_bypass_active()
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    assert not guard.dev_bypass_active()
    monkeypatch.delattr(sys, 'frozen', raising=False)


def test_ma_may_chuan_hoa_giong_nhau(sandbox):
    assert normalize_machine_id('{00aa438c-bf49-4c7e-ac68-cb3ee5658bbc}') == MACHINE
    assert normalize_machine_id('  ' + MACHINE + ' ') == MACHINE

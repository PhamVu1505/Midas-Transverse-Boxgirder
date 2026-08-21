"""Cổng kiểm tra — nơi DUY NHẤT phần còn lại của app hỏi "có được chạy không".

Giữ mọi chi tiết về định dạng giấy phép ở trong gói security: sau này đổi cách
ký hay thêm điều kiện thì chỉ sửa ở đây, không phải lần theo hàng chục chỗ gọi.

Thứ tự xét, và không được đổi:

1. **Cửa dev** — chỉ có tác dụng khi chạy từ mã nguồn. Bản đóng gói
   (sys.frozen) vô hiệu nó, kể cả khi biến môi trường được đặt.
2. **Giấy phép** hợp lệ cho máy này, còn hạn, có tính năng được hỏi.
3. **Danh sách chặn** — trúng thì chặn, kể cả khi giấy phép còn hạn. Chỉ đọc
   bản sao cục bộ, không chạm ổ mạng (checkpoint.sync lo việc đó ở luồng nền).
4. **Dùng thử** — chỉ khi KHÔNG có giấy phép hợp lệ nào. Giấy phép hợp lệ mà
   thiếu tính năng thì báo thiếu tính năng; dùng thử không được "cứu" một tính
   năng chưa mua, nếu không thì ai cũng có bản đầy đủ trong 7 ngày rồi mất.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from .checkpoint import BlockDecision, check_blocked
from .license_manager import LicenseInfo, LicenseStatus, get_license_status, FEATURES
from .trial import TrialStatus, get_trial_status

DEV_BYPASS_ENV = 'MTB_DEV_BYPASS'

SOURCE_LICENSE = 'license'
SOURCE_TRIAL = 'trial'
SOURCE_DEV = 'dev-bypass'


@dataclass(frozen=True)
class RuntimeState:
    ready: bool
    message: str
    source: str = ''
    license: LicenseInfo | None = None
    trial: TrialStatus | None = None
    block: BlockDecision | None = None
    path: str = ''

    @property
    def blocked(self) -> bool:
        return bool(self.block and self.block.blocked)

    def headline(self) -> str:
        """Một dòng cho thanh trạng thái."""
        if self.source == SOURCE_DEV:
            return 'DEV — bỏ qua kiểm tra giấy phép'
        if self.source == SOURCE_LICENSE and self.license:
            left = self.license.days_remaining()
            return (f'Giấy phép: {self.license.customer} · còn {left} ngày'
                    if left is not None else f'Giấy phép: {self.license.customer}')
        if self.source == SOURCE_TRIAL and self.trial:
            return f'Dùng thử — còn {self.trial.days_left} ngày'
        return 'Chưa kích hoạt'


class RuntimeGateError(RuntimeError):
    def __init__(self, state: RuntimeState):
        super().__init__(state.message)
        self.state = state


def dev_bypass_active() -> bool:
    """Chỉ đúng khi (a) chạy từ mã nguồn và (b) biến môi trường được bật.

    Chốt chặn sys.frozen: exe đóng gói luôn có cờ đó, nên cửa dev không thể lọt
    vào bản phát hành dù người dùng có tự đặt biến môi trường.
    """
    if getattr(sys, 'frozen', False):
        return False
    return os.environ.get(DEV_BYPASS_ENV, '').strip().lower() in {'1', 'true', 'yes', 'on'}


def _feature_label(feature: str | None) -> str:
    if not feature:
        return ''
    return FEATURES.get(str(feature).lower(), str(feature))


def get_runtime_state(feature: str | None = None) -> RuntimeState:
    """Trạng thái hiện tại. Không bao giờ ném — dùng để hiển thị."""
    if dev_bypass_active():
        extra = f' (tính năng: {_feature_label(feature)})' if feature else ''
        return RuntimeState(
            True,
            f'[DEV] Bỏ qua kiểm tra giấy phép qua {DEV_BYPASS_ENV}{extra} — '
            'chỉ có tác dụng khi chạy từ mã nguồn.',
            source=SOURCE_DEV)

    status: LicenseStatus = get_license_status(feature=feature)
    if status.ok and status.info is not None:
        decision = check_blocked(status.info)
        if decision.blocked:
            return RuntimeState(
                False,
                'Giấy phép đã bị thu hồi.\n'
                f'Lý do: {decision.reason}\n'
                'Liên hệ người cấp giấy phép để mở lại.',
                source=SOURCE_LICENSE, license=status.info,
                block=decision, path=status.path or '')
        return RuntimeState(True, status.message, source=SOURCE_LICENSE,
                            license=status.info, path=status.path or '')

    # Có giấy phép hợp lệ nhưng thiếu đúng tính năng đang hỏi: báo thiếu tính
    # năng, không lui về dùng thử.
    if feature is not None:
        base = get_license_status()
        if base.ok:
            return RuntimeState(False, status.message, source=SOURCE_LICENSE,
                                license=base.info, path=base.path or '')

    trial = get_trial_status()
    if trial.active:
        return RuntimeState(True, trial.message, source=SOURCE_TRIAL, trial=trial)

    message = status.message
    if trial.started_at or trial.tampered:
        message = f'{status.message}\n{trial.message}'
    return RuntimeState(False, message, license=status.info, trial=trial,
                        path=status.path or '')


def require_app_ready(feature: str | None = None) -> RuntimeState:
    """Ném RuntimeGateError nếu không được chạy."""
    state = get_runtime_state(feature)
    if not state.ready:
        raise RuntimeGateError(state)
    return state


def require_feature(feature: str) -> RuntimeState:
    return require_app_ready(feature)

"""Giấy phép, dùng thử, nhật ký sử dụng và điểm hẹn theo dõi.

Phần còn lại của app chỉ nên gọi qua guard:

    from src.security import require_app_ready, RuntimeGateError
    try:
        require_app_ready('mct')
    except RuntimeGateError as exc:
        ...   # exc.state.message là câu giải thích cho người dùng

Toàn cảnh và giới hạn: docs/LICENSE-SYSTEM.md.
"""
from .guard import (RuntimeGateError, RuntimeState, get_runtime_state,
                    require_app_ready, require_feature)
from .hwid import get_machine_id, machine_label
from .license_manager import (FEATURES, LicenseError, LicenseInfo,
                              LicenseStatus, get_license_status,
                              inspect_license_token, save_license)
from .trial import TRIAL_DAYS, get_trial_status

__all__ = [
    'RuntimeGateError', 'RuntimeState', 'get_runtime_state',
    'require_app_ready', 'require_feature',
    'get_machine_id', 'machine_label',
    'FEATURES', 'LicenseError', 'LicenseInfo', 'LicenseStatus',
    'get_license_status', 'inspect_license_token', 'save_license',
    'TRIAL_DAYS', 'get_trial_status',
]

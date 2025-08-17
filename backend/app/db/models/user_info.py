from enum import Enum


class UserInfoState(Enum):
    """Trạng thái thu thập thông tin người dùng"""

    INIT = "init"
    ASKING_NAME = "asking_name"
    ASKING_PHONE = "asking_phone"
    ASKING_EMAIL = "asking_email"
    ASKING_ADDRESS = "asking_address"
    CONFIRMING_INFO = "confirming_info"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

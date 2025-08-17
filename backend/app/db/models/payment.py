from dataclasses import dataclass
from enum import Enum


class PaymentMethod(Enum):
    """Enum cho các phương thức thanh toán"""

    COD = "cod"
    BANK_TRANSFER = "bank_transfer"
    MOMO = "momo"
    ZALOPAY = "zalopay"
    VNPAY = "vnpay"
    CREDIT_CARD = "credit_card"
    CASH = "cash"


class PaymentState(Enum):
    """Standardized payment workflow states"""

    WAITING_FOR_METHOD = "waiting_for_payment_method"
    METHOD_SELECTED = "payment_method_selected"
    PROCESSING_PAYMENT = "processing_payment"
    PAYMENT_CONFIRMED = "payment_confirmed"
    READY_FOR_ORDER = "ready_for_order"
    FAILED = "payment_failed"


class PaymentStep(Enum):
    """Standardized next steps"""

    SELECT_METHOD = "select_payment_method"
    CONFIRM_PAYMENT = "confirm_payment"
    ORDER_CONFIRMATION = "order_confirmation"
    PAYMENT_FAILED = "payment_failed"


@dataclass
class PaymentOption:
    """Dataclass cho tùy chọn thanh toán"""

    method: PaymentMethod
    display_name: str
    description: str
    fee: float = 0.0
    is_available: bool = True
    min_amount: float = 0.0
    max_amount: float = float("inf")

import re
from datetime import datetime
import logging
from typing import Dict, Any, Tuple

from app.db.models.user_info import UserInfoState

logger = logging.getLogger(__name__)


class UserInfoCollectionService:
    """Service thu thập thông tin người dùng khi tạo đơn hàng"""

    def __init__(self):
        # Patterns để validate thông tin
        self.phone_patterns = [
            r"^0[3|5|7|8|9][0-9]{8}$",  # Số VN: 0xxxxxxxxx
            r"^\+84[3|5|7|8|9][0-9]{8}$",  # Số VN: +84xxxxxxxxx
            r"^84[3|5|7|8|9][0-9]{8}$",  # Số VN: 84xxxxxxxxx
        ]

        # Từ khóa hủy bỏ
        self.cancel_keywords = ["hủy", "cancel", "dừng", "stop", "không", "thôi"]

        # Từ khóa xác nhận
        self.confirm_keywords = ["đúng", "ok", "yes", "có", "xác nhận", "đồng ý"]

        # Session storage để lưu trạng thái
        self.user_sessions = {}

    def init_collection_session(
        self, session_id: str, order_info: Dict
    ) -> Dict[str, Any]:
        """Khởi tạo phiên thu thập thông tin"""
        self.user_sessions[session_id] = {
            "state": UserInfoState.ASKING_NAME,
            "collected_info": {},
            "order_info": order_info,
            "attempts": {"name": 0, "phone": 0, "email": 0, "address": 0},
            "created_at": datetime.now(),
        }

        logger.info(f"🆕 Started info collection session for {session_id}")

        return {
            "success": True,
            "message": self._get_name_prompt(order_info),
            "type": "asking_name",
            "state": UserInfoState.ASKING_NAME.value,
            "session_info": self.user_sessions[session_id],
        }

    def _get_name_prompt(self, order_info: Dict) -> str:
        """Tạo prompt hỏi tên"""
        product_name = order_info.get("product_name", "sản phẩm")
        quantity = order_info.get("quantity", 1)
        unit = order_info.get("unit", "kg")

        return f"""📋 **THÔNG TIN ĐẶT HÀNG**

🛒 Sản phẩm: {product_name}
📊 Số lượng: {quantity} {unit}
💰 Tổng tiền: {order_info.get('total_amount', 0):,.0f} VND

Để hoàn tất đơn hàng, vui lòng cung cấp thông tin của bạn:

👤 **Họ và tên của bạn là gì?**
_Ví dụ: Nguyễn Văn An_"""

    def _get_phone_prompt(self) -> str:
        """Tạo prompt hỏi số điện thoại"""
        return """📱 **Số điện thoại của bạn là gì?**
_Ví dụ: 0901234567 hoặc +84901234567_

*Số điện thoại sẽ được sử dụng để liên hệ xác nhận đơn hàng*"""

    def _get_address_prompt(self) -> str:
        """Tạo prompt hỏi địa chỉ"""
        return """🏠 **Địa chỉ giao hàng của bạn là gì?**
_Ví dụ: 123 Đường ABC, Phường XYZ, Quận 1, TP.HCM_

*Vui lòng cung cấp địa chỉ đầy đủ để shipper có thể giao hàng*"""

    def _get_confirmation_prompt(self, collected_info: Dict, order_info: Dict) -> str:
        """Tạo prompt xác nhận thông tin"""
        return f"""✅ **XÁC NHẬN THÔNG TIN ĐƠN HÀNG**

**THÔNG TIN KHÁCH HÀNG:**
👤 Họ tên: {collected_info.get('name')}
📱 Điện thoại: {collected_info.get('phone')}
📧 Email: {collected_info.get('email')}
🏠 Địa chỉ: {collected_info.get('address')}

**THÔNG TIN SẢN PHẨM:**
🛒 Sản phẩm: {order_info.get('product_name')}
📊 Số lượng: {order_info.get('quantity')} {order_info.get('unit')}
💰 Tổng tiền: {order_info.get('total_amount', 0):,.0f} VND

**Thông tin trên có chính xác không?**
_Trả lời "đúng" để xác nhận hoặc "sửa" để chỉnh sửa_"""

    def validate_name(self, name: str) -> Tuple[bool, str]:
        """Validate tên người dùng"""
        name = name.strip()

        if len(name) < 2:
            return False, "Tên quá ngắn. Vui lòng nhập họ tên đầy đủ."

        if len(name) > 100:
            return False, "Tên quá dài. Vui lòng nhập tên ngắn gọn hơn."

        # Kiểm tra ký tự đặc biệt
        if re.search(r'[0-9@#$%^&*()_+=\[\]{}|;:",.<>?/~`]', name):
            return False, "Tên không được chứa số hoặc ký tự đặc biệt."

        return True, "OK"

    def validate_phone(self, phone: str) -> Tuple[bool, str]:
        """Validate số điện thoại"""
        phone = phone.strip().replace(" ", "").replace("-", "")

        for pattern in self.phone_patterns:
            if re.match(pattern, phone):
                return True, "OK"

        return (
            False,
            "Số điện thoại không hợp lệ. Vui lòng nhập số điện thoại Việt Nam (VD: 0901234567)",
        )

    def validate_address(self, address: str) -> Tuple[bool, str]:
        """Validate địa chỉ"""
        address = address.strip()

        if len(address) < 10:
            return False, "Địa chỉ quá ngắn. Vui lòng cung cấp địa chỉ đầy đủ."

        if len(address) > 500:
            return False, "Địa chỉ quá dài. Vui lòng rút gọn lại."

        return True, "OK"

    def validate_email(self, email: str) -> Tuple[bool, str]:
        """Validate email address"""
        email = email.strip().lower()

        if not email:
            return False, "Email không được để trống."

        # Basic email pattern
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(email_pattern, email):
            return (
                False,
                "Email không hợp lệ. Vui lòng nhập đúng định dạng (VD: example@gmail.com)",
            )

        if len(email) > 254:
            return False, "Email quá dài."

        return True, "OK"

    def _get_email_prompt(self) -> str:
        """Tạo prompt hỏi email"""
        return """📧 **Email của bạn là gì?**
    _Ví dụ: example@gmail.com hoặc user@yahoo.com_

    *Email sẽ được sử dụng để gửi xác nhận đơn hàng và cập nhật trạng thái*"""

    def process_user_response(self, session_id: str, user_input: str) -> Dict[str, Any]:
        """Xử lý phản hồi của người dùng"""

        if session_id not in self.user_sessions:
            return {
                "success": False,
                "message": "Phiên thu thập thông tin không tồn tại. Vui lòng bắt đầu lại.",
                "type": "session_not_found",
            }

        session = self.user_sessions[session_id]
        current_state = session["state"]
        user_input = user_input.strip()

        # Kiểm tra lệnh hủy
        if any(keyword in user_input.lower() for keyword in self.cancel_keywords):
            session["state"] = UserInfoState.CANCELLED
            return {
                "success": False,
                "message": "❌ Đã hủy quá trình đặt hàng.",
                "type": "cancelled",
            }

        # Xử lý theo trạng thái hiện tại
        if current_state == UserInfoState.ASKING_NAME:
            return self._process_name_response(session_id, user_input)

        elif current_state == UserInfoState.ASKING_PHONE:
            return self._process_phone_response(session_id, user_input)

        elif current_state == UserInfoState.ASKING_ADDRESS:
            return self._process_address_response(session_id, user_input)
        elif current_state == UserInfoState.ASKING_EMAIL:
            return self._process_email_response(session_id, user_input)
        elif current_state == UserInfoState.CONFIRMING_INFO:
            return self._process_confirmation_response(session_id, user_input)

        else:
            return {
                "success": False,
                "message": "Trạng thái không hợp lệ.",
                "type": "invalid_state",
            }

    def _process_name_response(
        self, session_id: str, user_input: str
    ) -> Dict[str, Any]:
        """Xử lý phản hồi về tên"""
        session = self.user_sessions[session_id]

        is_valid, error_msg = self.validate_name(user_input)

        if not is_valid:
            session["attempts"]["name"] += 1
            if session["attempts"]["name"] >= 3:
                return {
                    "success": False,
                    "message": "❌ Quá nhiều lần nhập sai. Vui lòng bắt đầu lại.",
                    "type": "max_attempts_exceeded",
                }

            return {
                "success": False,
                "message": f"❌ {error_msg}\n\n👤 **Vui lòng nhập lại họ tên:**",
                "type": "validation_error",
                "state": UserInfoState.ASKING_NAME.value,
            }

        # Lưu tên và chuyển sang hỏi số điện thoại
        session["collected_info"]["name"] = user_input
        session["state"] = UserInfoState.ASKING_PHONE

        return {
            "success": True,
            "message": f"✅ Cảm ơn {user_input}!\n\n{self._get_phone_prompt()}",
            "type": "asking_phone",
            "state": UserInfoState.ASKING_PHONE.value,
        }

    def _process_phone_response(
        self, session_id: str, user_input: str
    ) -> Dict[str, Any]:
        """Xử lý phản hồi về số điện thoại"""
        session = self.user_sessions[session_id]

        is_valid, error_msg = self.validate_phone(user_input)

        if not is_valid:
            session["attempts"]["phone"] += 1
            if session["attempts"]["phone"] >= 3:
                return {
                    "success": False,
                    "message": "❌ Quá nhiều lần nhập sai. Vui lòng bắt đầu lại.",
                    "type": "max_attempts_exceeded",
                }

            return {
                "success": False,
                "message": f"❌ {error_msg}\n\n📱 **Vui lòng nhập lại số điện thoại:**",
                "type": "validation_error",
                "state": UserInfoState.ASKING_PHONE.value,
            }

        # Lưu số điện thoại và chuyển sang hỏi địa chỉ
        session["collected_info"]["phone"] = user_input.replace(" ", "").replace(
            "-", ""
        )
        session["state"] = UserInfoState.ASKING_ADDRESS

        return {
            "success": True,
            "message": f"✅ Đã lưu số điện thoại!\n\n{self._get_address_prompt()}",
            "type": "asking_address",
            "state": UserInfoState.ASKING_ADDRESS.value,
        }

    def _process_email_response(
        self, session_id: str, user_input: str
    ) -> Dict[str, Any]:
        """Xử lý phản hồi về email"""
        session = self.user_sessions[session_id]

        is_valid, error_msg = self.validate_email(user_input)

        if not is_valid:
            session["attempts"]["email"] += 1
            if session["attempts"]["email"] >= 3:
                return {
                    "success": False,
                    "message": "❌ Quá nhiều lần nhập sai. Vui lòng bắt đầu lại.",
                    "type": "max_attempts_exceeded",
                }

            return {
                "success": False,
                "message": f"❌ {error_msg}\n\n📧 **Vui lòng nhập lại email:**",
                "type": "validation_error",
                "state": UserInfoState.ASKING_EMAIL.value,
            }

        # Lưu email và chuyển sang hỏi địa chỉ
        session["collected_info"]["email"] = user_input.lower()
        session["state"] = (
            UserInfoState.CONFIRMING_INFO
        )  # ← THAY ĐỔI: từ ASKING_ADDRESS thành CONFIRMING_INFO

        return {
            "success": True,
            "message": self._get_confirmation_prompt(  # ← THAY ĐỔI: gọi confirmation prompt
                session["collected_info"], session["order_info"]
            ),
            "type": "confirming_info",  # ← THAY ĐỔI
            "state": UserInfoState.CONFIRMING_INFO.value,  # ← THAY ĐỔI
        }

    def _process_address_response(
        self, session_id: str, user_input: str
    ) -> Dict[str, Any]:
        """Xử lý phản hồi về địa chỉ"""
        session = self.user_sessions[session_id]

        is_valid, error_msg = self.validate_address(user_input)

        if not is_valid:
            session["attempts"]["address"] += 1
            if session["attempts"]["address"] >= 3:
                return {
                    "success": False,
                    "message": "❌ Quá nhiều lần nhập sai. Vui lòng bắt đầu lại.",
                    "type": "max_attempts_exceeded",
                }

            return {
                "success": False,
                "message": f"❌ {error_msg}\n\n🏠 **Vui lòng nhập lại địa chỉ:**",
                "type": "validation_error",
                "state": UserInfoState.ASKING_ADDRESS.value,
            }

        # Lưu địa chỉ và chuyển sang email
        session["collected_info"]["address"] = user_input
        session["state"] = (
            UserInfoState.ASKING_EMAIL
        )  # ← THAY ĐỔI: từ CONFIRMING_INFO thành ASKING_EMAIL

        return {
            "success": True,
            "message": f"✅ Đã lưu địa chỉ!\n\n{self._get_email_prompt()}",  # ← THAY ĐỔI: gọi email prompt
            "type": "asking_email",  # ← THAY ĐỔI
            "state": UserInfoState.ASKING_EMAIL.value,  # ← THAY ĐỔI
        }

    def _process_confirmation_response(
        self, session_id: str, user_input: str
    ) -> Dict[str, Any]:
        """Xử lý phản hồi xác nhận"""
        session = self.user_sessions[session_id]
        user_input_lower = user_input.lower()

        if any(keyword in user_input_lower for keyword in self.confirm_keywords):
            # Xác nhận thông tin - hoàn tất
            session["state"] = UserInfoState.COMPLETED

            return {
                "success": True,
                "message": "✅ Thông tin đã được xác nhận! Đang tạo đơn hàng...",
                "type": "info_confirmed",
                "state": UserInfoState.COMPLETED.value,
                "data": {
                    "user_info": session["collected_info"],
                    "order_info": session["order_info"],
                },
            }

        elif "sửa" in user_input_lower or "chỉnh" in user_input_lower:
            # Yêu cầu sửa - bắt đầu lại từ tên
            session["state"] = UserInfoState.ASKING_NAME
            session["collected_info"] = {}
            session["attempts"] = {"name": 0, "phone": 0, "email": 0, "address": 0}

            return {
                "success": True,
                "message": f"🔄 Bắt đầu lại quá trình nhập thông tin.\n\n{self._get_name_prompt(session['order_info'])}",
                "type": "asking_name",
                "state": UserInfoState.ASKING_NAME.value,
            }

        else:
            return {
                "success": False,
                "message": f"""❓ Không hiểu phản hồi của bạn.

{self._get_confirmation_prompt(session["collected_info"], session["order_info"])}""",
                "type": "confirmation_unclear",
                "state": UserInfoState.CONFIRMING_INFO.value,
            }

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Lấy trạng thái phiên thu thập thông tin"""
        if session_id not in self.user_sessions:
            return {"exists": False, "message": "Phiên không tồn tại"}

        session = self.user_sessions[session_id]
        return {
            "exists": True,
            "state": session["state"].value,
            "collected_info": session["collected_info"],
            "order_info": session["order_info"],
            "attempts": session["attempts"],
            "created_at": session["created_at"],
        }

    def cleanup_session(self, session_id: str) -> bool:
        """Dọn dẹp phiên thu thập thông tin"""
        if session_id in self.user_sessions:
            del self.user_sessions[session_id]
            logger.info(f"🗑️ Cleaned up info collection session: {session_id}")
            return True
        return False

    def is_collection_in_progress(self, session_id: str) -> bool:
        """Kiểm tra xem có đang thu thập thông tin không"""
        if session_id not in self.user_sessions:
            return False

        state = self.user_sessions[session_id]["state"]
        return state not in [UserInfoState.COMPLETED, UserInfoState.CANCELLED]


# Factory function
def create_user_info_collection_service() -> UserInfoCollectionService:
    """Tạo UserInfoCollectionService"""
    return UserInfoCollectionService()


# # Demo usage
# if __name__ == "__main__":
#     # Test service
#     service = UserInfoCollectionService()

#     # Giả lập order info
#     order_info = {
#         "product_name": "Đùi góc tư gà đông lạnh xuất xứ Mỹ",
#         "quantity": 2.0,
#         "unit": "kg",
#         "total_amount": 100000
#     }

#     # Test flow
#     session_id = "test_session_123"

#     # 1. Khởi tạo
#     result = service.init_collection_session(session_id, order_info)
#     print("INIT:", result["message"])

#     # 2. Test validate functions
#     print("\n=== VALIDATION TESTS ===")
#     print("Name validation:")
#     print("- 'A':", service.validate_name("A"))
#     print("- 'Nguyễn Văn An':", service.validate_name("Nguyễn Văn An"))
#     print("- 'Test123':", service.validate_name("Test123"))

#     print("\nPhone validation:")
#     print("- '0901234567':", service.validate_phone("0901234567"))
#     print("- '123456':", service.validate_phone("123456"))
#     print("- '+84901234567':", service.validate_phone("+84901234567"))

#     print("\nAddress validation:")
#     print("- 'HCM':", service.validate_address("HCM"))
#     print("- '123 ABC Street, District 1, HCMC':", service.validate_address("123 ABC Street, District 1, HCMC"))

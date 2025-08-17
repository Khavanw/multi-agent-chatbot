import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from app.db.models.payment import (
    PaymentMethod,
    PaymentOption,
    PaymentState,
    PaymentStep,
)

logger = logging.getLogger(__name__)


class PaymentProcessor:
    """Xử lý phương thức thanh toán"""

    def __init__(self):
        self.payment_options = self._initialize_payment_options()
        self.payment_keywords = self._initialize_payment_keywords()

    def _initialize_payment_options(self) -> List[PaymentOption]:
        """Khởi tạo các phương thức thanh toán có sẵn"""
        return [
            PaymentOption(
                method=PaymentMethod.COD,
                display_name="Thanh toán khi nhận hàng (COD)",
                description="Thanh toán bằng tiền mặt khi nhận hàng",
                fee=0.0,
                is_available=True,
            ),
            PaymentOption(
                method=PaymentMethod.BANK_TRANSFER,
                display_name="Chuyển khoản ngân hàng",
                description="Chuyển khoản qua ngân hàng (Vietcombank, Techcombank, etc.)",
                fee=0.0,
                is_available=True,
            ),
            PaymentOption(
                method=PaymentMethod.MOMO,
                display_name="Ví MoMo",
                description="Thanh toán qua ví điện tử MoMo",
                fee=0.0,
                is_available=True,
                min_amount=10000,
            ),
            PaymentOption(
                method=PaymentMethod.ZALOPAY,
                display_name="ZaloPay",
                description="Thanh toán qua ví điện tử ZaloPay",
                fee=0.0,
                is_available=True,
                min_amount=10000,
            ),
            PaymentOption(
                method=PaymentMethod.VNPAY,
                display_name="VNPay",
                description="Thanh toán qua VNPay (ATM, Internet Banking, QR Code)",
                fee=0.0,
                is_available=True,
                min_amount=10000,
            ),
            PaymentOption(
                method=PaymentMethod.CREDIT_CARD,
                display_name="Thẻ tín dụng/Thẻ ghi nợ",
                description="Thanh toán bằng thẻ Visa, MasterCard, JCB",
                fee=0.0,
                is_available=True,
                min_amount=50000,
            ),
        ]

    def _initialize_payment_keywords(self) -> Dict[str, PaymentMethod]:
        """Khởi tạo từ khóa để nhận diện phương thức thanh toán"""
        return {
            # COD
            "cod": PaymentMethod.COD,
            "tiền mặt": PaymentMethod.COD,
            "nhận hàng": PaymentMethod.COD,
            "ship cod": PaymentMethod.COD,
            "thanh toán khi nhận": PaymentMethod.COD,
            # Bank Transfer
            "chuyển khoản": PaymentMethod.BANK_TRANSFER,
            "ngân hàng": PaymentMethod.BANK_TRANSFER,
            "banking": PaymentMethod.BANK_TRANSFER,
            "vietcombank": PaymentMethod.BANK_TRANSFER,
            "techcombank": PaymentMethod.BANK_TRANSFER,
            "bidv": PaymentMethod.BANK_TRANSFER,
            "vcb": PaymentMethod.BANK_TRANSFER,
            # MoMo
            "momo": PaymentMethod.MOMO,
            "ví momo": PaymentMethod.MOMO,
            # ZaloPay
            "zalopay": PaymentMethod.ZALOPAY,
            "zalo pay": PaymentMethod.ZALOPAY,
            "ví zalo": PaymentMethod.ZALOPAY,
            # VNPay
            "vnpay": PaymentMethod.VNPAY,
            "vn pay": PaymentMethod.VNPAY,
            "qr code": PaymentMethod.VNPAY,
            "quét mã": PaymentMethod.VNPAY,
            # Credit Card
            "thẻ": PaymentMethod.CREDIT_CARD,
            "visa": PaymentMethod.CREDIT_CARD,
            "mastercard": PaymentMethod.CREDIT_CARD,
            "credit card": PaymentMethod.CREDIT_CARD,
            "thẻ tín dụng": PaymentMethod.CREDIT_CARD,
            "thẻ ghi nợ": PaymentMethod.CREDIT_CARD,
        }

    def detect_payment_method_from_text(self, text: str) -> Optional[PaymentMethod]:
        """Phát hiện phương thức thanh toán từ text"""
        if not text:
            return None

        text_lower = text.lower().strip()
        logger.info(f"🔍 Detecting payment method from: '{text}'")

        # Tìm kiếm exact match
        for keyword, method in self.payment_keywords.items():
            if keyword in text_lower:
                logger.info(
                    f"✅ Found payment method: {method.value} (keyword: {keyword})"
                )
                return method

        # Tìm kiếm pattern cho số thẻ
        card_pattern = r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"
        if re.search(card_pattern, text):
            logger.info(f"✅ Found credit card pattern")
            return PaymentMethod.CREDIT_CARD

        # Tìm kiếm pattern cho số điện thoại (có thể là MoMo/ZaloPay)
        phone_pattern = r"\b0\d{9}\b"
        if re.search(phone_pattern, text):
            logger.info(f"✅ Found phone pattern, suggesting MoMo")
            return PaymentMethod.MOMO

        logger.info(f"❌ No payment method detected")
        return None

    def get_available_payment_options(
        self, order_amount: float = 0.0
    ) -> List[PaymentOption]:
        """Lấy danh sách phương thức thanh toán khả dụng"""
        available_options = []

        for option in self.payment_options:
            if (
                option.is_available
                and order_amount >= option.min_amount
                and order_amount <= option.max_amount
            ):
                available_options.append(option)

        return available_options

    def format_payment_options_message(self, order_amount: float = 0.0) -> str:
        """Tạo message hiển thị các phương thức thanh toán"""
        available_options = self.get_available_payment_options(order_amount)

        if not available_options:
            return "❌ Hiện tại không có phương thức thanh toán nào khả dụng."

        message = (
            f"💳 **Chọn phương thức thanh toán** (Tổng tiền: {order_amount:,.0f}đ)\n\n"
        )

        for i, option in enumerate(available_options, 1):
            fee_text = f" (+{option.fee:,.0f}đ phí)" if option.fee > 0 else ""
            message += f"**{i}. {option.display_name}**{fee_text}\n"
            message += f"   └ {option.description}\n\n"

        message += "📝 **Cách chọn:**\n"
        message += "• Nhập số thứ tự (1, 2, 3, ...)\n"
        message += "• Hoặc gõ tên phương thức (COD, MoMo, Chuyển khoản, ...)\n"
        message += "• Ví dụ: 'Tôi muốn thanh toán COD' hoặc chỉ gõ '1'"

        return message

    def process_payment_selection(
        self, user_input: str, order_amount: float = 0.0
    ) -> Dict[str, Any]:
        """Xử lý lựa chọn phương thức thanh toán"""
        result = {
            "success": False,
            "payment_method": None,
            "payment_option": None,
            "message": "",
            "requires_additional_info": False,
            "additional_info_type": None,
        }

        try:
            available_options = self.get_available_payment_options(order_amount)

            if not available_options:
                result["message"] = "❌ Không có phương thức thanh toán nào khả dụng."
                return result

            # Thử detect từ text
            detected_method = self.detect_payment_method_from_text(user_input)

            # Thử parse số thứ tự
            number_match = re.search(r"\b(\d+)\b", user_input)
            if number_match:
                try:
                    choice_num = int(number_match.group(1))
                    if 1 <= choice_num <= len(available_options):
                        selected_option = available_options[choice_num - 1]
                        detected_method = selected_option.method
                        logger.info(
                            f"✅ Selected by number: {choice_num} -> {detected_method.value}"
                        )
                except ValueError:
                    pass

            if not detected_method:
                result["message"] = (
                    f"❌ Không nhận diện được phương thức thanh toán từ: '{user_input}'\n\n"
                )
                result["message"] += self.format_payment_options_message(order_amount)
                return result

            # Tìm option tương ứng
            selected_option = None
            for option in available_options:
                if option.method == detected_method:
                    selected_option = option
                    break

            if not selected_option:
                result["message"] = (
                    f"❌ Phương thức thanh toán {detected_method.value} không khả dụng cho đơn hàng này."
                )
                return result

            # Xử lý thành công
            result["success"] = True
            result["payment_method"] = detected_method.value
            result["payment_option"] = selected_option

            # Kiểm tra cần thông tin bổ sung
            additional_info = self.get_additional_payment_info(
                detected_method, order_amount
            )
            if additional_info:
                result["requires_additional_info"] = True
                result["additional_info_type"] = additional_info["type"]
                result["message"] = additional_info["message"]
            else:
                result["message"] = (
                    f"✅ Đã chọn phương thức thanh toán: **{selected_option.display_name}**"
                )

            logger.info(f"✅ Payment method selected: {detected_method.value}")

        except Exception as e:
            logger.error(f"❌ Error processing payment selection: {str(e)}")
            result["message"] = "❌ Có lỗi xảy ra khi xử lý lựa chọn thanh toán."

        return result

    def get_additional_payment_info(
        self, payment_method: PaymentMethod, order_amount: float
    ) -> Optional[Dict[str, str]]:
        """Lấy thông tin bổ sung cần thiết cho từng phương thức thanh toán"""

        if payment_method == PaymentMethod.BANK_TRANSFER:
            return {
                "type": "bank_info",
                "message": f"""
🏦 **Thông tin chuyển khoản:**

**Ngân hàng:** Vietcombank
**Số tài khoản:** 0123456789
**Chủ tài khoản:** CÔNG TY TNHH ABC
**Số tiền:** {order_amount:,.0f}đ
**Nội dung:** [Mã đơn hàng sẽ được cung cấp]

📱 **Lưu ý:**
• Vui lòng chuyển khoản đúng số tiền
• Ghi rõ mã đơn hàng trong nội dung
• Sau khi chuyển khoản, chụp ảnh biên lai gửi cho chúng tôi

✅ **Xác nhận:** Gõ 'Đã chuyển khoản' khi hoàn tất
""",
            }

        elif payment_method == PaymentMethod.MOMO:
            return {
                "type": "momo_info",
                "message": f"""
📱 **Thanh toán MoMo:**

**Số điện thoại:** 0123456789
**Tên:** CÔNG TY TNHH ABC
**Số tiền:** {order_amount:,.0f}đ
**Nội dung:** [Mã đơn hàng sẽ được cung cấp]

📋 **Hướng dẫn:**
1. Mở ứng dụng MoMo
2. Chọn "Chuyển tiền" → "Đến số điện thoại"
3. Nhập số điện thoại và số tiền
4. Ghi mã đơn hàng vào nội dung
5. Xác nhận thanh toán

✅ **Xác nhận:** Gõ 'Đã thanh toán MoMo' khi hoàn tất
""",
            }

        elif payment_method == PaymentMethod.CREDIT_CARD:
            return {
                "type": "card_info",
                "message": f"""
💳 **Thanh toán thẻ tín dụng:**

**Số tiền:** {order_amount:,.0f}đ

🔒 **Bảo mật:**
• Chúng tôi sử dụng cổng thanh toán an toàn
• Thông tin thẻ được mã hóa SSL
• Không lưu trữ thông tin thẻ

📋 **Bước tiếp theo:**
1. Nhấp vào link thanh toán (sẽ được gửi)
2. Nhập thông tin thẻ
3. Xác thực OTP
4. Hoàn tất thanh toán

✅ **Xác nhận:** Gõ 'Sẵn sàng thanh toán thẻ'
""",
            }

        return None

    def create_payment_summary(
        self,
        payment_method: str,
        order_amount: float,
        additional_info: Dict[str, Any] = None,
    ) -> str:
        """Tạo tóm tắt thông tin thanh toán"""

        # Tìm payment option
        selected_option = None
        for option in self.payment_options:
            if option.method.value == payment_method:
                selected_option = option
                break

        if not selected_option:
            return "❌ Không tìm thấy thông tin phương thức thanh toán."

        total_amount = order_amount + selected_option.fee

        summary = f"""
📋 **TÓM TẮT THANH TOÁN**

🛍️ **Đơn hàng:**
• Tổng tiền hàng: {order_amount:,.0f}đ
• Phí thanh toán: {selected_option.fee:,.0f}đ
• **Tổng cộng: {total_amount:,.0f}đ**

💳 **Phương thức:** {selected_option.display_name}
📝 **Mô tả:** {selected_option.description}

⏰ **Thời gian:** {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""

        if additional_info:
            summary += f"\n📎 **Thông tin bổ sung:**\n"
            for key, value in additional_info.items():
                summary += f"• {key}: {value}\n"

        return summary


class PaymentWorkflow:
    """Workflow xử lý thanh toán hoàn chỉnh"""

    def __init__(self, payment_processor: PaymentProcessor):
        self.payment_processor = payment_processor
        self.current_state = PaymentState.WAITING_FOR_METHOD
        self.payment_data = {}

    def process_user_input(
        self, user_input: str, order_amount: float = 0.0
    ) -> Dict[str, Any]:
        """Xử lý input từ user theo workflow"""

        if self.current_step == "waiting_for_payment_method":
            return self._handle_payment_method_selection(user_input, order_amount)

        elif self.current_step == "waiting_for_payment_confirmation":
            return self._handle_payment_confirmation(user_input)

        elif self.current_state == PaymentState.READY_FOR_ORDER:
            return self._handle_order_ready()

        else:
            return {"success": False, "message": "Invalid payment state"}

    def _handle_payment_method_selection(
        self, user_input: str, order_amount: float
    ) -> Dict[str, Any]:
        """Xử lý chọn phương thức thanh toán"""

        result = self.payment_processor.process_payment_selection(
            user_input, order_amount
        )

        if result["success"]:
            # Save payment data
            self.payment_data = {
                "method": result["payment_method"],
                "option": result["payment_option"],
                "amount": order_amount,
            }

            payment_method = result["payment_method"]

            # 🎯 CHUẨN HÓA: TẤT CẢ METHODS ĐỀU CÓ 2 BƯỚC
            if payment_method == "cod":
                # COD: Chọn xong là sẵn sàng tạo order
                self.current_state = PaymentState.READY_FOR_ORDER
                result["next_step"] = PaymentStep.ORDER_CONFIRMATION.value
                result["message"] = self._get_cod_confirmation_message()

            elif payment_method in ["momo", "vnpay", "bank_transfer"]:
                # E-wallets: Cần bước xác nhận thanh toán
                self.current_state = PaymentState.METHOD_SELECTED
                result["next_step"] = PaymentStep.CONFIRM_PAYMENT.value
                # Giữ nguyên message từ payment processor

            else:
                # Unknown method - fallback to ready
                self.current_state = PaymentState.READY_FOR_ORDER
                result["next_step"] = PaymentStep.ORDER_CONFIRMATION.value

        return result

    def _handle_order_ready(self) -> Dict[str, Any]:
        """Handle when payment is ready for order creation"""
        return {
            "success": True,
            "next_step": PaymentStep.ORDER_CONFIRMATION.value,
            "message": "Thanh toán đã sẵn sàng. Đang tạo đơn hàng...",
        }

    def _get_cod_confirmation_message(self) -> str:
        """Standardized COD confirmation message"""
        return """✅ **Thanh toán khi nhận hàng (COD) đã được chọn**

📋 **Quy trình:**
1. Đơn hàng sẽ được tạo ngay
2. Chúng tôi sẽ liên hệ xác nhận
3. Giao hàng tận nơi
4. Bạn thanh toán khi nhận hàng

🎯 **Đang tạo đơn hàng...**"""

    def _handle_payment_confirmation(
        self, user_input: str, order_amount: float
    ) -> Dict[str, Any]:
        """Handle payment confirmation step - STANDARDIZED"""
        payment_method = self.payment_data.get("method")

        # Detect confirmation keywords
        confirmation_keywords = [
            # Tiếng Việt chung
            "đã thanh toán",
            "đã chuyển",
            "hoàn tất",
            "xong",
            "xác nhận",
            "đã gửi",
            "đã thực hiện",
            "thành công",
            "completed",
            # English
            "done",
            "paid",
            "transferred",
            "finished",
            "ok",
            "yes",
            "confirmed",
            "success",
            "successful",
            # Specific payment methods
            "đã chuyển khoản",
            "đã transfer",
            "đã banking",
            "đã momo",
            "đã zalopay",
            "đã vnpay",
            "đã quét mã",
            "đã scan",
            "đã thanh toán thẻ",
            "đã trả tiền mặt",
            "đã cash",
        ]

        user_input_lower = user_input.lower().strip()
        is_confirmed = any(
            keyword in user_input_lower for keyword in confirmation_keywords
        )
        transaction_pattern = r"\b\d{6,}\b"  # 6+ digits could be transaction ID
        has_transaction_id = bool(re.search(transaction_pattern, user_input))

        if is_confirmed or has_transaction_id:
            # 🎯 TẤT CẢ METHODS CHUYỂN VỀ CÙNG MỘT STATE
            self.current_state = PaymentState.READY_FOR_ORDER

            # Lưu thông tin xác nhận
            self.payment_data["confirmation_time"] = datetime.now().isoformat()
            self.payment_data["confirmation_text"] = user_input

            if has_transaction_id:
                transaction_match = re.search(transaction_pattern, user_input)
                self.payment_data["transaction_id"] = transaction_match.group(0)

            return {
                "success": True,
                "payment_method": payment_method,
                "next_step": PaymentStep.ORDER_CONFIRMATION.value,
                "message": self._get_payment_confirmed_message(payment_method),
            }
        else:
            # Chưa xác nhận, đưa ra hướng dẫn cụ thể theo từng phương thức
            guidance_message = self._get_payment_guidance_message(payment_method)

            return {
                "success": False,
                "message": guidance_message,
                "next_step": PaymentStep.CONFIRM_PAYMENT.value,
            }

    def _get_payment_guidance_message(self, payment_method: str) -> str:
        """Hướng dẫn xác nhận cụ thể cho từng phương thức thanh toán"""

        guidance_messages = {
            "cod": """⚠️ **Xác nhận thanh toán COD**
            
    📝 Vui lòng xác nhận bạn đồng ý thanh toán khi nhận hàng.
    💬 Gõ: 'Đồng ý COD' hoặc 'Xác nhận'""",
            "momo": """⚠️ **Xác nhận thanh toán MoMo**
            
    📱 Vui lòng xác nhận đã hoàn tất thanh toán qua ví MoMo.
    💬 Gõ: 'Đã thanh toán MoMo' hoặc 'Đã MoMo' hoặc mã giao dịch""",
            "vnpay": """⚠️ **Xác nhận thanh toán VNPay**
            
    💳 Vui lòng xác nhận đã hoàn tất thanh toán qua VNPay.
    💬 Gõ: 'Đã thanh toán VNPay' hoặc 'Đã VNPay' hoặc mã giao dịch""",
            "zalopay": """⚠️ **Xác nhận thanh toán ZaloPay**
            
    📱 Vui lòng xác nhận đã hoàn tất thanh toán qua ZaloPay.
    💬 Gõ: 'Đã thanh toán ZaloPay' hoặc 'Đã ZaloPay' hoặc mã giao dịch""",
            "bank_transfer": """⚠️ **Xác nhận chuyển khoản ngân hàng**
            
    🏦 Vui lòng xác nhận đã hoàn tất chuyển khoản.
    💬 Gõ: 'Đã chuyển khoản' hoặc 'Đã transfer' hoặc mã giao dịch""",
            "credit_card": """⚠️ **Xác nhận thanh toán thẻ tín dụng**
            
    💳 Vui lòng xác nhận đã hoàn tất thanh toán bằng thẻ.
    💬 Gõ: 'Đã thanh toán thẻ' hoặc 'Đã thanh toán' hoặc mã giao dịch""",
            "cash": """⚠️ **Xác nhận thanh toán tiền mặt**
            
    💵 Vui lòng xác nhận đã hoàn tất thanh toán bằng tiền mặt.
    💬 Gõ: 'Đã trả tiền mặt' hoặc 'Đã thanh toán cash'""",
        }

        return guidance_messages.get(
            payment_method,
            f"""⚠️ **Xác nhận thanh toán {payment_method.upper()}**
        
    💬 Vui lòng xác nhận đã hoàn thành thanh toán.
    📝 Gõ: 'Đã thanh toán' hoặc 'Xác nhận' khi hoàn tất.""",
        )

    def _get_payment_confirmed_message(self, payment_method: str) -> str:
        """Standardized payment confirmation message"""
        method_names = {
            "cod": "COD (Thanh toán khi nhận hàng)",
            "momo": "MoMo",
            "vnpay": "VNPay",
            "zalopay": "ZaloPay",
            "bank_transfer": "Chuyển khoản ngân hàng",
            "credit_card": "Thẻ tín dụng/ghi nợ",
            "cash": "Thanh toán tiền mặt",
        }

        method_display = method_names.get(payment_method, payment_method.upper())

        if payment_method == "cod":
            return f"""✅ **Xác nhận {method_display} thành công!**

    📋 **Tiếp theo:**
    1. Đơn hàng được tạo ngay lập tức
    2. Chúng tôi sẽ liên hệ xác nhận
    3. Chuẩn bị và giao hàng tận nơi
    4. Bạn thanh toán khi nhận hàng

    🎯 **Đang tạo đơn hàng...**"""

        elif payment_method in ["momo", "vnpay", "zalopay"]:
            return f"""✅ **Xác nhận thanh toán {method_display} thành công!**

    📋 **Tiếp theo:**
    1. Chúng tôi sẽ kiểm tra giao dịch trong vài phút
    2. Xác nhận đơn hàng qua email/SMS
    3. Chuẩn bị và giao hàng

    💡 **Lưu ý:** Nếu có vấn đề với giao dịch, chúng tôi sẽ liên hệ ngay.

    🎯 **Đang tạo đơn hàng...**"""

        elif payment_method == "bank_transfer":
            return f"""✅ **Xác nhận {method_display} thành công!**

    📋 **Tiếp theo:**
    1. Chúng tôi sẽ kiểm tra số dư trong 1-2 giờ
    2. Xác nhận đơn hàng khi nhận được tiền
    3. Chuẩn bị và giao hàng

    📧 **Lưu ý:** Vui lòng gửi ảnh biên lai chuyển khoản qua email để xử lý nhanh hơn.

    🎯 **Đang tạo đơn hàng...**"""

        elif payment_method == "credit_card":
            return f"""✅ **Xác nhận {method_display} thành công!**

    📋 **Tiếp theo:**
    1. Xác thực giao dịch qua ngân hàng (1-3 phút)
    2. Xác nhận đơn hàng tự động
    3. Chuẩn bị và giao hàng

    🔒 **Bảo mật:** Giao dịch được bảo vệ bởi SSL và 3D Secure.

    🎯 **Đang tạo đơn hàng...**"""

        elif payment_method == "cash":
            return f"""✅ **Xác nhận {method_display} thành công!**

    📋 **Tiếp theo:**
    1. Đơn hàng được tạo ngay
    2. Chuẩn bị hàng hóa 
    3. Giao hàng tận nơi

    💵 **Lưu ý:** Đã nhận thanh toán bằng tiền mặt.

    🎯 **Đang tạo đơn hàng...**"""

        else:
            # Fallback cho các phương thức khác
            return f"""✅ **Xác nhận thanh toán {method_display} thành công!**

    📋 **Tiếp theo:**
    1. Chúng tôi sẽ xử lý giao dịch
    2. Xác nhận đơn hàng
    3. Chuẩn bị và giao hàng

    🎯 **Đang tạo đơn hàng...**"""

    def start_payment_process(self, order_amount: float = 0.0) -> str:
        """Bắt đầu quy trình thanh toán"""
        self.current_step = "waiting_for_payment_method"
        self.payment_data = {}

        return self.payment_processor.format_payment_options_message(order_amount)

    def get_current_step(self) -> str:
        """Lấy bước hiện tại"""
        return self.current_step

    def get_payment_data(self) -> Dict[str, Any]:
        """Lấy dữ liệu thanh toán"""
        return self.payment_data.copy()

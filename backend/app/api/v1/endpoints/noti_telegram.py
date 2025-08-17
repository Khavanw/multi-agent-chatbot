from fastapi import APIRouter
import requests

from app.settings import APP_SETTINGS

router = APIRouter()


def send_to_telegram(message: str):
    url = f"https://api.telegram.org/bot{APP_SETTINGS.BOT_TOKEN}/sendMessage"
    data = {"chat_id": APP_SETTINGS.CHAT_ID, "text": message}
    res = requests.post(url, data=data)
    return res.ok


def _build_notifications_url(session_id: str) -> str:
    if not APP_SETTINGS.NOTIFI_NGROK:
        raise RuntimeError(
            "Missing NOTIFI_NGROK env. Please set NOTIFI_NGROK to your API base URL."
        )
    base = APP_SETTINGS.NOTIFI_NGROK.rstrip("/")
    return f"{base}/api/v1/order/notifications/{session_id}"


def _format_order_created_message(notification: dict) -> str:
    title = notification.get("title", "Thông báo đơn hàng")
    message = notification.get("message", "")
    data = notification.get("data", {}) or {}

    order_id = data.get("order_id", "-")
    customer_name = data.get("customer_name", "-")
    customer_phone = data.get("customer_phone", "-")
    customer_email = data.get("customer_email", "-")
    customer_address = data.get("customer_address", "-")
    product_name = data.get("product_name", "-")
    total_amount = data.get("total_amount", "-")
    payment_method = data.get("payment_method", "-")
    quantity = data.get("quantity", "-")
    unit = data.get("unit", "-")
    status = data.get("status", "-")

    lines = [
        f"{title}",
        f"{message}",
        "",
        f"Mã đơn: {order_id}",
        f"Khách hàng: {customer_name}",
        f"Số điện thoại: {customer_phone}",
        f"Email: {customer_email}",
        f"Địa chỉ: {customer_address}",
        f"Sản phẩm: {product_name}",
        f"Tổng tiền: {total_amount}",
        f"Phương thức thanh toán: {payment_method}"
        f"Số lượng: {quantity}"
        f"Đơn vị:{unit}"
        f"Trạng thái: {status}",
    ]
    return "\n".join(lines)


@router.get("/notify/telegram/order/{session_id}")
def notify_telegram_order(
    session_id: str,
):
    try:
        url = _build_notifications_url(session_id)
        resp = requests.get(url, timeout=10)
        if not resp.ok:
            return {
                "status": "error",
                "message": f"Không lấy được dữ liệu từ {url}",
                "http_status": resp.status_code,
            }

        data = resp.json() if resp.content else {}
        notifications = data.get("notifications", []) or []
        order_notifications = [
            n for n in notifications if n.get("type") == "order_created"
        ]

        if not order_notifications:
            return {
                "status": "error",
                "message": "Không có thông báo 'order_created' nào",
            }

        try:
            order_notifications.sort(key=lambda n: n.get("timestamp", ""))
        except Exception:
            pass
        latest = order_notifications[-1]

        formatted = _format_order_created_message(latest)
        ok = send_to_telegram(formatted)

        if ok:
            return {
                "status": "success",
                "message": "Đã gửi thông báo đơn hàng qua Telegram",
                "sent_preview": formatted,
            }
        else:
            return {"status": "error", "message": "Gửi Telegram thất bại"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

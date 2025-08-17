import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from fastapi import APIRouter, Request

from app.settings import APP_SETTINGS

router = APIRouter()


def _build_notifications_url(session_id: str) -> str:
    if not APP_SETTINGS.NOTIFI_NGROK:
        raise RuntimeError(
            "Missing NOTIFI_NGROK env. Please set NOTIFI_NGROK to your API base URL."
        )
    base = APP_SETTINGS.NOTIFI_NGROK.rstrip("/")
    return f"{base}/api/v1/order/notifications/{session_id}"


def _format_order_email_subject(notification: dict) -> str:
    return notification.get("title", "Thông tin đơn hàng")


def _format_order_email_body(notification: dict) -> str:
    title = notification.get("title", "Thông tin đơn hàng")
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
    image_url = data.get("image_url")

    lines = [
        title,
        message,
        "",
        f"Mã đơn: {order_id}",
        f"Khách hàng: {customer_name}",
        f"Số điện thoại: {customer_phone}",
        f"Email: {customer_email}",
        f"Địa chỉ: {customer_address}",
        f"Sản phẩm: {product_name}",
        f"Tổng tiền: {total_amount}",
        f"Phương thức thanh toán: {payment_method}",
        f"Số lượng: {quantity}",
        f"Đơn vị: {unit}",
        f"Trạng thái: {status}",
    ]

    if image_url:
        lines.append("")
        lines.append(f"Hình ảnh sản phẩm: {image_url}")
    return "\n".join(lines)


def _format_order_email_html(notification: dict) -> str:
    title = notification.get("title", "Thông tin đơn hàng")
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
    image_url = data.get("image_url")

    # cái đống này tạo giao diện html để hiển thị đẹp cho email và mobile
    html_parts = [
        f"<h3>{title}</h3>",
        f"<p>{message}</p>",
        '<table style="border-collapse:collapse;width:100%;max-width:520px">',
        f'<tr><td style="padding:6px 0;font-weight:600">Mã đơn:</td><td style="padding:6px 0">{order_id}</td></tr>',
        f'<tr><td style="padding:6px 0;font-weight:600">Khách hàng:</td><td style="padding:6px 0">{customer_name}</td></tr>',
        f'<tr><td style="padding:6px 0;font-weight:600">Số điện thoại:</td><td style="padding:6px 0">{customer_phone}</td></tr>',
        f'<tr><td style="padding:6px 0;font-weight:600">Email:</td><td style="padding:6px 0">{customer_email}</td></tr>',
        f'<tr><td style="padding:6px 0;font-weight:600">Địa chỉ:</td><td style="padding:6px 0">{customer_address}</td></tr>',
        f'<tr><td style="padding:6px 0;font-weight:600">Sản phẩm:</td><td style="padding:6px 0">{product_name}</td></tr>',
        f'<tr><td style="padding:6px 0;font-weight:600">Số lượng:</td><td style="padding:6px 0">{quantity} {unit}</td></tr>',
        f'<tr><td style="padding:6px 0;font-weight:600">Tổng tiền:</td><td style="padding:6px 0">{total_amount}</td></tr>',
        f'<tr><td style="padding:6px 0;font-weight:600">Phương thức thanh toán:</td><td style="padding:6px 0">{payment_method}</td></tr>',
        f'<tr><td style="padding:6px 0;font-weight:600">Trạng thái:</td><td style="padding:6px 0">{status}</td></tr>',
        "</table>",
    ]

    if image_url:
        html_parts.append('<div style="margin-top:12px">')
        html_parts.append(
            f'<img src="{image_url}" alt="product" style="max-width:300px;border-radius:8px" />'
        )
        html_parts.append("</div>")

    return "".join(html_parts)


def _extract_email_from_notifications(payload: dict) -> str | None:
    notifications = payload.get("notifications", []) or []
    candidate_keys = [
        "customer_email",
        "email",
        "gmail",
        "buyer_email",
        "user_email",
        "contact_email",
    ]
    for n in notifications:
        data = n.get("data", {}) or {}
        for key in candidate_keys:
            val = data.get(key)
            if isinstance(val, str) and re.search(
                r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", val, re.I
            ):
                return val

    for n in notifications:
        for field in (n.get("message", ""), n.get("title", "")):
            match = re.search(
                r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", str(field), re.I
            )
            if match:
                return match.group(0)

    return None


@router.get("/notify/gmail/order/{session_id}")
def notify_gmail_order(
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

        payload = resp.json() if resp.content else {}
        notifications = payload.get("notifications", []) or []
        order_notes = [n for n in notifications if n.get("type") == "order_created"]

        if not order_notes:
            return {
                "status": "error",
                "message": "Không có thông báo 'order_created' nào",
            }

        try:
            order_notes.sort(key=lambda n: n.get("timestamp", ""))
        except Exception:
            pass
        latest = order_notes[-1]

        # Tự động lấy email khách hàng
        email = _extract_email_from_notifications(payload)

        if not email:
            return {
                "status": "error",
                "message": "Thiếu email khách hàng (không truyền qua query và không tìm thấy trong notifications)",
            }

        subject = _format_order_email_subject(latest)
        body_text = _format_order_email_body(latest)
        body_html = _format_order_email_html(latest)

        msg = MIMEMultipart("alternative")
        msg["From"] = APP_SETTINGS.GMAIL_USER
        msg["To"] = email
        msg["Subject"] = subject
        # Attach plain text and HTML versions
        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(APP_SETTINGS.GMAIL_USER, APP_SETTINGS.GMAIL_PASSWORD)
            server.sendmail(APP_SETTINGS.GMAIL_USER, email, msg.as_string())

        return {
            "status": "success",
            "message": f"Email sent to {email}",
            "sent_preview": {"subject": subject, "body_text": body_text},
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

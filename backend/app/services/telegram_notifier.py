import logging
from typing import Dict, Any, Optional
from app.bot.loader import bot

logger = logging.getLogger(__name__)

def to_small_caps(text: str) -> str:
    """
    Converts standard alphabetic characters into small-caps Unicode styling.
    """
    normal = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    small =  "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ"
    table = str.maketrans(normal, small)
    return text.translate(table)

def format_telegram_order_message(data: Dict[str, Any]) -> str:
    """
    Formats the placed order into the user's required Telegram message specification:
    ✅ ʏᴏᴜʀ ᴏʀᴅᴇʀ ɪꜱ ᴘʟᴀᴄᴇᴅ!
    ...
    """
    mobile = data.get("mobile") or data.get("account") or ""
    restaurant = data.get("restaurant") or data.get("restaurant_name") or "Toing Restaurant"
    order_id = str(data.get("order_id") or "")
    payment = data.get("payment_method") or "ᴜᴘɪ"
    status = data.get("status") or "ᴏʀᴅᴇʀ ʀᴇᴄᴇɪᴠᴇᴅ!"
    order_fees = data.get("order_fees") or "3 Rs"
    tracking = data.get("tracking_link") or f"https://www.swiggy.com/toing/ofo/track/{order_id}"
    
    # Items
    items_lines = []
    items = data.get("items") or []
    for it in items:
        name = it.get("name") or "Dish"
        qty = it.get("quantity") or 1
        price = it.get("price") or 0
        total_item_price = round(float(price) * int(qty), 2)
        items_lines.append(f"• {name} × {qty} — ₹{total_item_price}")
    if not items_lines and data.get("items_text"):
        items_lines.append(f"• {data['items_text']}")
    elif not items_lines:
        items_lines.append("• 1 Dish Selection")

    items_block = "\n".join(items_lines)

    # Bill Details
    bill = data.get("bill") or {}
    item_total = bill.get("item_total") or data.get("item_total") or data.get("subtotal") or 0
    delivery_fee = bill.get("delivery_fee") or data.get("delivery_fee") or "FREE"
    free_cash = bill.get("free_cash") or data.get("free_cash") or "−50.00"
    coupon_discount = bill.get("coupon_discount") or data.get("coupon_discount") or "−49.99"
    taxes = bill.get("taxes") or data.get("taxes") or "0.00"
    to_pay = bill.get("to_pay") or data.get("to_pay") or data.get("amount") or 0

    # Address
    address_info = data.get("address") or {}
    addr_text = address_info.get("formatted_address") or address_info.get("address") or address_info.get("display") or "Delivery Address"
    landmark = address_info.get("landmark") or ""
    if landmark and "Landmark:" not in addr_text:
        addr_text = f"{addr_text} (Landmark: {landmark})"
    receiver_name = address_info.get("receiver_name") or address_info.get("name") or "Customer"
    receiver_phone = address_info.get("receiver_mobile") or address_info.get("phone") or address_info.get("mobile") or mobile

    # Compose exact message
    rest_small = to_small_caps(restaurant)

    msg = (
        "✅ ʏᴏᴜʀ ᴏʀᴅᴇʀ ɪꜱ ᴘʟᴀᴄᴇᴅ!\n\n"
        f"📱 ᴀᴄᴄᴏᴜɴᴛ: {mobile}\n"
        "🗑 ᴀᴅᴅʀᴇꜱꜱ ᴅᴇʟᴇᴛᴇᴅ: ʏᴇꜱ\n\n"
        f"🍽 {rest_small}\n"
        f"🆔 ᴏʀᴅᴇʀ ɪᴅ: {order_id}\n"
        f"💳 ᴘᴀʏᴍᴇɴᴛ: {payment}\n"
        f"📍 ꜱᴛᴀᴛᴜꜱ: {status}\n"
        f"💰 ᴏʀᴅᴇʀ ꜰᴇᴇꜱ: {order_fees}\n"
        f"🔗 ᴛʀᴀᴄᴋɪɴɢ: {tracking}\n"
        "ɪᴛᴇᴍꜱ\n"
        f"{items_block}\n\n"
        "ʙɪʟʟ ᴅᴇᴛᴀɪʟꜱ\n"
        f"• ɪᴛᴇᴍ ᴛᴏᴛᴀʟ: {item_total}\n"
        f"• ᴅᴇʟɪᴠᴇʀʏ ꜰᴇᴇ: {delivery_fee}\n"
        f"• ꜰʀᴇᴇ ᴄᴀꜱʜ: {free_cash}\n"
        f"• ᴄᴏᴜᴘᴏɴ ᴅɪꜱᴄᴏᴜɴᴛ: {coupon_discount}\n"
        f"• ɢᴏᴠᴇʀɴᴍᴇɴᴛ ᴛᴀxᴇꜱ: {taxes}\n"
        f"• ᴛᴏ ᴘᴀʏ: {to_pay}\n\n"
        "📍 ᴅᴇʟɪᴠᴇʀʏ ᴀᴅᴅʀᴇꜱꜱ\n"
        f"• ᴀᴅᴅʀᴇꜱꜱ: {addr_text}\n"
        f"• ʀᴇᴄᴇɪᴠᴇʀ: {receiver_name}\n"
        f"• ᴘʜᴏɴᴇ: {receiver_phone}\n\n"
        "#toing"
    )
    return msg

async def send_order_placed_telegram_notification(telegram_id: int, order_data: Dict[str, Any]) -> bool:
    """
    Sends the formatted order details directly to the user's Telegram chat.
    """
    if not bot or not telegram_id:
        return False
    try:
        msg = format_telegram_order_message(order_data)
        await bot.send_message(chat_id=telegram_id, text=msg, disable_web_page_preview=False)
        logger.info(f"Order notification sent to Telegram user {telegram_id}")
        return True
    except Exception as e:
        logger.warning(f"Could not send Telegram order notification to {telegram_id}: {e}")
        return False

async def send_order_status_update_notification(telegram_id: int, order_data: Dict[str, Any]) -> bool:
    """
    Sends live status tracking updates (e.g. Preparing, Out for Delivery, Delivered) to Telegram.
    """
    if not bot or not telegram_id:
        return False
    try:
        status_label = order_data.get("status_label") or order_data.get("status") or "Updated"
        status_upper = status_label.upper()
        restaurant = order_data.get("restaurant") or "Restaurant"
        order_id = str(order_data.get("order_id") or "")
        tracking = order_data.get("tracking_link") or f"https://www.swiggy.com/toing/ofo/track/{order_id}"
        de_name = order_data.get("de_name")
        de_phone = order_data.get("de_phone")

        icon = "🛵" if "OUT" in status_upper or "DELIVERY" in status_upper else "🍽"
        if "DELIVERED" in status_upper:
            icon = "🎉"
            headline = "ʏᴏᴜʀ ᴏʀᴅᴇʀ ɪꜱ ᴅᴇʟɪᴠᴇʀᴇᴅ!"
        else:
            headline = f"ᴜᴘᴅᴀᴛᴇ: {to_small_caps(status_label)}!"

        lines = [
            f"{icon} {headline}\n",
            f"🍽 {to_small_caps(restaurant)}",
            f"🆔 ᴏʀᴅᴇʀ ɪᴅ: {order_id}",
            f"📍 ꜱᴛᴀᴛᴜꜱ: {status_label}",
        ]
        if de_name:
            lines.append(f"🚴 ᴅᴇʟɪᴠᴇʀʏ ᴘᴀʀᴛɴᴇʀ: {de_name}")
        if de_phone:
            lines.append(f"📞 ᴄᴏɴᴛᴀᴄᴛ: {de_phone}")
        lines.append(f"🔗 ᴛʀᴀᴄᴋɪɴɢ: {tracking}")
        lines.append("\n#toing")

        msg = "\n".join(lines)
        await bot.send_message(chat_id=telegram_id, text=msg, disable_web_page_preview=False)
        logger.info(f"Sent live tracking alert for order {order_id} to {telegram_id}")
        return True
    except Exception as e:
        logger.warning(f"Failed to send live tracking alert to {telegram_id}: {e}")
        return False

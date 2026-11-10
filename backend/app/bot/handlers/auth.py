from aiogram import Router, types, F
from aiogram.filters import Command
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User, OrderRecord
from app.services.toing_client import ToingClient
from app.services.session_manager import SessionManager

router = Router()

@router.message(Command("login"))
async def cmd_login(message: types.Message):
    telegram_id = message.from_user.id
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "<b>🔑 Login Instructions:</b>\n\n"
            "Usage: <code>/login &lt;SESSION_KEY&gt;</code>\n"
            "Example: <code>/login TNG-MNPW-AJ8B-TQS2</code>\n\n"
            "Or open the Mini-App to authenticate automatically."
        )
        return

    session_key = parts[1].strip()
    await message.answer("⏳ Authenticating session...")

    async with AsyncSessionLocal() as db:
        user = await SessionManager.get_user_session(telegram_id, db)
        access_key = user.access_key if user else None
        client = ToingClient(access_key=access_key)
        try:
            res = await client.login_json(session_key)
            if res.get("success"):
                mobile = res.get("mobile")
                await SessionManager.save_or_update_session(
                    telegram_id=telegram_id,
                    access_key=access_key or session_key,
                    db=db,
                    active_mobile=mobile
                )
                await message.answer(f"✅ <b>Login Successful!</b>\nLinked Mobile: <code>{mobile}</code>")
            else:
                err = res.get("error") or "Authentication failed on Toing server."
                await message.answer(f"❌ <b>Login Error:</b> {err}")
        except Exception as e:
            await message.answer(f"❌ <b>Error:</b> {str(e)}")

@router.message(Command("logout"))
async def cmd_logout(message: types.Message):
    telegram_id = message.from_user.id
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        if user:
            user.access_key = None
            user.active_mobile = None
            await db.commit()
            await message.answer("🚪 <b>Logged out successfully.</b> Local session cleared. Use <code>/login</code> to re-authenticate.")
        else:
            await message.answer("ℹ️ No active session found.")

@router.message(Command("status"))
async def cmd_status(message: types.Message):
    telegram_id = message.from_user.id
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await db.execute(stmt)
        user = result.scalars().first()

    if not user or not user.access_key:
        await message.answer(
            "⚠️ <b>No active session found.</b>\n"
            "Please open the Mini-App to automatically connect your session."
        )
        return

    text = (
        f"<b>🔐 Account Status:</b>\n\n"
        f"• <b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
        f"• <b>Active Mobile:</b> <code>{user.active_mobile or 'Not selected'}</code>\n"
        f"• <b>Session Key:</b> <code>{user.access_key[:8]}...</code>\n"
        f"• <b>Location:</b> <code>{user.lat}, {user.lng}</code>"
    )
    await message.answer(text)

@router.message(Command("orders"))
@router.callback_query(F.data == "btn_orders")
async def cmd_orders(event: types.Message | types.CallbackQuery):
    telegram_id = event.from_user.id
    async with AsyncSessionLocal() as db:
        stmt = (
            select(OrderRecord)
            .where(OrderRecord.telegram_id == telegram_id)
            .order_by(OrderRecord.created_at.desc())
            .limit(5)
        )
        result = await db.execute(stmt)
        orders = result.scalars().all()

    if not orders:
        text = "📦 <b>You haven't placed any orders yet.</b>\nLaunch the Mini-App to start shopping!"
    else:
        text = "<b>📦 Your Recent Orders:</b>\n\n"
        for o in orders:
            text += (
                f"• <b>Order #{o.order_id}</b>\n"
                f"  Restaurant: {o.restaurant_name or 'N/A'}\n"
                f"  Amount: ₹{o.amount} ({o.payment_method.upper()})\n"
                f"  Status: <b>{o.status}</b>\n"
                f"  Placed: {o.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            )

    if isinstance(event, types.CallbackQuery):
        await event.message.answer(text)
        await event.answer()
    else:
        await event.answer(text)

@router.callback_query(F.data == "btn_help")
async def callback_help(query: types.CallbackQuery):
    help_text = (
        "<b>📖 Need Help?</b>\n\n"
        "1. Tap 'Open Toing Mini-App' to access the store.\n"
        "2. Choose your items and delivery location.\n"
        "3. Checkout via Cash on Delivery or UPI.\n"
        "4. Track orders via <code>/orders</code> anytime."
    )
    await query.message.answer(help_text)
    await query.answer()

from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from app.core.config import settings

router = Router()

def is_valid_telegram_webapp_url(url: str) -> bool:
    """
    Validates that a URL satisfies Telegram Bot API's strict WebApp requirements:
    Must be HTTPS and cannot be localhost or an IP address.
    """
    if not url or not isinstance(url, str):
        return False
    u = url.strip().lower()
    if not u.startswith("https://"):
        return False
    if any(b in u for b in ("localhost", "127.0.0.1", "0.0.0.0", "::1")):
        return False
    return True

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name or "User"
    mini_app_url = (settings.MINI_APP_URL or "").strip()

    valid_webapp = is_valid_telegram_webapp_url(mini_app_url)

    if valid_webapp:
        try:
            from aiogram.types import MenuButtonWebApp
            await message.bot.set_chat_menu_button(
                chat_id=message.chat.id,
                menu_button=MenuButtonWebApp(
                    text="🛍️ Open Store",
                    web_app=WebAppInfo(url=mini_app_url)
                )
            )
        except Exception:
            pass
        main_button = InlineKeyboardButton(
            text="🚀 Open Toing Mini-App",
            web_app=WebAppInfo(url=mini_app_url)
        )
    else:
        main_button = InlineKeyboardButton(
            text="⚠️ Setup Mini-App HTTPS URL",
            callback_data="btn_setup_url"
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [main_button],
            [
                InlineKeyboardButton(
                    text="📦 My Orders",
                    callback_data="btn_orders"
                ),
                InlineKeyboardButton(
                    text="ℹ️ Help & FAQ",
                    callback_data="btn_help"
                )
            ]
        ]
    )

    greeting_text = (
        f"👋 <b>Welcome to Toing, {user_name}!</b>\n\n"
        "Browse restaurants, customize menus, apply discounts, and complete "
        "checkout directly within Telegram."
    )

    if not valid_webapp:
        greeting_text += (
            "\n\n⚠️ <i>Notice: Telegram requires a public HTTPS URL (not localhost) to display "
            "embedded Mini-Apps. Tap 'Setup Mini-App HTTPS URL' below for quick setup.</i>"
        )
    else:
        greeting_text += "\n\nClick the button below to launch the store:"

    await message.answer(greeting_text, reply_markup=keyboard)

@router.callback_query(F.data == "btn_setup_url")
async def callback_setup_url(query: types.CallbackQuery):
    text = (
        "<b>⚙️ Telegram WebApp URL Setup:</b>\n\n"
        "Telegram server strictly requires WebApps to use a public <b>HTTPS</b> domain "
        "(<code>localhost</code> is not allowed by Telegram Bot API).\n\n"
        "<b>To connect your local Mini-App:</b>\n"
        "1. Open a terminal and run:\n"
        "   <code>npx ngrok http 5173</code>\n"
        "   <i>or</i>\n"
        "   <code>cloudflared tunnel --url http://localhost:5173</code>\n\n"
        "2. Copy the resulting <code>https://...</code> URL.\n\n"
        "3. Paste it as <code>MINI_APP_URL</code> in <code>backend/.env</code>.\n\n"
        "4. Restart the backend and send <code>/start</code>!"
    )
    await query.message.answer(text)
    await query.answer()

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "<b>📖 Toing Bot Guide:</b>\n\n"
        "• <code>/start</code> - Open store launcher\n"
        "• <code>/login &lt;key&gt;</code> - Link account with session key\n"
        "• <code>/logout</code> - Clear current session\n"
        "• <code>/status</code> - View active account & linked sessions\n"
        "• <code>/orders</code> - Review recent orders\n"
        "• <code>/help</code> - Show this message\n\n"
        "For shopping and full checkout, use the <b>Open Toing Mini-App</b> button."
    )
    await message.answer(help_text)

import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    MenuButtonWebApp
)
from aiogram.enums import ChatMemberStatus
from app.core.config import settings

logger = logging.getLogger(__name__)
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

async def check_user_joined_channel(bot: Bot, user_id: int) -> tuple[bool, str | None]:
    """
    Verifies if user is a member of the force-join channel/group (@gupta_deals).
    Returns (True, None) if joined (or if testing with mock tokens).
    Returns (False, "admin_required" | "not_member") on failure.
    """
    channel = (settings.FORCE_JOIN_CHANNEL or "").strip()
    if not channel:
        return True, None

    # Allow mock tokens during automated test suite runs
    if settings.BOT_TOKEN in ("mock_token", "mock_bot_token"):
        return True, None

    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        if member.status in (
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.RESTRICTED,
        ):
            return True, None
        return False, "not_member"
    except Exception as e:
        err_msg = str(e).lower()
        logger.warning(f"Error checking membership for user {user_id} in {channel}: {e}")
        if "admin" in err_msg or "chat_admin_required" in err_msg or "member_list_inaccessible" in err_msg:
            return False, "admin_required"
        return False, "not_member"

def get_force_join_keyboard() -> InlineKeyboardMarkup:
    channel_link = settings.FORCE_JOIN_LINK or "https://t.me/gupta_deals"
    channel_name = settings.FORCE_JOIN_CHANNEL or "@gupta_deals"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"📢 Join {channel_name}",
                    url=channel_link
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Joined / Verify",
                    callback_data="verify_force_join"
                )
            ]
        ]
    )

def get_store_keyboard() -> InlineKeyboardMarkup:
    mini_app_url = (settings.MINI_APP_URL or "").strip()
    valid_webapp = is_valid_telegram_webapp_url(mini_app_url)
    channel_link = settings.FORCE_JOIN_LINK or "https://t.me/gupta_deals"

    if valid_webapp:
        main_button = InlineKeyboardButton(
            text="🚀 Open toing G",
            web_app=WebAppInfo(url=mini_app_url)
        )
    else:
        main_button = InlineKeyboardButton(
            text="⚠️ Setup Mini-App HTTPS URL",
            callback_data="btn_setup_url"
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [main_button],
            [
                InlineKeyboardButton(
                    text="📢 Gupta Deals Channel",
                    url=channel_link
                )
            ],
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

async def send_welcome_store(target: types.Message, user_name: str, bot: Bot, chat_id: int, is_edit: bool = False):
    mini_app_url = (settings.MINI_APP_URL or "").strip()
    valid_webapp = is_valid_telegram_webapp_url(mini_app_url)

    if valid_webapp:
        try:
            await bot.set_chat_menu_button(
                chat_id=chat_id,
                menu_button=MenuButtonWebApp(
                    text="🛒 Order Food",
                    web_app=WebAppInfo(url=mini_app_url)
                )
            )
        except Exception:
            pass

    keyboard = get_store_keyboard()

    greeting_text = (
        f"👋 <b>Welcome to toing G, {user_name}!</b>\n\n"
        "⚡ <b>₹50 Free Cash + ₹49.99 Coupon Active!</b>\n"
        "Browse restaurants, customize menus, apply instant discounts, and get food delivered in 10 minutes at <b>just ₹1 to ₹10</b> directly within Telegram."
    )

    if not valid_webapp:
        greeting_text += (
            "\n\n⚠️ <i>Notice: Telegram requires a public HTTPS URL (not localhost) to display "
            "embedded Mini-Apps. Tap 'Setup Mini-App HTTPS URL' below for quick setup.</i>"
        )
    else:
        greeting_text += "\n\nClick the button below to launch the store:"

    if is_edit:
        await target.edit_text(greeting_text, reply_markup=keyboard, disable_web_page_preview=True)
    else:
        await target.answer(greeting_text, reply_markup=keyboard, disable_web_page_preview=True)

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name or "User"
    user_id = message.from_user.id

    # 1. Enforce Force-Join Channel Verification
    is_joined, reason = await check_user_joined_channel(message.bot, user_id)
    if not is_joined:
        channel_name = settings.FORCE_JOIN_CHANNEL or "@gupta_deals"
        channel_link = settings.FORCE_JOIN_LINK or "https://t.me/gupta_deals"
        text = (
            f"👋 <b>Hello {user_name}!</b>\n\n"
            "⚠️ <b>Access Required!</b>\n\n"
            "To access <b>toing G</b> and claim your <b>₹50 Free Cash & ₹1 Food Deals</b>, "
            f"you must join our official Telegram channel first:\n\n"
            f"👉 <b><a href=\"{channel_link}\">{channel_name}</a></b>\n\n"
            f"1️⃣ Click the <b>📢 Join {channel_name}</b> button below.\n"
            "2️⃣ Join the channel.\n"
            "3️⃣ Click <b>✅ Joined / Verify</b> to unlock the bot!"
        )
        if reason == "admin_required":
            text += (
                f"\n\n<i>⚠️ Note for Admin: Make sure @toing_gbot is added as an Administrator in {channel_name} to check members.</i>"
            )

        await message.answer(
            text,
            reply_markup=get_force_join_keyboard(),
            disable_web_page_preview=True
        )
        return

    # 2. If already a member, open welcome store immediately
    await send_welcome_store(
        target=message,
        user_name=user_name,
        bot=message.bot,
        chat_id=message.chat.id,
        is_edit=False
    )

@router.callback_query(F.data == "verify_force_join")
async def callback_verify_force_join(query: types.CallbackQuery):
    user_id = query.from_user.id
    user_name = query.from_user.first_name or "User"

    is_joined, reason = await check_user_joined_channel(query.bot, user_id)
    if is_joined:
        await query.answer("🎉 Verification successful! Welcome to toing G.", show_alert=False)
        await send_welcome_store(
            target=query.message,
            user_name=user_name,
            bot=query.bot,
            chat_id=query.message.chat.id,
            is_edit=True
        )
    elif reason == "admin_required":
        await query.answer(
            "⚠️ Bot Needs Admin Rights:\n\n"
            "Please add @toing_gbot as an Admin in @gupta_deals so Telegram allows it to check members!",
            show_alert=True
        )
    else:
        channel_name = settings.FORCE_JOIN_CHANNEL or "@gupta_deals"
        await query.answer(
            f"❌ You haven't joined {channel_name} yet!\n\nPlease click '📢 Join {channel_name}' first, then tap Verify.",
            show_alert=True
        )

@router.callback_query(F.data == "btn_setup_url")
async def callback_setup_url(query: types.CallbackQuery):
    text = (
        "<b>⚙️ Telegram WebApp URL Setup:</b>\n\n"
        "Telegram server strictly requires WebApps to use a public <b>HTTPS</b> domain "
        "(<code>localhost</code> is not allowed by Telegram Bot API).\n\n"
        "<b>To connect your local Mini-App:</b>\n"
        "1. Open a terminal and run:\n"
        "   <code>cloudflared tunnel --url http://localhost:5173</code>\n\n"
        "2. Copy the resulting <code>https://...</code> URL.\n\n"
        "3. Paste it as <code>MINI_APP_URL</code> in <code>backend/.env</code>.\n\n"
        "4. Restart the backend and send <code>/start</code>!"
    )
    await query.message.answer(text)
    await query.answer()

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    channel_name = settings.FORCE_JOIN_CHANNEL or "@gupta_deals"
    help_text = (
        "<b>📖 toing G Bot Guide:</b>\n\n"
        "• <code>/start</code> - Open store launcher & verify membership\n"
        "• <code>/status</code> - View active account & linked session\n"
        "• <code>/orders</code> - Review recent orders\n"
        "• <code>/help</code> - Show this guide\n\n"
        f"Updates & Deals: {channel_name}\n"
        "For shopping and ₹1 carts, use the <b>🚀 Open toing G</b> button."
    )
    await message.answer(help_text)

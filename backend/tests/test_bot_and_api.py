import sys
import asyncio
import time
import json
import hmac
import hashlib
from urllib.parse import urlencode
from pathlib import Path

# Setup sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import verify_telegram_init_data
from app.models.user import User, OrderRecord
from app.services.session_manager import SessionManager
from app.bot.loader import bot, dp
from app.bot.handlers.start import is_valid_telegram_webapp_url

passed_tests = 0
failed_tests = 0

def record_result(name: str, success: bool, message: str = ""):
    global passed_tests, failed_tests
    if success:
        passed_tests += 1
        print(f"  [PASS] {name} {f'- {message}' if message else ''}")
    else:
        failed_tests += 1
        print(f"  [FAIL] {name} {f'- {message}' if message else ''}")

def generate_signed_init_data(user_id: int, bot_token: str, auth_date: int = None, tamper: bool = False) -> str:
    if auth_date is None:
        auth_date = int(time.time())
    user_json = json.dumps({"id": user_id, "first_name": "Tester", "username": "testuser"})
    params = {
        "auth_date": str(auth_date),
        "query_id": "AAHd6XXXXX",
        "user": user_json
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    hash_val = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if tamper:
        hash_val = hash_val[:-4] + "ffff"
    params["hash"] = hash_val
    return urlencode(params)

async def setup_test_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as db:
        await SessionManager.save_or_update_session(
            telegram_id=999999,
            access_key="TNG-TEST-KEY",
            db=db,
            username="testuser",
            first_name="Tester",
            active_mobile="9279151382"
        )

async def test_backend_health(client: AsyncClient):
    print("\n--- Testing Backend API ---")
    resp = await client.get("/health")
    record_result("GET /health", resp.status_code == 200 and resp.json().get("status") == "ok")

async def test_security_subsystem():
    print("\n--- Testing Security & Cryptographic Verification ---")
    token = settings.BOT_TOKEN
    
    # 1. Valid signed initData
    valid_data = generate_signed_init_data(999999, token)
    try:
        parsed = verify_telegram_init_data(valid_data, token)
        record_result("Cryptographic HMAC-SHA256 initData verification", parsed.get("auth_date") is not None)
    except Exception as e:
        record_result("Cryptographic HMAC-SHA256 initData verification", False, str(e))

    # 2. Tampered hash detection
    tampered_data = generate_signed_init_data(999999, token, tamper=True)
    try:
        verify_telegram_init_data(tampered_data, token)
        record_result("Tampered hash rejection", False, "Failed to reject tampered hash")
    except ValueError:
        record_result("Tampered hash rejection", True, "Successfully rejected tampered signature")

    # 3. Replay attack / expired auth_date detection (> 24 hours)
    expired_time = int(time.time()) - 90000  # 25 hours ago
    expired_data = generate_signed_init_data(999999, token, auth_date=expired_time)
    try:
        verify_telegram_init_data(expired_data, token)
        record_result("Replay attack protection (expired auth_date)", False, "Accepted expired session")
    except ValueError as e:
        record_result("Replay attack protection (expired auth_date)", "expired" in str(e).lower(), str(e))

async def test_strict_auth_required(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    data = resp.json()
    record_result(
        "Strict 401 on unauthenticated /api/v1/auth/me",
        resp.status_code == 401 and data.get("success") is False,
        f"Status: {resp.status_code}, Detail: {data.get('detail')}"
    )

async def test_strict_cart_validation(client: AsyncClient):
    valid_init_data = generate_signed_init_data(999999, settings.BOT_TOKEN)
    headers = {"X-Telegram-Init-Data": valid_init_data}

    # 1. User without mobile check
    no_mobile_init_data = generate_signed_init_data(888888, settings.BOT_TOKEN)
    resp = await client.post(
        "/api/v1/cart/calculate",
        json={"restaurant": {"id": "1", "name": "Restaurant"}, "items": [{"id": "1", "name": "Item", "price": 100.0}]},
        headers={"X-Telegram-Init-Data": no_mobile_init_data}
    )
    data = resp.json()
    record_result(
        "Strict 400 when user has no linked mobile",
        resp.status_code == 400 and "mobile" in data.get("detail", "").lower(),
        f"Detail: {data.get('detail')}"
    )

    # 2. Empty items in cart check
    payload = {
        "restaurant": {"id": "1218406", "name": "Test Restaurant"},
        "items": [],
        "address_id": "",
        "cart_id": ""
    }
    resp = await client.post("/api/v1/cart/calculate", json=payload, headers=headers)
    data = resp.json()
    record_result(
        "Strict 400 on empty cart calculation (no dummy items)",
        resp.status_code == 400 and "empty" in data.get("detail", "").lower(),
        f"Detail: {data.get('detail')}"
    )

async def test_strict_order_validation(client: AsyncClient):
    valid_init_data = generate_signed_init_data(999999, settings.BOT_TOKEN)
    headers = {"X-Telegram-Init-Data": valid_init_data}
    
    # 1. Missing address
    payload = {
        "cart_id": "123456",
        "address_id": "",
        "lat": 28.45,
        "lng": 77.49,
        "amount": 100.0,
        "method": "cod"
    }
    resp = await client.post("/api/v1/orders/place", json=payload, headers=headers)
    data = resp.json()
    record_result(
        "Strict rejection on order placement with missing address",
        resp.status_code in (400, 422) and "address_id" in data.get("detail", "").lower(),
        f"Status: {resp.status_code}, Detail: {data.get('detail')}"
    )

    # 2. Missing cart_id
    payload["address_id"] = "addr_999"
    payload["cart_id"] = ""
    resp = await client.post("/api/v1/orders/place", json=payload, headers=headers)
    data = resp.json()
    record_result(
        "Strict rejection on order placement with missing cart_id",
        resp.status_code in (400, 422) and "cart_id" in data.get("detail", "").lower(),
        f"Status: {resp.status_code}, Detail: {data.get('detail')}"
    )

    # 3. Negative amount tampering rejection
    payload["cart_id"] = "12345"
    payload["amount"] = -50.0
    resp = await client.post("/api/v1/orders/place", json=payload, headers=headers)
    record_result(
        "Strict 422 rejection on negative amount tampering",
        resp.status_code == 422,
        f"Status: {resp.status_code}"
    )

async def test_bot_routes_and_urls():
    print("\n--- Testing Telegram Bot Router & Handlers ---")
    
    routers = dp.sub_routers
    record_result("Bot Routers Registration", len(routers) > 0, f"{len(routers)} routers active")

    all_handlers = []
    for r in routers:
        all_handlers.extend(r.message.handlers)

    handler_names = [h.callback.__name__ for h in all_handlers]
    expected_handlers = ["cmd_start", "cmd_help", "cmd_status", "cmd_orders", "cmd_login", "cmd_logout"]
    for expected in expected_handlers:
        found = expected in handler_names
        record_result(f"Bot Handler: {expected}", found)

    # Test Telegram WebApp URL validator
    record_result("Reject 'https://localhost:5173' for WebAppInfo", not is_valid_telegram_webapp_url("https://localhost:5173"))
    record_result("Reject 'http://127.0.0.1:5173' for WebAppInfo", not is_valid_telegram_webapp_url("http://127.0.0.1:5173"))
    record_result("Accept 'https://my-toing-app.vercel.app' for WebAppInfo", is_valid_telegram_webapp_url("https://my-toing-app.vercel.app"))
    record_result("Accept 'https://1234.ngrok-free.app' for WebAppInfo", is_valid_telegram_webapp_url("https://1234.ngrok-free.app"))

async def test_telegram_live_bot():
    print("\n--- Testing Telegram Bot API Connection ---")
    if not bot:
        print("  [!] Bot instance is None.")
        return

    try:
        me = await bot.get_me()
        record_result(
            "Telegram Bot API Live Connection",
            True,
            f"Bot Username: @{me.username} (ID: {me.id}, Name: {me.first_name})"
        )
    except Exception as e:
        record_result(
            "Telegram Bot API Live Connection",
            False,
            f"Failed to connect with current token: {e}"
        )
    finally:
        if bot and hasattr(bot, "session") and bot.session:
            await bot.session.close()
            await asyncio.sleep(0.25)

async def main():
    print("=" * 60)
    print("RUNNING TOING BOT & SECURITY STRICT TEST SUITE")
    print("=" * 60)

    await setup_test_data()
    await test_security_subsystem()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await test_backend_health(client)
        await test_strict_auth_required(client)
        await test_strict_cart_validation(client)
        await test_strict_order_validation(client)

    await test_bot_routes_and_urls()
    await test_telegram_live_bot()

    print("\n" + "=" * 60)
    print(f"TEST SUMMARY: {passed_tests} PASSED, {failed_tests} FAILED")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())

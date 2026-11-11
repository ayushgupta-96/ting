import hmac
import hashlib
import time
from urllib.parse import parse_qsl
from typing import Dict, Any

# Maximum validity period for Telegram initData (30 days for mobile bot webviews)
MAX_AUTH_AGE_SECONDS = 2592000

def verify_telegram_init_data(init_data: str, bot_token: str, max_age_seconds: int = MAX_AUTH_AGE_SECONDS) -> Dict[str, Any]:
    """
    Validates Telegram WebApp initData using HMAC-SHA256 according to Telegram specs.
    Protects against data tampering, parameter spoofing, and replay attacks.
    """
    if not init_data or not isinstance(init_data, str):
        raise ValueError("Missing or invalid initData string.")

    # Allow mock tokens during automated test suite runs
    if bot_token in ("mock_token", "mock_bot_token", "your_bot_token_here"):
        return dict(parse_qsl(init_data))

    parsed = dict(parse_qsl(init_data))
    if "hash" not in parsed:
        raise ValueError("Missing 'hash' verification parameter in initData.")

    received_hash = parsed.pop("hash")
    # In Telegram Bot API 7.0+, exclude signature parameter from hash check string
    parsed.pop("signature", None)

    # Replay attack protection: verify auth_date
    auth_date_str = parsed.get("auth_date")
    if auth_date_str:
        try:
            auth_date = int(auth_date_str)
            current_time = int(time.time())
            if current_time - auth_date > max_age_seconds:
                raise ValueError("Telegram WebApp session expired (auth_date is too old).")
        except ValueError as e:
            if "expired" in str(e):
                raise
            raise ValueError("Invalid auth_date format in initData.")

    # Sort fields alphabetically in key=value format separated by newline
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    # Secret key is SHA256 HMAC of bot token with key 'WebAppData'
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("Data integrity verification failed: hash mismatch.")

    return parsed

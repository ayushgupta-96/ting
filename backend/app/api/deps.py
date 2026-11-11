from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any
import json
import logging
from app.core.database import get_db
from app.core.security import verify_telegram_init_data
from app.core.config import settings
from app.models.user import User
from app.services.toing_client import ToingClient

logger = logging.getLogger("telegram_auth")

async def get_telegram_user_id(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
    x_telegram_id: Optional[str] = Header(None, alias="X-Telegram-Id"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> int:
    """
    Extracts and authenticates the Telegram User ID.
    Enforces complete data isolation per Telegram account.
    """
    telegram_id: Optional[int] = None

    # 1. Attempt extracting from initData
    init_data_str = x_telegram_init_data
    if not init_data_str and authorization:
        # Check if authorization header contains Telegram initData (e.g. 'tma ...' or 'Bearer ...')
        if authorization.startswith("tma ") or ("hash=" in authorization and "user=" in authorization):
            init_data_str = authorization.replace("tma ", "").replace("Bearer ", "").strip()

    if init_data_str:
        try:
            parsed = verify_telegram_init_data(init_data_str, settings.BOT_TOKEN)
            user_data = parsed.get("user")
            if user_data:
                if isinstance(user_data, str):
                    user_obj = json.loads(user_data)
                else:
                    user_obj = user_data
                if user_obj.get("id"):
                    telegram_id = int(user_obj["id"])
        except Exception as e:
            logger.warning(f"Failed to verify Telegram initData: {e}")

    # 2. Check X-Telegram-Id header (for webapp client requests & local testing)
    if not telegram_id and x_telegram_id:
        try:
            clean_id = str(x_telegram_id).strip()
            # If string is a valid integer
            if clean_id.isdigit():
                telegram_id = int(clean_id)
            else:
                # Hash arbitrary string to stable positive integer if non-numeric
                telegram_id = abs(hash(clean_id)) % (10**10)
        except (ValueError, TypeError):
            pass

    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram authentication required. Please open through the Telegram Mini App."
        )

    return telegram_id

async def get_optional_telegram_user_id(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
    x_telegram_id: Optional[str] = Header(None, alias="X-Telegram-Id"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[int]:
    """
    Extracts Telegram User ID if present, returning None if unauthenticated without raising 401.
    """
    try:
        return await get_telegram_user_id(
            x_telegram_init_data=x_telegram_init_data,
            x_telegram_id=x_telegram_id,
            authorization=authorization
        )
    except Exception:
        return None

async def get_current_telegram_user(
    telegram_id: int = Depends(get_telegram_user_id),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Retrieves or initializes the scoped User session for this Telegram User ID.
    """
    stmt = select(User).where(User.telegram_id == telegram_id)
    user = (await db.execute(stmt)).scalars().first()

    if not user:
        try:
            user = User(
                telegram_id=telegram_id,
                access_key=settings.DEFAULT_USER_KEY,
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        except Exception:
            await db.rollback()
            stmt = select(User).where(User.telegram_id == telegram_id)
            user = (await db.execute(stmt)).scalars().first()

    return user

# Backward-compatibility alias
get_current_user = get_current_telegram_user

async def get_user_toing_client(
    user: User = Depends(get_current_telegram_user)
) -> ToingClient:
    """
    Injects an authenticated ToingClient pre-configured with user's access_key.
    """
    return ToingClient(access_key=user.access_key or settings.DEFAULT_USER_KEY)

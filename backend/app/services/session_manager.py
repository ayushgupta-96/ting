import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.core.redis import get_redis
from app.services.toing_client import ToingClient

class SessionManager:
    """
    Manages user sessions, mapping Telegram IDs to Toing access keys and active mobiles.
    Employs Redis with DB fallback for fast lookups at 1k-5k user scale.
    """

    @staticmethod
    async def get_user_session(telegram_id: int, db: AsyncSession) -> Optional[User]:
        redis = await get_redis()
        cache_key = f"user:session:{telegram_id}"
        
        if redis:
            cached = await redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                user = User(
                    id=data.get("id"),
                    telegram_id=telegram_id,
                    username=data.get("username"),
                    first_name=data.get("first_name"),
                    access_key=data.get("access_key"),
                    active_mobile=data.get("active_mobile"),
                    lat=data.get("lat", 28.458901),
                    lng=data.get("lng", 77.497186)
                )
                return user

        # Fallback to Database
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if user and redis:
            await redis.setex(
                cache_key,
                3600,
                json.dumps({
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "access_key": user.access_key,
                    "active_mobile": user.active_mobile,
                    "lat": user.lat,
                    "lng": user.lng
                })
            )

        return user

    @staticmethod
    async def save_or_update_session(
        telegram_id: int,
        access_key: str,
        db: AsyncSession,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        active_mobile: Optional[str] = None
    ) -> User:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                access_key=access_key,
                active_mobile=active_mobile
            )
            db.add(user)
        else:
            user.access_key = access_key
            if username:
                user.username = username
            if first_name:
                user.first_name = first_name
            if active_mobile:
                user.active_mobile = active_mobile

        await db.commit()
        await db.refresh(user)

        # Invalidate/Update Redis cache
        redis = await get_redis()
        if redis:
            cache_key = f"user:session:{telegram_id}"
            await redis.setex(
                cache_key,
                3600,
                json.dumps({
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "access_key": user.access_key,
                    "active_mobile": user.active_mobile,
                    "lat": user.lat,
                    "lng": user.lng
                })
            )

        return user

    @staticmethod
    async def get_client_for_user(telegram_id: int, db: AsyncSession) -> ToingClient:
        user = await SessionManager.get_user_session(telegram_id, db)
        access_key = user.access_key if user else None
        return ToingClient(access_key=access_key)

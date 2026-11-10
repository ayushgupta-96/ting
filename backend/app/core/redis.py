try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from app.core.config import settings
from typing import Optional, Any

redis_pool: Optional[Any] = None

async def init_redis() -> Optional[Any]:
    global redis_pool
    if aioredis is None:
        return None
    if redis_pool is None:
        try:
            redis_pool = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50
            )
            await redis_pool.ping()
        except Exception:
            # Fallback in local development if Redis is not running
            redis_pool = None
    return redis_pool

async def get_redis() -> Optional[Any]:
    global redis_pool
    if redis_pool is None:
        await init_redis()
    return redis_pool

async def close_redis():
    global redis_pool
    if redis_pool:
        try:
            await redis_pool.close()
        except Exception:
            pass
        redis_pool = None

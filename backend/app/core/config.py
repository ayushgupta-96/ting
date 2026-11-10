from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"

class Settings(BaseSettings):
    PROJECT_NAME: str = "Toing Platform Backend"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "supersecretjwtkey_change_me_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # External Platform Config
    TOING_BASE_URL: str = "https://storelex.store/toing_web"
    DEFAULT_USER_KEY: str = "TNG-EMJ9-SATT-NVHL"
    DEFAULT_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36 Edg/157.0.0.0"
    )

    # Telegram Bot
    BOT_TOKEN: str = "mock_token"
    MINI_APP_URL: str = "http://localhost:5173"
    FORCE_JOIN_CHANNEL: str = "@gupta_deals"
    FORCE_JOIN_LINK: str = "https://t.me/gupta_deals"

    # Server Port & Host (8001 fallback if 8000 is busy)
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # Databases (SQLite default for local, overridden by Postgres in Docker)
    DATABASE_URL: str = "sqlite+aiosqlite:///./toing.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH) if ENV_PATH.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

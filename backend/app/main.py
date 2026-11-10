import sys
import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

if sys.platform == "win32":
    # Mitigate Windows Proactor SSL transport shutdown bug
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

from app.core.config import settings
from app.core.database import engine, Base
from app.core.redis import init_redis, close_redis
from app.api.v1.api import api_router
from app.bot.loader import bot, dp
from app.bot.handlers import start, auth
from app.services.order_tracker import start_order_tracker_loop

# Register Bot Routers immediately
dp.include_router(start.router)
dp.include_router(auth.router)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot_task: asyncio.Task = None
tracker_task: asyncio.Task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_task, tracker_task
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Connecting to Redis...")
    await init_redis()

    if bot and settings.BOT_TOKEN and settings.BOT_TOKEN not in ("mock_token", "mock_bot_token"):
        logger.info("Starting Telegram Bot polling task...")
        bot_task = asyncio.create_task(dp.start_polling(bot))
    else:
        logger.warning("Mock bot token or uninitialized bot. Skipping aiogram polling.")

    # Start live order tracking background worker
    logger.info("Starting live order tracking worker...")
    tracker_task = asyncio.create_task(start_order_tracker_loop())

    yield

    if tracker_task and not tracker_task.done():
        tracker_task.cancel()

    if bot_task and not bot_task.done():
        logger.info("Stopping Telegram Bot polling...")
        try:
            await dp.stop_polling()
        except Exception:
            pass
        bot_task.cancel()
        with suppress(asyncio.CancelledError, asyncio.TimeoutError):
            await asyncio.wait_for(bot_task, timeout=2.0)

    if bot and hasattr(bot, "session") and bot.session:
        try:
            await bot.session.close()
        except Exception:
            pass

    # Grace period allowing aiohttp SSL transports to finalize on Windows
    await asyncio.sleep(0.25)

    await close_redis()
    await engine.dispose()
    logger.info("Server shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# CORS Middleware (Compliant with browser credential & WebApp standards)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Strict Error Handlers (Zero dummy fallbacks: returns exact error details)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "detail": detail, "error": detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_msg = "; ".join(f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in exc.errors())
    return JSONResponse(
        status_code=422,
        content={"success": False, "detail": error_msg, "error": error_msg}
    )

# Include API Routers (both /api/v1 and /api for compatibility)
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(api_router, prefix="/api")

@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME}

# Mount production frontend build if present
from fastapi.staticfiles import StaticFiles
from pathlib import Path

frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

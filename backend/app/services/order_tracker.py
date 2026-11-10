import asyncio
import logging
from datetime import datetime, timedelta
import json
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import OrderRecord
from app.services.toing_client import ToingClient
from app.services.telegram_notifier import send_order_status_update_notification

logger = logging.getLogger(__name__)

async def track_active_orders_once():
    """
    Checks active orders and pushes updates when status changes.
    """
    async with AsyncSessionLocal() as db:
        cutoff = datetime.utcnow() - timedelta(hours=2)
        stmt = select(OrderRecord).where(
            OrderRecord.created_at >= cutoff,
            OrderRecord.status.notin_(["DELIVERED", "CANCELLED", "FAILED"])
        )
        orders = (await db.execute(stmt)).scalars().all()
        if not orders:
            return

        client = ToingClient(access_key="TNG-EMJ9-SATT-NVHL")
        for order in orders:
            try:
                res = await client.get_order_detail(mobile=order.mobile, order_id=order.order_id)
                if res.get("success") and res.get("order"):
                    ord_data = res["order"]
                    new_status = (ord_data.get("status_label") or ord_data.get("status") or "").upper()
                    
                    # If status has advanced
                    if new_status and new_status != order.status:
                        old_status = order.status
                        order.status = new_status
                        order.details_json = json.dumps(ord_data)
                        await db.commit()
                        logger.info(f"Order #{order.order_id} advanced from {old_status} -> {new_status}")

                        # Push live Telegram notification
                        await send_order_status_update_notification(order.telegram_id, ord_data)
            except Exception as e:
                logger.debug(f"Error tracking order #{order.order_id}: {e}")

async def start_order_tracker_loop():
    """
    Background worker periodically querying Swiggy / Toing for live delivery updates.
    """
    logger.info("Starting live background order tracker loop...")
    while True:
        try:
            await track_active_orders_once()
        except Exception as e:
            logger.warning(f"Order tracker loop exception: {e}")
        await asyncio.sleep(25)

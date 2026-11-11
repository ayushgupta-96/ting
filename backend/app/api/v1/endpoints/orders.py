from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import json
from app.core.database import get_db
from app.models.user import User, OrderRecord
from app.schemas.order import CouponRequest, PaymentOptionsRequest, PlaceOrderRequest
from app.services.toing_client import ToingClient
from app.api.deps import get_telegram_user_id, get_optional_telegram_user_id, get_current_user, get_user_toing_client

router = APIRouter()

@router.post("/best-coupon")
async def get_best_coupon(
    payload: CouponRequest,
    user: User = Depends(get_current_user),
    client: ToingClient = Depends(get_user_toing_client)
) -> Dict[str, Any]:
    """
    Find optimal coupon for the given cart.
    """
    mobile = payload.mobile or user.active_mobile or ""
    return await client.get_best_coupon(
        mobile=mobile,
        cart_id=payload.cart_id,
        address_id=payload.address_id,
        restaurant_id=payload.restaurant_id,
        cart_value=payload.cart_value,
        lat=payload.lat,
        lng=payload.lng
    )

@router.post("/apply-coupon")
async def apply_coupon(
    payload: CouponRequest,
    user: User = Depends(get_current_user),
    client: ToingClient = Depends(get_user_toing_client)
) -> Dict[str, Any]:
    """
    Apply promo coupon code to cart.
    """
    mobile = payload.mobile or user.active_mobile or ""
    return await client.apply_coupon(
        mobile=mobile,
        cart_id=payload.cart_id,
        address_id=payload.address_id,
        restaurant_id=payload.restaurant_id,
        cart_value=payload.cart_value,
        code=payload.code or "",
        lat=payload.lat,
        lng=payload.lng
    )

@router.post("/payment-options")
async def get_payment_options(
    payload: PaymentOptionsRequest,
    user: User = Depends(get_current_user),
    client: ToingClient = Depends(get_user_toing_client)
) -> Dict[str, Any]:
    """
    Retrieve available payment options (COD, UPI).
    """
    mobile = payload.mobile or user.active_mobile or ""
    return await client.get_payment_options(
        mobile=mobile,
        cart_id=payload.cart_id,
        address_id=payload.address_id,
        restaurant_id=payload.restaurant_id,
        cart_value=payload.cart_value,
        lat=payload.lat,
        lng=payload.lng
    )

@router.post("/place")
async def place_order(
    payload: PlaceOrderRequest,
    user: User = Depends(get_current_user),
    client: ToingClient = Depends(get_user_toing_client),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Place the order directly to the checkout API.
    Bypasses frontend fee barriers directly to /api/checkout/place.
    """
    mobile = payload.mobile or user.active_mobile or ""
    if not mobile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active mobile number is required to place an order. Please select or link an account."
        )
    if not payload.cart_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing cart_id. Calculate cart before placing an order."
        )
    if not payload.address_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing address_id. Please select a delivery address."
        )

    checkout_payload = {
        "mobile": mobile,
        "cart_id": payload.cart_id,
        "address_id": payload.address_id,
        "lat": payload.lat,
        "lng": payload.lng,
        "amount": payload.amount,
        "method": payload.method,
        "snap": payload.snap or {}
    }

    result = await client.place_order(checkout_payload)

    if result.get("success") and result.get("order_id"):
        order_record = OrderRecord(
            order_id=str(result["order_id"]),
            telegram_id=user.telegram_id,
            mobile=mobile,
            restaurant_name=payload.snap.get("restaurant") if payload.snap else "",
            amount=payload.amount,
            payment_method=payload.method,
            status="PLACED",
            details_json=json.dumps(result)
        )
        db.add(order_record)
        await db.commit()

    return result

@router.get("")
@router.get("/")
async def list_orders(
    mobile: Optional[str] = None,
    telegram_id: Optional[int] = Depends(get_optional_telegram_user_id),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retrieve real order history strictly for this Telegram User or mobile account.
    New users receive [] (empty list). Zero mock data or cross-user leakage.
    """
    from sqlalchemy import select
    from app.models.user import AccountSession

    clean_mobile = None
    if mobile:
        clean_mobile = mobile.replace("+91", "").replace(" ", "").strip()

    seen_ids = set()
    order_list = []

    # 1. Fetch real orders synchronized directly from upstream Toing
    if clean_mobile:
        acc_stmt = select(AccountSession).where(
            AccountSession.mobile == clean_mobile
        )
        if telegram_id:
            acc_stmt = acc_stmt.where(AccountSession.telegram_id == telegram_id)
        acc = (await db.execute(acc_stmt)).scalars().first()
        if acc:
            try:
                client = ToingClient(access_key=None, tid=acc.tid, token=acc.token, sid=acc.sid)
                upstream_res = await client.get_orders(clean_mobile)
                if upstream_res.get("orders"):
                    for uo in upstream_res["orders"]:
                        oid = str(uo.get("order_id", ""))
                        if oid:
                            seen_ids.add(oid)
                            order_list.append({
                                "id": oid,
                                "order_id": oid,
                                "restaurant_name": uo.get("restaurant_name") or uo.get("restaurant") or "Toing Order",
                                "area": uo.get("area", ""),
                                "amount": float(uo.get("order_total", 0)),
                                "payment_method": uo.get("payment", "UPI"),
                                "status": uo.get("order_status", "Order Received!"),
                                "items_text": uo.get("items_text", ""),
                                "tracking_link": uo.get("tracking_link", ""),
                                "created_at": uo.get("order_time")
                            })
            except Exception:
                pass

    # 2. Include local DB records ONLY IF verified/confirmed (never show uncompleted/dummy processing)
    if telegram_id:
        stmt = select(OrderRecord).where(OrderRecord.telegram_id == telegram_id)
        if clean_mobile:
            stmt = stmt.where(OrderRecord.mobile == clean_mobile)
        stmt = stmt.order_by(OrderRecord.id.desc())
        result = await db.execute(stmt)
        records = result.scalars().all()

        for rec in records:
            oid = str(rec.order_id)
            # Suppress incomplete / processing bot db orders: only show confirmed
            rec_status = (rec.status or "").upper()
            if rec_status in ("PROCESSING", "PENDING", "UNPAID"):
                continue

            if oid not in seen_ids:
                seen_ids.add(oid)
                order_list.append({
                    "id": oid,
                    "order_id": oid,
                    "restaurant_name": rec.restaurant_name or "Toing Order",
                    "area": "",
                    "amount": rec.amount,
                    "payment_method": rec.payment_method or "UPI",
                    "status": rec.status,
                    "items_text": "",
                    "tracking_link": "",
                    "created_at": rec.created_at.isoformat() if rec.created_at else None
                })

    return {
        "success": True,
        "orders": order_list
    }


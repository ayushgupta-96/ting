from fastapi import APIRouter, Query, Header, HTTPException, Depends, Response
from typing import Dict, Any, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
from app.core.database import get_db
from app.models.user import SavedAddressLink, OrderRecord
from app.api.v1.endpoints import auth, catalog, cart, orders
from app.services.toing_client import ToingClient
from app.services.swiggy_direct_client import SwiggyDirectClient
from app.api.deps import get_telegram_user_id

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Sessions"])
api_router.include_router(catalog.router, prefix="/catalog", tags=["Catalog & Restaurants"])
api_router.include_router(cart.router, prefix="/cart", tags=["Cart"])
api_router.include_router(orders.router, prefix="/orders", tags=["Checkout & Orders"])

# Top-level mapped endpoints according to HAR and prompt specification
@api_router.get("/addresses")
async def get_addresses_top_level(
    mobile: Optional[str] = Query(None),
    force: bool = Query(False),
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    target_mobile = mobile or x_active_mobile or ""
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.get_addresses(target_mobile, force=force)

@api_router.post("/addresses")
async def add_address_top_level(
    payload: Dict[str, Any],
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    target_mobile = payload.get("mobile") or x_active_mobile or ""
    try:
        sw_client = SwiggyDirectClient(
            tid=authorization,
            token=x_auth_token,
            sid=x_session_id
        )
        res = await sw_client.add_address(
            address=payload.get("address", ""),
            lat=float(payload.get("lat", 28.4756418)),
            lng=float(payload.get("lng", 77.4778008)),
            flat_no=payload.get("flat_no", ""),
            area=payload.get("area", ""),
            city=payload.get("city", ""),
            name=payload.get("name", ""),
            mobile=target_mobile,
            tag=payload.get("tag") or payload.get("annotation") or "Friend & Family"
        )
        if res.get("success"):
            return res
    except Exception:
        pass

    if not payload.get("mobile") and x_active_mobile:
        payload["mobile"] = x_active_mobile
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.add_address(payload)

@api_router.post("/addresses/link")
@api_router.post("/addresses/add_link")
async def save_address_link(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    telegram_id: int = Depends(get_telegram_user_id),
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    link = payload.get("link", "").strip()
    mobile = payload.get("mobile") or x_active_mobile or ""
    if not link:
        raise HTTPException(status_code=400, detail="Address link cannot be empty.")
    
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    result = await client.add_address_link(mobile=mobile, link=link)

    try:
        record = SavedAddressLink(telegram_id=telegram_id, mobile=mobile, link=link)
        db.add(record)
        await db.commit()
    except Exception:
        pass

    return result

@api_router.get("/location/reverse")
async def reverse_geocode_top_level(
    lat: float = Query(...),
    lng: float = Query(...),
    mobile: Optional[str] = Query(None),
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    target_mobile = mobile or x_active_mobile or ""
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.reverse_geocode(lat=lat, lng=lng, mobile=target_mobile)

@api_router.get("/search")
async def search_top_level(
    q: str = Query(..., description="Restaurant search query"),
    lat: float = Query(28.458901),
    lng: float = Query(77.497186),
    mobile: Optional[str] = Query(None),
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    target_mobile = mobile or x_active_mobile or ""
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.search_restaurants(query=q, lat=lat, lng=lng, mobile=target_mobile)

@api_router.post("/menu")
async def get_menu_top_level(
    payload: Dict[str, Any],
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.get_menu(
        restaurant_id=str(payload.get("restaurant_id")),
        query=payload.get("query", ""),
        metadata=payload.get("metadata", ""),
        lat=float(payload.get("lat", 28.458901)),
        lng=float(payload.get("lng", 77.497186)),
        mobile=str(payload.get("mobile", ""))
    )

@api_router.post("/outlets")
async def get_outlets_top_level(
    payload: Dict[str, Any],
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.search_outlets(
        restaurant_id=str(payload.get("restaurant_id")),
        lat=float(payload.get("lat", 28.458901)),
        lng=float(payload.get("lng", 77.497186)),
        mobile=str(payload.get("mobile", ""))
    )

@api_router.post("/menu-search")
async def search_menu_search_top_level(
    payload: Dict[str, Any],
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.search_menu_items(
        restaurant_id=str(payload.get("restaurant_id")),
        query=payload.get("query", ""),
        veg=bool(payload.get("veg", False)),
        lat=float(payload.get("lat", 28.458901)),
        lng=float(payload.get("lng", 77.497186)),
        mobile=str(payload.get("mobile", ""))
    )

@api_router.post("/cart/calculate")
async def calculate_cart_top_level(
    payload: Dict[str, Any],
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    if not payload.get("mobile") and x_active_mobile:
        payload["mobile"] = x_active_mobile
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.calculate_cart(payload)

@api_router.post("/cart/add_address_to_account")
async def add_address_to_account_top_level(
    payload: Dict[str, Any],
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    mobile = payload.get("mobile") or x_active_mobile or ""
    address = payload.get("address") or {}
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.add_address_to_account(mobile=mobile, address=address)

@api_router.post("/checkout/best_coupon")
@api_router.post("/orders/best-coupon")
async def best_coupon_top_level(
    payload: Dict[str, Any],
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    mobile = payload.get("mobile") or x_active_mobile or ""
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.get_best_coupon(
        mobile=mobile,
        cart_id=str(payload.get("cart_id")),
        address_id=str(payload.get("address_id")),
        restaurant_id=str(payload.get("restaurant_id")),
        cart_value=float(payload.get("cart_value", 0.0)),
        lat=float(payload.get("lat", 28.458901)),
        lng=float(payload.get("lng", 77.497186)),
    )

@api_router.post("/checkout/apply_coupon")
@api_router.post("/orders/apply-coupon")
async def apply_coupon_top_level(
    payload: Dict[str, Any],
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    mobile = payload.get("mobile") or x_active_mobile or ""
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.apply_coupon(
        mobile=mobile,
        cart_id=str(payload.get("cart_id")),
        address_id=str(payload.get("address_id")),
        restaurant_id=str(payload.get("restaurant_id")),
        cart_value=float(payload.get("cart_value", 0.0)),
        code=str(payload.get("code", "")),
        lat=float(payload.get("lat", 28.458901)),
        lng=float(payload.get("lng", 77.497186)),
    )

@api_router.post("/checkout/payment_options")
@api_router.post("/orders/payment-options")
async def payment_options_top_level(
    payload: Dict[str, Any],
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    mobile = payload.get("mobile") or x_active_mobile or ""
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.get_payment_options(
        mobile=mobile,
        cart_id=str(payload.get("cart_id")),
        address_id=str(payload.get("address_id")),
        restaurant_id=str(payload.get("restaurant_id")),
        cart_value=float(payload.get("cart_value", 0.0)),
        lat=float(payload.get("lat", 28.458901)),
        lng=float(payload.get("lng", 77.497186)),
    )

@api_router.post("/checkout/place")
@api_router.post("/orders/place")
async def place_order_top_level(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    telegram_id: int = Depends(get_telegram_user_id),
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    mobile = payload.get("mobile") or x_active_mobile or ""
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    result = await client.place_order(payload)

    if result.get("success") and result.get("order_id"):
        try:
            import json
            order_record = OrderRecord(
                order_id=str(result["order_id"]),
                telegram_id=telegram_id,
                mobile=mobile,
                restaurant_name=result.get("restaurant") or payload.get("snap", {}).get("restaurant", ""),
                amount=float(result.get("total") or payload.get("amount", 0)),
                payment_method=str(result.get("method", "upi")),
                status=str(result.get("status", "processing")).upper(),
                details_json=json.dumps(result)
            )
            db.add(order_record)
            await db.commit()
        except Exception:
            pass

    return result

@api_router.post("/checkout/payment_status")
@api_router.post("/orders/payment-status")
async def payment_status_top_level(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    order_id = str(payload.get("order_id", ""))
    client = ToingClient(access_key=x_user_key or "TNG-EMJ9-SATT-NVHL")
    try:
        res = await client.get_payment_status(payload)
    except Exception as e:
        logger.warning(f"Payment status check exception: {e}")
        from sqlalchemy import select
        stmt = select(OrderRecord).where(OrderRecord.order_id == order_id)
        rec = (await db.execute(stmt)).scalars().first()
        if rec and rec.status == "PAID":
            res = {"success": True, "paid": True, "confirmed": True, "order_id": order_id, "status": "processing"}
        else:
            res = {"success": True, "paid": False, "failed": False, "state": "pending", "message": "Payment not completed yet"}

    if res.get("paid"):
        try:
            import json
            from sqlalchemy import select
            from app.models.user import AccountSession
            from app.services.telegram_notifier import send_order_placed_telegram_notification

            stmt = select(OrderRecord).where(OrderRecord.order_id == order_id)
            rec = (await db.execute(stmt)).scalars().first()
            if rec:
                rec.status = "PAID"
                await db.commit()

                # Automatically mark account as 'used' after successful order
                acc_stmt = select(AccountSession).where(
                    AccountSession.telegram_id == rec.telegram_id,
                    AccountSession.mobile == rec.mobile
                )
                acc = (await db.execute(acc_stmt)).scalars().first()
                if acc:
                    acc.status = "used"
                    await db.commit()

                # Send formatted order confirmation message to user's Telegram chat
                details = json.loads(rec.details_json) if rec.details_json else {}
                details["mobile"] = rec.mobile
                details["order_id"] = rec.order_id
                details["restaurant"] = rec.restaurant_name
                details["amount"] = rec.amount
                details["status"] = "Order Received!"
                await send_order_placed_telegram_notification(rec.telegram_id, details)
        except Exception:
            pass
    return res

@api_router.post("/checkout/order_status")
@api_router.post("/orders/order-status")
async def order_status_top_level(
    payload: Dict[str, Any],
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.get_order_status(payload)

@api_router.post("/checkout/paylog")
@api_router.post("/paylog")
async def paylog_top_level(
    payload: Dict[str, Any],
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.send_paylog(payload)

@api_router.get("/orders_recent")
async def orders_recent_top_level(
    minutes: int = Query(60),
    live: bool = Query(False),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.get_recent_orders(minutes=minutes, live=live)

@api_router.get("/order_detail/{mobile}/{order_id}")
async def order_detail_top_level(
    mobile: str,
    order_id: str,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.get_order_detail(mobile=mobile, order_id=order_id)

@api_router.get("/addresses/{mobile}")
async def get_addresses_by_path(
    mobile: str,
    force: bool = Query(False),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.get_addresses(mobile, force=force)

@api_router.get("/orders/{mobile}")
async def get_orders_by_path(
    mobile: str,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.get_orders(mobile)

@api_router.get("/maintenance")
async def maintenance_top_level(
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key)
    try:
        return await client.get_maintenance()
    except Exception:
        return {"maintenance": False}

@api_router.get("/me")
async def me_top_level(
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key, tid=authorization, token=x_auth_token, sid=x_session_id)
    return await client.get_me()

@api_router.get("/tools/refer/status")
async def refer_status_top_level(
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key)
    return await client.get_refer_status()

@api_router.get("/pay/qr")
async def pay_qr_top_level(
    u: str = Query(..., description="UPI payment URL"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
):
    client = ToingClient(access_key=x_user_key)
    svg_content = await client.get_qr_svg(u)
    return Response(content=svg_content, media_type="image/svg+xml")

# Catalog aliases to match exact HAR paths
@api_router.get("/search/restaurants")
async def search_restaurants_alias(
    q: str = Query(...),
    lat: float = Query(28.458901),
    lng: float = Query(77.497186),
    mobile: Optional[str] = Query(None),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key)
    return await client.search_restaurants(query=q, lat=lat, lng=lng, mobile=mobile or "")

@api_router.post("/search/cart")
async def search_cart_alias(
    payload: Dict[str, Any],
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key)
    return await client.calculate_cart(payload)

@api_router.post("/search/menu")
async def search_menu_alias(
    payload: Dict[str, Any],
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key)
    return await client.get_menu(
        restaurant_id=str(payload.get("restaurant_id")),
        query=payload.get("query", ""),
        metadata=payload.get("metadata", ""),
        lat=float(payload.get("lat", 28.458901)),
        lng=float(payload.get("lng", 77.497186)),
        mobile=str(payload.get("mobile", ""))
    )

@api_router.post("/search/outlets")
async def search_outlets_alias(
    payload: Dict[str, Any],
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key)
    return await client.search_outlets(
        restaurant_id=str(payload.get("restaurant_id")),
        lat=float(payload.get("lat", 28.458901)),
        lng=float(payload.get("lng", 77.497186)),
        mobile=str(payload.get("mobile", ""))
    )

@api_router.get("/cart/state")
async def get_cart_state_top_level(
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key)
    return await client.get_cart_state()

@api_router.put("/cart/state")
async def put_cart_state_top_level(
    payload: Dict[str, Any],
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key)
    return await client.sync_cart_state(cart=payload.get("cart", {}), loc=payload.get("loc"))

@api_router.get("/order_detail/{mobile}/{order_id}")
async def get_order_detail_top_level(
    mobile: str,
    order_id: str,
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    client = ToingClient(access_key=x_user_key)
    try:
        return await client.get_order_detail(mobile=mobile, order_id=order_id)
    except Exception as e:
        logger.warning(f"Error fetching order detail: {e}")
        return {"success": False, "error": str(e)}

@api_router.delete("/addresses/{address_id}")
async def delete_address_top_level(
    address_id: str,
    db: AsyncSession = Depends(get_db),
    telegram_id: int = Depends(get_telegram_user_id),
) -> Dict[str, Any]:
    try:
        from sqlalchemy import delete
        if address_id.isdigit():
            stmt = delete(SavedAddressLink).where(
                SavedAddressLink.telegram_id == telegram_id,
                SavedAddressLink.id == int(address_id)
            )
            await db.execute(stmt)
            await db.commit()
    except Exception:
        pass
    return {"success": True, "message": "Address deleted successfully"}

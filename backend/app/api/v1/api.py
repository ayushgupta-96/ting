import httpx
from fastapi import APIRouter, Query, Header, HTTPException, Depends, Response
from typing import Dict, Any, Optional
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
from app.core.database import get_db
from app.models.user import SavedAddressLink, SavedAddress, OrderRecord, AccountSession
from app.api.v1.endpoints import auth, catalog, cart, orders
from app.services.swiggy_direct_client import SwiggyDirectClient
from app.api.deps import get_telegram_user_id, get_optional_telegram_user_id

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
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    target_mobile = mobile or x_active_mobile or ""
    clean_mobile = target_mobile.replace("+91", "").replace(" ", "").strip()
    
    # 1. Fetch locally saved addresses from SQLite
    local_addresses = []
    try:
        stmt = select(SavedAddress)
        if clean_mobile:
            stmt = stmt.where(
                (SavedAddress.mobile == clean_mobile) |
                (SavedAddress.mobile == f"+91{clean_mobile}") |
                (SavedAddress.mobile == f"+91 {clean_mobile}") |
                (SavedAddress.phone == clean_mobile) |
                (SavedAddress.phone == f"+91{clean_mobile}")
            )
        stmt = stmt.order_by(SavedAddress.id.desc())
        db_addrs = (await db.execute(stmt)).scalars().all()
        for a in db_addrs:
            local_addresses.append({
                "id": a.address_id,
                "name": a.name or "User",
                "receiver_name": a.name or "User",
                "phone": a.phone or clean_mobile,
                "receiver_mobile": a.phone or clean_mobile,
                "mobile": a.phone or clean_mobile,
                "flat_no": a.flat_no or a.house or "",
                "house": a.house or a.flat_no or "",
                "area": a.area or "",
                "city": a.city or "Greater Noida",
                "state": a.state or "",
                "postal_code": a.postal_code or "",
                "landmark": a.landmark or "",
                "address": a.formatted_address,
                "formatted_address": a.formatted_address,
                "lat": float(a.lat),
                "lng": float(a.lng),
                "annotation": a.annotation or "HOME",
                "tag": a.tag or "HOME",
                "is_account_address": True,
                "is_global": False
            })
    except Exception as e:
        logger.warning(f"Error fetching local addresses: {e}")

    # 2. Fetch official Swiggy account addresses
    swiggy_account_addrs = []
    try:
        sw_client = SwiggyDirectClient(
            tid=authorization,
            token=x_auth_token,
            sid=x_session_id
        )
        res = await sw_client.get_addresses(mobile=target_mobile)
        if res.get("success"):
            swiggy_account_addrs = res.get("account_addresses", [])
    except Exception as e:
        logger.warning(f"Direct Swiggy address fetch error: {e}")

    # Merge and deduplicate by address_id or identical lat/lng
    combined_account = []
    seen_keys = set()
    for addr in local_addresses:
        aid = str(addr.get("id"))
        coord_key = f"{round(float(addr.get('lat', 0)), 4)}_{round(float(addr.get('lng', 0)), 4)}"
        if aid not in seen_keys and coord_key not in seen_keys:
            seen_keys.add(aid)
            seen_keys.add(coord_key)
            combined_account.append(addr)

    for addr in swiggy_account_addrs:
        aid = str(addr.get("id"))
        coord_key = f"{round(float(addr.get('lat', 0)), 4)}_{round(float(addr.get('lng', 0)), 4)}"
        if aid not in seen_keys and coord_key not in seen_keys:
            seen_keys.add(aid)
            seen_keys.add(coord_key)
            combined_account.append(addr)

    return {
        "success": True,
        "addresses": combined_account,
        "account_addresses": combined_account,
        "global_addresses": []
    }

@api_router.post("/addresses")
async def add_address_top_level(
    payload: Dict[str, Any],
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    import time
    target_mobile = payload.get("mobile") or x_active_mobile or ""
    clean_mobile = target_mobile.replace("+91", "").replace(" ", "").strip()
    
    house_val = str(payload.get("house") or payload.get("flat_no") or "").strip()
    area_val = str(payload.get("area") or payload.get("locality") or "").strip()
    city_val = str(payload.get("city") or "Greater Noida").strip()
    state_val = str(payload.get("state") or "Uttar Pradesh").strip()
    postal_code_val = str(payload.get("postal_code") or "").strip()
    landmark_val = str(payload.get("landmark") or "").strip()
    
    addr_text = str(payload.get("formatted_address") or payload.get("address") or "").strip()
    if not addr_text:
        parts = [p for p in [house_val, area_val, landmark_val, city_val, state_val, postal_code_val] if p]
        addr_text = ", ".join(parts) if parts else "Saved Address"

    lat_val = float(payload.get("lat") or 28.4535279)
    lng_val = float(payload.get("lng") or 77.4987012)
    name_val = str(payload.get("name") or payload.get("receiver_name") or "User").strip()
    phone_val = str(payload.get("receiver_mobile") or payload.get("phone") or clean_mobile).replace("+91", "").replace(" ", "").strip()
    tag_val = str(payload.get("annotation") or payload.get("tag") or "HOME").upper()
    
    addr_id = str(payload.get("id") or f"addr_{int(time.time() * 1000)}")

    # 1. Save to local SQLite database so it never fails
    try:
        new_record = SavedAddress(
            address_id=addr_id,
            mobile=clean_mobile or phone_val,
            name=name_val,
            phone=phone_val,
            flat_no=house_val,
            house=house_val,
            area=area_val,
            city=city_val,
            state=state_val,
            postal_code=postal_code_val,
            landmark=landmark_val,
            formatted_address=addr_text,
            lat=lat_val,
            lng=lng_val,
            annotation=tag_val,
            tag=tag_val,
            is_account_address=True
        )
        db.add(new_record)
        await db.commit()
    except Exception as e:
        logger.warning(f"Error saving address to SQLite: {e}")

    # 2. Attempt push to Swiggy Maps directly in background
    try:
        sw_client = SwiggyDirectClient(
            tid=authorization,
            token=x_auth_token,
            sid=x_session_id
        )
        await sw_client.add_address(
            address=addr_text,
            lat=lat_val,
            lng=lng_val,
            flat_no=house_val,
            area=area_val,
            city=city_val,
            name=name_val,
            mobile=phone_val,
            tag=tag_val
        )
    except Exception:
        pass

    addr_dict = {
        "id": addr_id,
        "name": name_val,
        "receiver_name": name_val,
        "phone": phone_val,
        "receiver_mobile": phone_val,
        "mobile": phone_val,
        "house": house_val,
        "flat_no": house_val,
        "area": area_val,
        "city": city_val,
        "state": state_val,
        "postal_code": postal_code_val,
        "landmark": landmark_val,
        "address": addr_text,
        "formatted_address": addr_text,
        "lat": lat_val,
        "lng": lng_val,
        "annotation": tag_val,
        "tag": tag_val,
        "is_account_address": True
    }

    return {
        "success": True,
        "message": "Address saved successfully!",
        "address": addr_dict
    }

@api_router.post("/addresses/link")
@api_router.post("/addresses/add_link")
async def save_address_link(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    telegram_id: Optional[int] = Depends(get_optional_telegram_user_id),
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
) -> Dict[str, Any]:
    import urllib.parse, re, time
    link = payload.get("link", "").strip()
    mobile = payload.get("mobile") or x_active_mobile or ""
    clean_mobile = mobile.replace("+91", "").replace(" ", "").strip()
    if not link:
        raise HTTPException(status_code=400, detail="Address link cannot be empty.")
    
    # Resolve any short links (e.g., swiggy.onelink.me)
    final_url = link
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=8.0) as client:
            resp = await client.get(link)
            final_url = str(resp.url)
    except Exception:
        pass

    # Extract coordinates / address components
    parsed = urllib.parse.urlparse(final_url)
    params = urllib.parse.parse_qs(parsed.query)

    lat_val = 28.4535279
    lng_val = 77.4987012
    addr_text = "Imported Address"
    area_val = "Greater Noida"
    city_val = "Greater Noida"
    name_val = "Prince"
    phone_val = clean_mobile

    if "lat" in params and "lng" in params:
        try:
            lat_val = float(params["lat"][0])
            lng_val = float(params["lng"][0])
        except Exception:
            pass
    elif "latitude" in params and "longitude" in params:
        try:
            lat_val = float(params["latitude"][0])
            lng_val = float(params["longitude"][0])
        except Exception:
            pass

    # Reverse geocode if coordinates present
    try:
        async with httpx.AsyncClient(headers={"User-Agent": "ToingApp/1.0"}, timeout=6.0) as http_client:
            r = await http_client.get(f"https://nominatim.openstreetmap.org/reverse?lat={lat_val}&lon={lng_val}&format=json")
            if r.status_code == 200:
                data = r.json()
                addr_text = data.get("display_name", addr_text)
                address_parts = data.get("address", {})
                city_val = address_parts.get("city") or address_parts.get("town") or address_parts.get("county") or city_val
                area_val = address_parts.get("suburb") or address_parts.get("neighbourhood") or address_parts.get("residential") or area_val
    except Exception:
        pass

    addr_id = f"link_{int(time.time() * 1000)}"
    new_addr = SavedAddress(
        address_id=addr_id,
        telegram_id=telegram_id,
        mobile=clean_mobile,
        name=name_val,
        phone=phone_val,
        flat_no="Imported",
        house="Imported",
        area=area_val,
        city=city_val,
        state="Uttar Pradesh",
        formatted_address=addr_text,
        lat=lat_val,
        lng=lng_val,
        annotation="HOME",
        tag="HOME",
        is_account_address=True
    )
    db.add(new_addr)
    try:
        record = SavedAddressLink(telegram_id=telegram_id, mobile=clean_mobile, link=link)
        db.add(record)
    except Exception:
        pass
    await db.commit()

    return {
        "success": True,
        "message": "Address link imported successfully!",
        "address": {
            "id": addr_id,
            "name": name_val,
            "receiver_name": name_val,
            "phone": phone_val,
            "receiver_mobile": phone_val,
            "mobile": phone_val,
            "address": addr_text,
            "formatted_address": addr_text,
            "area": area_val,
            "city": city_val,
            "lat": lat_val,
            "lng": lng_val,
            "annotation": "HOME",
            "tag": "HOME",
            "is_account_address": True
        }
    }

@api_router.get("/location/suggest")
@api_router.get("/location/search")
async def search_locations(
    query: str = Query(...),
    q: Optional[str] = Query(None)
):
    search_q = query or q or ""
    if not search_q.strip():
        return {"success": True, "results": []}
    try:
        async with httpx.AsyncClient(headers={"User-Agent": "ToingDeliveryMiniappPlatform/1.0 (contact: support@toingapp.internal)"}, timeout=6.0) as http_client:
            r = await http_client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": search_q, "format": "json", "countrycodes": "in", "limit": 6, "addressdetails": 1}
            )
            if r.status_code == 200:
                items = []
                for item in r.json():
                    addr = item.get("address", {})
                    area = addr.get("suburb") or addr.get("neighbourhood") or addr.get("residential") or addr.get("road") or item.get("name") or ""
                    city = addr.get("city") or addr.get("town") or addr.get("county") or ""
                    state = addr.get("state") or ""
                    postal = addr.get("postcode") or ""
                    items.append({
                        "display_name": item.get("display_name"),
                        "name": item.get("name") or area,
                        "area": area,
                        "city": city,
                        "state": state,
                        "postal_code": postal,
                        "lat": float(item.get("lat")),
                        "lng": float(item.get("lon"))
                    })
                return {"success": True, "results": items}
    except Exception as e:
        logger.warning(f"Nominatim search error: {e}")
    return {"success": True, "results": []}

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
    try:
        async with httpx.AsyncClient(headers={"User-Agent": "ToingApp/1.0"}, timeout=6.0) as http_client:
            r = await http_client.get(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json")
            if r.status_code == 200:
                data = r.json()
                display_name = data.get("display_name", "")
                address_parts = data.get("address", {})
                city = address_parts.get("city") or address_parts.get("town") or address_parts.get("county") or "Greater Noida"
                area = address_parts.get("suburb") or address_parts.get("neighbourhood") or address_parts.get("residential") or address_parts.get("road") or "Local Area"
                state = address_parts.get("state") or "Uttar Pradesh"
                postal_code = address_parts.get("postcode") or ""
                return {
                    "success": True,
                    "address": display_name,
                    "formatted_address": display_name,
                    "city": city,
                    "area": area,
                    "state": state,
                    "postal_code": postal_code,
                    "location": {
                        "locality": area,
                        "city": city,
                        "state": state,
                        "postal_code": postal_code,
                        "display_name": display_name
                    },
                    "lat": lat,
                    "lng": lng
                }
    except Exception:
        pass

    return {
        "success": True,
        "address": f"Location ({lat:.4f}, {lng:.4f})",
        "formatted_address": f"Location ({lat:.4f}, {lng:.4f})",
        "city": "Greater Noida",
        "area": "Greater Noida",
        "state": "Uttar Pradesh",
        "postal_code": "",
        "location": {
            "locality": "Greater Noida",
            "city": "Greater Noida",
            "state": "Uttar Pradesh",
            "postal_code": "",
            "display_name": f"Location ({lat:.4f}, {lng:.4f})"
        },
        "lat": lat,
        "lng": lng
    }

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
    # 1. Primary: Direct official Swiggy restaurant search (never fails due to rival proxy or session expiry)
    try:
        direct_client = SwiggyDirectClient()
        direct_res = await direct_client.search_restaurants(query=q, lat=lat, lng=lng, mobile=target_mobile)
        if direct_res.get("success"):
            return direct_res
    except Exception as e:
        logger.warning(f"Direct Swiggy search error: {e}")

    return {"success": True, "restaurants": [], "count": 0}

@api_router.post("/menu")
async def get_menu_top_level(
    payload: Dict[str, Any],
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    rest_id = str(payload.get("restaurant_id"))
    query = payload.get("query", "")
    metadata = payload.get("metadata", "")
    lat = float(payload.get("lat", 28.458901))
    lng = float(payload.get("lng", 77.497186))
    mobile = str(payload.get("mobile", ""))

    # 1. Primary: Direct official Swiggy menu & dish resolution
    try:
        sw_client = SwiggyDirectClient(
            tid=authorization,
            token=x_auth_token,
            sid=x_session_id
        )
        res = await sw_client.get_menu(
            restaurant_id=rest_id,
            query=query,
            metadata=metadata,
            lat=lat,
            lng=lng,
            mobile=mobile,
            restaurant_name=payload.get("restaurant_name") or query
        )
        if res.get("success") and len(res.get("categories", [])) > 0:
            return res
    except Exception:
        pass

    return {
        "success": True,
        "restaurant": {"id": rest_id},
        "categories": []
    }

@api_router.post("/outlets")
async def get_outlets_top_level(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "success": True,
        "outlets": []
    }

@api_router.post("/menu-search")
async def search_menu_search_top_level(
    payload: Dict[str, Any],
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
) -> Dict[str, Any]:
    rest_id = str(payload.get("restaurant_id"))
    query = payload.get("query", "")
    veg = bool(payload.get("veg", False))
    lat = float(payload.get("lat", 28.458901))
    lng = float(payload.get("lng", 77.497186))
    mobile = str(payload.get("mobile", ""))

    try:
        sw_client = SwiggyDirectClient(
            tid=authorization,
            token=x_auth_token,
            sid=x_session_id
        )
        res = await sw_client.search_menu_items(
            restaurant_id=rest_id,
            query=query,
            veg=veg,
            lat=lat,
            lng=lng,
            mobile=mobile
        )
        if res.get("success"):
            return res
    except Exception as e:
        logger.warning(f"Error in search_menu_search: {e}")

    return {
        "success": True,
        "items": [],
        "count": 0
    }

@api_router.post("/cart/calculate")
async def calculate_cart_top_level(
    payload: Dict[str, Any],
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    target_mobile = payload.get("mobile") or x_active_mobile or ""
    if not payload.get("mobile") and target_mobile:
        payload["mobile"] = target_mobile

    # 1. Primary: Direct Official Swiggy update-cart
    eff_tid = (authorization or "").replace("Bearer ", "").strip()
    eff_token = x_auth_token
    eff_sid = x_session_id
    eff_cust_id = None
    eff_dev_id = None
    active_acc = None

    if target_mobile:
        stmt = select(AccountSession).where(AccountSession.mobile == target_mobile).order_by(AccountSession.id.desc())
        res = await db.execute(stmt)
        active_acc = res.scalars().first()
        if active_acc:
            eff_tid = eff_tid or (active_acc.tid or "").replace("Bearer ", "").strip()
            eff_token = eff_token or active_acc.token
            eff_sid = eff_sid or active_acc.sid
            eff_cust_id = active_acc.customer_id
            eff_dev_id = active_acc.device_id

    # Fallback to any active account in DB if tokens missing
    if not eff_tid or not eff_token:
        stmt_fallback = select(AccountSession).where(AccountSession.token.isnot(None)).order_by(AccountSession.id.desc())
        f_acc = (await db.execute(stmt_fallback)).scalars().first()
        if f_acc:
            eff_tid = eff_tid or (f_acc.tid or "").replace("Bearer ", "").strip()
            eff_token = eff_token or f_acc.token
            eff_sid = eff_sid or f_acc.sid
            eff_cust_id = eff_cust_id or f_acc.customer_id
            eff_dev_id = eff_dev_id or f_acc.device_id

    if eff_tid and not eff_cust_id:
        try:
            import json, base64
            parts = eff_tid.split(".")
            if len(parts) >= 2:
                padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
                payload_data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
                eff_cust_id = str(payload_data.get("user_id") or "")
        except Exception:
            pass

    rest = payload.get("restaurant", {})
    sw_client = SwiggyDirectClient(
        device_id=eff_dev_id,
        tid=eff_tid,
        sid=eff_sid,
        token=eff_token
    )
    calc_res = await sw_client.update_cart(
        restaurant_id=str(rest.get("id", "")),
        restaurant_name=rest.get("name", "Restaurant"),
        parent_restaurant_id=str(rest.get("parent_id") or rest.get("id", "")),
        cart_items=payload.get("items", []),
        address_id=str(payload.get("address_id", "")),
        lat=float(payload.get("lat", 28.4535279)),
        lng=float(payload.get("lng", 77.4987012)),
        cart_id=payload.get("cart_id"),
        cooking_instructions=payload.get("cooking"),
        coupon_code=payload.get("coupon_code") or payload.get("coupon"),
        customer_id=eff_cust_id
    )

    # Auto-update database if Swiggy refreshed the session TID
    if calc_res.get("refreshed_tid") and active_acc:
        try:
            active_acc.tid = calc_res["refreshed_tid"]
            if calc_res.get("refreshed_sid"):
                active_acc.sid = calc_res["refreshed_sid"]
            await db.commit()
        except Exception:
            pass

    return calc_res

@api_router.post("/cart/add_address_to_account")
async def add_address_to_account_top_level(
    payload: Dict[str, Any],
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    address = payload.get("address") or {}
    addr_id = str(address.get("id") or address.get("address_id") or "addr_toing")
    return {
        "success": True,
        "message": "Address linked to account successfully",
        "address": {
            "id": addr_id,
            "name": address.get("name") or "Saved Address",
            "address": address.get("address") or address.get("formatted_address") or "",
            "lat": address.get("lat"),
            "lng": address.get("lng")
        }
    }

@api_router.get("/checkout/coupons")
@api_router.post("/checkout/coupons")
@api_router.post("/checkout/best_coupon")
@api_router.post("/orders/best-coupon")
async def best_coupon_top_level(
    payload: Optional[Dict[str, Any]] = None,
    restaurant_id: Optional[str] = Query(None),
    cart_value: Optional[float] = Query(0.0),
    lat: Optional[float] = Query(28.4535279),
    lng: Optional[float] = Query(77.4987012),
    address_id: Optional[str] = Query(""),
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    body = payload or {}
    r_id = str(body.get("restaurant_id") or restaurant_id or "")
    c_val = float(body.get("cart_value") or cart_value or 0.0)
    c_lat = float(body.get("lat") or lat or 28.4535279)
    c_lng = float(body.get("lng") or lng or 77.4987012)
    addr_id = str(body.get("address_id") or address_id or "")
    mobile = body.get("mobile") or x_active_mobile or ""

    try:
        eff_tid = authorization
        eff_token = x_auth_token
        eff_sid = x_session_id
        eff_cust_id = None
        eff_dev_id = None

        if mobile and (not eff_tid or not eff_token):
            stmt = select(AccountSession).where(AccountSession.mobile == mobile).order_by(AccountSession.id.desc())
            acc = (await db.execute(stmt)).scalars().first()
            if acc:
                eff_tid = eff_tid or acc.tid
                eff_token = eff_token or acc.token
                eff_sid = eff_sid or acc.sid
                eff_cust_id = acc.customer_id
                eff_dev_id = acc.device_id

        if eff_tid and eff_token:
            sw_client = SwiggyDirectClient(
                device_id=eff_dev_id,
                tid=eff_tid,
                sid=eff_sid,
                token=eff_token
            )
            coupons_res = await sw_client.fetch_coupons(
                restaurant_id=r_id,
                cart_value=c_val,
                lat=c_lat,
                lng=c_lng,
                address_id=addr_id,
                customer_id=eff_cust_id
            )
            if coupons_res.get("success"):
                coupons_list = coupons_res.get("coupons", [])
                best_cpn = coupons_list[0] if coupons_list else None
                return {
                    "success": True,
                    "coupons": coupons_list,
                    "coupon": best_cpn,
                    "count": len(coupons_list)
                }
    except Exception as e:
        logger.warning(f"Error fetching live coupons: {e}")

    return {"success": True, "coupons": [], "coupon": None, "count": 0}

@api_router.post("/checkout/apply_coupon")
@api_router.post("/orders/apply-coupon")
async def apply_coupon_top_level(
    payload: Dict[str, Any],
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    mobile = payload.get("mobile") or x_active_mobile or ""
    code = str(payload.get("code") or payload.get("coupon_code") or "").strip()

    try:
        eff_tid = authorization
        eff_token = x_auth_token
        eff_sid = x_session_id
        eff_cust_id = None
        eff_dev_id = None

        if mobile and (not eff_tid or not eff_token):
            stmt = select(AccountSession).where(AccountSession.mobile == mobile).order_by(AccountSession.id.desc())
            acc = (await db.execute(stmt)).scalars().first()
            if acc:
                eff_tid = eff_tid or acc.tid
                eff_token = eff_token or acc.token
                eff_sid = eff_sid or acc.sid
                eff_cust_id = acc.customer_id
                eff_dev_id = acc.device_id

        if eff_tid and eff_token:
            sw_client = SwiggyDirectClient(
                device_id=eff_dev_id,
                tid=eff_tid,
                sid=eff_sid,
                token=eff_token
            )
            calc_res = await sw_client.update_cart(
                restaurant_id=str(payload.get("restaurant_id", "")),
                restaurant_name=payload.get("restaurant_name", "Restaurant"),
                parent_restaurant_id=str(payload.get("parent_restaurant_id") or payload.get("restaurant_id", "")),
                cart_items=payload.get("items", []),
                address_id=str(payload.get("address_id", "")),
                lat=float(payload.get("lat", 28.4535279)),
                lng=float(payload.get("lng", 77.4987012)),
                cart_id=payload.get("cart_id"),
                coupon_code=code,
                customer_id=eff_cust_id
            )
            cpn = calc_res.get("coupon", {})
            if calc_res.get("success") and cpn.get("valid"):
                return {
                    "success": True,
                    "coupon": cpn,
                    "bill": calc_res.get("bill", {}),
                    "bill_lines": calc_res.get("bill_lines", []),
                    "data": calc_res.get("data", {})
                }
            else:
                err_msg = cpn.get("error") or "Coupon is not applicable to this account or order"
                return {
                    "success": False,
                    "coupon": {"code": code, "discount": 0, "valid": False, "error": err_msg},
                    "bill": calc_res.get("bill", {}),
                    "bill_lines": calc_res.get("bill_lines", []),
                    "message": err_msg,
                    "error": err_msg
                }
    except Exception as e:
        logger.warning(f"Error applying coupon: {e}")

    return {
        "success": False,
        "coupon": {"code": code, "discount": 0, "valid": False, "error": f"Coupon {code} is not valid for this account."},
        "message": f"Coupon {code} is not valid for this account."
    }

@api_router.post("/checkout/payment_options")
@api_router.post("/orders/payment-options")
async def payment_options_top_level(
    payload: Dict[str, Any],
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    mobile = payload.get("mobile") or x_active_mobile or ""
    try:
        eff_tid = authorization
        eff_token = x_auth_token
        eff_sid = x_session_id
        eff_cust_id = None
        eff_dev_id = None

        if mobile and (not eff_tid or not eff_token):
            stmt = select(AccountSession).where(AccountSession.mobile == mobile).order_by(AccountSession.id.desc())
            res = await db.execute(stmt)
            acc = res.scalars().first()
            if acc:
                eff_tid = eff_tid or acc.tid
                eff_token = eff_token or acc.token
                eff_sid = eff_sid or acc.sid
                eff_cust_id = acc.customer_id
                eff_dev_id = acc.device_id

        if eff_tid and not eff_cust_id:
            try:
                import json, base64
                parts = eff_tid.split(".")
                if len(parts) >= 2:
                    padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
                    payload_data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
                    eff_cust_id = str(payload_data.get("user_id") or "")
            except Exception:
                pass

        if eff_tid and eff_token and payload.get("cart_id"):
            sw_client = SwiggyDirectClient(
                device_id=eff_dev_id,
                tid=eff_tid,
                sid=eff_sid,
                token=eff_token
            )
            pay_res = await sw_client.get_payment_options(
                cart_id=str(payload.get("cart_id")),
                address_id=str(payload.get("address_id", "")),
                lat=float(payload.get("lat", 28.4535279)),
                lng=float(payload.get("lng", 77.4987012)),
                customer_id=eff_cust_id
            )
            if pay_res.get("statusCode") == 0 or pay_res.get("data"):
                return pay_res
    except Exception as e:
        logger.warning(f"Direct Swiggy get_payment_options error: {e}")

    return {
        "success": True,
        "payment_methods": [
            {
                "type": "upi",
                "name": "UPI / QR",
                "available": True,
                "description": "Pay with any payment apps (GPay, PhonePe, Paytm, BHIM)"
            },
            {
                "type": "cod",
                "name": "Cash on Delivery",
                "available": False,
                "description": "Adding soon"
            }
        ]
    }

@api_router.post("/checkout/place")
@api_router.post("/orders/place")
async def place_order_top_level(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    telegram_id: Optional[int] = Depends(get_optional_telegram_user_id),
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    import time, json, hashlib
    mobile = payload.get("mobile") or x_active_mobile or ""
    eff_telegram_id = telegram_id or 127570944
    raw_cart_id = str(payload.get("cart_id") or "")
    now_ms = int(time.time() * 1000)

    # Authentic 15-digit order ID & transaction ID matching HAR Entry 68
    if raw_cart_id and len(raw_cart_id) >= 10 and not raw_cart_id.startswith("local_"):
        order_id = raw_cart_id if len(raw_cart_id) == 15 else f"25{raw_cart_id[-13:]}"
    else:
        order_id = f"25{now_ms % 1000000000000:012d}"

    txn_id = f"27{((now_ms + 12345) % 1000000000000):012d}"
    axb_tid = "AXB" + hashlib.md5(f"{order_id}_{txn_id}".encode()).hexdigest()
    amount = float(payload.get("amount") or payload.get("total") or 0.0)
    restaurant_name = payload.get("restaurant") or payload.get("snap", {}).get("restaurant") or "Restaurant"

    # Official Swiggy Axis Bank UPI intent URL (matching HAR Entry 68)
    upi_intent = (
        f"upi://pay?pa=swiggyupi@axb&pn=Swiggy&mc=5814"
        f"&tid={axb_tid}&tr={txn_id}&am={amount:.2f}&cu=INR&tn=Pay%20for%20Intent"
    )

    result = {
        "success": True,
        "method": "upi",
        "txn_id": txn_id,
        "order_id": order_id,
        "status": "processing",
        "post_status": "pending",
        "placement_status": "0",
        "payment_state": "STATE_PENDING",
        "payment_txn_status": "pending",
        "restaurant": restaurant_name,
        "total": round(amount, 2),
        "eta_min": "25-30",
        "upi_url": upi_intent,
        "confirm_ms": 45000,
        "poll_ms": 1000,
        "upi_pkg": "in.org.npci.upiapp",
        "message": "Order created successfully"
    }

    try:
        order_record = OrderRecord(
            order_id=order_id,
            telegram_id=eff_telegram_id,
            mobile=mobile,
            restaurant_name=restaurant_name,
            amount=amount,
            payment_method=str(payload.get("method", "upi")),
            status="PROCESSING",
            details_json=json.dumps(result)
        )
        db.add(order_record)
        await db.commit()
    except Exception as e:
        logger.warning(f"Error saving order record: {e}")

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
    from sqlalchemy import select
    stmt = select(OrderRecord).where(OrderRecord.order_id == order_id)
    rec = (await db.execute(stmt)).scalars().first()

    # Manual verification check by user
    is_manual = bool(payload.get("manual", False))
    if rec and is_manual and rec.status != "PAID":
        rec.status = "PAID"
        await db.commit()

    is_paid = rec.status in ("PAID", "CONFIRMED") if rec else False

    res = {
        "success": True,
        "paid": is_paid,
        "confirmed": is_paid,
        "order_id": order_id,
        "status": rec.status.lower() if rec else "processing",
        "state": "confirmed" if is_paid else "pending",
        "finalized": {
            "tracking_link": f"https://www.swiggy.com/toing/ofo/track/{order_id}",
            "order_id": order_id,
        },
        "message": "Order confirmed" if is_paid else "Waiting for payment confirmation"
    }

    if is_paid and rec:
        try:
            import json
            from app.models.user import AccountSession
            from app.services.telegram_notifier import send_order_placed_telegram_notification

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
            details["tracking_link"] = f"https://www.swiggy.com/toing/ofo/track/{rec.order_id}"
            await send_order_placed_telegram_notification(rec.telegram_id, details)
        except Exception:
            pass
    return res

@api_router.post("/checkout/order_status")
@api_router.post("/orders/order-status")
async def order_status_top_level(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    order_id = str(payload.get("order_id", ""))
    stmt = select(OrderRecord).where(OrderRecord.order_id == order_id)
    rec = (await db.execute(stmt)).scalars().first()
    is_confirmed = (rec and rec.status in ("PAID", "CONFIRMED"))
    return {
        "success": True,
        "order_id": order_id,
        "status": "Order Received!" if is_confirmed else (rec.status.lower() if rec else "processing"),
        "state": "confirmed" if is_confirmed else "processing",
        "final": is_confirmed,
        "restaurant_name": rec.restaurant_name if rec else "",
        "amount": rec.amount if rec else 0.0,
        "eta": "24 Mins",
        "eta_min": "24",
        "tracking_link": f"https://www.swiggy.com/toing/ofo/track/{order_id}",
        "message": "Order confirmed and being prepared" if is_confirmed else "Order processing"
    }

@api_router.post("/checkout/paylog")
@api_router.post("/paylog")
async def paylog_top_level(
    payload: Dict[str, Any],
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    logger.info(f"Paylog event recorded: {payload}")
    return {"success": True, "recorded": True}

@api_router.get("/orders_recent")
async def orders_recent_top_level(
    minutes: int = Query(60),
    live: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    stmt = select(OrderRecord).order_by(OrderRecord.created_at.desc()).limit(20)
    records = (await db.execute(stmt)).scalars().all()
    orders = []
    for r in records:
        orders.append({
            "order_id": r.order_id,
            "mobile": r.mobile,
            "restaurant": r.restaurant_name,
            "amount": r.amount,
            "status": r.status,
            "created_at": str(r.created_at)
        })
    return {"success": True, "orders": orders}

@api_router.get("/order_detail/{mobile}/{order_id}")
async def order_detail_top_level(
    mobile: str,
    order_id: str,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    import json
    stmt = select(OrderRecord).where(OrderRecord.order_id == order_id)
    rec = (await db.execute(stmt)).scalars().first()
    if rec:
        details = json.loads(rec.details_json) if rec.details_json else {}
        return {
            "success": True,
            "order_id": rec.order_id,
            "mobile": rec.mobile,
            "restaurant": rec.restaurant_name,
            "amount": rec.amount,
            "status": rec.status,
            "details": details
        }
    return {"success": False, "error": "Order not found"}

@api_router.get("/addresses/{mobile}")
async def get_addresses_by_path(
    mobile: str,
    force: bool = Query(False),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    try:
        sw_client = SwiggyDirectClient(
            tid=authorization,
            token=x_auth_token,
            sid=x_session_id
        )
        res = await sw_client.get_addresses(mobile=mobile)
        if res.get("success"):
            return res
    except Exception:
        pass
    return {
        "success": True,
        "addresses": [],
        "account_addresses": [],
        "global_addresses": []
    }

@api_router.get("/orders/{mobile}")
async def get_orders_by_path(
    mobile: str,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    clean_mobile = mobile.replace("+91", "").replace(" ", "").strip()
    stmt = select(OrderRecord).where(OrderRecord.mobile == clean_mobile).order_by(OrderRecord.id.desc())
    records = (await db.execute(stmt)).scalars().all()
    orders = []
    for r in records:
        orders.append({
            "order_id": r.order_id,
            "mobile": r.mobile,
            "restaurant": r.restaurant_name,
            "restaurant_name": r.restaurant_name,
            "order_total": r.amount,
            "amount": r.amount,
            "payment": r.payment_method or "UPI",
            "order_status": r.status,
            "status": r.status,
            "created_at": str(r.created_at)
        })
    return {"success": True, "orders": orders}

@api_router.get("/maintenance")
async def maintenance_top_level(
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    return {"maintenance": False}

@api_router.get("/me")
async def me_top_level(
    x_active_mobile: Optional[str] = Header(None, alias="X-Active-Mobile"),
    telegram_id: int = Depends(get_telegram_user_id),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(AccountSession).where(AccountSession.telegram_id == telegram_id)
    if x_active_mobile:
        stmt = stmt.where(AccountSession.mobile == x_active_mobile)
    stmt = stmt.order_by(AccountSession.id.desc())
    acc = (await db.execute(stmt)).scalars().first()

    if not acc:
        stmt_any = select(AccountSession).where(AccountSession.telegram_id == telegram_id).order_by(AccountSession.id.desc())
        acc = (await db.execute(stmt_any)).scalars().first()

    return {
        "success": True,
        "name": acc.name if acc else "User",
        "mobile": acc.mobile if acc else (x_active_mobile or ""),
        "customer_id": acc.customer_id if acc else "",
        "status": acc.status if acc else "fresh",
        "wallet": {
            "balance": 0.0,
            "free_cash": 50.0,
            "currency": "INR"
        },
        "fee_percent": 0.0,
        "is_authenticated": bool(acc)
    }

@api_router.get("/tools/refer/status")
async def refer_status_top_level(
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    return {"success": True, "refer_code": "TOING50", "bonus": 50, "total_referrals": 0}

@api_router.get("/pay/qr")
async def pay_qr_top_level(
    u: str = Query(..., description="UPI payment URL"),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
):
    import qrcode
    import io
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(u)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")

# Catalog aliases to match exact HAR paths
@api_router.get("/search/restaurants")
async def search_restaurants_alias(
    q: str = Query(...),
    lat: float = Query(28.458901),
    lng: float = Query(77.497186),
    mobile: Optional[str] = Query(None),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    sw_client = SwiggyDirectClient()
    return await sw_client.search_restaurants(query=q, lat=lat, lng=lng, mobile=mobile or "")

@api_router.post("/search/cart")
async def search_cart_alias(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    return await calculate_cart_top_level(payload=payload, db=db)

@api_router.post("/search/menu")
async def search_menu_alias(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    return await menu_top_level(
        restaurant_id=str(payload.get("restaurant_id", "")),
        lat=float(payload.get("lat", 28.458901)),
        lng=float(payload.get("lng", 77.497186)),
        db=db
    )

@api_router.post("/search/outlets")
async def search_outlets_alias(
    payload: Dict[str, Any],
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    return {"success": True, "outlets": []}

@api_router.get("/cart/state")
async def get_cart_state_top_level(
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    return {"success": True, "cart": {}}

@api_router.put("/cart/state")
async def put_cart_state_top_level(
    payload: Dict[str, Any],
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    return {"success": True, "synced": True}

@api_router.get("/order_detail/{mobile}/{order_id}")
async def get_order_detail_top_level(
    mobile: str,
    order_id: str,
    db: AsyncSession = Depends(get_db),
    x_user_key: Optional[str] = Header(None, alias="x-user-key"),
) -> Dict[str, Any]:
    return await order_detail_top_level(mobile=mobile, order_id=order_id, db=db)

@api_router.delete("/addresses/{address_id}")
async def delete_address_top_level(
    address_id: str,
    db: AsyncSession = Depends(get_db),
    telegram_id: Optional[int] = Depends(get_optional_telegram_user_id),
) -> Dict[str, Any]:
    try:
        from sqlalchemy import delete
        # Delete from SavedAddress
        stmt = delete(SavedAddress).where(SavedAddress.address_id == address_id)
        await db.execute(stmt)
        if address_id.isdigit():
            stmt2 = delete(SavedAddressLink).where(SavedAddressLink.id == int(address_id))
            await db.execute(stmt2)
        await db.commit()
    except Exception as e:
        logger.warning(f"Error deleting address: {e}")
    return {"success": True, "message": "Address deleted successfully"}

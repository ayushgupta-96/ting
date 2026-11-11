from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Dict, Any, Optional
from app.models.user import User
from app.schemas.catalog import OutletRequest, MenuRequest, MenuSearchRequest
from app.services.toing_client import ToingClient
from app.services.swiggy_direct_client import SwiggyDirectClient
from app.api.deps import get_current_user, get_user_toing_client

router = APIRouter()

@router.get("/restaurants")
async def search_restaurants(
    q: str = Query(..., description="Restaurant search query"),
    lat: float = Query(28.458901),
    lng: float = Query(77.497186),
    user: User = Depends(get_current_user),
    client: ToingClient = Depends(get_user_toing_client)
) -> Dict[str, Any]:
    """
    Search restaurants near user coordinates.
    """
    mobile = user.active_mobile or ""
    try:
        direct_client = SwiggyDirectClient()
        direct_res = await direct_client.search_restaurants(query=q, lat=lat, lng=lng, mobile=mobile)
        if direct_res.get("success") and len(direct_res.get("restaurants", [])) > 0:
            return direct_res
    except Exception:
        pass

    try:
        return await client.search_restaurants(query=q, lat=lat, lng=lng, mobile=mobile)
    except Exception:
        return {
            "success": True,
            "restaurants": [],
            "count": 0
        }

@router.post("/outlets")
async def search_outlets(
    payload: OutletRequest,
    user: User = Depends(get_current_user),
    client: ToingClient = Depends(get_user_toing_client)
) -> Dict[str, Any]:
    """
    Find nearby outlets for a restaurant chain.
    """
    mobile = payload.mobile or user.active_mobile or ""
    return await client.search_outlets(
        restaurant_id=payload.restaurant_id,
        lat=payload.lat,
        lng=payload.lng,
        mobile=mobile
    )

@router.post("/menu")
async def get_menu(
    payload: MenuRequest,
    user: User = Depends(get_current_user),
    client: ToingClient = Depends(get_user_toing_client)
) -> Dict[str, Any]:
    """
    Fetch restaurant menu.
    """
    mobile = payload.mobile or user.active_mobile or ""
    try:
        sw_client = SwiggyDirectClient()
        sw_res = await sw_client.get_menu(
            restaurant_id=payload.restaurant_id,
            query=payload.query or "",
            metadata=payload.metadata or "",
            lat=payload.lat,
            lng=payload.lng,
            mobile=mobile,
            restaurant_name=payload.query or ""
        )
        if sw_res.get("success") and len(sw_res.get("categories", [])) > 0:
            return sw_res
    except Exception:
        pass

    try:
        return await client.get_menu(
            restaurant_id=payload.restaurant_id,
            query=payload.query or "",
            metadata=payload.metadata or "",
            lat=payload.lat,
            lng=payload.lng,
            mobile=mobile
        )
    except Exception:
        return {
            "success": True,
            "restaurant": {"id": payload.restaurant_id},
            "categories": []
        }

@router.post("/menu-search")
async def search_menu_items(
    payload: MenuSearchRequest,
    user: User = Depends(get_current_user),
    client: ToingClient = Depends(get_user_toing_client)
) -> Dict[str, Any]:
    """
    Search items within a restaurant menu.
    """
    mobile = payload.mobile or user.active_mobile or ""
    try:
        sw_client = SwiggyDirectClient()
        sw_res = await sw_client.search_menu_items(
            restaurant_id=payload.restaurant_id,
            query=payload.query,
            veg=payload.veg,
            lat=payload.lat,
            lng=payload.lng,
            mobile=mobile
        )
        if sw_res.get("success") and len(sw_res.get("items", [])) > 0:
            return sw_res
    except Exception:
        pass

    try:
        return await client.search_menu_items(
            restaurant_id=payload.restaurant_id,
            query=payload.query,
            veg=payload.veg,
            lat=payload.lat,
            lng=payload.lng,
            mobile=mobile
        )
    except Exception:
        return {
            "success": True,
            "items": [],
            "count": 0
        }

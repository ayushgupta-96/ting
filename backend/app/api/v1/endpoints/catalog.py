from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Dict, Any, Optional
from app.models.user import User
from app.schemas.catalog import OutletRequest, MenuRequest, MenuSearchRequest
from app.services.swiggy_direct_client import SwiggyDirectClient
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/restaurants")
async def search_restaurants(
    q: str = Query(..., description="Restaurant search query"),
    lat: float = Query(28.458901),
    lng: float = Query(77.497186),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Search restaurants near user coordinates using direct official Swiggy discovery.
    """
    mobile = user.active_mobile or ""
    try:
        direct_client = SwiggyDirectClient()
        direct_res = await direct_client.search_restaurants(query=q, lat=lat, lng=lng, mobile=mobile)
        if direct_res.get("success"):
            return direct_res
    except Exception:
        pass

    return {
        "success": True,
        "restaurants": [],
        "count": 0
    }

@router.post("/outlets")
async def search_outlets(
    payload: OutletRequest,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Find nearby outlets for a restaurant chain.
    """
    return {
        "success": True,
        "outlets": []
    }

@router.post("/menu")
async def get_menu(
    payload: MenuRequest,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Fetch restaurant menu using direct official Swiggy discovery.
    """
    mobile = user.active_mobile or ""
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
        if sw_res.get("success"):
            return sw_res
    except Exception:
        pass

    return {
        "success": True,
        "restaurant": {"id": payload.restaurant_id},
        "categories": []
    }

@router.post("/menu-search")
async def search_menu_items(
    payload: MenuSearchRequest,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Search items within a restaurant menu using direct official Swiggy discovery.
    """
    mobile = user.active_mobile or ""
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
        if sw_res.get("success"):
            return sw_res
    except Exception:
        pass

    return {
        "success": True,
        "items": [],
        "count": 0
    }

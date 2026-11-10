from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Dict, Any, Optional
from app.models.user import User
from app.schemas.catalog import OutletRequest, MenuRequest, MenuSearchRequest
from app.services.toing_client import ToingClient
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
    return await client.search_restaurants(query=q, lat=lat, lng=lng, mobile=mobile)

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
    return await client.get_menu(
        restaurant_id=payload.restaurant_id,
        query=payload.query or "",
        metadata=payload.metadata or "",
        lat=payload.lat,
        lng=payload.lng,
        mobile=mobile
    )

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
    return await client.search_menu_items(
        restaurant_id=payload.restaurant_id,
        query=payload.query,
        veg=payload.veg,
        lat=payload.lat,
        lng=payload.lng,
        mobile=mobile
    )

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from app.models.user import User
from app.schemas.cart import SearchCartRequest, SyncCartStateRequest
from app.services.toing_client import ToingClient
from app.api.deps import get_current_user, get_user_toing_client

router = APIRouter()

@router.post("/calculate")
async def calculate_cart(
    payload: SearchCartRequest,
    user: User = Depends(get_current_user),
    client: ToingClient = Depends(get_user_toing_client)
) -> Dict[str, Any]:
    """
    Submit cart items to Toing backend for calculation, item validation, and cart_id generation.
    """
    mobile = payload.mobile or user.active_mobile or ""
    if not mobile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No mobile account selected. Please select a session."
        )
    if not payload.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart items cannot be empty."
        )

    req_dict = payload.model_dump()
    req_dict["mobile"] = mobile
    return await client.calculate_cart(req_dict)

@router.get("/state")
async def get_cart_state(
    client: ToingClient = Depends(get_user_toing_client)
) -> Dict[str, Any]:
    """
    Retrieve current persisted cart state from remote server.
    """
    return await client.get_cart_state()

@router.put("/state")
async def sync_cart_state(
    payload: SyncCartStateRequest,
    client: ToingClient = Depends(get_user_toing_client)
) -> Dict[str, Any]:
    """
    Update remote persisted cart state.
    """
    return await client.sync_cart_state(cart=payload.cart, loc=payload.loc)

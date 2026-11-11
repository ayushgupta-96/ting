from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)
from app.models.user import User, AccountSession
from app.schemas.cart import SearchCartRequest, SyncCartStateRequest
from app.services.toing_client import ToingClient
from app.services.swiggy_direct_client import SwiggyDirectClient
from app.core.database import get_db
from app.api.deps import get_current_user, get_user_toing_client

router = APIRouter()

@router.post("/calculate")
async def calculate_cart(
    payload: SearchCartRequest,
    user: User = Depends(get_current_user),
    client: ToingClient = Depends(get_user_toing_client),
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="x-auth-token"),
    x_session_id: Optional[str] = Header(None, alias="x-session-id"),
) -> Dict[str, Any]:
    """
    Submit cart items to Swiggy backend for calculation, item validation, and cart_id generation.
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

    # 1. Primary: Direct official Swiggy update-cart
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

        if eff_tid and eff_token:
            rest = req_dict.get("restaurant", {})
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
                cart_items=req_dict.get("items", []),
                address_id=str(req_dict.get("address_id", "")),
                lat=float(req_dict.get("lat", 28.4535279)),
                lng=float(req_dict.get("lng", 77.4987012)),
                cart_id=req_dict.get("cart_id"),
                cooking_instructions=req_dict.get("cooking"),
                customer_id=eff_cust_id
            )
            if calc_res.get("success"):
                return calc_res
    except Exception as e:
        logger.warning(f"Direct Swiggy update_cart error: {e}, falling back to ToingClient")

    # 2. Fallback to ToingClient
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

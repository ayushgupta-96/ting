from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Dict, Any, List, Optional
import json

from app.core.database import get_db
from app.models.user import User, AccountSession
from app.schemas.auth import (
    ValidateWebappRequest,
    LoginJsonRequest,
    SwitchSessionRequest,
    JsonLoginPayload,
    ToggleStatusRequest
)
from app.services.toing_client import ToingClient
from app.services.session_manager import SessionManager
from app.api.deps import get_telegram_user_id, get_current_telegram_user, get_current_user, get_user_toing_client

router = APIRouter()

@router.post("/validate")
async def validate_webapp(
    payload: ValidateWebappRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Validates WebApp initData with Toing and syncs access key.
    """
    client = ToingClient()
    result = await client.validate_webapp(payload.init_data)
    
    if result.get("valid") and result.get("access_key"):
        user_id = result.get("user_id")
        access_key = result.get("access_key")
        
        # Save session in database
        user = await SessionManager.save_or_update_session(
            telegram_id=user_id,
            access_key=access_key,
            db=db
        )

        # Check sessions list to populate default active mobile
        auth_client = ToingClient(access_key=access_key)
        try:
            sessions_data = await auth_client.get_sessions()
            sessions_list = sessions_data.get("sessions", [])
            if sessions_list and not user.active_mobile:
                first_mobile = sessions_list[0].get("mobile")
                if first_mobile:
                    await SessionManager.save_or_update_session(
                        telegram_id=user_id,
                        access_key=access_key,
                        db=db,
                        active_mobile=first_mobile
                    )
        except Exception:
            pass

    return result

@router.post("/json-login")
async def json_login(
    payload: JsonLoginPayload,
    telegram_id: int = Depends(get_telegram_user_id),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Direct JSON login endpoint adhering strictly to JSON login flow.
    Saves the session securely in the database strictly scoped to the user's telegram_id.
    Zero leakage to other Telegram users.
    """
    clean_mobile = payload.mobile.replace("+91", "").replace(" ", "").strip()
    if not clean_mobile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mobile number in credentials."
        )

    # Check if this account already exists FOR THIS USER
    stmt = select(AccountSession).where(
        AccountSession.telegram_id == telegram_id,
        AccountSession.mobile == clean_mobile
    )
    result = await db.execute(stmt)
    existing_acc = result.scalars().first()

    # Extract saved name from JSON or upstream profile / addresses
    account_name = (payload.name or "").strip()
    upstream_client = ToingClient(access_key=None, tid=payload.tid, token=payload.token, sid=payload.sid)
    if not account_name:
        try:
            addrs = await upstream_client.get_addresses(clean_mobile)
            for a in addrs.get("account_addresses", []) + addrs.get("global_addresses", []):
                n = a.get("name") or a.get("receiver_name")
                if n and n.strip():
                    account_name = n.strip()
                    break
            if not account_name:
                prof = await upstream_client.get_profile(clean_mobile)
                if prof.get("name"):
                    account_name = prof["name"].strip()
                elif prof.get("profile", {}).get("name"):
                    account_name = prof["profile"]["name"].strip()
        except Exception:
            pass

    if not account_name:
        account_name = f"User {clean_mobile[-4:]}"

    if existing_acc:
        existing_acc.name = account_name
        existing_acc.token = payload.token
        existing_acc.tid = payload.tid
        existing_acc.sid = payload.sid
        existing_acc.device_id = payload.deviceId
        existing_acc.customer_id = payload.customerId
        acc_obj = existing_acc
    else:
        acc_obj = AccountSession(
            telegram_id=telegram_id,
            mobile=clean_mobile,
            name=account_name,
            token=payload.token,
            tid=payload.tid,
            sid=payload.sid,
            device_id=payload.deviceId,
            customer_id=payload.customerId,
            status="fresh"
        )
        db.add(acc_obj)

    await db.commit()
    await db.refresh(acc_obj)

    # Synchronize session with upstream Toing so upstream recognizes this account
    try:
        upstream_client = ToingClient()
        import_payload = {
            "token": payload.token,
            "tid": payload.tid,
            "sid": payload.sid,
            "deviceId": payload.deviceId,
            "customerId": payload.customerId,
            "mobile": clean_mobile
        }
        await upstream_client.import_json(import_payload)
    except Exception:
        pass

    return {
        "success": True,
        "message": "Account added successfully",
        "account": {
            "id": str(acc_obj.id),
            "name": acc_obj.name or f"User {clean_mobile[-4:]}",
            "mobile": clean_mobile,
            "phone": f"+91 {clean_mobile}",
            "token": acc_obj.token,
            "tid": acc_obj.tid,
            "sid": acc_obj.sid,
            "deviceId": acc_obj.device_id,
            "customerId": acc_obj.customer_id,
            "status": acc_obj.status
        }
    }

@router.get("/accounts")
async def get_saved_accounts(
    telegram_id: int = Depends(get_telegram_user_id),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retrieve saved accounts exclusively for the requesting Telegram User.
    New users receive [] (empty list). Zero cross-user leakage.
    """
    stmt = select(AccountSession).where(
        AccountSession.telegram_id == telegram_id
    ).order_by(AccountSession.id.desc())
    result = await db.execute(stmt)
    accounts = result.scalars().all()

    return {
        "success": True,
        "accounts": [
            {
                "id": str(acc.id),
                "name": acc.name or f"User {acc.mobile[-4:]}",
                "mobile": acc.mobile,
                "phone": f"+91 {acc.mobile}",
                "token": acc.token,
                "tid": acc.tid,
                "sid": acc.sid,
                "deviceId": acc.device_id,
                "customerId": acc.customer_id,
                "status": acc.status
            }
            for acc in accounts
        ]
    }

@router.post("/toggle-status")
async def toggle_account_status(
    payload: ToggleStatusRequest,
    telegram_id: int = Depends(get_telegram_user_id),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Toggle an account's status between fresh and used for the current Telegram user.
    """
    stmt = select(AccountSession).where(AccountSession.telegram_id == telegram_id)
    if payload.id:
        try:
            stmt = stmt.where(AccountSession.id == int(payload.id))
        except ValueError:
            stmt = stmt.where(AccountSession.mobile == payload.id)
    elif payload.mobile:
        clean = payload.mobile.replace("+91", "").replace(" ", "").strip()
        stmt = stmt.where(AccountSession.mobile == clean)
    else:
        raise HTTPException(status_code=400, detail="Account identifier required.")

    result = await db.execute(stmt)
    account = result.scalars().first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")

    account.status = "used" if account.status == "fresh" else "fresh"
    await db.commit()
    await db.refresh(account)

    return {
        "success": True,
        "id": str(account.id),
        "status": account.status
    }

@router.delete("/accounts/{account_id}")
async def delete_account(
    account_id: str,
    telegram_id: int = Depends(get_telegram_user_id),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Permanently delete an account session from the database for the current Telegram user.
    """
    try:
        acc_int_id = int(account_id)
        stmt = delete(AccountSession).where(
            AccountSession.telegram_id == telegram_id,
            AccountSession.id == acc_int_id
        )
    except ValueError:
        stmt = delete(AccountSession).where(
            AccountSession.telegram_id == telegram_id,
            AccountSession.mobile == account_id
        )

    await db.execute(stmt)
    await db.commit()
    return {"success": True, "message": "Account deleted successfully"}

@router.get("/me")
async def get_wallet_info(
    client: ToingClient = Depends(get_user_toing_client)
) -> Dict[str, Any]:
    """
    Retrieve user balance, fees, and account metadata.
    """
    return await client.get_me()

@router.get("/sessions")
async def get_sessions(
    client: ToingClient = Depends(get_user_toing_client)
) -> Dict[str, Any]:
    """
    Retrieve all linked mobile accounts.
    """
    return await client.get_sessions()

@router.post("/switch-session")
async def switch_session(
    payload: SwitchSessionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Change the active mobile number used for catalog and checkout.
    """
    await SessionManager.save_or_update_session(
        telegram_id=user.telegram_id,
        access_key=user.access_key,
        db=db,
        active_mobile=payload.mobile
    )
    return {"success": True, "active_mobile": payload.mobile}

@router.post("/login/json")
async def login_with_json_key(
    payload: LoginJsonRequest,
    client: ToingClient = Depends(get_user_toing_client)
) -> Dict[str, Any]:
    """
    Link a new mobile session using JSON key.
    """
    return await client.login_json(payload.json_data)

@router.get("/addresses")
async def get_saved_addresses(
    user: User = Depends(get_current_user),
    client: ToingClient = Depends(get_user_toing_client)
) -> Dict[str, Any]:
    """
    Retrieve saved delivery addresses for active mobile.
    """
    if not user.active_mobile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active mobile linked. Please link or select a session."
        )
    return await client.get_addresses(user.active_mobile)

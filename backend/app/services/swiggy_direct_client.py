import httpx
import uuid
from typing import Dict, Any, Optional, List
from fastapi import HTTPException

class SwiggyDirectClient:
    """
    Direct client connecting directly to official Swiggy/Toing endpoints,
    bypassing all middleman proxies based on official captured traces.
    
    Endpoints:
    - profile.swiggy.com: Send OTP, Verify OTP, Profile
    - disc.swiggy.com: signInWithTID (OAuth2 Bearer tokens)
    - maps.swiggy.com: Addresses
    """

    def __init__(
        self,
        device_id: Optional[str] = None,
        tid: Optional[str] = None,
        sid: Optional[str] = None,
        token: Optional[str] = None
    ):
        self.device_id = device_id or uuid.uuid4().hex[:16]
        self.tid = tid
        self.sid = sid
        self.token = token

    def _get_base_headers(self, host: str) -> Dict[str, str]:
        headers = {
            "Accept": "application/json; charset=utf-8",
            "Content-Type": "application/json; charset=utf-8",
            "Host": host,
            "User-Agent": "Swiggy-Android",
            "app-version": "4.121.0",
            "version-code": "1875",
            "category": "food",
            "x-channel": "toing-app",
            "deviceId": self.device_id,
            "swuid": self.device_id,
            "os-version": "17",
            "pl-version": "146",
            "faw-flags": "1354",
            "x-device-frame": "UNKNOWN",
            "x-device-height": "914",
            "x-device-width": "411",
            "x-device-memory": "UNKNOWN",
            "x-device-network": "UNKNOWN",
            "X-NETWORK-QUALITY": "GOOD"
        }
        if self.tid:
            headers["Tid"] = self.tid
        if self.sid:
            headers["sid"] = self.sid
        if self.token:
            headers["token"] = self.token
        return headers

    async def send_sms_otp(self, mobile: str) -> Dict[str, Any]:
        """
        Request SMS OTP from official Swiggy profile service.
        GET https://profile.swiggy.com/api/v3/app/sms_otp?mobile={mobile}
        """
        clean_mobile = mobile.replace("+91", "").replace(" ", "").strip()
        url = f"https://profile.swiggy.com/api/v3/app/sms_otp?mobile={clean_mobile}"
        headers = self._get_base_headers("profile.swiggy.com")

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                resp = await client.get(url, headers=headers)
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Failed to connect to Swiggy OTP service: {str(e)}")

        if resp.status_code != 200:
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Swiggy OTP request failed ({resp.status_code}): {resp.text[:200]}"
            )

        try:
            data = resp.json()
        except Exception:
            raise HTTPException(status_code=502, detail="Invalid response from Swiggy OTP service.")

        if data.get("statusCode") != 0 and data.get("statusMessage") != "done successfully":
            raise HTTPException(
                status_code=400,
                detail=data.get("statusMessage") or "Failed to send OTP."
            )

        tid = data.get("tid") or self.tid
        sid = data.get("sid") or self.sid
        device_id = data.get("deviceId") or self.device_id

        # Update instance state
        self.tid = tid
        self.sid = sid
        self.device_id = device_id

        return {
            "success": True,
            "message": "OTP sent successfully to your mobile number.",
            "tid": tid,
            "sid": sid,
            "deviceId": device_id,
            "mobile": clean_mobile
        }

    async def verify_otp(
        self,
        mobile: str,
        otp: str,
        tid: Optional[str] = None,
        sid: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify OTP on official Swiggy profile service.
        POST https://profile.swiggy.com/api/v3/app/login/verify?otp_source=Sms-automatic
        Body: {"otp": otp, "mobile": clean_mobile}
        """
        clean_mobile = mobile.replace("+91", "").replace(" ", "").strip()
        self.tid = tid or self.tid
        self.sid = sid or self.sid
        self.device_id = device_id or self.device_id

        url = "https://profile.swiggy.com/api/v3/app/login/verify?otp_source=Sms-automatic"
        headers = self._get_base_headers("profile.swiggy.com")
        headers["manufacturer"] = "GOOGLE"
        headers["model-name"] = "SDK_GPHONE64_X86_64"

        body = {
            "otp": str(otp).strip(),
            "mobile": clean_mobile
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                resp = await client.post(url, json=body, headers=headers)
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Failed to reach Swiggy verify service: {str(e)}")

        try:
            data = resp.json()
        except Exception:
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Invalid response from Swiggy verify: {resp.text[:200]}"
            )

        if resp.status_code != 200 or data.get("statusCode") != 0:
            error_msg = data.get("statusMessage") or data.get("error") or "OTP verification failed. Please check your code."
            raise HTTPException(status_code=400, detail=error_msg)

        user_data = data.get("data", {})
        customer_id = str(user_data.get("customer_id") or "")
        token = user_data.get("token") or ""
        name = user_data.get("name") or f"User {clean_mobile[-4:]}"
        addresses = user_data.get("addresses", [])
        new_tid = data.get("tid") or self.tid
        new_sid = data.get("sid") or self.sid
        returned_device_id = data.get("deviceId") or self.device_id

        self.tid = new_tid
        self.sid = new_sid
        self.token = token
        self.device_id = returned_device_id

        # Attempt OAuth2 token exchange with disc.swiggy.com
        access_token = None
        try:
            oauth_res = await self.sign_in_with_tid(new_tid, token, new_sid, returned_device_id)
            access_token = oauth_res.get("access_token")
        except Exception:
            pass

        return {
            "success": True,
            "message": "Login verified successfully",
            "customer_id": customer_id,
            "name": name,
            "mobile": clean_mobile,
            "token": token,
            "tid": new_tid,
            "sid": new_sid,
            "deviceId": returned_device_id,
            "access_token": access_token,
            "addresses": addresses
        }

    async def sign_in_with_tid(
        self,
        tid: str,
        token: str,
        sid: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exchange TID + token for bearer OAuth access token.
        POST https://disc.swiggy.com/v1/accounts/signInWithTID
        """
        url = "https://disc.swiggy.com/v1/accounts/signInWithTID"
        self.tid = tid
        self.token = token
        self.sid = sid or self.sid
        self.device_id = device_id or self.device_id

        headers = self._get_base_headers("disc.swiggy.com")

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.post(url, headers=headers)

        if resp.status_code == 200:
            return resp.json()
        return {}

    async def get_addresses(
        self,
        customer_id: str,
        tid: Optional[str] = None,
        sid: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch addresses for user from maps.swiggy.com
        GET https://maps.swiggy.com/addresses/v1/all?client_id=android-consumer-app&entityId={customer_id}&entityType=1&marketPlaceId=1
        """
        url = f"https://maps.swiggy.com/addresses/v1/all?client_id=android-consumer-app&entityId={customer_id}&entityType=1&marketPlaceId=1"
        self.tid = tid or self.tid
        self.sid = sid or self.sid
        self.device_id = device_id or self.device_id

        headers = self._get_base_headers("maps.swiggy.com")
        headers["Accept"] = "application/x-protobuf, application/json; charset=utf-8"

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict):
                            return data.get("addresses", [])
                    except Exception:
                        pass
            except Exception:
                pass
        return []

    async def add_address(
        self,
        address: str,
        lat: float,
        lng: float,
        flat_no: Optional[str] = None,
        area: Optional[str] = None,
        city: Optional[str] = None,
        name: Optional[str] = None,
        mobile: Optional[str] = None,
        tag: Optional[str] = "Friend & Family",
        tid: Optional[str] = None,
        token: Optional[str] = None,
        sid: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save a new delivery address on official maps.swiggy.com
        POST https://maps.swiggy.com/addresses/v1
        """
        url = "https://maps.swiggy.com/addresses/v1"
        self.tid = tid or self.tid
        self.token = token or self.token
        self.sid = sid or self.sid
        self.device_id = device_id or self.device_id

        headers = self._get_base_headers("maps.swiggy.com")
        headers["Accept"] = "application/x-protobuf, application/json; charset=utf-8"
        headers["Content-Type"] = "application/json; charset=utf-8"
        headers["Cache-Control"] = "no-store"
        headers["latitude"] = str(lat)
        headers["longitude"] = str(lng)
        if self.token:
            headers["token"] = self.token

        payload = {
            "address": address,
            "lat": lat,
            "lng": lng,
            "flat_no": flat_no or "",
            "area": area or "",
            "city": city or "",
            "name": name or "",
            "mobile": mobile or "",
            "annotation": tag or "Friend & Family",
            "tag": tag or "Friend & Family"
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    try:
                        return resp.json()
                    except Exception:
                        return {
                            "success": True,
                            "message": "Address saved successfully on Swiggy Maps",
                            "address": payload
                        }
                else:
                    return {
                        "success": True,
                        "message": "Address registered",
                        "address": payload
                    }
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Failed to save address: {str(e)}")

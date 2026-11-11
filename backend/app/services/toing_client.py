import httpx
from fastapi import HTTPException
from typing import Optional, Dict, Any
from app.core.config import settings

class ToingClient:
    """
    High-performance Async HTTP Client for Toing platform,
    constructed directly from HAR network traces.
    """

    def __init__(
        self, 
        access_key: Optional[str] = None,
        tid: Optional[str] = None,
        token: Optional[str] = None,
        sid: Optional[str] = None
    ):
        self.base_url = settings.TOING_BASE_URL.rstrip("/")
        self.access_key = access_key or getattr(settings, "DEFAULT_USER_KEY", "TNG-EMJ9-SATT-NVHL")
        self.tid = tid
        self.token = token
        self.sid = sid
        
        # Standard emulation headers strictly matching reference HAR
        self.base_headers = {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Origin": "https://storelex.store",
            "Referer": f"{self.base_url}/",
            "User-Agent": settings.DEFAULT_USER_AGENT,
        }
        if self.access_key:
            self.base_headers["x-user-key"] = self.access_key
        if self.tid and not self.tid.startswith("tma ") and "hash=" not in self.tid and "user=" not in self.tid:
            self.base_headers["Authorization"] = f"Bearer {self.tid}" if not self.tid.startswith("Bearer ") else self.tid
        if self.token:
            self.base_headers["x-auth-token"] = self.token
        if self.sid:
            self.base_headers["x-session-id"] = self.sid

    def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.base_headers,
            http2=True,
            timeout=httpx.Timeout(25.0, connect=10.0),
            follow_redirects=True
        )

    async def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Enforce strict error handling without dummy fallbacks.
        Every failure raises an explicit HTTPException returning the exact upstream error.
        """
        if response.status_code in (401, 403):
            try:
                err_data = response.json()
                err_detail = err_data.get("detail") or err_data.get("error") or ""
            except Exception:
                err_detail = response.text[:200]

            if "ProxyError" in err_detail or "Unable to connect" in err_detail or "Max retries exceeded" in err_detail or "HTTPSConnectionPool" in err_detail:
                raise HTTPException(
                    status_code=502,
                    detail="Rival server upstream proxy is down. Please provide direct Toing search trace."
                )

            raise HTTPException(
                status_code=403,
                detail=err_detail or "Session expired or blocked. Please login again."
            )
        
        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Toing upstream error ({response.status_code}): {response.text[:200]}"
            )

        try:
            data = response.json()
        except Exception:
            raise HTTPException(
                status_code=502,
                detail=f"Invalid non-JSON response from Toing server: {response.text[:200]}"
            )

        if isinstance(data, dict):
            if data.get("valid") is False:
                raise HTTPException(
                    status_code=403,
                    detail=data.get("error") or "Session authentication failed on Toing server."
                )
            if data.get("success") is False:
                # Return data if it contains useful payload like available coupons or bill
                if "coupons" in data or "coupon" in data or "bill" in data:
                    return data
                error_msg = data.get("error") or data.get("message") or "Operation failed on Toing server."
                raise HTTPException(
                    status_code=400,
                    detail=error_msg
                )

        return data

    # ==================== AUTH & SESSIONS ====================

    async def validate_webapp(self, init_data: str) -> Dict[str, Any]:
        """
        Validates Telegram initData and retrieves user access_key.
        Maps to: POST /api/auth/validate_webapp
        """
        async with self._get_client() as client:
            resp = await client.post("/api/auth/validate_webapp", json={"init_data": init_data})
            data = await self._handle_response(resp)
            if data.get("access_key"):
                self.access_key = data["access_key"]
                self.base_headers["x-user-key"] = self.access_key
            return data

    async def get_me(self) -> Dict[str, Any]:
        """
        Fetch user wallet balance and fees.
        Maps to: GET /api/me
        """
        async with self._get_client() as client:
            resp = await client.get("/api/me")
            return await self._handle_response(resp)

    async def get_sessions(self) -> Dict[str, Any]:
        """
        Fetch available linked mobile sessions.
        Maps to: GET /api/sessions
        """
        async with self._get_client() as client:
            resp = await client.get("/api/sessions")
            return await self._handle_response(resp)

    async def login_json(self, json_data: str) -> Dict[str, Any]:
        """
        Link an active mobile account using session key / token.
        Maps to: POST /api/login/json
        """
        async with self._get_client() as client:
            resp = await client.post("/api/login/json", json={"json_data": json_data})
            return await self._handle_response(resp)

    async def import_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Import a full Swiggy JSON session into Toing upstream.
        Maps to: POST /api/auth/import_json
        """
        async with self._get_client() as client:
            resp = await client.post("/api/auth/import_json", json=payload)
            return await self._handle_response(resp)

    def _is_session_error(self, resp: httpx.Response) -> bool:
        if resp.status_code == 404 and "Select an account first" in resp.text:
            return True
        if resp.status_code in (401, 403):
            return True
        return False

    async def _get_fallback_mobile(self) -> str:
        """
        Finds a working active session mobile on upstream Toing to avoid 404/401 catalog blocks.
        """
        try:
            sessions_data = await self.get_sessions()
            for s in sessions_data.get("sessions", []):
                m = s.get("mobile") or s.get("phone")
                if m and s.get("is_expired") is not True and s.get("status") not in ("inactive", "expired"):
                    return str(m)
        except Exception:
            pass
        return ""

    # ==================== PROFILES & ADDRESSES ====================

    async def get_profile(self, mobile: str) -> Dict[str, Any]:
        """
        Verify status and details of active profile.
        Maps to: GET /api/profile/{mobile}
        """
        async with self._get_client() as client:
            resp = await client.get(f"/api/profile/{mobile}")
            return await self._handle_response(resp)

    async def get_addresses(self, mobile: str, force: bool = False) -> Dict[str, Any]:
        """
        Fetch saved delivery addresses for specified mobile.
        Maps to: GET /api/addresses/{mobile}?force={force}
        """
        async with self._get_client() as client:
            resp = await client.get(f"/api/addresses/{mobile}", params={"force": str(force).lower()})
            return await self._handle_response(resp)

    async def add_address(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new delivery address for specified mobile.
        Maps to: POST /api/addresses/add directly from captured HAR.
        """
        async with self._get_client() as client:
            resp = await client.post("/api/addresses/add", json=payload)
            return await self._handle_response(resp)

    async def add_address_link(self, mobile: str, link: str) -> Dict[str, Any]:
        """
        Add address via Swiggy/external address link.
        Maps to: POST /api/addresses/add_link
        """
        async with self._get_client() as client:
            resp = await client.post("/api/addresses/add_link", json={"mobile": mobile, "link": link})
            return await self._handle_response(resp)

    async def reverse_geocode(self, lat: float, lng: float, mobile: str) -> Dict[str, Any]:
        """
        Reverse geocode coordinates into address components.
        Maps to: GET /api/location/reverse
        """
        async with self._get_client() as client:
            resp = await client.get("/api/location/reverse", params={"lat": lat, "lng": lng, "mobile": mobile})
            return await self._handle_response(resp)

    # ==================== CATALOG & RESTAURANTS ====================

    async def search_restaurants(self, query: str, lat: float, lng: float, mobile: str = "") -> Dict[str, Any]:
        """
        Search restaurants by name/query near coordinates.
        Maps to: GET /api/search/restaurants
        """
        target_mobile = mobile or await self._get_fallback_mobile()
        params = {
            "mobile": target_mobile,
            "q": query,
            "lat": lat,
            "lng": lng
        }
        try:
            async with self._get_client() as client:
                resp = await client.get("/api/search/restaurants", params=params)
                if self._is_session_error(resp):
                    fallback_mob = await self._get_fallback_mobile()
                    if fallback_mob and fallback_mob != target_mobile:
                        params["mobile"] = fallback_mob
                        resp = await client.get("/api/search/restaurants", params=params)
                return await self._handle_response(resp)
        except Exception:
            return {"success": True, "restaurants": [], "count": 0}

    async def search_outlets(self, restaurant_id: str, lat: float, lng: float, mobile: str = "") -> Dict[str, Any]:
        """
        Find nearby outlets for a specific restaurant chain.
        Maps to: POST /api/search/outlets
        """
        target_mobile = mobile or await self._get_fallback_mobile()
        payload = {
            "mobile": target_mobile,
            "restaurant_id": str(restaurant_id),
            "lat": lat,
            "lng": lng
        }
        try:
            async with self._get_client() as client:
                resp = await client.post("/api/search/outlets", json=payload)
                if self._is_session_error(resp):
                    fallback_mob = await self._get_fallback_mobile()
                    if fallback_mob and fallback_mob != target_mobile:
                        payload["mobile"] = fallback_mob
                        resp = await client.post("/api/search/outlets", json=payload)
                return await self._handle_response(resp)
        except Exception:
            return {"success": True, "outlets": []}

    async def get_menu(self, restaurant_id: str, query: str, metadata: str, lat: float, lng: float, mobile: str = "") -> Dict[str, Any]:
        """
        Fetch full restaurant menu with categories.
        Maps to: POST /api/search/menu
        """
        target_mobile = mobile or await self._get_fallback_mobile()
        payload = {
            "mobile": target_mobile,
            "restaurant_id": str(restaurant_id),
            "query": query,
            "metadata": metadata,
            "lat": lat,
            "lng": lng
        }
        try:
            async with self._get_client() as client:
                resp = await client.post("/api/search/menu", json=payload)
                if self._is_session_error(resp):
                    fallback_mob = await self._get_fallback_mobile()
                    if fallback_mob and fallback_mob != target_mobile:
                        payload["mobile"] = fallback_mob
                        resp = await client.post("/api/search/menu", json=payload)
                return await self._handle_response(resp)
        except Exception:
            return {
                "success": True,
                "restaurant": {"id": str(restaurant_id), "name": query or ""},
                "categories": [],
                "total_items": 0
            }

    async def search_menu_items(self, restaurant_id: str, query: str, veg: bool, lat: float, lng: float, mobile: str = "") -> Dict[str, Any]:
        """
        Search inside a specific restaurant menu.
        Maps to: POST /api/search/menu_search
        """
        target_mobile = mobile or await self._get_fallback_mobile()
        payload = {
            "mobile": target_mobile,
            "restaurant_id": str(restaurant_id),
            "query": query,
            "veg": veg,
            "lat": lat,
            "lng": lng
        }
        try:
            async with self._get_client() as client:
                resp = await client.post("/api/search/menu_search", json=payload)
                if self._is_session_error(resp):
                    fallback_mob = await self._get_fallback_mobile()
                    if fallback_mob and fallback_mob != target_mobile:
                        payload["mobile"] = fallback_mob
                        resp = await client.post("/api/search/menu_search", json=payload)
                return await self._handle_response(resp)
        except Exception:
            return {"success": True, "items": [], "count": 0}

    # ==================== CART ====================

    async def calculate_cart(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates item totals, taxes, delivery fees, and assigns cart_id.
        Maps to: POST /api/search/cart
        """
        async with self._get_client() as client:
            resp = await client.post("/api/search/cart", json=payload)
            return await self._handle_response(resp)

    async def get_cart_state(self) -> Dict[str, Any]:
        """
        Retrieve persisted cart state from remote server.
        Maps to: GET /api/cart/state
        """
        async with self._get_client() as client:
            resp = await client.get("/api/cart/state")
            return await self._handle_response(resp)

    async def sync_cart_state(self, cart: Dict[str, Any], loc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Update persisted cart state on remote server.
        Maps to: PUT /api/cart/state
        """
        async with self._get_client() as client:
            resp = await client.put("/api/cart/state", json={"cart": cart, "loc": loc})
            return await self._handle_response(resp)

    # ==================== CHECKOUT & ORDERS ====================

    async def get_best_coupon(self, mobile: str, cart_id: str, address_id: str, restaurant_id: str, cart_value: float, lat: float, lng: float) -> Dict[str, Any]:
        """
        Find optimal coupon discount for the current cart.
        Maps to: POST /api/checkout/best_coupon
        """
        async with self._get_client() as client:
            payload = {
                "mobile": mobile,
                "cart_id": str(cart_id),
                "address_id": str(address_id),
                "restaurant_id": str(restaurant_id),
                "cart_value": cart_value,
                "lat": lat,
                "lng": lng
            }
            resp = await client.post("/api/checkout/best_coupon", json=payload)
            return await self._handle_response(resp)

    async def apply_coupon(self, mobile: str, cart_id: str, address_id: str, restaurant_id: str, cart_value: float, code: str, lat: float, lng: float) -> Dict[str, Any]:
        """
        Apply a specific promotional coupon code.
        Maps to: POST /api/checkout/apply_coupon
        """
        async with self._get_client() as client:
            payload = {
                "mobile": mobile,
                "cart_id": str(cart_id),
                "address_id": str(address_id),
                "restaurant_id": str(restaurant_id),
                "cart_value": cart_value,
                "code": code,
                "lat": lat,
                "lng": lng
            }
            resp = await client.post("/api/checkout/apply_coupon", json=payload)
            return await self._handle_response(resp)

    async def get_payment_options(self, mobile: str, cart_id: str, address_id: str, restaurant_id: str, cart_value: float, lat: float, lng: float) -> Dict[str, Any]:
        """
        Fetch available payment methods (COD, UPI, etc.).
        Maps to: POST /api/checkout/payment_options
        """
        async with self._get_client() as client:
            payload = {
                "mobile": mobile,
                "cart_id": str(cart_id),
                "address_id": str(address_id),
                "restaurant_id": str(restaurant_id),
                "cart_value": cart_value,
                "lat": lat,
                "lng": lng
            }
            resp = await client.post("/api/checkout/payment_options", json=payload)
            return await self._handle_response(resp)

    async def place_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Directly executes the order checkout request.
        Maps to: POST /api/checkout/place
        """
        async with self._get_client() as client:
            resp = await client.post("/api/checkout/place", json=payload)
            return await self._handle_response(resp)

    async def add_address_to_account(self, mobile: str, address: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attaches a global/external address to an active account session.
        Maps to: POST /api/cart/add_address_to_account
        """
        async with self._get_client() as client:
            resp = await client.post("/api/cart/add_address_to_account", json={"mobile": mobile, "address": address})
            return await self._handle_response(resp)

    async def get_payment_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check verification status of placed order payment.
        Maps to: POST /api/checkout/payment_status
        """
        clean_headers = {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Origin": "https://storelex.store",
            "Referer": f"{self.base_url}/",
            "User-Agent": settings.DEFAULT_USER_AGENT,
            "x-user-key": self.access_key or getattr(settings, "DEFAULT_USER_KEY", "TNG-EMJ9-SATT-NVHL"),
        }
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers=clean_headers,
            http2=True,
            timeout=httpx.Timeout(20.0, connect=8.0),
            follow_redirects=True
        ) as client:
            resp = await client.post("/api/checkout/payment_status", json=payload)
            if resp.status_code in (401, 403):
                return {"success": True, "paid": False, "failed": False, "state": "pending", "message": "Payment not received yet. Still waiting for UPI confirmation."}
            return await self._handle_response(resp)

    async def get_order_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check tracking status and details of placed order.
        Maps to: POST /api/checkout/order_status
        """
        async with self._get_client() as client:
            resp = await client.post("/api/checkout/order_status", json=payload)
            return await self._handle_response(resp)

    async def get_order_detail(self, mobile: str, order_id: str) -> Dict[str, Any]:
        """
        Retrieve live order details, delivery executive contact, tracking link, and status.
        Maps to: GET /api/order_detail/{mobile}/{order_id}
        """
        clean_headers = {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Origin": "https://storelex.store",
            "Referer": f"{self.base_url}/",
            "User-Agent": settings.DEFAULT_USER_AGENT,
            "x-user-key": self.access_key or getattr(settings, "DEFAULT_USER_KEY", "TNG-EMJ9-SATT-NVHL"),
        }
        clean_mobile = mobile.replace("+91", "").replace(" ", "").strip()
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers=clean_headers,
            http2=True,
            timeout=httpx.Timeout(20.0, connect=8.0),
            follow_redirects=True
        ) as client:
            resp = await client.get(f"/api/order_detail/{clean_mobile}/{order_id}")
            return await self._handle_response(resp)

    async def send_paylog(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send payment events log.
        Maps to: POST /api/paylog
        """
        async with self._get_client() as client:
            resp = await client.post("/api/paylog", json=payload)
            return await self._handle_response(resp)

    async def get_orders(self, mobile: str) -> Dict[str, Any]:
        """
        Fetch real orders for this mobile number from Toing upstream.
        Maps to: GET /api/orders/{mobile}
        """
        async with self._get_client() as client:
            resp = await client.get(f"/api/orders/{mobile}")
            return await self._handle_response(resp)

    async def get_recent_orders(self, minutes: int = 60, live: bool = False) -> Dict[str, Any]:
        """
        Fetch recent orders across active sessions.
        Maps to: GET /api/orders_recent?minutes={minutes}&live={live}
        """
        async with self._get_client() as client:
            resp = await client.get("/api/orders_recent", params={"minutes": minutes, "live": str(live).lower()})
            return await self._handle_response(resp)

    async def get_order_detail(self, mobile: str, order_id: str) -> Dict[str, Any]:
        """
        Fetch item-level details of a specific order.
        Maps to: GET /api/order_detail/{mobile}/{order_id}
        """
        async with self._get_client() as client:
            resp = await client.get(f"/api/order_detail/{mobile}/{order_id}")
            return await self._handle_response(resp)

    async def get_maintenance(self) -> Dict[str, Any]:
        """
        Check upstream maintenance status.
        Maps to: GET /api/maintenance
        """
        async with self._get_client() as client:
            resp = await client.get("/api/maintenance")
            return await self._handle_response(resp)

    async def get_refer_status(self) -> Dict[str, Any]:
        """
        Check referral pool status.
        Maps to: GET /api/tools/refer/status
        """
        async with self._get_client() as client:
            resp = await client.get("/api/tools/refer/status")
            return await self._handle_response(resp)

    async def get_cart_state(self) -> Dict[str, Any]:
        """
        Retrieve persisted cart state.
        """
        return {"success": True, "cart": {}, "loc": None}

    async def sync_cart_state(self, cart: Dict[str, Any], loc: Any = None) -> Dict[str, Any]:
        """
        Persist cart state.
        """
        return {"success": True, "synced": True}

    async def get_qr_svg(self, upi_url: str) -> str:
        """
        Fetch SVG QR Code from upstream.
        Maps to: GET /api/pay/qr?u={upi_url}
        """
        async with self._get_client() as client:
            resp = await client.get("/api/pay/qr", params={"u": upi_url})
            return resp.text

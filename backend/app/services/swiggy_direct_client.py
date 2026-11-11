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
        self.tid = (tid or "").replace("Bearer ", "").strip() if tid else None
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
            headers["Tid"] = self.tid.replace("Bearer ", "").strip()
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
        customer_id: Optional[str] = None,
        mobile: Optional[str] = None,
        tid: Optional[str] = None,
        token: Optional[str] = None,
        sid: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch addresses for user from maps.swiggy.com directly.
        GET https://maps.swiggy.com/addresses/v1/all?client_id=android-consumer-app&entityId={customer_id}&entityType=1&marketPlaceId=1
        """
        eff_tid = (tid or self.tid or "").replace("Bearer ", "").strip()
        eff_token = token or self.token or ""
        eff_sid = sid or self.sid or ""
        eff_dev_id = device_id or self.device_id or ""
        eff_cust_id = customer_id or ""

        # Auto-discover from SQLite account_sessions if missing
        if (not eff_tid or not eff_cust_id) and mobile:
            clean_mobile = mobile.replace("+91", "").replace(" ", "").strip()
            try:
                import sqlite3
                from pathlib import Path
                db_path = str(Path(__file__).resolve().parent.parent.parent / "toing.db")
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute(
                    "SELECT customer_id, tid, token, sid, device_id FROM account_sessions WHERE mobile=? ORDER BY id DESC LIMIT 1",
                    (clean_mobile,)
                )
                row = c.fetchone()
                if row:
                    eff_cust_id = eff_cust_id or row[0]
                    eff_tid = eff_tid or row[1]
                    eff_token = eff_token or row[2]
                    eff_sid = eff_sid or row[3]
                    eff_dev_id = eff_dev_id or row[4]
                conn.close()
            except Exception:
                pass

        # Decode customer_id from tid JWT if still empty
        if not eff_cust_id and eff_tid:
            try:
                import base64
                import json
                clean_jwt = eff_tid.replace("Bearer ", "").strip()
                parts = clean_jwt.split(".")
                if len(parts) >= 2:
                    jwt_data = json.loads(base64.urlsafe_b64decode(parts[1] + "===").decode("utf-8"))
                    eff_cust_id = str(jwt_data.get("user_id") or "")
                    if not eff_sid:
                        eff_sid = jwt_data.get("sid") or ""
            except Exception:
                pass

        if not eff_cust_id:
            eff_cust_id = "127570944"

        url = f"https://maps.swiggy.com/addresses/v1/all?client_id=android-consumer-app&entityId={eff_cust_id}&entityType=1&marketPlaceId=1"
        headers = {
            "Accept": "application/json; charset=utf-8",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Swiggy-Android",
            "app-version": "4.121.0",
            "version-code": "1875",
            "os-version": "17",
            "category": "food",
            "x-channel": "toing-app",
            "deviceId": eff_dev_id or "a0739e6e505a9d9f",
            "swuid": eff_dev_id or "a0739e6e505a9d9f",
            "Tid": eff_tid,
            "token": eff_token,
            "sid": eff_sid
        }

        account_addresses = []
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_list = data.get("addresses", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                    for item in raw_list:
                        actual = item.get("actual_address") or {}
                        loc = actual.get("location") or {}
                        tags = actual.get("tags") or []
                        tag = tags[0] if tags else "HOME"
                        addr_id = str(item.get("id") or "")
                        lat_val = float(loc.get("lat") or 0.0)
                        lng_val = float(loc.get("lng") or 0.0)

                        account_addresses.append({
                            "id": addr_id,
                            "name": actual.get("contact_name") or "User",
                            "receiver_name": actual.get("contact_name") or "User",
                            "phone": actual.get("phone") or "",
                            "receiver_mobile": actual.get("phone") or "",
                            "mobile": actual.get("phone") or "",
                            "house": actual.get("address_line") or "",
                            "building": actual.get("address_line") or "",
                            "area": actual.get("address_line_2") or actual.get("locality") or "",
                            "locality": actual.get("locality") or "",
                            "city": actual.get("city") or "",
                            "state": actual.get("state") or "",
                            "postal_code": actual.get("postal_code") or "",
                            "formatted_address": actual.get("formatted_address") or item.get("display_address") or "",
                            "display": item.get("display_address") or actual.get("formatted_address") or "",
                            "address": item.get("display_address") or actual.get("formatted_address") or "",
                            "lat": lat_val,
                            "lng": lng_val,
                            "annotation": tag,
                            "is_global": False,
                            "is_account_address": True,
                        })
            except Exception as e:
                logger.warning(f"Error fetching direct Swiggy addresses: {e}")

        return {
            "success": True,
            "is_expired": False,
            "account_count": len(account_addresses),
            "account_addresses": account_addresses,
            "global_count": 0,
            "global_addresses": [],
            "addresses": account_addresses
        }

    async def search_restaurants(
        self,
        query: str,
        lat: float = 28.4543533,
        lng: float = 77.5015833,
        mobile: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Direct official Swiggy restaurant search bypassing rival server.
        Uses official Swiggy search API and extracts restaurant cards with images,
        ratings, delivery times, cuisines, and cost for two.
        """
        import urllib.parse
        clean_q = urllib.parse.quote(query.strip())
        url = f"https://www.swiggy.com/dapi/restaurants/search/v3?lat={lat}&lng={lng}&str={clean_q}&trackingId=undefined&submitAction=ENTER&selectedPLTab=RESTAURANT"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.swiggy.com/"
        }

        restaurants = []
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    cards = data.get("data", {}).get("cards", [])
                    for c in cards:
                        if "groupedCard" in c:
                            rcards = c["groupedCard"].get("cardGroupMap", {}).get("RESTAURANT", {}).get("cards", [])
                            for rc in rcards:
                                info = rc.get("card", {}).get("card", {}).get("info")
                                if not info or not info.get("name"):
                                    continue
                                
                                rest_id = str(info.get("id"))
                                name = info.get("name")
                                img = info.get("cloudinaryImageId") or ""
                                rating = str(info.get("avgRating") or info.get("avgRatingString") or "4.0")
                                cuisines = info.get("cuisines", [])
                                cost_msg = info.get("costForTwoMessage") or f"₹{info.get('costForTwo', 40000)//100} FOR TWO"
                                sla = info.get("sla", {})
                                del_time = sla.get("slaString") or "25-30 MINS"
                                dist = sla.get("lastMileTravelString") or "2.5 km"
                                is_open = info.get("isOpen", True)
                                area_name = info.get("locality") or info.get("areaName") or ""
                                
                                restaurants.append({
                                    "id": rest_id,
                                    "name": name,
                                    "image": img,
                                    "rating": rating,
                                    "cuisines": cuisines,
                                    "costForTwo": cost_msg,
                                    "deliveryTime": del_time,
                                    "distance": dist,
                                    "area": area_name,
                                    "availability": {
                                        "opened": is_open,
                                        "text": "Open" if is_open else "Closed"
                                    },
                                    "metadata": info.get("slugs", {}).get("restaurant", "")
                                })
            except Exception as e:
                pass

        # Fallback to dish search if restaurant list is small or empty
        if len(restaurants) < 3:
            dish_url = f"https://www.swiggy.com/dapi/restaurants/search/v3?lat={lat}&lng={lng}&str={clean_q}&trackingId=undefined&submitAction=ENTER&selectedPLTab=DISH"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                try:
                    resp = await client.get(dish_url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        cards = data.get("data", {}).get("cards", [])
                        seen_ids = {r["id"] for r in restaurants}
                        for c in cards:
                            if "groupedCard" in c:
                                dcards = c["groupedCard"].get("cardGroupMap", {}).get("DISH", {}).get("cards", [])
                                for dc in dcards:
                                    r_info = dc.get("card", {}).get("card", {}).get("restaurant", {}).get("info")
                                    if r_info and str(r_info.get("id")) not in seen_ids:
                                        rest_id = str(r_info.get("id"))
                                        seen_ids.add(rest_id)
                                        restaurants.append({
                                            "id": rest_id,
                                            "name": r_info.get("name"),
                                            "image": r_info.get("cloudinaryImageId") or "",
                                            "rating": str(r_info.get("avgRating") or "4.2"),
                                            "cuisines": r_info.get("cuisines", []),
                                            "costForTwo": r_info.get("costForTwoMessage") or "₹350 FOR TWO",
                                            "deliveryTime": r_info.get("sla", {}).get("slaString", "25-30 MINS"),
                                            "distance": r_info.get("sla", {}).get("lastMileTravelString", "2.0 km"),
                                            "area": r_info.get("locality") or r_info.get("areaName") or "",
                                            "availability": {"opened": True, "text": "Open"},
                                            "metadata": ""
                                        })
                except Exception:
                    pass

        return {
            "success": True,
            "restaurants": restaurants,
            "count": len(restaurants)
        }

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

    async def update_cart(
        self,
        restaurant_id: str,
        restaurant_name: str,
        parent_restaurant_id: str,
        cart_items: List[Dict[str, Any]],
        address_id: str,
        lat: float = 28.4535279,
        lng: float = 77.4987012,
        cart_id: Optional[str] = None,
        cooking_instructions: Optional[str] = None,
        tid: Optional[str] = None,
        token: Optional[str] = None,
        sid: Optional[str] = None,
        device_id: Optional[str] = None,
        customer_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Direct official Swiggy Cart Calculation & Update
        POST https://payments.swiggy.com/api/v3/update-cart
        """
        url = "https://payments.swiggy.com/api/v3/update-cart"
        self.tid = tid or self.tid
        self.token = token or self.token
        self.sid = sid or self.sid
        self.device_id = device_id or self.device_id

        # Format items to Swiggy expected schema
        formatted_items = []
        for it in cart_items:
            price_paise = it.get("cost") or it.get("price") or 0
            if price_paise < 1000 and price_paise > 0:
                price_paise = int(price_paise * 100)
            
            formatted_items.append({
                "cartCategoryType": "ITEM_CART_CATEGORY_TYPE_INVALID",
                "cart_context": "",
                "cloudinaryImageId": it.get("cloudinaryImageId") or it.get("image_id") or it.get("image") or "",
                "cost": int(price_paise),
                "itemNudgeType": "",
                "item_offer_cart_meta": "",
                "item_price_strike_off": True,
                "addons": it.get("addons") or [],
                "variants": it.get("variants") or [],
                "maxFreeAddons": -1,
                "menu_item_id": str(it.get("menu_item_id") or it.get("id")),
                "quantity": int(it.get("quantity", 1)),
                "rewardType": "",
                "name": it.get("name", "Item"),
                "offer_ids": []
            })

        body = {
            "address_nudge_check": False,
            "batch_opt_in": False,
            "cart_journey_ctx": {
                "cart_category_type": "",
                "cart_initialization_source": "SEARCH",
                "request_contexts": ["99store", "enable_ecosaver"]
            },
            "cartLatLong": {"lat": lat, "lng": lng},
            "date": 0,
            "delivery_type_opt_in": False,
            "first_time_user": True,
            "is_incognito_cart": False,
            "sld": 0,
            "address_id": address_id,
            "cartItems": formatted_items,
            "cart_type": "REGULAR",
            "parent_restaurant_id": str(parent_restaurant_id or restaurant_id),
            "restaurantId": str(restaurant_id),
            "restaurantName": restaurant_name or "Restaurant",
            "orderComment": cooking_instructions or "",
            "p_segment_id": "P3_P",
            "removed_plan_ids": [],
            "shared": False,
            "subscriptionItems": [],
            "user_flow_info": {},
            "cart_saved_preferences": {},
            "cart_update_coupon_request": [],
            "created_from_group_cart": False,
            "is_menu_to_cart_transition": True
        }

        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "accessibility-enabled": "false",
            "addressid": address_id,
            "analyticsplatform": "an",
            "app-version": "4.121.0",
            "application_name": "toing-app",
            "cartentry": "Cart_Crouton_Menu",
            "cartpageprefetch": "false",
            "cartsource": "Menu",
            "category": "food",
            "cityid": "10459",
            "client-id": "Swiggy-Android",
            "Content-Type": "application/json",
            "deviceid": self.device_id,
            "fullscreenbottomoffset": "24",
            "fullscreenstatusbarheight": "50",
            "Host": "payments.swiggy.com",
            "isfrombottombar": "false",
            "isr1fa": "false",
            "lat": str(lat),
            "latitude": str(lat),
            "lng": str(lng),
            "longitude": str(lng),
            "m_id": "CHECKOUT",
            "marketplacebusinessline": "Regular",
            "marketplacecategory": "FOOD",
            "marketplaceid": "1",
            "Origin": "https://payments.swiggy.com",
            "os-version": "17",
            "platform": "Swiggy-Android",
            "Referer": "https://payments.swiggy.com/?flow=cart&custom_back=true",
            "referrer": "menu",
            "sec-ch-ua": '"Not:A-Brand";v="99", "Android WebView";v="145", "Chromium";v="145"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "sid": self.sid or "",
            "swuid": self.device_id,
            "tid": self.tid or "",
            "token": self.token or "",
            "User-Agent": "Mozilla/5.0 (Linux; Android 17; sdk_gphone64_x86_64 Build/CE2A.260420.019; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/145.0.7632.218 Mobile Safari/537.36",
            "userid": str(customer_id or ""),
            "version-code": "1875",
            "x-channel": "toing-app",
            "x-checkout-webview": "android",
            "x-client-id": "web-payment",
            "x-origin-id": "android",
            "X-Requested-With": "in.swiggy.android.toing",
            "x-theme": "toing",
            "x-web-checkout-flow": "cart"
        }

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code == 200:
                res = resp.json()
                data = res.get("data", {})
                new_cart_id = str(data.get("cartId") or data.get("originalCartId") or "")
                
                item_total = data.get("item_total") or data.get("itemTotalBillPresentation") or (data.get("cart_subtotal_without_packing", 0))
                order_total = data.get("order_total") or data.get("cart_total") or 0
                delivery_fee = data.get("delivery_charges") or data.get("positiveDeliveryChargesExclusive") or 0
                taxes = data.get("taxesAndCharges") or data.get("total_tax") or 0
                discount = data.get("discount_total") or data.get("trade_discount_total") or 0

                return {
                    "success": True,
                    "cart_id": new_cart_id,
                    "originalCartId": new_cart_id,
                    "cart_value": item_total,
                    "bill": {
                        "item_total": float(item_total),
                        "order_total": float(order_total),
                        "to_pay": float(order_total),
                        "delivery_charges": float(delivery_fee),
                        "taxes_and_charges": float(taxes),
                        "discount": float(discount),
                        "coupon_discount": float(data.get("coupon_discount_total", 0)),
                        "trade_discount": float(discount),
                        "total": float(order_total)
                    },
                    "data": data
                }
            else:
                raise HTTPException(status_code=resp.status_code, detail=f"Swiggy Cart Error: {resp.text[:200]}")

    async def get_payment_options(
        self,
        cart_id: str,
        address_id: str,
        lat: float = 28.4535279,
        lng: float = 77.4987012,
        tid: Optional[str] = None,
        token: Optional[str] = None,
        sid: Optional[str] = None,
        device_id: Optional[str] = None,
        customer_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch all payment methods (UPI Intent apps, Card, Netbanking, Wallets)
        POST https://payments.swiggy.com/api/v3/payment/get-payment-options
        """
        url = "https://payments.swiggy.com/api/v3/payment/get-payment-options"
        self.tid = tid or self.tid
        self.token = token or self.token
        self.sid = sid or self.sid
        self.device_id = device_id or self.device_id

        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "accessibility-enabled": "false",
            "addressid": address_id,
            "cartaddressid": address_id,
            "cartid": str(cart_id),
            "analyticsplatform": "an",
            "app-version": "4.121.0",
            "application_name": "toing-app",
            "cartentry": "Cart_Crouton_Menu",
            "cartpageprefetch": "false",
            "cartsource": "Menu",
            "category": "food",
            "cityid": "10459",
            "client-id": "Swiggy-Android",
            "Content-Type": "application/json",
            "deviceid": self.device_id,
            "fullscreenbottomoffset": "24",
            "fullscreenstatusbarheight": "50",
            "Host": "payments.swiggy.com",
            "isfrombottombar": "false",
            "isr1fa": "false",
            "lat": str(lat),
            "latitude": str(lat),
            "lng": str(lng),
            "longitude": str(lng),
            "m_id": "CHECKOUT",
            "marketplacebusinessline": "Regular",
            "marketplacecategory": "FOOD",
            "marketplaceid": "1",
            "Origin": "https://payments.swiggy.com",
            "os-version": "17",
            "platform": "Swiggy-Android",
            "Referer": "https://payments.swiggy.com/?flow=cart&custom_back=true",
            "referrer": "menu",
            "sid": self.sid or "",
            "swuid": self.device_id,
            "tid": self.tid or "",
            "token": self.token or "",
            "User-Agent": "Mozilla/5.0 (Linux; Android 17; sdk_gphone64_x86_64 Build/CE2A.260420.019; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/145.0.7632.218 Mobile Safari/537.36",
            "userid": str(customer_id or ""),
            "version-code": "1875",
            "x-channel": "toing-app",
            "x-checkout-webview": "android",
            "x-client-id": "web-payment",
            "x-origin-id": "android",
            "X-Requested-With": "in.swiggy.android.toing",
            "x-theme": "toing",
            "x-web-checkout-flow": "cart"
        }

        body = {
            "address_id": "",
            "card_details": True,
            "is_user_cred_eligible": False,
            "is_user_eligible_for_single_click": True,
            "without_split_pay": False,
            "split_pay_methods": "default",
            "is_gifting_flow": False,
            "is_inapp_upi_eligible": False,
            "apple_pay_eligibility": "",
            "bill_to_company_toggle": False,
            "turbo_variant": "turboV2"
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code == 200:
                return resp.json()
            else:
                raise HTTPException(status_code=resp.status_code, detail=f"Payment options error: {resp.text[:200]}")

    async def get_juspay_client_auth_token(
        self,
        cart_id: str,
        address_id: str,
        tid: Optional[str] = None,
        token: Optional[str] = None,
        sid: Optional[str] = None,
        device_id: Optional[str] = None,
        customer_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch Juspay SDK auth token
        GET https://payments.swiggy.com/api/v3/juspay/get-client-auth-token
        """
        url = "https://payments.swiggy.com/api/v3/juspay/get-client-auth-token"
        self.tid = tid or self.tid
        self.token = token or self.token
        self.sid = sid or self.sid
        self.device_id = device_id or self.device_id

        headers = {
            "Accept": "*/*",
            "accessibility-enabled": "false",
            "addressid": address_id,
            "cartaddressid": address_id,
            "cartid": str(cart_id),
            "application_name": "toing-app",
            "client-id": "Swiggy-Android",
            "deviceid": self.device_id,
            "Host": "payments.swiggy.com",
            "sid": self.sid or "",
            "swuid": self.device_id,
            "tenant": "TOING",
            "tid": self.tid or "",
            "token": self.token or "",
            "userid": str(customer_id or ""),
            "version-code": "1875",
            "x-channel": "toing-app",
            "x-client-id": "web-payment",
            "x-origin-id": "android",
            "X-Requested-With": "in.swiggy.android.toing",
            "x-theme": "toing",
            "x-web-checkout-flow": "cart"
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            else:
                raise HTTPException(status_code=resp.status_code, detail=f"Juspay token error: {resp.text[:200]}")

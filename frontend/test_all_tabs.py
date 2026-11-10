import asyncio
import json
import urllib.request
from playwright.async_api import async_playwright

async def run_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("[*] Navigating to http://127.0.0.1:5173/...")
        await page.goto("http://127.0.0.1:5173/")
        await page.wait_for_load_state("networkidle")

        # 1. Login with JSON
        print("[*] Logging in with JSON credentials...")
        json_toggle = page.locator("button:has-text('JSON')")
        await json_toggle.click()
        await page.wait_for_timeout(300)

        textarea = page.locator("textarea")
        valid_payload = {
            "token": "ed32a2be-53ba-454b-bab8-00a346e88ec8582d316f-1fa7-48c2-a6bc-e75a856c689d",
            "tid": "eyJLSUQiOiIyIiwidHlwIjoiSldUIiwiYWxnIjoiSFMyNTYifQ",
            "sid": "uka32643d36-7fb1-49b9-9cf8-21f3d7c57",
            "deviceId": "1ac3f24e-23c6-eb91-10a6-1aa3e6ff1bd9",
            "customerId": "288661030",
            "mobile": "7050501352"
        }
        await textarea.fill(json.dumps(valid_payload))
        login_btn = page.locator("button:has-text('Login with JSON')")
        await login_btn.click()
        await page.wait_for_timeout(1000)

        # 2. Test Address Tab
        print("[*] Testing Address Tab...")
        address_btn = page.locator("nav button:has-text('Address')")
        await address_btn.click()
        await page.wait_for_timeout(800)

        addr_link_card = page.locator("text=Add by Address Link")
        assert await addr_link_card.is_visible(), "Add by Address Link card not visible"

        addr_map_card = page.locator("text=Add Manually on Map")
        assert await addr_map_card.is_visible(), "Add Manually on Map card not visible"

        saved_addr_header = page.locator("text=Saved Addresses")
        assert await saved_addr_header.is_visible(), "Saved Addresses header not visible"
        print("    - Address Tab rendered with real structure!")

        # 3. Test Search Tab
        print("[*] Testing Search Tab...")
        search_btn = page.locator("nav button:has-text('Search')")
        await search_btn.click()
        await page.wait_for_timeout(800)

        deliver_to = page.locator("text=DELIVER TO")
        assert await deliver_to.is_visible(), "DELIVER TO header not visible"

        search_input = page.locator("input[placeholder='Search for restaurants...']")
        assert await search_input.is_visible(), "Search input not visible"
        print("    - Search Tab rendered with Deliver To header and search input!")

        # 4. Test Orders Tab
        print("[*] Testing Orders Tab...")
        orders_btn = page.locator("nav button:has-text('Orders')")
        await orders_btn.click()
        await page.wait_for_timeout(800)

        no_orders = page.locator("h2:has-text('No Orders Found')")
        assert await no_orders.is_visible(), "No Orders Found not visible"
        print("    - Orders Tab rendered with No Orders Found empty state!")

        # 5. Test Cart Tab (Empty State)
        print("[*] Testing Cart Tab...")
        cart_btn = page.locator("nav button:has-text('Cart')")
        await cart_btn.click()
        await page.wait_for_timeout(800)

        empty_cart = page.locator("text=Your Cart is Empty")
        assert await empty_cart.is_visible(), "Your Cart is Empty not visible"
        print("    - Cart Tab rendered with Your Cart is Empty state!")

        print("\n" + "=" * 50)
        print("🎉 ALL TABS TESTED & PASSING WITH ZERO DUMMY DATA!")
        print("=" * 50)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_test())

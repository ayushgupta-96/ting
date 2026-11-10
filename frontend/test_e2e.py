import asyncio
import json
import urllib.request
from playwright.async_api import async_playwright

async def run_test():
    # 1. Clean DB before test
    try:
        req = urllib.request.Request('http://127.0.0.1:8001/api/auth/accounts')
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode('utf-8'))
            for acc in data.get('accounts', []):
                del_req = urllib.request.Request(
                    f"http://127.0.0.1:8001/api/auth/accounts/{acc['id']}",
                    method='DELETE'
                )
                urllib.request.urlopen(del_req)
        print("[+] DB cleaned for fresh test run.")
    except Exception as e:
        print(f"DB clean error: {e}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("[*] Navigating to http://127.0.0.1:5173/...")
        await page.goto("http://127.0.0.1:5173/")
        await page.wait_for_load_state("networkidle")

        # TEST 1: TAB ROUTING GUARD (Unauthenticated user)
        print("[*] TEST 1: Verifying Tab Routing Guard when activeAccount is null...")
        cart_button = page.locator("nav button:has-text('Cart')")
        await cart_button.click()
        await page.wait_for_timeout(500)

        toast = page.locator("text=Please login to an account first.")
        is_toast_visible = await toast.is_visible()
        print(f"    - Toast visible on clicking Cart: {is_toast_visible}")
        assert is_toast_visible, "Route guard failed to display 'Please login to an account first.'"

        # Confirm we stayed on Accounts tab
        add_acc_header = page.locator("h2:has-text('Add Account')")
        assert await add_acc_header.is_visible(), "Route guard failed to keep active tab on Accounts"
        print("    - Successfully intercepted and snapped back to Accounts tab!")

        # TEST 2: JSON LOGIN FLOW & VALIDATION
        print("[*] TEST 2: Verifying JSON Login Flow...")
        json_toggle = page.locator("button:has-text('JSON')")
        await json_toggle.click()
        await page.wait_for_timeout(300)

        textarea = page.locator("textarea")
        assert await textarea.is_visible(), "JSON credentials textarea not visible"

        login_btn = page.locator("button:has-text('Login with JSON')")
        assert await login_btn.is_visible(), "'Login with JSON' button not visible"

        # Test validation error with incomplete JSON
        print("    - Testing validation on missing fields...")
        await textarea.fill('{"token": "xyz", "mobile": "7050501352"}')
        await login_btn.click()
        await page.wait_for_timeout(500)

        missing_toast = page.locator("text=Missing required fields")
        assert await missing_toast.is_visible(), "Validation failed to report missing required fields"
        print("    - Validation correctly blocked incomplete JSON!")

        # Test valid JSON login
        print("    - Testing valid credential payload...")
        valid_payload = {
            "token": "ed32a2be-53ba-454b-bab8-00a346e88ec8582d316f-1fa7-48c2-a6bc-e75a856c689d",
            "tid": "eyJLSUQiOiIyIiwidHlwIjoiSldUIiwiYWxnIjoiSFMyNTYifQ",
            "sid": "uka32643d36-7fb1-49b9-9cf8-21f3d7c57",
            "deviceId": "1ac3f24e-23c6-eb91-10a6-1aa3e6ff1bd9",
            "customerId": "288661030",
            "mobile": "7050501352"
        }
        await textarea.fill(json.dumps(valid_payload))
        await login_btn.click()
        await page.wait_for_timeout(1000)

        success_toast = page.locator("text=Account added successfully")
        assert await success_toast.is_visible(), "Success toast 'Account added successfully' not found"
        print("    - Green success toast displayed: 'Account added successfully'!")

        # Verify active account in TopBar and Saved Accounts list
        top_bar_account = page.locator("header").locator("text=7050501352")
        assert await top_bar_account.is_visible(), "Active account phone not updated in TopBar"

        saved_card = page.locator("main").locator("text=7050501352")
        assert await saved_card.is_visible(), "Saved account card not rendered in list"
        print("    - Account +91 7050501352 active in TopBar and Saved Accounts list!")

        # TEST 3: FREE NAVIGATION & ZERO DUMMY DATA IN ORDERS
        print("[*] TEST 3: Verifying navigation to Orders and zero dummy data...")
        orders_button = page.locator("nav button:has-text('Orders')")
        await orders_button.click()
        await page.wait_for_timeout(800)

        no_orders_heading = page.locator("h2:has-text('No Orders Found')")
        assert await no_orders_heading.is_visible(), "Empty state 'No Orders Found' not displayed"

        subtitle = page.locator("text=This account has no orders yet.")
        assert await subtitle.is_visible(), "'This account has no orders yet.' subtitle not displayed"

        refresh_btn = page.locator("button:has-text('Refresh')")
        assert await refresh_btn.is_visible(), "Refresh button not visible in Orders empty state"
        print("    - Orders tab displays exact 'No Orders Found' empty state with ZERO dummy orders!")

        # TEST 4: VERIFY REFRESH SNAPS BACK TO ACCOUNTS
        print("[*] TEST 4: Verifying page reload resets activeAccount to null and triggers route guard...")
        await page.reload()
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(500)

        # On fresh reload, user is not logged in: click Address
        address_btn = page.locator("nav button:has-text('Address')")
        await address_btn.click()
        await page.wait_for_timeout(500)

        toast_reload = page.locator("text=Please login to an account first.")
        assert await toast_reload.is_visible(), "Guard did not trigger on fresh reload"
        print("    - Fresh reload properly reset activeAccount to null and intercepted navigation!")

        print("\n" + "=" * 50)
        print("🎉 ALL 4 TESTS PASSED FLAWLESSLY! ZERO DUMMY DATA.")
        print("=" * 50)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_test())

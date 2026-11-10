import asyncio
import os
import json
from playwright.async_api import async_playwright

TEST_JSON = """{
  "token": "e30.eyJsYXN0X3JlZnJlc2hlZCI6MTc2ODcxNjQ3MiwidWlkIjoxNDg4MDQwMTE2LCJ1c2VyX25hbWUiOiJQcmluY2UiLCJleHAiOjE3NzY0OTI0NzIsImlhdCI6MTc2ODcxNjQ3Mn0.fake",
  "tid": "test_tid_token_12345",
  "sid": "test_sid_token_67890",
  "deviceId": "test_device_e2e",
  "customerId": "1488040116",
  "mobile": "7050501352"
}"""

ARTIFACT_DIR = r"C:\Users\akg79\.gemini\antigravity\brain\f4b377a6-8895-47c0-8a2d-f0d08bd2704a"

async def test_flow():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 390, "height": 844})
        page = await context.new_page()

        page.on("console", lambda msg: print(f"[CONSOLE] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))

        print("=== Step 1: Open Mini-App and Login with JSON ===")
        await page.goto("http://localhost:5173", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Ensure active account via JSON login
        await page.locator("button:has-text('JSON')").click()
        await page.wait_for_timeout(300)
        await page.locator("textarea").fill(TEST_JSON)
        await page.locator("button:has-text('Login with JSON')").click()
        await page.wait_for_timeout(1500)

        print("=== Step 2: Select Delivery Address ===")
        await page.locator("nav button:has-text('Address')").click()
        await page.wait_for_timeout(2000)

        # Select Prince address card
        prince_addr = page.locator("text=Prince").first
        if await prince_addr.count() > 0:
            await prince_addr.click()
            print("Selected Prince address.")
        else:
            first_card = page.locator("text=HOME, text=FRIENDS").first
            await first_card.click()
            print("Selected fallback address.")
        await page.wait_for_timeout(1000)

        print("=== Step 3: Search Tab & Menu 'EXPLORE THIS MENU' Verification ===")
        await page.locator("nav button:has-text('Search')").click()
        await page.wait_for_timeout(1500)

        # Search for restaurant
        search_input = page.locator("input[placeholder='Search for restaurants...']")
        await search_input.fill("beeji de")
        print("Waiting for 'Beeji De Chole Bhature' restaurant to appear...")
        await page.wait_for_selector("text=Beeji De Chole Bhature", timeout=25000)
        print("Found 'Beeji De Chole Bhature' restaurant!")

        # Click restaurant to open menu
        await page.locator("text=Beeji De Chole Bhature").first.click()
        await page.wait_for_timeout(1500)

        # 1. VERIFY: 'EXPLORE THIS MENU' MUST NOT BE VISIBLE BY DEFAULT
        body_text_initial = await page.inner_text("body")
        assert "EXPLORE THIS MENU" not in body_text_initial, "ERROR: 'EXPLORE THIS MENU' is visible before clicking search dishes!"
        print("-> PASS: 'EXPLORE THIS MENU' is correctly hidden on initial restaurant view.")
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "menu_explore_hidden.png"))

        # 2. CLICK 'Search dishes in this restaurant'
        dish_input = page.locator("input[placeholder='Search dishes in this restaurant']")
        await dish_input.click()
        await page.wait_for_timeout(800)

        # 3. VERIFY: 'EXPLORE THIS MENU' NOW APPEARS
        body_text_after_click = await page.inner_text("body")
        assert "EXPLORE THIS MENU" in body_text_after_click, "ERROR: 'EXPLORE THIS MENU' did not appear when clicking search dishes!"
        print("-> PASS: 'EXPLORE THIS MENU' appeared when clicking search dishes.")
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "menu_explore_visible.png"))

        print("=== Step 4: Add dish to cart ===")
        add_btn = page.locator("button:has-text('ADD')").first
        await add_btn.click()
        await page.wait_for_timeout(1000)

        print("=== Step 5: Navigate to Cart Tab ===")
        await page.locator("nav button:has-text('Cart')").click()
        await page.wait_for_timeout(2000)

        cart_text = await page.inner_text("body")
        print("Cart Tab Loaded:")
        print(cart_text[:600])

        assert "Bill Details" in cart_text, "Missing Bill Details card in Cart"
        assert "Pay Now" in cart_text, "Missing Pay Now button"
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "cart_before_checkout.png"))

        print("=== Step 6: Click Pay Now & Verify Real Order Creation ===")
        pay_now_btn = page.locator("button:has-text('Pay Now')")
        await pay_now_btn.click()
        await page.wait_for_timeout(3500)

        checkout_text = await page.inner_text("body")
        print("Checkout / Payment Screen Loaded:")
        print(checkout_text[:800])
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "checkout_order_created.png"))

        # Verify Order Created banner and elements matching screenshot media_1794311764986_e216a4f5.png
        assert "Pay via UPI App" in checkout_text, "Missing 'Pay via UPI App' button"
        assert "Check Payment" in checkout_text, "Missing 'Check Payment' button"
        assert "Verifying your payment with Toing" in checkout_text, "Missing verification status text"
        assert "Selected Delivery Address" in checkout_text, "Missing Selected Delivery Address card"
        assert "Order Items Summary" in checkout_text, "Missing Order Items Summary card"
        assert "Bill Details Breakdown" in checkout_text, "Missing Bill Details Breakdown card"

        print("=== SUCCESS: ALL VERIFICATION REQUIREMENTS PASSED 100% ===")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_flow())

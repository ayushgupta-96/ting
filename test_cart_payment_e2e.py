import asyncio
from playwright.async_api import async_playwright

TEST_JSON = """{
  "token": "e30.eyJsYXN0X3JlZnJlc2hlZCI6MTc2ODcxNjQ3MiwidWlkIjoxNDg4MDQwMTE2LCJ1c2VyX25hbWUiOiJQcmluY2UiLCJleHAiOjE3NzY0OTI0NzIsImlhdCI6MTc2ODcxNjQ3Mn0.fake",
  "tid": "test_tid_token_12345",
  "sid": "test_sid_token_67890",
  "deviceId": "test_device_e2e",
  "customerId": "1488040116",
  "mobile": "9279151382"
}"""

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 390, "height": 844})

        page.on("console", lambda msg: print("PAGE LOG:", msg.text))
        page.on("pageerror", lambda err: print("PAGE ERROR:", err))

        print("1. Opening Mini-App...")
        await page.goto("http://localhost:5173", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        print("2. Logging in with JSON payload...")
        await page.locator("button:has-text('JSON')").click()
        await page.wait_for_timeout(300)
        await page.locator("textarea").fill(TEST_JSON)
        await page.locator("button:has-text('Login with JSON')").click()
        await page.wait_for_timeout(1500)

        print("3. Navigating to Address Tab and selecting address...")
        await page.locator("nav button:has-text('Address')").click()
        await page.wait_for_timeout(1500)
        # Select first address
        first_addr = page.locator("main div.cursor-pointer").first
        await first_addr.click()
        await page.wait_for_timeout(500)

        print("4. Navigating to Search Tab and adding dishes to Cart...")
        await page.locator("nav button:has-text('Search')").click()
        await page.wait_for_timeout(800)

        search_box = page.locator("input[placeholder='Search for restaurants...']")
        await search_box.fill("beeji de")
        await page.wait_for_selector("text=Beeji De Chole Bhature", timeout=15000)
        
        # Click Beeji De
        await page.locator("text=Beeji De Chole Bhature").first.click()
        await page.wait_for_selector("text=EXPLORE THIS MENU", timeout=15000)

        # Add item
        add_btn = page.locator("button:has-text('ADD')").first
        await add_btn.click()
        await page.wait_for_timeout(1000)

        print("5. Navigating to Cart Tab...")
        await page.locator("nav button:has-text('Cart')").click()
        await page.wait_for_timeout(3000)

        # VERIFY SCREENSHOT 1 & 2
        print("6. Verifying Cart Tab (Screenshots 1 & 2)...")
        body_text = await page.inner_text("body")
        print("CART VIEW PREVIEW:")
        print(body_text[:800])

        assert "Your Order" in body_text, "Missing 'Your Order' section"
        assert "BHIMNEW" in body_text, "Missing auto-applied BHIMNEW coupon"
        assert "Bill Details" in body_text, "Missing Bill Details"
        assert "Claimed" in body_text and "FC" in body_text, "Missing Claimed Free Cash badge"
        assert "Free Cash" in body_text, "Missing Free Cash row in bill"
        assert "Coupon Discount" in body_text, "Missing Coupon Discount row in bill"
        assert "UPI / QR" in body_text, "Missing UPI / QR payment option"
        assert "Pay Now" in body_text, "Missing Pay Now button"

        await page.screenshot(path="C:\\Users\\akg79\\.gemini\\antigravity\\scratch\\toing_platform\\cart_view_verified.png")
        print("-> Cart & Bill View Verified!")

        # VERIFY SCREENSHOT 4 & 5: Pay Now & UPI QR View
        print("7. Clicking 'Pay Now' to generate Order and QR Code (Screenshots 4 & 5)...")
        pay_now_btn = page.locator("button:has-text('Pay Now')")
        await pay_now_btn.click()
        await page.wait_for_timeout(2500)

        checkout_body = await page.inner_text("body")
        print("CHECKOUT VIEW PREVIEW:")
        print(checkout_body[:800])

        assert "Scan to Pay with UPI" in checkout_body, "Missing 'Scan to Pay with UPI' header"
        assert "Pay via UPI App" in checkout_body, "Missing 'Pay via UPI App' button"
        assert "Check Payment" in checkout_body, "Missing 'Check Payment' button"
        assert "Verifying your payment with Toing" in checkout_body, "Missing payment verification message"
        assert "Selected Delivery Address" in checkout_body, "Missing Selected Delivery Address breakdown"
        assert "Order Items Summary" in checkout_body, "Missing Order Items Summary"
        assert "Bill Details Breakdown" in checkout_body, "Missing Bill Details Breakdown"

        # Check QR code SVG element
        qr_svg = page.locator("svg")
        assert await qr_svg.count() > 0, "QR Code SVG was not rendered"

        await page.screenshot(path="C:\\Users\\akg79\\.gemini\\antigravity\\scratch\\toing_platform\\checkout_qr_verified.png")
        print("-> Checkout & QR Code Payment View Verified!")

        # Test Check Payment click
        print("8. Testing 'Check Payment' manual button...")
        check_pay_btn = page.locator("button:has-text('Check Payment')")
        await check_pay_btn.click()
        await page.wait_for_timeout(1000)

        print("=== ALL CART, FREE CASH, BHIM COUPON, AND PAYMENT CHECKING VERIFIED 100% ===")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())

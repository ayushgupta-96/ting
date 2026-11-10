import asyncio
import json
from playwright.async_api import async_playwright

TEST_PAYLOAD = json.dumps({
    "token": "e30.eyJsYXN0X3JlZnJlc2hlZCI6MTc2ODcxNjQ3MiwidWlkIjoxNDg4MDQwMTE2LCJ1c2VyX25hbWUiOiJQcmluY2UiLCJleHAiOjE3NzY0OTI0NzIsImlhdCI6MTc2ODcxNjQ3Mn0.fake",
    "tid": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.fake",
    "sid": "test_sid_dyn",
    "deviceId": "dev_dyn",
    "customerId": "1488040116",
    "mobile": "9279151382"
})

async def run():
    print("\n--- Testing Synchronized Dynamic Cart & Toing Coupons ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 390, "height": 844})

        page.on("console", lambda msg: print("PAGE LOG:", msg.text))
        page.on("pageerror", lambda err: print("PAGE ERROR:", err))

        print("1. Opening app...")
        await page.goto("http://localhost:5173", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        print("2. Logging in with test JSON...")
        await page.locator("button:has-text('JSON')").click()
        await page.wait_for_timeout(300)
        await page.locator("textarea").fill(TEST_PAYLOAD)
        await page.locator("button:has-text('Login with JSON')").click()
        await page.wait_for_timeout(1500)

        print("3. Navigating to Address and selecting address...")
        await page.locator("nav button:has-text('Address')").click()
        await page.wait_for_timeout(1500)
        first_addr = page.locator("main div.cursor-pointer").first
        await first_addr.click()
        await page.wait_for_timeout(500)

        print("4. Navigating to Search and adding dish to Cart...")
        await page.locator("nav button:has-text('Search')").click()
        await page.wait_for_timeout(800)
        search_box = page.locator("input[placeholder='Search for restaurants...']")
        await search_box.fill("beeji de")
        await page.wait_for_selector("text=Beeji De Chole Bhature", timeout=15000)
        await page.locator("text=Beeji De Chole Bhature").first.click()
        await page.wait_for_selector("button:has-text('ADD')", timeout=15000)
        await page.locator("button:has-text('ADD')").first.click()
        await page.wait_for_timeout(1000)

        print("5. Navigating to Cart...")
        await page.locator("nav button:has-text('Cart')").click()
        await page.wait_for_timeout(3000)

        body_text = await page.inner_text("body")
        print("\nCART PAGE CONTENT:")
        print(body_text[:1000])

        assert "Your Order" in body_text
        assert "Bill Details" in body_text

        # Verify that Bill Details has dynamic lines (Item Total, Delivery Fee, To Pay)
        assert "Item Total" in body_text
        assert "To Pay" in body_text

        # Click "Change" or "View Coupons" to open the Toing Offers Modal
        print("\n6. Opening Toing Coupons Modal...")
        coupon_btn = page.locator("button:has-text('Change'), button:has-text('View Coupons')").first
        await coupon_btn.click()
        await page.wait_for_timeout(1000)

        modal_text = await page.inner_text("body")
        print("\nCOUPONS MODAL CONTENT:")
        print(modal_text[modal_text.find("Apply Coupon Code"):modal_text.find("Apply Coupon Code") + 600])

        assert "Apply Coupon Code" in modal_text
        assert "AVAILABLE OFFERS FROM TOING" in modal_text

        # Screenshot of the dynamic modal
        await page.screenshot(path=r"C:\Users\akg79\.gemini\antigravity\scratch\toing_platform\cart_dynamic_coupons.png")
        print("✓ Verified dynamic coupons modal from Toing!")

        # Close modal by clicking X or backdrop
        await page.locator("div.fixed button >> svg.lucide-x").click()
        await page.wait_for_timeout(800)

        print("\n7. Clicking 'Pay Now' to check dynamic Bill Breakdown in Checkout...")
        pay_btn = page.locator("button:has-text('Pay Now')")
        await pay_btn.click()
        await page.wait_for_selector("text=Scan to Pay with UPI", timeout=15000)

        checkout_text = await page.inner_text("body")
        print("\nCHECKOUT SCREEN:")
        print(checkout_text[:800])
        assert "Scan to Pay with UPI" in checkout_text
        assert "Bill Details Breakdown" in checkout_text
        assert "Order Items Summary" in checkout_text

        await page.screenshot(path=r"C:\Users\akg79\.gemini\antigravity\scratch\toing_platform\checkout_dynamic_bill.png")
        print("✓ Verified dynamic checkout view!")

        await browser.close()
        print("\n=== ALL DYNAMIC CART & SYNCHRONIZED COUPONS TESTS PASSED ===")

if __name__ == "__main__":
    asyncio.run(run())

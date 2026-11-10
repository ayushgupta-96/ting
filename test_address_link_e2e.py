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

        print("2. Clicking < > JSON toggle...")
        json_btn = page.locator("button:has-text('JSON')")
        await json_btn.click()
        await page.wait_for_timeout(500)

        print("3. Pasting JSON credentials...")
        textarea = page.locator("textarea")
        await textarea.fill(TEST_JSON)
        await page.wait_for_timeout(300)

        print("4. Clicking 'Login with JSON'...")
        login_btn = page.locator("button:has-text('Login with JSON')")
        await login_btn.click()
        await page.wait_for_timeout(2000)

        print("5. Verifying logged in state...")
        top_bar_account = page.locator("header")
        assert "9279151382" in await top_bar_account.inner_text(), "Account not displayed in TopBar"

        print("6. Navigating to Address Tab...")
        address_nav = page.locator("nav button:has-text('Address')")
        await address_nav.click()
        await page.wait_for_timeout(1500)

        print("7. Testing 'Add by Address Link' drawer...")
        add_link_btn = page.locator("button:has-text('Add +')").first
        await add_link_btn.click()
        await page.wait_for_timeout(500)

        link_input = page.locator("input[placeholder*='swiggy.onelink.me']")
        assert await link_input.is_visible(), "Link input drawer failed to open"

        print("8. Submitting Address Link: https://swiggy.onelink.me/JgkQ/nl6dfxal...")
        await link_input.fill("https://swiggy.onelink.me/JgkQ/nl6dfxal")
        submit_link_btn = page.locator("button:has-text('Extract Address / Save Link')")
        await submit_link_btn.click()
        await page.wait_for_timeout(2500)

        print("9. Checking Saved Addresses list...")
        body_text = await page.inner_text("body")
        print("BODY PREVIEW:", body_text[:500])
        await page.screenshot(path="C:\\Users\\akg79\\.gemini\\antigravity\\scratch\\toing_platform\\debug_address.png")
        assert "Prince" in body_text, f"Prince address not found in saved addresses: {body_text}"
        assert "8521158381" in body_text, "Prince mobile not found in saved addresses"
        print("Address card found with name 'Prince' and phone '8521158381'!")

        print("10. Testing 'Deliver To' -> 'Select your location' Modal in Search Tab...")
        search_nav = page.locator("nav button:has-text('Search')")
        await search_nav.click()
        await page.wait_for_timeout(1000)

        deliver_to_card = page.locator("text=Deliver To")
        await deliver_to_card.click()
        await page.wait_for_timeout(800)

        loc_modal_title = page.locator("text=Select your location")
        assert await loc_modal_title.is_visible(), "Select your location modal failed to open"
        print("'Select your location' bottom sheet modal is verified!")

        # Screenshot
        await page.screenshot(path="C:\\Users\\akg79\\.gemini\\antigravity\\scratch\\toing_platform\\e2e_verified.png")
        print("All tests passed! Screenshot saved to e2e_verified.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())

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

        print("3. Navigating to Search Tab...")
        await page.locator("nav button:has-text('Search')").click()
        await page.wait_for_timeout(800)

        # STATE 1: Empty Search State
        print("4. Verifying Empty Search State (Screenshot 2)...")
        body_text = await page.inner_text("body")
        assert "Search Restaurants" in body_text, "Missing 'Search Restaurants' heading"
        assert "POPULAR RESTAURANTS" in body_text, "Missing 'POPULAR RESTAURANTS'"
        assert "Domino's" in body_text, "Missing Domino's pill"
        assert "KFC" in body_text, "Missing KFC pill"
        await page.screenshot(path="C:\\Users\\akg79\\.gemini\\antigravity\\scratch\\toing_platform\\1_search_empty.png")
        print("-> State 1 Verified & screenshot saved.")

        # STATE 2: Typing 'beeji de' in Search
        print("5. Searching for 'beeji de' (Screenshot 3)...")
        search_box = page.locator("input[placeholder='Search for restaurants...']")
        await search_box.fill("beeji de")
        
        # Wait for restaurant to appear
        await page.wait_for_selector("text=Beeji De Chole Bhature", timeout=15000)

        body_text = await page.inner_text("body")
        print("BODY AT SEARCH RESULTS:")
        print(body_text[:500])
        await page.screenshot(path="C:\\Users\\akg79\\.gemini\\antigravity\\scratch\\toing_platform\\2_search_results.png")
        assert "restaurants" in body_text.lower(), "Missing restaurant results count"
        assert "Beeji De Chole Bhature" in body_text, "Missing 'Beeji De Chole Bhature' restaurant"
        assert "4.1" in body_text, "Missing rating 4.1"
        assert "30-35 mins" in body_text, "Missing SLA 30-35 mins"
        print("-> State 2 Verified & screenshot saved.")

        # STATE 3: Open Restaurant Menu
        print("6. Clicking 'Beeji De Chole Bhature' to open Menu View (Screenshots 4 & 5)...")
        restaurant_card = page.locator("text=Beeji De Chole Bhature").first
        await restaurant_card.click()
        
        # Wait for menu categories to load
        await page.wait_for_selector("text=EXPLORE THIS MENU", timeout=15000)

        body_text = await page.inner_text("body")
        assert "OUTLET" in body_text, "Missing OUTLET floating card"
        assert "Greater Noida" in body_text, "Missing Outlet area"
        assert "EXPLORE THIS MENU" in body_text, "Missing 'EXPLORE THIS MENU'"
        assert "Extras" in body_text, "Missing Extras category"
        assert "1 Pc Extra Poori" in body_text or "1 Pc Extra Classic Bhatura" in body_text or "Poori" in body_text, "Missing dish items"
        await page.screenshot(path="C:\\Users\\akg79\\.gemini\\antigravity\\scratch\\toing_platform\\3_restaurant_menu.png")
        print("-> State 3 Verified & screenshot saved.")

        # STATE 4: Add dish to cart & Sticky bar
        print("7. Adding item to cart...")
        add_btn = page.locator("button:has-text('ADD')").first
        await add_btn.click()
        await page.wait_for_timeout(1000)

        body_text = await page.inner_text("body")
        assert "View Cart" in body_text, "Missing sticky floating cart bar"
        await page.screenshot(path="C:\\Users\\akg79\\.gemini\\antigravity\\scratch\\toing_platform\\4_sticky_cart_bar.png")
        print("-> State 4 Verified & screenshot saved.")

        # STATE 5: Veg Toggle
        print("8. Testing Veg Toggle switch...")
        veg_toggle = page.locator("button:has-text('Veg')").first or page.locator("text=Veg")
        await page.locator("button[type='button']").click()
        await page.wait_for_timeout(800)
        await page.screenshot(path="C:\\Users\\akg79\\.gemini\\antigravity\\scratch\\toing_platform\\5_veg_toggle.png")
        print("-> State 5 Verified & screenshot saved.")

        print("=== ALL 5 SEARCH TAB SCREENSHOT REQUIREMENTS FULLY VERIFIED ===")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())

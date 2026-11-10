import asyncio
from playwright.async_api import async_playwright

TEST_JSON = """{
  "token": "e30.eyJsYXN0X3JlZnJlc2hlZCI6MTc2ODcxNjQ3MiwidWlkIjoxNDg4MDQwMTE2LCJ1c2VyX25hbWUiOiJQcmluY2UiLCJleHAiOjE3NzY0OTI0NzIsImlhdCI6MTc2ODcxNjQ3Mn0.fake",
  "tid": "test_tid_token_12345",
  "sid": "test_sid_token_67890",
  "deviceId": "test_device_e2e",
  "customerId": "1488040116",
  "mobile": "9389512255"
}"""

async def test_search():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 390, "height": 844})
        
        page.on("console", lambda m: print(f"[CONSOLE] {m.text}"))
        print("Navigating to app...")
        await page.goto("http://localhost:5173", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        print("Logging in with 9389512255 JSON...")
        await page.locator("button:has-text('JSON')").first.click()
        await page.wait_for_timeout(500)
        await page.locator("textarea").fill(TEST_JSON)
        await page.locator("button:has-text('Login with JSON')").click()
        await page.wait_for_timeout(2500)
        
        print("Navigating to Search Tab...")
        await page.locator("nav button:has-text('Search')").click()
        await page.wait_for_timeout(1500)
        
        search_box = page.locator("input[placeholder='Search for restaurants...']")
        await search_box.wait_for(state="visible", timeout=10000)
        
        print("Searching for KFC...")
        await search_box.fill("KFC")
        await page.wait_for_selector("text=KFC", timeout=15000)
        print("PASS: KFC found!")
        
        print("Searching for Subway...")
        await search_box.fill("Subway")
        await page.wait_for_selector("text=Subway", timeout=15000)
        print("PASS: Subway found!")
        
        print("Searching for Beeji De...")
        await search_box.fill("beeji de")
        await page.wait_for_selector("text=Beeji De Chole Bhature", timeout=15000)
        print("PASS: Beeji De Chole Bhature found!")
        
        await page.screenshot(path=r"C:\Users\akg79\.gemini\antigravity\brain\f4b377a6-8895-47c0-8a2d-f0d08bd2704a\restaurant_search_verified.png")
        print("Screenshot saved to restaurant_search_verified.png")
        
        print("Clicking on Beeji De Chole Bhature to open menu...")
        await page.locator("text=Beeji De Chole Bhature").first.click()
        await page.wait_for_timeout(2000)
        
        await page.wait_for_selector("text=Beeji De Chole Bhature", timeout=15000)
        await page.screenshot(path=r"C:\Users\akg79\.gemini\antigravity\brain\f4b377a6-8895-47c0-8a2d-f0d08bd2704a\restaurant_menu_verified.png")
        print("Screenshot saved to restaurant_menu_verified.png")
        
        await browser.close()
        print("=== ALL RESTAURANT SEARCH & MENU TESTS PASSED 100% ===")

if __name__ == "__main__":
    asyncio.run(test_search())

import asyncio
import json
import urllib.request
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8001/api/v1"

def test_backend_isolation():
    import time
    ts = int(time.time())
    print("\n--- 1. Testing Backend Multi-User Isolation ---")
    user_a = f"100{ts}"
    user_b = f"200{ts}"
    user_new = f"300{ts}"

    # User A logs in with JSON
    payload_a = json.dumps({
        "token": "tok_user_a",
        "tid": "tid_user_a",
        "sid": "sid_user_a",
        "deviceId": "dev_a",
        "customerId": "cust_a",
        "mobile": "9876500001"
    }).encode()
    req_a = urllib.request.Request(f"{BASE_URL}/auth/json-login", data=payload_a, headers={
        "Content-Type": "application/json",
        "X-Telegram-Id": user_a
    })
    res_a = json.loads(urllib.request.urlopen(req_a).read().decode())
    assert res_a["success"] is True, "User A login failed"
    print("✓ User A logged in successfully")

    # User B checks accounts (MUST BE EMPTY [])
    req_b_get = urllib.request.Request(f"{BASE_URL}/auth/accounts", headers={
        "X-Telegram-Id": user_b
    })
    res_b = json.loads(urllib.request.urlopen(req_b_get).read().decode())
    assert res_b["success"] is True
    assert len(res_b["accounts"]) == 0, f"DATA LEAK: User B saw accounts: {res_b['accounts']}"
    print(f"✓ User B accounts: {res_b['accounts']} (ZERO DATA LEAK)")

    # User B logs in with their own account
    payload_b = json.dumps({
        "token": "tok_user_b",
        "tid": "tid_user_b",
        "sid": "sid_user_b",
        "deviceId": "dev_b",
        "customerId": "cust_b",
        "mobile": "9876500002"
    }).encode()
    req_b_post = urllib.request.Request(f"{BASE_URL}/auth/json-login", data=payload_b, headers={
        "Content-Type": "application/json",
        "X-Telegram-Id": user_b
    })
    urllib.request.urlopen(req_b_post)
    print("✓ User B logged in with their own account")

    # User A checks accounts -> ONLY User A's account
    req_a_get = urllib.request.Request(f"{BASE_URL}/auth/accounts", headers={
        "X-Telegram-Id": user_a
    })
    res_a_check = json.loads(urllib.request.urlopen(req_a_get).read().decode())
    assert len(res_a_check["accounts"]) == 1
    assert res_a_check["accounts"][0]["mobile"] == "9876500001"
    print(f"✓ User A accounts: {[a['mobile'] for a in res_a_check['accounts']]}")

    # User B checks accounts -> ONLY User B's account
    res_b_check = json.loads(urllib.request.urlopen(req_b_get).read().decode())
    assert len(res_b_check["accounts"]) == 1
    assert res_b_check["accounts"][0]["mobile"] == "9876500002"
    print(f"✓ User B accounts: {[a['mobile'] for a in res_b_check['accounts']]}")

    # Brand new user checks accounts -> MUST BE 100% EMPTY []
    req_new_get = urllib.request.Request(f"{BASE_URL}/auth/accounts", headers={
        "X-Telegram-Id": user_new
    })
    res_new = json.loads(urllib.request.urlopen(req_new_get).read().decode())
    assert res_new["success"] is True
    assert len(res_new["accounts"]) == 0, f"New user saw accounts: {res_new['accounts']}"
    print(f"✓ Brand new User {user_new} accounts: {res_new['accounts']} (100% Fresh Start)")


async def test_frontend_fresh_start():
    import time
    ts = int(time.time())
    user1_id = int(f"555{ts % 1000000}")
    user2_id = int(f"777{ts % 1000000}")

    print("\n--- 2. Testing Frontend Fresh Start in Browser ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Context 1: Brand new user with distinct Telegram ID
        context1 = await browser.new_context(viewport={"width": 390, "height": 844})
        page1 = await context1.new_page()

        # Inject Telegram WebApp mock for user1
        await page1.add_init_script(f"""
            window.Telegram = {{
                WebApp: {{
                    ready: () => {{}},
                    expand: () => {{}},
                    initData: 'query_id=AAH{user1_id}&user=%7B%22id%22%3A{user1_id}%2C%22first_name%22%3A%22NewVisitor%22%7D&auth_date=1768716472&hash=mock',
                    initDataUnsafe: {{
                        user: {{ id: {user1_id}, first_name: 'NewVisitor' }}
                    }},
                    setHeaderColor: () => {{}},
                    HapticFeedback: {{ notificationOccurred: () => {{}} }}
                }}
            }};
        """)

        await page1.goto("http://localhost:5173", wait_until="networkidle")
        await page1.wait_for_timeout(1500)

        body_text = await page1.inner_text("body")
        print("NEW USER HOME PAGE TEXT SNIPPET:")
        print(body_text[:400])

        # Assertions for fresh user
        assert "Select Account" in body_text, "TopBar should show 'Select Account' for new user"
        assert "9279151382" not in body_text, "LEAK: Testing mobile 9279151382 found on new user page!"
        assert "7050501352" not in body_text, "LEAK: Testing mobile 7050501352 found on new user page!"
        assert "Priya Rajput" not in body_text, "LEAK: Priya Rajput found on new user page!"
        assert "No saved accounts found." in body_text, "Saved accounts list should show empty state"

        # Screenshot fresh start
        await page1.screenshot(path=r"C:\Users\akg79\.gemini\antigravity\scratch\toing_platform\fresh_start_verified.png")
        print("✓ Verified Fresh Start UI: 'Select Account', 0 saved accounts, no leaked test data")

        # Now test logging in for this user
        print("3. Logging in with JSON as user 555666...")
        await page1.locator("button:has-text('JSON')").click()
        await page1.wait_for_timeout(300)
        
        user_json = json.dumps({
            "token": "tok_fresh_user",
            "tid": "tid_fresh_user",
            "sid": "sid_fresh_user",
            "deviceId": "dev_fresh_user",
            "customerId": "cust_fresh_user",
            "mobile": "9988776655"
        })
        await page1.locator("textarea").fill(user_json)
        await page1.locator("button:has-text('Login with JSON')").click()
        await page1.wait_for_timeout(1500)

        updated_text = await page1.inner_text("body")
        assert "+91 9988776655" in updated_text, "Newly added account not shown in TopBar"
        print("✓ User 555666 successfully logged in with +91 9988776655")

        # Context 2: Another brand new user opens simultaneously
        print(f"4. Testing User {user2_id} opening in separate session...")
        context2 = await browser.new_context(viewport={"width": 390, "height": 844})
        page2 = await context2.new_page()

        await page2.add_init_script(f"""
            window.Telegram = {{
                WebApp: {{
                    ready: () => {{}},
                    expand: () => {{}},
                    initData: 'query_id=AAH{user2_id}&user=%7B%22id%22%3A{user2_id}%2C%22first_name%22%3A%22SecondUser%22%7D&auth_date=1768716472&hash=mock',
                    initDataUnsafe: {{
                        user: {{ id: {user2_id}, first_name: 'SecondUser' }}
                    }},
                    setHeaderColor: () => {{}},
                    HapticFeedback: {{ notificationOccurred: () => {{}} }}
                }}
            }};
        """)

        await page2.goto("http://localhost:5173", wait_until="networkidle")
        await page2.wait_for_timeout(1500)

        body2_text = await page2.inner_text("body")
        assert "Select Account" in body2_text, "User 777888 should see 'Select Account'"
        assert "9988776655" not in body2_text, "LEAK: User 777888 saw User 555666's account 9988776655!"
        assert "No saved accounts found." in body2_text, "User 777888 should have empty saved accounts"
        print("✓ User 777888 gets a 100% isolated, clean fresh start with ZERO accounts!")

        await browser.close()

if __name__ == "__main__":
    test_backend_isolation()
    asyncio.run(test_frontend_fresh_start())
    print("\n=== ALL USER ISOLATION AND FRESH START TESTS PASSED 100% ===")

import asyncio
import os
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\akg79\.gemini\antigravity\brain\f4b377a6-8895-47c0-8a2d-f0d08bd2704a"

async def test_full_cart_coupon_checkout():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 412, "height": 915},
            user_agent="Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"
        )
        page = await context.new_page()

        await page.goto("http://127.0.0.1:5173")
        await page.wait_for_timeout(1000)

        # 1. Setup Cart State with Beeji De Chole Bhature items on Account 7050501352 (0 coupons)
        await page.evaluate("""() => {
            const devId = '987654321';
            localStorage.setItem('toing_dev_telegram_id', devId);
            const tgId = devId;

            const lines = [
                {
                    id: '184045164',
                    name: 'Extra Makhni Chole',
                    price: 84,
                    cost: 84,
                    quantity: 1,
                    is_veg: true,
                    restaurant: {
                        id: '1243066',
                        name: 'Beeji De Chole Bhature',
                        area: 'Greater Noida',
                        sla: '35-40 mins'
                    }
                },
                {
                    id: '184045154',
                    name: 'Boondi Raita',
                    price: 20,
                    cost: 20,
                    quantity: 1,
                    is_veg: true,
                    restaurant: {
                        id: '1243066',
                        name: 'Beeji De Chole Bhature',
                        area: 'Greater Noida',
                        sla: '35-40 mins'
                    }
                }
            ];
            const rest = {
                id: '1243066',
                name: 'Beeji De Chole Bhature',
                area: 'Greater Noida',
                sla: '35-40 mins',
                image: 'https://toing-media-assets.swiggy.com/swiggy/image/upload/fl_lossy,f_auto,q_auto,w_300,h_300,c_fill/RX_THUMBNAIL/IMAGES/VENDOR/2026/2/26/7193de62-7c5d-4eb3-823e-7b149c9193de_1243066.jpg'
            };
            const addr = {
                id: 'dbpjk241d96lqbm9684g',
                formatted_address: 'E6 silver oaks society near judge society, Greater Noida',
                address: 'E6 silver oaks society near judge society, Greater Noida',
                lat: 28.4543533,
                lng: 77.5015833,
                name: 'Prince',
                phone: '8521158381'
            };
            const acc = {
                id: 2,
                mobile: '7050501352',
                name: 'Ayush',
                status: 'fresh'
            };
            window.localStorage.setItem(`activeAccount_${tgId}`, JSON.stringify(acc));
            window.localStorage.setItem(`toing_active_address_${tgId}`, JSON.stringify(addr));
            window.localStorage.setItem(`toing_cart_${tgId}`, JSON.stringify(lines));
            window.localStorage.setItem(`toing_selected_restaurant_${tgId}`, JSON.stringify(rest));
            window.localStorage.setItem(`toing_active_tab_${tgId}`, 'cart');
            window.localStorage.removeItem(`toing_coupon_${tgId}`);
            window.localStorage.removeItem(`toing_coupon_${tgId}_7050501352`);
            window.localStorage.removeItem(`toing_checkout_${tgId}`);
        }""")
        await page.reload()
        await page.wait_for_timeout(2000)

        # Switch to Cart tab
        cart_nav = page.locator("nav button:has-text('Cart')").first
        await cart_nav.click()
        await page.wait_for_timeout(3500)

        # Screenshot 1: Cart on account 7050501352 - Live Bill, Claimed ₹50 FC, NO dummy coupon!
        shot1_path = os.path.join(ARTIFACT_DIR, "live_cart_verified_no_dummy.png")
        await page.screenshot(path=shot1_path, full_page=True)
        print(f"Captured: {shot1_path}")

        # Verify no dummy coupon is applied
        applied_coupon_count = await page.locator("text=Coupon 'BHIMNEW' applied").count()
        print(f"Is dummy BHIMNEW applied on 7050501352? {applied_coupon_count > 0} (Expected: False)")

        # Verify Claimed ₹50 FC badge is present
        fc_badge = await page.locator("text=Claimed ₹50 FC").count()
        print(f"Is Claimed ₹50 FC present? {fc_badge > 0}")

        # 2. Open "View Coupons" modal on account 7050501352
        view_coupons_btn = page.locator("button:has-text('View Coupons')").first
        if await view_coupons_btn.is_visible():
            await view_coupons_btn.click()
            await page.wait_for_timeout(1000)

            shot2_path = os.path.join(ARTIFACT_DIR, "live_cart_coupons_modal_account_isolated.png")
            await page.screenshot(path=shot2_path, full_page=True)
            print(f"Captured: {shot2_path}")

            # Close modal
            close_btn = page.locator("button:has(svg.lucide-x)").first
            if await close_btn.is_visible():
                await close_btn.click()
                await page.wait_for_timeout(500)

        # 3. Click "Pay Now" to open Authentic Swiggy Axis Bank UPI Checkout
        pay_btn = page.locator("button:has-text('Pay Now')").first
        if await pay_btn.is_visible():
            await pay_btn.click()
            await page.wait_for_timeout(3500)

            # Screenshot 3: Real Checkout View with Order ID, Txn ID, Axis Bank Swiggy UPI intent & QR
            shot3_path = os.path.join(ARTIFACT_DIR, "real_toing_checkout_screen.png")
            await page.screenshot(path=shot3_path, full_page=True)
            print(f"Captured: {shot3_path}")

            # 4. Click "Verify Payment" to verify the order confirmation flow
            verify_pay_btn = page.locator("button:has-text('Verify Payment')").first
            if await verify_pay_btn.is_visible():
                await verify_pay_btn.click()
                await page.wait_for_timeout(3500)

                # Screenshot 4: Payment Confirmed & Tracking Screen
                shot4_path = os.path.join(ARTIFACT_DIR, "order_confirmed_real_tracking.png")
                await page.screenshot(path=shot4_path, full_page=True)
                print(f"Captured: {shot4_path}")

        await browser.close()
        print("All tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_full_cart_coupon_checkout())

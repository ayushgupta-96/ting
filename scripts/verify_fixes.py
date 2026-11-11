import httpx
import json

# 1. Test calculate cart with 7050501352 (0 coupons account) trying BHIMNEW
cart_payload = {
    'mobile': '7050501352',
    'restaurant': {'id': '1243066', 'name': 'Beeji De Chole Bhature'},
    'items': [
        {'id': '184045164', 'name': 'Extra Mithe Chatkare Chole', 'price': 84, 'quantity': 1},
        {'id': '184045154', 'name': 'Boondi Raita', 'price': 20, 'quantity': 1}
    ],
    'address_id': 'dbpjk241d96lqbm9684g',
    'lat': 28.4543533,
    'lng': 77.5015833,
    'coupon_code': 'BHIMNEW'
}
r1 = httpx.post('http://127.0.0.1:8001/api/cart/calculate', json=cart_payload)
print('1. Cart Calculate Status:', r1.status_code)
d1 = r1.json()
print('   Coupon in response:', d1.get('coupon'))
print('   Bill To Pay:', d1.get('bill', {}).get('to_pay'))
print('   Bill lines:', [f"{l['label']}: {l['value']}" for l in d1.get('bill_lines', [])])

# 2. Test apply coupon top-level with BHIMNEW on 7050501352
r2 = httpx.post('http://127.0.0.1:8001/api/checkout/apply_coupon', json={
    'mobile': '7050501352',
    'restaurant_id': '1243066',
    'code': 'BHIMNEW',
    'items': cart_payload['items'],
    'address_id': 'dbpjk241d96lqbm9684g'
})
print('2. Apply Coupon Status:', r2.status_code)
print('   Apply Coupon Result:', r2.json())

# 3. Test checkout place order
r3 = httpx.post('http://127.0.0.1:8001/api/checkout/place', json={
    'mobile': '7050501352',
    'cart_id': '1298745321',
    'address_id': 'dbpjk241d96lqbm9684g',
    'lat': 28.4543533,
    'lng': 77.5015833,
    'restaurant_id': '1243066',
    'cart_value': 54,
    'amount': 9,
    'method': 'upi',
    'restaurant': 'Beeji De Chole Bhature'
})
print('3. Place Order Status:', r3.status_code)
d3 = r3.json()
print('   Order ID:', d3.get('order_id'))
print('   Txn ID:', d3.get('txn_id'))
print('   UPI URL:', d3.get('upi_url'))
print('   Status:', d3.get('status'))

# 4. Test payment status
r4 = httpx.post('http://127.0.0.1:8001/api/checkout/payment_status', json={
    'order_id': d3.get('order_id'),
    'manual': True
})
print('4. Payment Status Result:', r4.json())

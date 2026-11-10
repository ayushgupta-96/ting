import json
from urllib.parse import urlparse

har_path = r'C:/Users/akg79/.gemini/antigravity/brain/f4b377a6-8895-47c0-8a2d-f0d08bd2704a/.user_uploaded/media_1794327330041_dc50f56c.har'

with open(har_path, 'r', encoding='utf-8', errors='ignore') as f:
    har = json.load(f)

entries = har.get('log', {}).get('entries', [])
print(f'Total HAR entries: {len(entries)}')

endpoints = {}
for e in entries:
    req = e.get('request', {})
    res = e.get('response', {})
    url = req.get('url', '')
    method = req.get('method', '')
    status = res.get('status', 0)
    
    parsed = urlparse(url)
    domain = parsed.netloc
    path = parsed.path
    
    # Store all endpoints under storelex.store or any API call
    key = (method, path)
    if key not in endpoints:
        headers = {h['name'].lower(): h['value'] for h in req.get('headers', [])}
        post_data = req.get('postData', {}).get('text', '')
        resp_text = res.get('content', {}).get('text', '')
        endpoints[key] = {
            'method': method,
            'path': path,
            'domain': domain,
            'sample_url': url,
            'status': status,
            'count': 1,
            'headers': headers,
            'post_data': post_data,
            'resp_text': resp_text[:500] if resp_text else ''
        }
    else:
        endpoints[key]['count'] += 1

print(f'\nTotal unique endpoints: {len(endpoints)}\n')
for (m, p), info in sorted(endpoints.items()):
    print(f"{m} {p} (Domain: {info['domain']}, Status: {info['status']}, Hits: {info['count']})")
    if info['post_data']:
        print(f"   Payload: {info['post_data'][:200]}")
    print()

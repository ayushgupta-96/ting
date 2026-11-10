import re

files = [
    r'C:\Users\akg79\.gemini\antigravity\scratch\toing_platform\app.js_dump.js',
    r'C:\Users\akg79\AppData\Local\Programs\antigravity\cart_js_dump.js',
    r'C:\Users\akg79\.gemini\antigravity\scratch\toing_platform\search.js_dump.js'
]

for filename in files:
    name = filename.split('\\')[-1]
    print(f'=== Endpoints in {name} ===')
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        endpoints = set(re.findall(r'[\'"](/toing_web/api/[a-zA-Z0-9_\-/?=]+)[\'"]', content))
        endpoints |= set(re.findall(r'[\'"](/api/[a-zA-Z0-9_\-/?=]+)[\'"]', content))
        for ep in sorted(endpoints):
            print('  ', ep)
    except Exception as e:
        print(f'Error reading {filename}: {e}')

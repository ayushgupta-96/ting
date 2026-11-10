import re

scripts = [
    r'C:\Users\akg79\.gemini\antigravity\scratch\toing_platform\app.js',
    r'C:\Users\akg79\.gemini\antigravity\scratch\toing_platform\cart.js',
    r'C:\Users\akg79\.gemini\antigravity\scratch\toing_platform\search.js'
]

for s in scripts:
    name = s.split('\\')[-1]
    print(f'=== Analyzing {name} ===')
    with open(s, 'r', encoding='utf-8') as f:
        code = f.read()

    # Find fetch or ajax calls
    fetch_matches = re.findall(r'fetch\([^\)]+\)', code)
    print(f'Found {len(fetch_matches)} fetch calls.')
    for m in fetch_matches[:10]:
        print('  fetch:', m[:100])

    # Find string paths starting with /
    paths = set(re.findall(r'[\'"](/[^ \'"\)\(]+)[\'"]', code))
    print('  Paths found:')
    for p in sorted(paths):
        if any(k in p for k in ['api', 'address', 'order', 'cart', 'search']):
            print('    ', p)

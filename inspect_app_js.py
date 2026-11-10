with open(r'C:\Users\akg79\.gemini\antigravity\scratch\toing_platform\app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

targets = ['/api/addresses/', '/api/orders', '/api/cart']

for target in targets:
    print(f'===================== TARGET: {target} =====================')
    for i, line in enumerate(lines):
        if target in line:
            start = max(0, i - 15)
            end = min(len(lines), i + 35)
            print(f'--- Match around line {i+1} ---')
            print(''.join(lines[start:end]))
            print('----------------------------------------------------')

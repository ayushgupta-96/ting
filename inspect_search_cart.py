with open(r'C:\Users\akg79\.gemini\antigravity\scratch\toing_platform\search.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== search.js CART REFERENCES ===")
for i, line in enumerate(lines):
    if 'cart' in line.lower():
        start = max(0, i - 10)
        end = min(len(lines), i + 25)
        print(f'--- Match around line {i+1} ---')
        print(''.join(lines[start:end]))
        print('----------------------------------------------------')

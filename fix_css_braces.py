"""Fix the hero-mockup CSS - escape { } to {{ }} for Python f-string compatibility."""
import re

PAGE = 'pages/00_landing.py'

with open(PAGE, 'r') as f:
    txt = f.read()

# The hero-mockup CSS block was inserted with single {} braces but it lives inside
# st.markdown(f"""...""") which is an f-string, so braces must be doubled.
# Use regex to find the block and fix it.

pattern = r'(/\* ── Hero Screenshot Mockup ── \*/.*?\.hero-mockup img \{[^}]*\}\s*\n)'

def double_braces(m):
    block = m.group(1)
    # Replace every { and } that isn't already doubled
    # First, temporarily protect already-doubled braces
    block = block.replace('{{', '\x00L\x00').replace('}}', '\x00R\x00')
    block = block.replace('{', '{{').replace('}', '}}')
    block = block.replace('\x00L\x00', '{{').replace('\x00R\x00', '}}')
    return block

fixed, n = re.subn(pattern, double_braces, txt, flags=re.DOTALL)

if n > 0:
    with open(PAGE, 'w') as f:
        f.write(fixed)
    print(f'✅ Fixed {n} CSS block(s) — braces doubled')
else:
    # Fallback: just check if already doubled
    if '/* ── Hero Screenshot Mockup ── */' in txt:
        print('CSS block found. Checking brace state...')
        idx = txt.index('/* ── Hero Screenshot Mockup ── */')
        snippet = txt[idx:idx+400]
        print(snippet)
    else:
        print('ERROR: CSS block not found at all!')

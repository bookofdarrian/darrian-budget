"""Patch 00_landing.py to add a hero dashboard screenshot."""
import base64

IMG = 'static/hero_screenshot.jpg'
PAGE = 'pages/00_landing.py'

with open(IMG, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()

with open(PAGE, 'r') as f:
    txt = f.read()

# 1. Add imports
if 'import base64' not in txt:
    txt = txt.replace('import streamlit as st\n',
                      'import streamlit as st\nimport base64\nfrom pathlib import Path\n')

# 2. Add CSS (before Primary Button Override)
mockup_css = """
/* ── Hero Screenshot Mockup ── */
.hero-mockup {
  margin: 40px auto 0;
  max-width: 900px;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(255,140,66,0.25);
  box-shadow: 0 32px 80px rgba(0,0,0,0.6), 0 0 80px rgba(255,140,66,0.08);
}
.hero-mockup-bar {
  background: #0F1320;
  height: 32px;
  border-bottom: 1px solid rgba(255,140,66,0.15);
  display: flex;
  align-items: center;
  padding: 0 14px;
  gap: 7px;
}
.hero-mockup-dot {
  width: 12px; height: 12px;
  border-radius: 50%;
  display: inline-block;
}
.hero-mockup img {
  width: 100%;
  display: block;
}
"""

if 'hero-mockup' not in txt:
    txt = txt.replace('/* ── Primary Button Override ── */',
                      mockup_css + '\n/* ── Primary Button Override ── */')

# 3. Add image HTML between trust badges and stats bar
hero_html_block = f'''
# ─── HERO SCREENSHOT ──────────────────────────────────────────────────────────
_HERO_IMG = "{b64}"
st.markdown(
    f\'\'\'<div class="hero-mockup">
  <div class="hero-mockup-bar">
    <span class="hero-mockup-dot" style="background:#ff5f57;"></span>
    <span class="hero-mockup-dot" style="background:#febc2e;"></span>
    <span class="hero-mockup-dot" style="background:#28c840;"></span>
  </div>
  <img src="data:image/jpeg;base64,{{_HERO_IMG}}"
       alt="Peach State Savings Dashboard"
       loading="lazy" />
</div>\'\'\',
    unsafe_allow_html=True,
)

'''

marker = '# ═══════════════════════════════════════════════════════════════════════════════\n# STATS BAR'
if '_HERO_IMG' not in txt:
    txt = txt.replace(marker, hero_html_block + marker)

with open(PAGE, 'w') as f:
    f.write(txt)

print('✅ Done')
print('  import base64:', 'import base64' in txt)
print('  hero-mockup CSS:', 'hero-mockup' in txt)
print('  image injected:', '_HERO_IMG' in txt)

"""
utils/carousel.py
Reusable photo carousel components for Peach State Savings, SoleOps, and College Confused.

Design Philosophy (Darrian Belcher Story):
  - Sikh-raised Black man, middle son, two sisters, divorced parents
  - Mom raised in Hampton VA → interned in NYC
  - Dad raised in Chicago → interned in ATL
  - Raised in Hampton VA, now building in Atlanta
  - Black Panther ideologist: uplift everyone, celebrate culture, inspire through authenticity
  - Streets, fashion, nature, lifestyle, shoes, headshots — the FULL canvas of who he is

Carousel types:
  1. Shoe Product Carousel    — sneaker heat / SoleOps context
  2. Street Fashion Carousel  — style, identity, culture
  3. Nature Inspiration        — grounded roots, peace, intentionality
  4. Headshot + Lifestyle      — the person behind the brand
  5. Story Band                — full-width quote/founder band
  6. Roots Cities Band         — Hampton · NYC · Chicago · Atlanta geographic identity
"""

from __future__ import annotations

# ─── PLACEHOLDER PHOTO CATALOG ────────────────────────────────────────────────
# Each entry: (emoji, label, sublabel, accent_color_hex)
# When real photos are uploaded to /static/photos/ replace src with <img> tags.
# The system is already wired to use real images if placed in static/photos/

SHOE_PHOTOS = [
    ("👟", "Air Jordan 1 Retro High OG", "Chicago · $280 avg resale", "#FF4136"),
    ("👟", "Nike SB Dunk Low Travis Scott", "Special Field · $520 avg resale", "#B06AFF"),
    ("👟", "New Balance 9060", "Sea Salt/White · $180 avg resale", "#22D47E"),
    ("👟", "Adidas Yeezy 350 V2", "Zebra · $260 avg resale", "#FFB347"),
    ("👟", "Air Force 1 Low '07", "Triple White · $120 avg resale", "#00D4FF"),
    ("👟", "Jordan 4 Retro", "Fire Red 2020 · $400 avg resale", "#FF4136"),
    ("👟", "Nike Dunk High", "University Blue · $190 avg resale", "#4169E1"),
    ("👟", "Salehe Bembury x Crocs", "Pollex Clog · $95 avg resale", "#FF69B4"),
]

STREET_FASHION_PHOTOS = [
    ("🧥", "Street Layer", "Richmond VA · Oversized Puffer Era"),
    ("🕶️", "Drip Check", "Atlanta GA · Summer Fits"),
    ("👔", "Business Casual Reimagined", "NYC Energy · Corporate but Cultural"),
    ("🎽", "Clean Basics", "Hampton Roots · Less Is More"),
    ("🧢", "Fitted Season", "Midwest Inspired · Chicago Dad Style"),
    ("👗", "Culture Forward", "ATL Internship Vibes · Elevated Streetwear"),
]

NATURE_PHOTOS = [
    ("🌅", "Hampton Sunrise", "Chesapeake Bay morning light · where home began"),
    ("🌆", "Atlanta Skyline at Dusk", "Where the work gets done · Peach State"),
    ("🌃", "NYC Night Energy", "Mom's internship city · where ambition was born"),
    ("🍂", "Chicago Autumn", "Dad's city · resilience in every season"),
    ("🌊", "Virginia Beach Shore", "Hampton roads · salt air and stillness"),
    ("🌿", "Piedmont Park", "Atlanta green space · build and breathe"),
    ("🌸", "Spring in the South", "Georgia peach season · renewal"),
    ("🏙️", "Midtown Atlanta", "The headquarters of the dream"),
]

LIFESTYLE_HEADSHOT_PHOTOS = [
    ("📸", "The Founder Shot", "Darrian Belcher · Builder · ATL"),
    ("💻", "Deep Work Mode", "Late nights → early launches"),
    ("🎬", "Content Creation Day", "Cameras, microphones, and vision"),
    ("🤝", "Community First", "Networking with purpose · Black excellence"),
    ("🏃", "Morning Routine", "Discipline before inspiration"),
    ("📚", "Always Learning", "Hampton to ATL · reading to lead"),
]

CITIES_BAND = [
    ("🏖️", "Hampton, VA", "Where I was raised · Mom's city"),
    ("🌆", "Atlanta, GA", "Where I'm building · Dad's internship"),
    ("🌃", "New York, NY", "Mom's internship · ambition in the air"),
    ("💨", "Chicago, IL", "Dad's roots · where resilience lives"),
]

# ─── BASE CSS (inject once per page) ─────────────────────────────────────────

CAROUSEL_BASE_CSS = """
<style>
/* ═══ CAROUSEL BASE ═══════════════════════════════════════════════════════════ */
:root {
  --car-radius: 14px;
  --car-gap: 16px;
  --car-card-w: 220px;
  --car-card-h: 280px;
  --car-speed: 28s;
  --car-speed-slow: 38s;
}

.carousel-section {
  margin: 56px 0;
  overflow: hidden;
}
.carousel-section-header {
  text-align: center;
  margin-bottom: 28px;
  padding: 0 20px;
}
.carousel-eyebrow {
  display: inline-block;
  font-size: 0.74rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 10px;
}
.carousel-title {
  font-size: clamp(1.4rem, 3vw, 2rem);
  font-weight: 800;
  color: #F0F4FF;
  letter-spacing: -0.03em;
  line-height: 1.2;
  margin: 0 0 10px;
}
.carousel-subtitle {
  font-size: 0.9rem;
  color: #7A80A0;
  max-width: 520px;
  margin: 0 auto;
  line-height: 1.65;
}

/* ─── Track wrapper ── */
.car-track-wrap {
  position: relative;
  overflow: hidden;
}
.car-track-wrap::before,
.car-track-wrap::after {
  content: '';
  position: absolute;
  top: 0; bottom: 0; width: 80px;
  z-index: 3;
  pointer-events: none;
}

/* ─── Inner scroll row ── */
.car-inner {
  display: flex;
  gap: var(--car-gap);
  animation: carScroll var(--car-speed) linear infinite;
  width: max-content;
}
.car-inner:hover { animation-play-state: paused; }
.car-inner.slow { animation-duration: var(--car-speed-slow); }
.car-inner.reverse { animation-direction: reverse; }

@keyframes carScroll {
  0%   { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

/* ─── Base card ── */
.car-card {
  flex-shrink: 0;
  width: var(--car-card-w);
  height: var(--car-card-h);
  border-radius: var(--car-radius);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  padding: 16px 14px;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  text-decoration: none;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  border: 1px solid rgba(255,255,255,0.08);
}
.car-card:hover {
  transform: translateY(-4px) scale(1.02);
}

/* ─── Emoji display area ── */
.car-emoji {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -62%);
  font-size: 4.5rem;
  opacity: 0.85;
  filter: drop-shadow(0 4px 24px rgba(0,0,0,0.4));
  transition: transform 0.2s ease;
  pointer-events: none;
}
.car-card:hover .car-emoji {
  transform: translate(-50%, -65%) scale(1.08);
}

/* ─── Card text layer ── */
.car-card-label {
  font-size: 0.82rem;
  font-weight: 700;
  color: #fff;
  text-align: center;
  line-height: 1.3;
  position: relative;
  z-index: 2;
  text-shadow: 0 1px 8px rgba(0,0,0,0.6);
}
.car-card-sub {
  font-size: 0.7rem;
  color: rgba(255,255,255,0.6);
  text-align: center;
  margin-top: 4px;
  position: relative;
  z-index: 2;
  text-shadow: 0 1px 6px rgba(0,0,0,0.5);
}

/* ─── Gradient overlay at bottom of card ── */
.car-card-overlay {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 60%;
  border-radius: 0 0 var(--car-radius) var(--car-radius);
  pointer-events: none;
  z-index: 1;
}

/* ─── Story band ── */
.carousel-story-band {
  margin: 24px 0;
  padding: 28px 32px;
  border-radius: 16px;
  border-left: 4px solid;
  background: rgba(255,255,255,0.03);
  display: flex;
  align-items: flex-start;
  gap: 16px;
}
.carousel-story-quote {
  font-size: 1rem;
  font-style: italic;
  color: #C8D0EE;
  line-height: 1.75;
  flex: 1;
}
.carousel-story-attr {
  font-size: 0.78rem;
  font-weight: 700;
  margin-top: 10px;
  letter-spacing: 0.04em;
}

/* ─── Cities band ── */
.carousel-cities-band {
  display: flex;
  justify-content: center;
  gap: 0;
  margin: 32px 0;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,0.08);
}
.carousel-city-cell {
  flex: 1;
  padding: 20px 16px;
  text-align: center;
  border-right: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.02);
  transition: background 0.2s;
}
.carousel-city-cell:last-child { border-right: none; }
.carousel-city-cell:hover { background: rgba(255,255,255,0.05); }
.carousel-city-emoji { font-size: 1.6rem; margin-bottom: 6px; }
.carousel-city-name {
  font-size: 0.85rem;
  font-weight: 800;
  color: #F0F4FF;
  margin-bottom: 2px;
}
.carousel-city-sub {
  font-size: 0.72rem;
  color: #7A80A0;
  line-height: 1.4;
}

@media (max-width: 640px) {
  :root { --car-card-w: 160px; --car-card-h: 210px; }
  .carousel-cities-band { flex-wrap: wrap; }
  .carousel-city-cell { flex: 1 0 45%; }
  .carousel-story-band { padding: 20px; }
}
</style>
"""


# ─── THEME CSS (one per site accent color) ───────────────────────────────────

def carousel_theme_css(theme: str = "cyan") -> str:
    """
    Returns site-specific overlay colors for carousel track fade edges.
    theme: "cyan" (SoleOps), "green" (PSS), "blue" (CC)
    """
    colors = {
        "cyan":  ("#06080F", "#00D4FF"),
        "green": ("#0A1A0F", "#22D47E"),
        "blue":  ("#080A12", "#4F8EF7"),
        "gold":  ("#0A0800", "#FFB347"),
        "peach": ("#100800", "#FF8C42"),
    }
    bg, accent = colors.get(theme, colors["cyan"])
    return f"""
<style>
.car-track-wrap-{theme}::before {{
  background: linear-gradient(to right, {bg} 0%, transparent 100%);
}}
.car-track-wrap-{theme}::after {{
  background: linear-gradient(to left, {bg} 0%, transparent 100%);
}}
</style>
"""


# ─── CARD BUILDER ────────────────────────────────────────────────────────────

def _build_card(emoji: str, label: str, sub: str,
                bg_from: str, bg_to: str,
                accent: str,
                photo_src: str | None = None) -> str:
    """Build one carousel card. Uses emoji placeholder or real img if photo_src given."""
    if photo_src:
        bg_style = f"background: url('{photo_src}') center/cover no-repeat;"
    else:
        bg_style = f"background: linear-gradient(160deg, {bg_from} 0%, {bg_to} 100%);"

    return f"""<div class="car-card" style="{bg_style}" role="figure" aria-label="{label}">
  <span class="car-emoji">{emoji}</span>
  <div class="car-card-overlay" style="background: linear-gradient(to top, rgba(0,0,0,0.75) 0%, transparent 100%);"></div>
  <div style="position:relative;z-index:2;text-align:center;">
    <div class="car-card-label">{label}</div>
    <div class="car-card-sub">{sub}</div>
  </div>
</div>"""


def _build_track(cards_html: str, theme: str, slow: bool = False,
                 reverse: bool = False) -> str:
    """Wraps cards in the infinite-scroll track."""
    slow_cls = " slow" if slow else ""
    rev_cls = " reverse" if reverse else ""
    # Duplicate for seamless loop
    inner = f'<div class="car-inner{slow_cls}{rev_cls}">{cards_html}{cards_html}</div>'
    return f'<div class="car-track-wrap car-track-wrap-{theme}">{inner}</div>'


# ─── PUBLIC RENDER FUNCTIONS ─────────────────────────────────────────────────

def render_shoe_product_carousel(theme: str = "cyan") -> str:
    """Infinite-scroll sneaker product carousel for SoleOps."""
    card_styles = [
        ("#1a0505", "#3D0000"),  # deep red
        ("#0D0B1E", "#2B1A4F"),  # purple
        ("#051a0a", "#0A3B1E"),  # green
        ("#1A1200", "#3D2B00"),  # gold
        ("#050D1A", "#0A2040"),  # navy
        ("#1A0510", "#3D0028"),  # crimson
        ("#000D1A", "#001A3D"),  # midnight blue
        ("#0D1A00", "#1A3D00"),  # forest
    ]
    cards = ""
    for i, (emoji, label, sub) in enumerate(SHOE_PHOTOS):
        bg_f, bg_t = card_styles[i % len(card_styles)]
        cards += _build_card(emoji, label, sub, bg_f, bg_t, "#00D4FF")
    return _build_track(cards, theme)


def render_street_fashion_carousel(theme: str = "cyan") -> str:
    """Street & fashion inspiration carousel."""
    card_styles = [
        ("#0D0D0D", "#1A1A1A"),
        ("#0A0510", "#1F0A2A"),
        ("#05050D", "#0A0A1F"),
        ("#0D0800", "#1F1500"),
        ("#050D0A", "#0A1F14"),
        ("#0D0505", "#1F0A0A"),
    ]
    cards = ""
    for i, (emoji, label, sub) in enumerate(STREET_FASHION_PHOTOS):
        bg_f, bg_t = card_styles[i % len(card_styles)]
        cards += _build_card(emoji, label, sub, bg_f, bg_t, "#B06AFF")
    return _build_track(cards, theme, slow=True, reverse=True)


def render_nature_inspiration_carousel(theme: str = "green") -> str:
    """Nature + city skyline carousel. Great for PSS and CC."""
    card_styles = [
        ("#021A0A", "#053D1E"),  # dawn green
        ("#0A0D1A", "#1A1F3D"),  # dusk navy
        ("#1A0A00", "#3D1E00"),  # sunset
        ("#030D0A", "#071A14"),  # deep forest
        ("#00030D", "#000718"),  # ocean night
        ("#0A0500", "#1F0F00"),  # autumn
        ("#060A00", "#0F1400"),  # meadow
        ("#0A0800", "#1F1400"),  # golden hour
    ]
    cards = ""
    for i, (emoji, label, sub) in enumerate(NATURE_PHOTOS):
        bg_f, bg_t = card_styles[i % len(card_styles)]
        cards += _build_card(emoji, label, sub, bg_f, bg_t, "#22D47E")
    return _build_track(cards, theme, slow=True)


def render_headshot_lifestyle_carousel(theme: str = "cyan") -> str:
    """Headshot + lifestyle photos — the human behind the brand."""
    card_styles = [
        ("#080510", "#14103D"),
        ("#03080A", "#071018"),
        ("#0A0810", "#1F1A2A"),
        ("#080A03", "#141A07"),
        ("#0A0305", "#1A070B"),
        ("#030A08", "#071A14"),
    ]
    cards = ""
    for i, (emoji, label, sub) in enumerate(LIFESTYLE_HEADSHOT_PHOTOS):
        bg_f, bg_t = card_styles[i % len(card_styles)]
        cards += _build_card(emoji, label, sub, bg_f, bg_t, "#F0F4FF")
    return _build_track(cards, theme, slow=True)


def render_story_band_html(quote: str, attribution: str, accent: str = "#22D47E") -> str:
    """Full-width founder quote band."""
    return f"""
<div class="carousel-story-band" style="border-color:{accent};">
  <span style="font-size:2rem;line-height:1;color:{accent};opacity:0.7;">"</span>
  <div>
    <div class="carousel-story-quote">{quote}</div>
    <div class="carousel-story-attr" style="color:{accent};">— {attribution}</div>
  </div>
</div>"""


def render_roots_cities_band(accent: str = "#22D47E") -> str:
    """Four-city heritage band: Hampton · NYC · Chicago · Atlanta."""
    cells = ""
    for emoji, city, sub in CITIES_BAND:
        cells += f"""
<div class="carousel-city-cell">
  <div class="carousel-city-emoji">{emoji}</div>
  <div class="carousel-city-name" style="color:{accent};">{city}</div>
  <div class="carousel-city-sub">{sub}</div>
</div>"""
    return f"""
<div class="carousel-cities-band" role="region" aria-label="Darrian's roots and cities">
  {cells}
</div>"""

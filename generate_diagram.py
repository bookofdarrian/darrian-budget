#!/usr/bin/env python3
"""Generate a high-res LinkedIn architecture diagram PNG."""

from PIL import Image, ImageDraw, ImageFont
import os

DIAGRAM = """
 AUTONOMOUS AI SDLC PIPELINE — TECHNICAL ARCHITECTURE
 Darrian Belcher  ·  peachstatesavings.com  ·  March 2026
 ──────────────────────────────────────────────────────────────────────
 STACK : Python · Streamlit · SQLite/PostgreSQL · Claude Opus 4
 INFRA : Proxmox CT100 · Tailscale · Nginx · GitHub Actions
 ══════════════════════════════════════════════════════════════════════

   ⏰  CRON: 11PM DAILY  (CT100 · run_scheduled_agents.py)
                   │
                   ▼
   ┌───────────────────────────────────────────────────────────┐
   │  orchestrator.py  —  MULTI-AGENT COORDINATOR             │
   │  reads: BACKLOG.md  ·  git log  ·  pages/ directory      │
   └──────────────────────┬────────────────────────────────────┘
                          │
             ┌────────────┼─────────────┐
             ▼            ▼             ▼
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │ 🧠 PLANNER  │  │ ⚙️  BACKEND │  │  🎨  UI     │
   │   AGENT     │  │   AGENT     │  │   AGENT     │
   │             │  │             │  │             │
   │ → reads     │  │ → db.py     │  │ → Streamlit │
   │   backlog   │  │   patterns  │  │   sidebar   │
   │ → writes    │  │ → _ensure   │  │   layout    │
   │   spec.md   │  │   _tables() │  │   standard  │
   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
          └─────────────────┼────────────────┘
                            │
                            ▼
   ┌───────────────────────────────────────────────────────────┐
   │  🧪  TEST AGENT                                           │
   │  → python3 -m py_compile pages/XX.py  (syntax check)     │
   │  → pytest tests/unit/ -v              (unit tests)        │
   │  → bandit -r pages/XX.py             (security scan)      │
   └────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
   ┌───────────────────────────────────────────────────────────┐
   │  ✅  QA AGENT  —  QUALITY GATE                            │
   │                                                           │
   │  ✓ No hardcoded credentials    ✓ get_conn() / init_db()   │
   │  ✓ require_login() present     ✓ inject_css() called      │
   │  ✓ Sidebar standard followed   ✓ Tests: ALL PASS          │
   │  ✓ No st.experimental_*        ✓ USE_POSTGRES flag used   │
   └──────────────────────┬────────────────────────────────────┘
                          │
                    ┌─────┴──────┐
                  PASS          FAIL
                    │              │
                    ▼              ▼
   ┌────────────────────┐   ┌────────────────────┐
   │  🚀  GIT AGENT     │   │  error_log.txt      │
   │                    │   │  BACKLOG.md updated │
   │  git checkout -b   │   │  No commit, no PR   │
   │  feature/auto-*    │   │  → Retry next night │
   │  git commit -m     │   └────────────────────┘
   │  "feat: auto-*"    │
   │  gh pr create      │
   │  --base dev        │
   └──────────┬─────────┘
              │
              ▼
   ┌───────────────────────────────────────────────────────────┐
   │  👤  HUMAN REVIEW  —  ALWAYS REQUIRED (Morning)           │
   │  Darrian applies product judgment · Merges or revises     │
   └─────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
   ┌───────────────────────────────────────────────────────────┐
   │             VISA-STYLE GATED BRANCH PIPELINE              │
   │  ─────────────────────────────────────────────────────    │
   │  feature/* → dev → qa → staging → main (prod)             │
   │     │          │      │      │        │                    │
   │   unit       smoke  integ  regres   peachstatesavings.com  │
   │   tests      test   test   sion                            │
   │                                                            │
   │  GitHub Actions: ci.yml · promote-qa.yml · deploy.yml     │
   │  Branch protection: require PR review + passing checks    │
   └───────────────────────────────────────────────────────────┘

 INSPIRED BY:
   Hank Green    → focused agent design (domain-specific over monolithic)
   Edan Meyer    → self-learning loops (backlog auto-updates on pass/fail)
   Tina Huang    → TFCDC framework · hyper-specific app architecture
 ──────────────────────────────────────────────────────────────────────
 COST: ~$0.50–$2/night  ·  PAGES SHIPPED: 73+  ·  INFRA: $0/month
"""

def find_font(size):
    """Try to find a monospace font, fall back to default."""
    candidates = [
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
        "/Library/Fonts/Courier New.ttf",
        "/System/Library/Fonts/Monaco.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def main():
    BG_COLOR = (13, 17, 23)        # GitHub dark bg
    TEXT_COLOR = (201, 209, 217)   # GitHub default text
    ACCENT_COLOR = (88, 166, 255)  # Blue headers
    BORDER_COLOR = (48, 54, 61)    # Subtle border

    font_size = 20
    font = find_font(font_size)
    padding = 50

    lines = DIAGRAM.split("\n")

    # Measure dimensions
    dummy = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy)

    line_height = font_size + 6
    max_width = 0
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
        except Exception:
            w = len(line) * (font_size * 0.6)
        if w > max_width:
            max_width = w

    img_w = int(max_width) + padding * 2
    img_h = len(lines) * line_height + padding * 2

    img = Image.new("RGB", (img_w, img_h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Draw subtle border
    draw.rectangle([4, 4, img_w - 5, img_h - 5], outline=BORDER_COLOR, width=2)

    # Draw each line
    y = padding
    for i, line in enumerate(lines):
        # Color the header lines differently
        if i < 4 or "INSPIRED BY" in line or "COST:" in line or "══" in line or "──" in line:
            color = ACCENT_COLOR
        elif "PASS" in line or "✓" in line:
            color = (63, 185, 80)   # green
        elif "FAIL" in line or "error" in line.lower():
            color = (248, 81, 73)   # red
        elif "👤" in line or "HUMAN" in line:
            color = (255, 166, 77)  # orange — human gate stands out
        else:
            color = TEXT_COLOR

        draw.text((padding, y), line, font=font, fill=color)
        y += line_height

    out_path = "/Users/darrianbelcher/Downloads/darrian-budget/linkedin_diagram.png"
    img.save(out_path, "PNG", dpi=(150, 150))
    print(f"✅ Saved: {out_path}")
    print(f"   Size: {img_w}x{img_h}px")


if __name__ == "__main__":
    main()

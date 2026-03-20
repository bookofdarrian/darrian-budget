#!/usr/bin/env python3
"""
autopost_applescript.py  v2
Pure JS injection into Chrome — no System Events / keystrokes needed.
Uses document.execCommand('insertText') to type into React contenteditable boxes.
"""

import subprocess, time, json

# ── Tweets ────────────────────────────────────────────────────────────────────
TWEETS = [
    "🧵 THREAD: I built 140 AI-powered apps while working at Visa, going to Georgia Tech, and running a sneaker business.\n\nHere's everything, and everyone who made it possible. 🍑 (1/12)",
    "2/ Three platforms. One home server. Zero outside funding.\n→ Peach State Savings (peachstatesavings.com) — personal finance OS\n→ SoleOps (getsoleops.com) — sneaker resale suite\n→ College Confused (collegeconfused.org) — first-gen college prep\nAll live. All real. All built by me + AI.",
    "3/ Peach State Savings is a 140+ page financial operating system.\n\nBudget tracker, income manager, RSU vest calendar, portfolio monitor, cash flow forecast, debt payoff planner, investment rebalancer, AI budget chat, crypto tracker, sneaker resale P&L, tax projection...\n\nFree at peachstatesavings.com",
    "4/ SoleOps is the sneaker reseller's operating system.\n\nThe feature I'm most proud of: an ARB scanner that monitors Mercari 24/7 and sends a Telegram alert when a pair drops below my max buy price.\n\nIt texted me a $200 opportunity before breakfast last month.",
    "5/ College Confused is personal.\n\nI was a first-gen college student. No one in my family knew what FAFSA was. I got into 25 schools.\n\nCC is the free AI platform I wish I'd had. FAFSA walkthrough, essay assistant, scholarship tracker, AI mock interviews.\n\nAlways free. collegeconfused.org",
    "6/ The tech: Python + Streamlit. SQLite/PostgreSQL. Anthropic Claude API.\nHome server running Proxmox. Tailscale VPN. Nginx. Docker. Grafana + Prometheus.\n\nAnd the wildest part — an overnight AI dev system that builds features WHILE I SLEEP. Tested. Committed. Deployed.",
    "7/ Now the most important part.\n\nSHOUTOUTS.\n\nNothing I've built happened alone. Let me be explicit about that.",
    "8/ @AnthropicAI + Claude — my co-creator.\n\nClaude isn't just a tool. It reviews my code, writes features, debugs errors, and talks to my users about their money.\n\nThey built something that genuinely changed what one person can build.",
    "9/ The Streamlit team — you lowered the barrier.\n\nI'm a TPM, not a frontend engineer. Streamlit let me build 140 production-quality app pages in Python, no React required.\n\nstreamlit.io — no more excuses.",
    "10/ My Visa + Georgia Tech communities.\n\nTPM at Visa taught me how to ship real programs. Georgia Tech taught me to think in data and systems.\n\nBoth show up in every product decision I make.",
    "11/ My people. This is for y'all.\n\nMy family — every sacrifice, every belief, everything.\nDr. Bedir — for promoting the growth of beautiful minds.\nJosh, Keona, Nylah, Omar, Noah, Liddon, Nauri, Metri, Joa, Juan + the whole Menace2 GC.\nVine — you were there from the start.\n252 // 525 — you already know.\nRIP Danny 🕊️ — gone too soon. Building for you.",
    "12/ If you made it here:\n✅ peachstatesavings.com — free personal finance OS\n👟 getsoleops.com — sneaker resale suite (April launch)\n🎓 collegeconfused.org — free first-gen college prep\n📱 @bookofdarrian — follow the build\n\nOne year ago: a spreadsheet.\nToday: three live products.\nTomorrow: $1K MRR.\n\nThe build continues. 🍑",
]

FB_POST = """I've been building in silence for a while. Today I'm sharing everything.

Over the past year — while working full-time as a Technical Program Manager at Visa and finishing my Georgia Tech data analytics degree — I've been building three AI-powered platforms from a home server in my house.

📊 Peach State Savings (peachstatesavings.com) — 140+ page personal finance OS. Free for everyone.

👟 SoleOps (getsoleops.com — April 2026) — AI listing generator, inventory manager, P&L dashboard, ARB scanner with Telegram alerts. First 25 signups get 30 free Pro days.

🎓 College Confused (collegeconfused.org) — Free AI college prep for first-gen students. FAFSA walkthrough, essay assistant, scholarship tracker, AI mock interviews. Always free.

I could not have done this without:

❤️ Anthropic / Claude AI — genuine co-creator on every feature
❤️ The Streamlit framework team
❤️ Georgia Tech for teaching me to build in systems
❤️ My colleagues at Visa for the program discipline I apply to every build
❤️ My family — every sacrifice, every "go do what you gotta do" — this is for you
❤️ Dr. Bedir — for promoting the growth of beautiful minds. Thank you for seeing us.
❤️ Josh, Keona, Nylah, Omar, Noah, Liddon, Nauri, Metri, Joa, Juan + the whole Menace2 GC
❤️ Vine — you were there from the start. Still building for you.
❤️ 252 // 525 — you already know. Always.
❤️ RIP Danny 🕊️ — gone too soon. This one's for you too.

One year ago I had a spreadsheet. Today I have three live products and a server that builds features while I sleep.

This is just the beginning. 🍑"""


# ── Core helpers ──────────────────────────────────────────────────────────────

def run_js(js: str) -> str:
    """Inject JS into Chrome's active tab, return result as string."""
    # JSON-encode the JS string so AppleScript handles all special chars safely
    js_json = json.dumps(js)
    script = f'''tell application "Google Chrome"
    activate
    set jsCode to {js_json}
    set r to (execute active tab of front window javascript jsCode)
    if r is missing value then return ""
    return (r as string)
end tell'''
    result = subprocess.run(['osascript', '-e', script],
                          capture_output=True, text=True, timeout=15)
    return result.stdout.strip()


def navigate(url: str, wait: float = 4.0):
    """Navigate Chrome's active tab."""
    script = f'''tell application "Google Chrome"
    activate
    set URL of active tab of front window to "{url}"
end tell'''
    subprocess.run(['osascript', '-e', script])
    time.sleep(wait)


def wait_for_element(selector: str, timeout: int = 15) -> bool:
    """Poll until selector appears in DOM."""
    for _ in range(timeout * 2):
        result = run_js(f'document.querySelector({json.dumps(selector)}) ? "yes" : "no"')
        if result == "yes":
            return True
        time.sleep(0.5)
    return False


def type_into(selector: str, text: str) -> str:
    """Focus element and use execCommand('insertText') to type — works for React contenteditable."""
    # Escape text for JSON embedding
    text_json = json.dumps(text)
    js = f'''
(function() {{
    var el = document.querySelector({json.dumps(selector)});
    if (!el) return "NOT_FOUND";
    el.focus();
    el.click();
    // Select all existing content and delete it
    document.execCommand("selectAll", false, null);
    document.execCommand("delete", false, null);
    // Type new content
    var success = document.execCommand("insertText", false, {text_json});
    return success ? "OK" : "EXEC_FAILED";
}})()
'''
    return run_js(js)


def click_selector(selector: str) -> str:
    """Click element matching selector."""
    js = f'''
(function() {{
    var el = document.querySelector({json.dumps(selector)});
    if (!el) return "NOT_FOUND";
    el.click();
    return "clicked";
}})()
'''
    return run_js(js)


def click_last(selector: str) -> str:
    """Click last element matching selector."""
    js = f'''
(function() {{
    var els = document.querySelectorAll({json.dumps(selector)});
    if (!els.length) return "NOT_FOUND";
    els[els.length-1].click();
    return "clicked";
}})()
'''
    return run_js(js)


# ── Twitter Thread ────────────────────────────────────────────────────────────

def post_twitter_thread():
    print("\n📌 STEP 1: Twitter/X Thread (12 tweets)")
    navigate("https://x.com/compose/post", wait=5)

    # Verify compose box is present
    found = wait_for_element('div[data-testid="tweetTextarea_0"]', timeout=12)
    if not found:
        print("  ⚠️  Compose box not found — are you logged into Twitter in Chrome?")
        print("  Waiting 30s for you to log in and open compose...")
        time.sleep(30)
        navigate("https://x.com/compose/post", wait=5)

    TEXTAREA = 'div[data-testid="tweetTextarea_0"]'
    ADD_BTN   = 'div[data-testid="addButton"], button[data-testid="addButton"]'
    POST_BTN  = 'div[data-testid="tweetButton"], button[data-testid="tweetButton"]'

    for i, tweet in enumerate(TWEETS):
        print(f"  → Tweet {i+1}/12...", end=" ", flush=True)

        # Focus the correct textarea (last one in the list)
        focus_js = f'''
(function() {{
    var boxes = document.querySelectorAll('div[data-testid^="tweetTextarea"]');
    if (!boxes.length) return "NOT_FOUND";
    var el = boxes[boxes.length - 1];
    el.focus(); el.click();
    document.execCommand("selectAll", false, null);
    document.execCommand("delete", false, null);
    var ok = document.execCommand("insertText", false, {json.dumps(tweet)});
    return ok ? "OK" : "EXEC_FAILED:" + el.tagName;
}})()
'''
        result = run_js(focus_js)
        print(f"{result}", end=" ", flush=True)
        time.sleep(1.2)

        if i < len(TWEETS) - 1:
            r = click_selector(ADD_BTN)
            if r == "NOT_FOUND":
                r = click_last(ADD_BTN)
            print(f"add={r}")
            time.sleep(1.5)
        else:
            print("(last)")

    print("  → Posting thread...")
    time.sleep(0.5)
    result = click_last(POST_BTN)
    if result == "NOT_FOUND":
        print("  ⚠️  Post button not found. Thread is built — please click 'Post' manually in Chrome.")
        time.sleep(20)
    else:
        print(f"  ✅ Thread posted! ({result})")
        time.sleep(4)


# ── Facebook Personal ─────────────────────────────────────────────────────────

def post_facebook():
    print("\n📌 STEP 2: Facebook personal post")
    navigate("https://www.facebook.com", wait=5)

    # Click "What's on your mind" box to open composer
    clicked = run_js('''
(function() {
    // Try multiple selectors for the post box
    var selectors = [
        "div[aria-label*='mind']",
        "div[aria-label*='Mind']",
        "div[role='button'][tabindex='0']"
    ];
    for (var s of selectors) {
        var el = document.querySelector(s);
        if (el) { el.click(); return "clicked:" + s; }
    }
    return "NOT_FOUND";
})()
''')
    print(f"  Opened composer: {clicked}")
    time.sleep(2.5)

    # Type into the expanded textbox
    result = run_js(f'''
(function() {{
    // Find contenteditable area inside the dialog
    var dialog = document.querySelector("div[role='dialog']") || document;
    var boxes = dialog.querySelectorAll("div[contenteditable='true']");
    if (!boxes.length) return "NO_BOXES";
    var el = boxes[boxes.length - 1];
    el.focus(); el.click();
    document.execCommand("selectAll", false, null);
    document.execCommand("delete", false, null);
    var ok = document.execCommand("insertText", false, {json.dumps(FB_POST)});
    return ok ? "OK" : "EXEC_FAILED";
}})()
''')
    print(f"  Text inserted: {result}")
    time.sleep(2)

    # Click Post button
    post_result = run_js('''
(function() {
    var btn = document.querySelector("div[aria-label='Post']") ||
              document.querySelector("div[aria-label='Share']");
    if (btn) { btn.click(); return "posted"; }
    // Try all buttons labeled Post
    var btns = Array.from(document.querySelectorAll("div[role='button']"))
               .filter(b => b.textContent.trim() === "Post");
    if (btns.length) { btns[btns.length-1].click(); return "posted-fallback"; }
    return "NOT_FOUND";
})()
''')
    if "NOT_FOUND" in str(post_result):
        print("  ⚠️  Post button not found. Post is typed — click 'Post' manually in Chrome.")
        time.sleep(15)
    else:
        print(f"  ✅ Facebook post submitted! ({post_result})")
        time.sleep(3)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("🍑  Auto-Post v2 — Pure JS, No System Events")
    print("=" * 55)
    print("Using Chrome's active window — make sure you're logged in.\n")

    try:
        post_twitter_thread()
    except Exception as e:
        print(f"  ❌ Twitter error: {e}")

    try:
        post_facebook()
    except Exception as e:
        print(f"  ❌ Facebook error: {e}")

    print("\n" + "=" * 55)
    print("✅  Text posts done!")
    print("=" * 55)
    print("""
Remaining (need screen recording first):
  → TikTok @bookofdarrian   — 60-sec app montage
  → TikTok @peachstatesavings — 30-sec Telegram alert
  → Instagram Reel + Feed
  → YouTube Shorts

All captions staged at:
  http://100.95.125.112:8501/social_media_manager → Queue tab
""")

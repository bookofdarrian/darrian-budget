#!/usr/bin/env python3
"""
install_bookmarks.py
Automatically installs all Peach State Savings bookmarks into:
  1. Chrome  — directly edits the JSON bookmarks file
  2. Safari  — triggers the import dialog via AppleScript
  3. Prints iPhone sync instructions

Run: python3 install_bookmarks.py
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from html.parser import HTMLParser

# ── Paths ──────────────────────────────────────────────────────────────────────
HERE          = os.path.dirname(os.path.abspath(__file__))
BOOKMARK_HTML = os.path.join(HERE, "PEACH_STATE_BOOKMARKS.html")
HOME          = os.path.expanduser("~")

# Chrome on macOS — try Default profile first, then Profile 1
CHROME_CANDIDATES = [
    os.path.join(HOME, "Library", "Application Support", "Google", "Chrome", "Default",   "Bookmarks"),
    os.path.join(HOME, "Library", "Application Support", "Google", "Chrome", "Profile 1", "Bookmarks"),
    os.path.join(HOME, "Library", "Application Support", "Google", "Chrome", "Profile 2", "Bookmarks"),
]

# ── Chrome timestamp helper ─────────────────────────────────────────────────────
def _chrome_ts():
    """Microseconds since 1601-01-01 UTC (Chrome's internal timestamp format)."""
    return str(int((time.time() + 11644473600) * 1_000_000))


# ── Netscape Bookmark HTML Parser ─────────────────────────────────────────────
class _BookmarkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._stack   = []
        self._root    = []
        self._in_h3   = False
        self._in_a    = False
        self._cur_href = ""
        self._cur_txt  = ""

    def _top(self):
        return self._stack[-1] if self._stack else None

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        if tag == "dl":
            folder = {"type": "folder", "name": "", "children": []}
            top = self._top()
            if top is not None:
                top["children"].append(folder)
            else:
                self._root.append(folder)
            self._stack.append(folder)
        elif tag == "h3":
            self._in_h3  = True
            self._cur_txt = ""
        elif tag == "a":
            self._in_a    = True
            self._cur_href = ad.get("href", "")
            self._cur_txt  = ""

    def handle_endtag(self, tag):
        if tag == "dl" and self._stack:
            self._stack.pop()
        elif tag == "h3":
            self._in_h3 = False
            top = self._top()
            if top is not None:
                top["name"] = self._cur_txt.strip()
        elif tag == "a":
            self._in_a = False
            top = self._top()
            if top is not None:
                top["children"].append({
                    "type": "url",
                    "name": self._cur_txt.strip(),
                    "url":  self._cur_href,
                })

    def handle_data(self, data):
        if self._in_h3 or self._in_a:
            self._cur_txt += data

    def get_root(self):
        return self._root


def _parse_html(path):
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    p = _BookmarkParser()
    p.feed(html)
    return p.get_root()


# ── Chrome JSON conversion ─────────────────────────────────────────────────────
_id_seq = [900000]

def _next_id():
    _id_seq[0] += 1
    return str(_id_seq[0])


def _to_chrome(node):
    """Recursively convert a parsed bookmark node to Chrome JSON format."""
    ts  = _chrome_ts()
    nid = _next_id()
    if node["type"] == "url":
        return {
            "date_added":   ts,
            "guid":         f"pss-bm-url-{nid}",
            "id":           nid,
            "name":         node["name"],
            "type":         "url",
            "url":          node["url"],
        }
    return {
        "children":      [_to_chrome(c) for c in node.get("children", [])],
        "date_added":    ts,
        "date_modified": ts,
        "guid":          f"pss-bm-dir-{nid}",
        "id":            nid,
        "name":          node["name"],
        "type":          "folder",
    }


def _find_max_id(node):
    if not isinstance(node, dict):
        return 0
    try:
        mid = int(node.get("id", 0))
    except (ValueError, TypeError):
        mid = 0
    for child in node.get("children", []):
        mid = max(mid, _find_max_id(child))
    return mid


# ── Chrome Installer ───────────────────────────────────────────────────────────
def install_chrome():
    print("\n📌 Chrome Bookmark Installer")
    print("   ─────────────────────────")

    # Find the Chrome bookmarks file
    chrome_path = None
    for candidate in CHROME_CANDIDATES:
        if os.path.exists(candidate):
            chrome_path = candidate
            break

    if not chrome_path:
        print("   ⚠️  Chrome bookmarks file not found. Is Chrome installed?")
        print("      Manual: chrome://bookmarks → ⋮ → Import bookmarks → PEACH_STATE_BOOKMARKS.html")
        return False

    print(f"   Found: {chrome_path}")

    # Backup
    backup = chrome_path + ".pss_backup"
    shutil.copy2(chrome_path, backup)
    print(f"   ✅ Backup saved: {backup}")

    # Load existing bookmarks
    with open(chrome_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Bump the ID counter past existing max
    max_id = max(
        _find_max_id(data["roots"].get("bookmark_bar", {})),
        _find_max_id(data["roots"].get("other",        {})),
        _find_max_id(data["roots"].get("synced",       {})),
    )
    _id_seq[0] = max(max_id + 500, _id_seq[0])

    # Parse our HTML
    root_nodes = _parse_html(BOOKMARK_HTML)

    # ── Build the main "🍑 Peach State Savings" folder for Other Bookmarks ──
    ts  = _chrome_ts()
    nid = _next_id()
    pss_folder = {
        "children":      [_to_chrome(n) for n in root_nodes],
        "date_added":    ts,
        "date_modified": ts,
        "guid":          f"pss-root-{nid}",
        "id":            nid,
        "name":          "🍑 Peach State Savings",
        "type":          "folder",
    }

    # Remove old PSS folder (deduplication on re-run)
    other = data["roots"]["other"]["children"]
    other = [c for c in other if c.get("name") != "🍑 Peach State Savings"]
    other.insert(0, pss_folder)
    data["roots"]["other"]["children"] = other

    # ── Also pin "📱 Phone — Top 12" to the Bookmark Bar ──
    phone_node = next(
        (n for n in root_nodes if "Phone" in n.get("name", "")), None
    )
    if phone_node:
        phone_chrome = _to_chrome(phone_node)
        phone_chrome["name"] = "📱 PSS Quick"
        bar = data["roots"]["bookmark_bar"]["children"]
        bar = [c for c in bar if c.get("name") != "📱 PSS Quick"]
        bar.insert(0, phone_chrome)
        data["roots"]["bookmark_bar"]["children"] = bar
        print("   ✅ '📱 PSS Quick' pinned to Bookmarks Bar")

    # Write back
    with open(chrome_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    print("   ✅ '🍑 Peach State Savings' added to Other Bookmarks")
    print("   ✅ Chrome bookmarks file updated!")
    return True


# ── Safari Installer via AppleScript ──────────────────────────────────────────
def install_safari():
    print("\n🧭 Safari Bookmark Installer")
    print("   ─────────────────────────")

    osa = f"""
set bmFile to POSIX file "{BOOKMARK_HTML}"

tell application "Safari"
    activate
end tell

delay 1

tell application "System Events"
    tell process "Safari"
        set frontmost to true
        delay 0.5

        -- File menu -> Import From -> Bookmarks HTML File
        click menu bar item "File" of menu bar 1
        delay 0.4
        tell menu 1 of menu bar item "File" of menu bar 1
            click menu item "Import From"
            delay 0.4
            tell menu 1 of menu item "Import From"
                click menu item "Bookmarks HTML File\\u2026"
            end tell
        end tell

        delay 1.5

        -- In the open-file sheet, type the path using Go To Folder
        keystroke "g" using {{command down, shift down}}
        delay 0.8
        keystroke "{BOOKMARK_HTML}"
        delay 0.5
        key code 36  -- Return (confirm path)
        delay 0.8
        key code 36  -- Return (confirm file selection)
        delay 0.5
    end tell
end tell
"""
    try:
        result = subprocess.run(
            ["osascript", "-e", osa],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print("   ✅ Safari import dialog completed!")
            print("   ✅ Check Safari sidebar — bookmarks should be there now")
            return True
        else:
            err = result.stderr.strip()
            print(f"   ⚠️  AppleScript returned error: {err}")
    except subprocess.TimeoutExpired:
        print("   ⚠️  Safari AppleScript timed out")
    except Exception as e:
        print(f"   ⚠️  Safari install failed: {e}")

    print()
    print("   ► Manual Safari import:")
    print("     Safari → File → Import From → Bookmarks HTML File")
    print(f"     Select: {BOOKMARK_HTML}")
    return False


# ── iPhone sync instructions ───────────────────────────────────────────────────
def print_phone_instructions():
    print()
    print("📱 iPhone / iPad Sync Instructions")
    print("   ─────────────────────────────────")
    print()
    print("   Chrome → Phone:")
    print("   ① On your Mac: make sure you're signed into Chrome with your Google account")
    print("   ② On iPhone: open Chrome → ⋮ → Settings → Sign in to Chrome")
    print("   ③ Bookmarks sync automatically — done! ✅")
    print()
    print("   Safari → iPhone:")
    print("   ① On iPhone: Settings → [Your Name] → iCloud → toggle Safari ON")
    print("   ② Bookmarks sync to iPhone Safari within a few minutes ✅")
    print()
    print("   ─────────────────────────────────")
    print("   Your top pages for the phone bookmark bar (📱 PSS Quick):")
    print("   📊 PSS       → peachstatesavings.com")
    print("   💳 $pend     → /expenses")
    print("   ✅ Todo      → /todo")
    print("   📱 Social    → /social_media_manager  ⭐ NEW")
    print("   🎬 Creator   → /creator_companion")
    print("   📝 Notes     → /notes")
    print("   👟 Sole      → /soleops_inventory_manager")
    print("   📋 Brief     → /soleops_daily_briefing_digest")
    print("   💰 Price     → /resale_price_advisor")
    print("   🤖 AI        → /personal_assistant")
    print("   📈 RSU       → /rsu_vest_calendar")
    print("   🔮 Flow      → /cash_flow_forecast")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print()
    print("=" * 55)
    print("🍑  Peach State Savings — Bookmark Auto-Installer")
    print("=" * 55)

    if not os.path.exists(BOOKMARK_HTML):
        print(f"❌ Bookmark file not found: {BOOKMARK_HTML}")
        sys.exit(1)

    # ── Step 1: Kill Chrome briefly to safely edit bookmarks file ──────────
    chrome_running = subprocess.run(
        ["pgrep", "-x", "Google Chrome"], capture_output=True
    ).returncode == 0

    if chrome_running:
        print("\n⚠️  Chrome is running — closing it briefly to update bookmarks...")
        subprocess.run(
            ["osascript", "-e", 'tell application "Google Chrome" to quit'],
            capture_output=True
        )
        time.sleep(2.5)

    # ── Step 2: Install Chrome bookmarks ───────────────────────────────────
    chrome_ok = install_chrome()

    # ── Step 3: Reopen Chrome ──────────────────────────────────────────────
    if chrome_running or chrome_ok:
        print("\n   🔄 Reopening Chrome...")
        subprocess.Popen(["open", "-a", "Google Chrome"])
        time.sleep(2)

    # ── Step 4: Install Safari bookmarks ──────────────────────────────────
    safari_ok = install_safari()

    # ── Step 5: Phone sync guide ───────────────────────────────────────────
    print_phone_instructions()

    # ── Summary ────────────────────────────────────────────────────────────
    print()
    print("=" * 55)
    print("✅  Installation Summary")
    print("=" * 55)
    print(f"   Chrome  : {'✅ Installed' if chrome_ok  else '⚠️  Manual import needed'}")
    print(f"   Safari  : {'✅ Installed' if safari_ok  else '⚠️  Manual import needed'}")
    print(f"   iPhone  : Sync via Google/iCloud (see instructions above)")
    print()
    print("📂  Bookmark file path (for manual import if needed):")
    print(f"   {BOOKMARK_HTML}")
    print()


if __name__ == "__main__":
    main()

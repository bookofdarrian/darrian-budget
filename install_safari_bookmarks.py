#!/usr/bin/env python3
"""
install_safari_bookmarks.py
Directly modifies ~/Library/Safari/Bookmarks.plist to add all
Peach State Savings bookmarks. Safari must be CLOSED before running.
"""

import json
import os
import plistlib
import shutil
import subprocess
import sys
import time
import uuid
from html.parser import HTMLParser

HERE          = os.path.dirname(os.path.abspath(__file__))
BOOKMARK_HTML = os.path.join(HERE, "PEACH_STATE_BOOKMARKS.html")
SAFARI_PLIST  = os.path.expanduser("~/Library/Safari/Bookmarks.plist")
BACKUP_PATH   = SAFARI_PLIST + ".pss_backup"


# ── HTML Parser ────────────────────────────────────────────────────────────────
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


# ── Safari plist node builder ──────────────────────────────────────────────────
def _new_uuid():
    return str(uuid.uuid4()).upper()


def _to_safari(node):
    """Recursively convert a parsed bookmark node to Safari plist dict."""
    if node["type"] == "url":
        return {
            "WebBookmarkType":       "WebBookmarkTypeLeaf",
            "WebBookmarkUUID":       _new_uuid(),
            "URLString":             node["url"],
            "URIDictionary":         {"title": node["name"]},
            "ReadingListNonSync":    {},
        }
    # Folder
    children = [_to_safari(c) for c in node.get("children", [])]
    return {
        "WebBookmarkType":       "WebBookmarkTypeList",
        "WebBookmarkUUID":       _new_uuid(),
        "WebBookmarkIdentifier": f"BookmarksList-{_new_uuid()}",
        "Title":                 node["name"],
        "Children":              children,
    }


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print()
    print("=" * 55)
    print("🧭  Safari Bookmark Installer — Direct Plist Method")
    print("=" * 55)

    if not os.path.exists(SAFARI_PLIST):
        print(f"❌ Safari Bookmarks.plist not found at: {SAFARI_PLIST}")
        print("   Make sure Safari has been opened at least once.")
        sys.exit(1)

    # ── Close Safari first ────────────────────────────────────────────────────
    safari_running = subprocess.run(
        ["pgrep", "-x", "Safari"], capture_output=True
    ).returncode == 0

    if safari_running:
        print("⚠️  Closing Safari to safely edit bookmarks...")
        subprocess.run(
            ["osascript", "-e", 'tell application "Safari" to quit'],
            capture_output=True
        )
        time.sleep(2)

    # ── Backup ────────────────────────────────────────────────────────────────
    shutil.copy2(SAFARI_PLIST, BACKUP_PATH)
    print(f"✅ Backup saved: {BACKUP_PATH}")

    # ── Convert binary plist to XML for reading ───────────────────────────────
    subprocess.run(
        ["plutil", "-convert", "xml1", SAFARI_PLIST],
        check=True
    )

    with open(SAFARI_PLIST, "rb") as f:
        data = plistlib.load(f)

    # ── Parse our HTML bookmarks ──────────────────────────────────────────────
    root_nodes = _parse_html(BOOKMARK_HTML)

    # ── Build the PSS folder ──────────────────────────────────────────────────
    pss_folder = {
        "WebBookmarkType":       "WebBookmarkTypeList",
        "WebBookmarkUUID":       _new_uuid(),
        "WebBookmarkIdentifier": f"PSS-Root-{_new_uuid()}",
        "Title":                 "🍑 Peach State Savings",
        "Children":              [_to_safari(n) for n in root_nodes],
    }

    # ── Find the "BookmarksMenu" child (Other Bookmarks equivalent) ────────────
    # Safari plist root has a "Children" list of special folders
    root_children = data.get("Children", [])

    # Remove existing PSS folder if re-running
    root_children = [
        c for c in root_children
        if not (isinstance(c, dict) and c.get("Title") == "🍑 Peach State Savings")
    ]

    # Find BookmarksMenu to insert after it; otherwise append
    insert_idx = None
    for i, child in enumerate(root_children):
        if isinstance(child, dict) and child.get("WebBookmarkIdentifier") == "BookmarksMenu":
            insert_idx = i + 1
            break

    if insert_idx is not None:
        root_children.insert(insert_idx, pss_folder)
    else:
        root_children.append(pss_folder)

    data["Children"] = root_children

    # ── Also add Phone Quick folder to BookmarksBar ───────────────────────────
    phone_node = next(
        (n for n in root_nodes if "Phone" in n.get("name", "")), None
    )
    if phone_node:
        phone_safari = _to_safari(phone_node)
        phone_safari["Title"] = "📱 PSS Quick"

        for child in data.get("Children", []):
            if isinstance(child, dict) and child.get("WebBookmarkIdentifier") == "BookmarksBar":
                bar_kids = child.get("Children", [])
                bar_kids = [
                    c for c in bar_kids
                    if not (isinstance(c, dict) and c.get("Title") == "📱 PSS Quick")
                ]
                bar_kids.insert(0, phone_safari)
                child["Children"] = bar_kids
                print("✅ '📱 PSS Quick' pinned to Safari Bookmarks Bar")
                break

    # ── Write back as binary plist ────────────────────────────────────────────
    with open(SAFARI_PLIST, "wb") as f:
        plistlib.dump(data, f, fmt=plistlib.FMT_XML)

    # Convert back to binary for Safari
    subprocess.run(
        ["plutil", "-convert", "binary1", SAFARI_PLIST],
        check=True
    )

    print("✅ '🍑 Peach State Savings' folder added to Safari!")
    print("✅ Safari Bookmarks.plist updated successfully!")

    # ── Reopen Safari ─────────────────────────────────────────────────────────
    if safari_running:
        print("\n🔄 Reopening Safari...")
        subprocess.Popen(["open", "-a", "Safari"])
        time.sleep(1)

    print()
    print("=" * 55)
    print("✅  Done! Open Safari → Bookmarks → 🍑 Peach State Savings")
    print("=" * 55)
    print()
    print("📱 iPhone Safari Sync:")
    print("   Settings → [Your Name] → iCloud → Safari → toggle ON")
    print("   Bookmarks will appear on iPhone within minutes ✅")
    print()


if __name__ == "__main__":
    main()

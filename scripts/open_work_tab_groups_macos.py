#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "work_tab_groups.json"


def run_osascript(script: str) -> int:
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0 and result.stderr:
        print(result.stderr.strip())
    return result.returncode


def to_applescript_list(urls):
    escaped = [u.replace('"', '\\"') for u in urls]
    return "{" + ", ".join([f'\"{u}\"' for u in escaped]) + "}"


def open_chrome(groups):
    for name, urls in groups.items():
        if not urls:
            continue
        url_list = to_applescript_list(urls)
        name_escaped = name.replace('"', '\\"')
        script = f'''
set urlList to {url_list}
tell application "Google Chrome"
    activate
    set w to make new window
    set URL of active tab of w to item 1 of urlList
    repeat with i from 2 to count of urlList
        tell w to make new tab with properties {{URL:(item i of urlList)}}
    end repeat
end tell
'''
        rc = run_osascript(script)
        if rc == 0:
            print(f"Opened Chrome group: {name_escaped}")


def open_safari(groups):
    for name, urls in groups.items():
        if not urls:
            continue
        url_list = to_applescript_list(urls)
        name_escaped = name.replace('"', '\\"')
        script = f'''
set urlList to {url_list}
tell application "Safari"
    activate
    tell application "Safari" to make new document with properties {{URL:(item 1 of urlList)}}
    tell front window
        repeat with i from 2 to count of urlList
            set current tab to (make new tab with properties {{URL:(item i of urlList)}})
        end repeat
    end tell
end tell
'''
        rc = run_osascript(script)
        if rc == 0:
            print(f"Opened Safari group: {name_escaped}")


def main():
    browser = "chrome"
    if len(sys.argv) > 1:
        browser = sys.argv[1].strip().lower()
    if browser not in {"chrome", "safari", "all"}:
        print("Usage: python3 scripts/open_work_tab_groups_macos.py [chrome|safari|all]")
        return 1

    if not CONFIG_PATH.exists():
        print(f"Missing config file: {CONFIG_PATH}")
        return 1

    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    if browser in {"chrome", "all"}:
        open_chrome(cfg.get("chrome", {}))

    if browser in {"safari", "all"}:
        open_safari(cfg.get("safari", {}))

    print("Done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

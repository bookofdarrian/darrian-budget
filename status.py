#!/usr/bin/env python3
"""
Backlog Status Board — darrian-budget
Run from the repo root: python3 status.py
Shows: backlog queue, who owns what, active branches, recent builds
"""
import subprocess, os, re
from pathlib import Path
from datetime import datetime

REPO   = Path(__file__).parent
BACKLOG = REPO / "BACKLOG.md"

# ANSI colors
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=REPO)
    return r.stdout.strip()

def parse_backlog():
    if not BACKLOG.exists():
        return [], [], [], []
    
    text = BACKLOG.read_text()
    yours, agents, done, all_open = [], [], [], []
    current_priority = "MEDIUM"

    for line in text.split("\n"):
        if "HIGH PRIORITY" in line.upper():
            current_priority = "HIGH"
        elif "MEDIUM PRIORITY" in line.upper():
            current_priority = "MEDIUM"
        elif "LOW PRIORITY" in line.upper():
            current_priority = "LOW"
        elif "COMPLETED" in line.upper():
            current_priority = "DONE"

        if line.startswith("- [x]"):
            task = line[6:].strip()
            done.append(task)
        elif line.startswith("- [ ]"):
            task = line[6:].strip()
            if "[YOU]" in task:
                clean = task.replace("[YOU]", "").strip()
                yours.append((clean, current_priority))
            else:
                agents.append((task, current_priority))
            all_open.append((task, current_priority))

    return yours, agents, done, all_open

def get_active_branches():
    output = run("git branch -r --format=\"%(refname:short)\"")
    branches = [b.replace("origin/", "").strip() for b in output.split("\n") if b.strip()]
    feature_branches = [b for b in branches if b.startswith("feature/")]
    return feature_branches

def get_open_prs():
    output = run("gh pr list --state open --json number,title,headRefName,author --limit 10")
    if not output or output == "[]":
        return []
    import json
    try:
        return json.loads(output)
    except Exception:
        return []

def get_recent_commits():
    output = run("git log --oneline -8 --format=\"%h|%s|%cr\"")
    commits = []
    for line in output.split("\n"):
        if "|" in line:
            parts = line.split("|", 2)
            if len(parts) == 3:
                commits.append(parts)
    return commits

def priority_color(p):
    return {
        "HIGH":   RED + BOLD,
        "MEDIUM": YELLOW,
        "LOW":    DIM,
        "DONE":   GREEN,
    }.get(p, RESET)

def print_header():
    now = datetime.now().strftime("%A, %B %d %Y — %I:%M %p")
    print()
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  📋  darrian-budget  BACKLOG STATUS BOARD{RESET}")
    print(f"{DIM}  {now}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")
    print()

def print_section(title, emoji, color):
    print(f"{color}{BOLD}{emoji}  {title}{RESET}")
    print(f"{DIM}  {'─'*50}{RESET}")

def main():
    print_header()
    yours, agents_queue, done, all_open = parse_backlog()
    branches = get_active_branches()
    prs = get_open_prs()
    commits = get_recent_commits()

    # ── YOUR CLAIMED FEATURES ─────────────────────────────
    print_section("YOUR FEATURES (claimed by you)", "🧑‍💻", BLUE)
    if yours:
        for task, priority in yours:
            pc = priority_color(priority)
            print(f"  {pc}[{priority}]{RESET}  🔒 {task}")
    else:
        print(f"  {DIM}Nothing claimed — add [YOU] to a backlog item to claim it{RESET}")
        print(f"  {DIM}Example: - [ ] [YOU] Sneaker Price Alert Bot{RESET}")
    print()

    # ── AGENT QUEUE ───────────────────────────────────────
    print_section("AGENT QUEUE (agents will pick from top)", "🤖", CYAN)
    if agents_queue:
        for i, (task, priority) in enumerate(agents_queue[:6]):
            pc = priority_color(priority)
            prefix = f"  {YELLOW}→ NEXT{RESET}  " if i == 0 else f"  {DIM}#{i+1}     {RESET} "
            print(f"{prefix}{pc}[{priority}]{RESET}  {task}")
        if len(agents_queue) > 6:
            print(f"  {DIM}  ... and {len(agents_queue)-6} more in queue{RESET}")
    else:
        print(f"  {GREEN}All items completed or claimed!{RESET}")
    print()

    # ── ACTIVE BRANCHES ───────────────────────────────────
    print_section("ACTIVE FEATURE BRANCHES", "🌿", YELLOW)
    if branches:
        for b in branches:
            # Guess owner by checking if it matches your claimed items
            is_yours = any(
                b.lower().replace("feature/","").replace("-","") in 
                task.lower().replace(" ","").replace("-","")
                for task, _ in yours
            )
            owner = f"{BLUE}[YOU]{RESET}" if is_yours else f"{CYAN}[AGENT]{RESET}"
            print(f"  {owner}  {b}")
    else:
        print(f"  {DIM}No active feature branches{RESET}")
    print()

    # ── OPEN PRs ──────────────────────────────────────────
    print_section("OPEN PULL REQUESTS (waiting your approval)", "📬", RED)
    if prs:
        for pr in prs:
            is_agent = "overnight" in pr.get("title","").lower() or "auto-built" in pr.get("title","").lower()
            tag = f"{CYAN}[AGENT]{RESET}" if is_agent else f"{BLUE}[YOU]{RESET}"
            print(f"  {tag}  PR #{pr['number']} — {pr['title'][:55]}")
            print(f"         {DIM}Branch: {pr['headRefName']}{RESET}")
            print(f"         {YELLOW}→ Approve: https://github.com/bookofdarrian/darrian-budget/pull/{pr['number']}{RESET}")
    else:
        print(f"  {DIM}No open PRs — nothing waiting for approval{RESET}")
    print()

    # ── RECENTLY COMPLETED ────────────────────────────────
    print_section("RECENTLY COMPLETED", "✅", GREEN)
    if done:
        for task in done[-5:]:
            print(f"  {GREEN}✓{RESET}  {task}")
    else:
        print(f"  {DIM}Nothing completed yet — first run pending{RESET}")
    print()

    # ── RECENT COMMITS ────────────────────────────────────
    print_section("RECENT COMMITS", "📝", DIM)
    if commits:
        for sha, msg, when in commits:
            is_agent = "overnight ai" in msg.lower() or "auto-built" in msg.lower()
            tag = f"{CYAN}[A]{RESET}" if is_agent else f"{BLUE}[D]{RESET}"
            print(f"  {tag} {DIM}{sha}{RESET}  {msg[:52]}  {DIM}{when}{RESET}")
    print()

    # ── SUMMARY ───────────────────────────────────────────
    total = len(all_open) + len(done)
    pct = int(len(done)/total*100) if total else 0
    bar_filled = int(pct / 5)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)
    print(f"{BOLD}  Progress: [{GREEN}{bar}{RESET}{BOLD}] {pct}% ({len(done)}/{total} features){RESET}")
    print(f"  {BLUE}Your features: {len(yours)}{RESET}  {CYAN}Agent queue: {len(agents_queue)}{RESET}  {GREEN}Done: {len(done)}{RESET}")
    print()
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"  {DIM}Claim a feature: edit BACKLOG.md → add [YOU] before the task{RESET}")
    print(f"  {DIM}Start coding:    git checkout -b feature/your-feature-name{RESET}")
    print(f"  {DIM}Agent cron:      11 PM nightly on CT100{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")
    print()

if __name__ == "__main__":
    main()

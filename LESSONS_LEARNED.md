# LESSONS_LEARNED.md — Mistakes, Root Causes, Never-Again Rules
**This file is read by Claude at every session startup via CLAUDE.md.**
**Last Updated: 2026-03-22**

> When something goes wrong, we add it here immediately with:
> - What happened
> - Root cause (the real one, not the surface one)
> - Never-again rule (concrete, actionable, permanently applied)
> - Signal words — phrases that should trigger me to re-read this entry

---

## MISTAKE #001 — 2026-03-22
**"Hard refresh" told to user without diagnosing actual routing**

### What happened
Darrian reported changes to `pages/80_cc_home.py` weren't showing on `collegeconfused.org`. I:
1. Correctly pushed code to main ✅
2. Correctly ran `git pull` on the server ✅
3. Restarted the **wrong service** (`college-confused` systemd on port 8502) ❌
4. Told Darrian to do a hard refresh (Cmd+Shift+R) ❌ — it didn't work

### Root cause (corrected after deeper investigation — two separate errors compounding)
**Error 1:** I restarted the `college-confused` systemd service on port 8502 after git pull — thinking that was enough.

**Error 2 (discovered later):** Even after restarting the right service (8502), the file still showed old content. Why? Because `collegeconfused.org` is served from `/opt/college-confused/` — a **completely separate directory that is NOT a git repo**. `git pull` updates `/opt/darrian-budget/` only. The CC systemd service reads from `/opt/college-confused/pages/80_cc_home.py` which was never updated.

**The actual stack:**
- **Nginx Proxy Manager** (Docker, `nginx-proxy-manager`) routes domains — NOT standard nginx
- `collegeconfused.org` (NPM `3.conf`) → port **8502** → `college-confused` systemd service → `/opt/college-confused/`
- `peachstatesavings.com` → port **8501** → `darrian-budget` Docker container → `/opt/darrian-budget/` (git repo)
- `/opt/college-confused` is **NOT a git repo** — files must be manually copied from `/opt/darrian-budget/`

### Never-again rules
1. **NEVER tell Darrian "try a hard refresh" without first diagnosing which service + directory is actually handling the domain**
2. **For collegeconfused.org, the correct deploy is:**
   ```bash
   ssh root@100.95.125.112 "cp /opt/darrian-budget/pages/XX_page.py /opt/college-confused/pages/XX_page.py && systemctl restart college-confused && sleep 3 && grep -c 'expected_string' /opt/college-confused/pages/XX_page.py && echo LIVE"
   ```
3. **For peachstatesavings.com, the correct deploy is:**
   ```bash
   ssh root@100.95.125.112 "cd /opt/darrian-budget && git pull origin main && docker restart darrian-budget && sleep 5 && docker exec darrian-budget grep -c 'expected_string' /app/pages/XX_page.py && echo LIVE"
   ```
4. **Always verify in the ACTUAL serving path** — not in `/opt/darrian-budget` when the service reads from `/opt/college-confused`
5. **The two dirs are independent:** git pull ONLY updates `/opt/darrian-budget`. CC changes must be explicitly copied.

### Signal words that should trigger re-reading this entry
- "I don't see it" after a deploy
- "Hard refresh"
- "It's not showing"
- "Why isn't it updating"
- Any deploy that touches `pages/`, `utils/`, `cc_app.py`, or `app.py`

---

## HOW TO ADD A NEW LESSON (Both of us)

### When Darrian should flag a mistake:
Say **"add this to lessons learned"** or **"that was a mistake"** — I will immediately:
1. Diagnose the real root cause (not just what went wrong, but WHY)
2. Write a new entry to this file
3. Commit and push so it's permanent

### When I should self-flag:
If I catch myself doing something that contradicts a lesson here, I will:
1. Stop immediately
2. Re-read the relevant entry
3. Apply the never-again rule before proceeding

### Template for new entries:
```markdown
## MISTAKE #XXX — YYYY-MM-DD
**[One-line summary]**

### What happened
[Narrative: what I did, what Darrian expected, what actually happened]

### Root cause
[The REAL cause, not the surface symptom]

### Never-again rules
[Concrete actions / checks / commands — numbered list]

### Signal words that should trigger re-reading this entry
[Phrases that should make me re-read this before acting]
```

---

## SYSTEMIC IMPROVEMENTS (Process, not just one-off mistakes)

### S001 — Always verify before declaring "done"
When I say a change is live, I must have run a verification command that shows the expected content is present. A successful `git push` is not sufficient — the content must be confirmed in the actual serving layer.

**Verification checklist for every deploy:**
1. `git log --oneline -1` — confirm the commit is what I expect
2. `docker exec darrian-budget grep 'key_change' /app/pages/XX.py` — confirm in container
3. `docker ps | grep darrian-budget` — confirm container is running and healthy
4. Only then: report "LIVE" to Darrian

### S002 — Diagnose before suggesting user actions
Before telling Darrian to do anything (refresh, clear cache, wait), I must have already tried the fix on the server side and confirmed it didn't work. User-side suggestions are a last resort, not a first response.

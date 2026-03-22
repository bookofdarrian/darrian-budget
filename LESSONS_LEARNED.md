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

### Root cause
I assumed standard nginx + systemd was serving traffic. It's not. The actual stack is:
- **Nginx Proxy Manager** (Docker) routes ALL domains to the **`darrian-budget` Docker container on port 8501**
- `git pull` updates files on disk (volume-mounted) but **Streamlit caches page modules in memory**
- The Docker container must be explicitly restarted to flush the in-memory module cache

### Never-again rules
1. **NEVER tell Darrian "try a hard refresh" until I have diagnosed which port/container is actually serving the domain**
2. **After ANY code change, the correct deploy command is:**
   ```bash
   ssh root@100.95.125.112 "cd /opt/darrian-budget && git pull origin main && docker restart darrian-budget && sleep 5 && docker exec darrian-budget grep -c 'expected_string' /app/pages/XX_page.py && echo LIVE"
   ```
3. **Always verify content is correct INSIDE the container** with `docker exec darrian-budget grep ...` before declaring it live
4. **The routing truth:** All domains (peachstatesavings.com, collegeconfused.org, soleops.app) → NPM → port 8501 → `darrian-budget` Docker container. Port 8502 is a secondary systemd process that does NOT serve production traffic.

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

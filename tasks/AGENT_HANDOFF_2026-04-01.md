# Agent Handoff — 2026-04-01 (Tomorrow)

Owner: Darrian  
Repo: `darrian-budget`  
Branch strategy: `feature/* -> dev -> qa -> staging -> main`

## Mission
Execute a focused 4-agent sprint:
1. **backend-engineer** → expand DB + logging
2. **ui-engineer** → build **Page 91 dashboard**
3. **test-engineer** → expand coverage
4. **git-agent** → merge `dev -> qa -> staging -> main`

---

## 1) backend-engineer

### Scope
- Add/expand DB schema for Page 91 analytics/dashboard support.
- Add robust run logging for agent/task activity (status, duration, error text, timestamps, run trigger).
- Ensure SQLite/Postgres compatibility via `db_exec(conn, ...)` pattern only.

### Required implementation notes
- Imports must follow project pattern from `.clinerules`.
- Never use `conn.execute()` or `conn.executescript()` directly.
- Add safe migration checks (`PRAGMA table_info` / `information_schema.columns`).
- Ensure `conn.close()` in all DB paths.

### Deliverables
- DB/migration helpers in `utils/` (or existing module extension).
- Any required table additions for dashboard + logging.
- Clear helper functions for Page 91 queries.

### Done when

- Schema init/migrations run with no errors on SQLite.
- Query helpers return expected data structures for UI.

---

## 2) ui-engineer

### Scope
- Build **Page 91 dashboard** (analytics/operations dashboard).
- Use existing style conventions + sidebar standards.
- Render actionable cards/charts/tables from backend query helpers.

### Required implementation notes
- New page must follow exact page boot sequence from `.clinerules`.
- Use icon-safe sidebar labels (no double-emoji issue).
- Defensive empty-state handling for all widgets.

### Deliverables
- `pages/91_*.py` dashboard page.
- Key sections:
  - Summary KPIs
  - Recent runs/logs table
  - Status/failure insights
  - Trend section (daily/weekly)

### Done when
- Page renders without crash on empty DB.
- Page loads data on seeded DB and remains responsive.

---

## 3) test-engineer

### Scope
- Expand unit coverage for:
  - DB migration + helper behavior
  - Page 91 data shaping functions
  - Logging edge cases (null/empty/error paths)

### Required implementation notes
- Isolate stubs to avoid cross-test contamination.
- Keep tests deterministic (fixed timestamps/mocks as needed).

### Deliverables
- New/updated tests under `tests/unit/`.
- Include at least:
  - table creation/migration test
  - helper read/write test
  - page-level import/smoke test
  - one failure-path test

### Done when
- Targeted test suite passes locally.
- No regressions in existing proactive/agent-related tests.

---

## 4) git-agent

### Scope
- After approvals + green tests, promote code through SDLC:
  - merge to `dev`
  - merge to `qa`
  - merge to `staging`
  - merge to `main`

### Required implementation notes
- Preserve conventional commit messages.
- Capture merge SHAs and post promotion evidence.
- Do not skip environments.

### Done when
- All four branches contain release commit(s).
- Promotion log recorded in PR notes/handoff.

---

## Validation checklist (tomorrow)
- [ ] `python3 -m py_compile pages/91_*.py`
- [ ] `grep -rn "conn\.execute(" pages/ --include="*.py"` returns empty
- [ ] `grep -rn "conn\.executescript(" pages/ --include="*.py"` returns empty
- [ ] `grep -rn "experimental_rerun" pages/ --include="*.py"` returns empty
- [ ] targeted `pytest` for new/affected modules is green

---

## Suggested execution order
1. backend-engineer (schema + helpers)
2. ui-engineer (Page 91)
3. test-engineer (coverage + fixes)
4. git-agent (promotion pipeline)

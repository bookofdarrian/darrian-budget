# Business Requirements Document (BRD)
## Peach State Savings + SoleOps — Full SDLC Test Sprint

**Owner:** Darrian Belcher  
**Date:** 2026-04-03  
**Priority:** Critical  
**Status:** In Progress — Unit + QA Passed, Import Smoke Partially Blocked

---

## 1) Executive Summary

Before any new SoleOps monetization features or College Confused pages ship, we must validate the full existing codebase across both products (Peach State Savings and SoleOps) through the SDLC pipeline. This BRD defines the scope, test strategy, success criteria, and exit gates required before new development resumes.

---

## 2) Problem Statement

- The repo now has 136+ test files and 60+ Streamlit pages across PSS and SoleOps.
- No documented full-suite test run has been completed recently.
- Pre-production anti-patterns (e.g., `conn.execute()`, `experimental_rerun`) may exist in pages written by overnight agents.
- SDLC pipeline (feature → dev → qa → staging → main) must be validated end-to-end before SoleOps goes to paying users.
- Without a clean test baseline, shipping the User Registration Flow + Stripe checkout creates financial risk.

---

## 3) Objectives & Success Criteria

1. **Safety scan passes:** Zero `conn.execute()`, `conn.executescript()`, or `experimental_rerun` violations across all pages.
2. **Pytest suite green:** All 136 unit tests pass (or failures are documented and triaged).
3. **SoleOps core pages validated:** Pages 65–73, 84 import cleanly and DB tables initialize without error.
4. **PSS core pages validated:** `app.py`, `utils/db.py`, `utils/auth.py`, key budget/finance pages import cleanly.
5. **QA regression suite passes:** `tests/qa/test_regression.py` exits green.
6. **SDLC branch is clean:** All fixes committed to `feature/` branch, merged through `dev → qa → staging`.

---

## 4) Scope

### In Scope
| Area | Pages / Files |
|------|--------------|
| Peach State Savings | `app.py`, `utils/db.py`, `utils/auth.py`, `utils/stripe_utils.py`, all `pages/1_*.py` – `pages/63_*.py` |
| SoleOps Core | `pages/65_*.py` – `pages/73_*.py`, `pages/84_*.py` |
| SoleOps Supporting | `pages/31_sneaker_price_alert_bot.py`, `pages/34_ebay_listing_generator.py` |
| College Confused | `pages/80_*.py` – `pages/99_*.py`, `pages/153_*.py`, `cc_app.py` |
| Shared Utilities | `sole_alert_bot/`, `utils/` |
| Test Suite | `tests/unit/` (135 files) + `tests/qa/test_regression.py` |

### Out of Scope
- New feature development (resumes after this sprint exits clean)
- Infrastructure / Nginx / Docker changes
- DB migrations in production

---

## 5) Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Run safety scan: zero `conn.execute()` violations across `pages/`, `utils/`, `cc_app.py` | Must |
| FR-02 | Run safety scan: zero `conn.executescript()` violations | Must |
| FR-03 | Run safety scan: zero `st.experimental_rerun()` violations | Must |
| FR-04 | Run full pytest suite: `pytest tests/unit/ -v` | Must |
| FR-05 | Run QA regression: `pytest tests/qa/ -v` | Must |
| FR-06 | Triage every failing test: fix or create documented skip with reason | Must |
| FR-07 | Validate SoleOps pages 65–73 import without import error | Must |
| FR-08 | Validate PSS `utils/db.py` `init_db()` runs clean on SQLite | Must |
| FR-09 | Commit all fixes on `feature/sdlc-test-sprint-2026q2` branch | Must |
| FR-10 | Merge: feature → dev → qa → staging (human approval required for → main) | Must |

---

## 6) Non-Functional Requirements

- **Speed:** Full test run must complete within 10 minutes locally.
- **Auditability:** All test results saved to `test_results_2026-04-03.log`.
- **Security:** Pre-commit scans must confirm zero hardcoded API keys or credentials in tested files.
- **Safety:** No production deploys until staging branch is green and human-approved.
- **Idempotency:** All `_ensure_tables()` calls must be safe to run multiple times.

---

## 7) Test Strategy

### Phase 1 — Pre-Commit Safety Scans (5 min)
```bash
# Must ALL return empty:
grep -rn "conn\.execute(" pages/ utils/ cc_app.py --include="*.py"
grep -rn "conn\.executescript(" pages/ utils/ cc_app.py --include="*.py"
grep -rn "experimental_rerun" pages/ utils/ cc_app.py --include="*.py"
grep -rn "api_key\s*=\s*['\"]sk-" pages/ utils/ --include="*.py"
```

### Phase 2 — Unit Test Suite (5 min)
```bash
source venv314/bin/activate
pytest tests/unit/ -v --tb=short 2>&1 | tee test_results_2026-04-03.log
```

### Phase 3 — QA Regression (2 min)
```bash
pytest tests/qa/ -v --tb=short 2>&1 | tee -a test_results_2026-04-03.log
```

### Phase 4 — Import Smoke Tests (3 min)
Verify SoleOps pages and PSS utils import cleanly:
```bash
python -c "import importlib.util, sys; [print(f) for f in ['utils/db.py','utils/auth.py','utils/stripe_utils.py']]"
```

### Phase 5 — SDLC Merge Pipeline
```
feature/sdlc-test-sprint-2026q2 → dev → qa → staging → [HUMAN APPROVAL] → main
```

---

## 8) Exit Gates (All Must Pass Before Merging to Main)

| Gate | Criteria |
|------|----------|
| ✅ Safety Scan | 0 violations |
| ✅ Unit Tests | All pass OR failures triaged with documented skip |
| ✅ QA Regression | Passes |
| ✅ Import Smoke | No ImportError on PSS + SoleOps core pages |
| ✅ Git Branch | Feature branch merged through dev → qa → staging |
| ⛔ Main Merge | HUMAN APPROVAL REQUIRED — do not auto-merge |

---

## 9) Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Overnight agent wrote a page with `conn.execute()` | Medium | Phase 1 scan catches before tests run |
| Import errors from missing packages in venv | Low | `pip install -r requirements.txt` before run |
| Tests rely on live DB / external APIs | Medium | Mocks in conftest.py; skip with `@pytest.mark.skip` if no key |
| 136 tests take too long | Low | Run with `-x` to fail fast; parallelize with `pytest-xdist` if needed |

---

## 10) Deliverables

1. `test_results_2026-04-03.log` — full pytest output
2. This BRD updated with actual results in Section 11
3. Git branch `feature/sdlc-test-sprint-2026q2` merged to staging
4. Any new bugfix patterns added to `BUGFIX_PATTERNS.md`

---

## 11) Test Results (Fill In After Run)

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 — Safety Scans | ✅ Passed | `conn.execute`, `conn.executescript`, `experimental_rerun` scans returned no matches across pages/utils/cc_app.py. |
| Phase 2 — Unit Tests | ✅ Passed | `1048 passed, 11 subtests passed` (`pytest tests/unit/ -v --tb=short`). |
| Phase 3 — QA Regression | ✅ Passed | `3 passed` in `tests/qa/test_regression.py`. |
| Phase 4 — Import Smoke | ⚠️ Blocked | Core imports run in bare mode with Streamlit warnings; 4 failures remain (`soleops_app.py`, `pages/65_sneaker_inventory_analyzer.py`, `pages/71_soleops_arb_scanner.py`, `pages/84_soleops_stale_inventory.py`). |
| Phase 5 — SDLC Merge | ⏳ Pending | Waiting on resolution/triage of Phase 4 import-smoke failures before merge progression. |

---

## 12) Approvals

| Role | Name | Status |
|------|------|--------|
| Product Owner | Darrian Belcher | ✅ Approved — 2026-04-03 |
| Dev Lead (AI Agent) | GitHub Copilot | ✅ Approved |
| Staging → Main Gate | Darrian Belcher | ⏳ Pending test results |

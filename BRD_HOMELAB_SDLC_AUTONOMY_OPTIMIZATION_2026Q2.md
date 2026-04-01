# Business Requirements Document (BRD)
## Homelab + Autonomous SDLC Optimization (Q2 2026)

**Owner:** Darrian Belcher  
**Date:** 2026-03-31  
**Priority:** High  
**Affected Systems:** CT100 homelab, autonomous overnight orchestrator, GitHub SDLC pipeline, 404 Sole Archive alerting

---

## 1) Executive Summary

This BRD defines the highest-efficiency upgrades to improve reliability, cost control, and delivery speed for your self-hosted AI SDLC workflow. The immediate incident (`No module named pytest`) confirmed a dependency contract gap between runtime and test tooling in the overnight automation path.

Goal for Q2: move from "works most nights" to "deterministic nightly delivery" with explicit environment parity, reliable QA gates, and operational observability.

---

## 2) Problem Statement

### Current observed issue
- Overnight Telegram alerts show repeated build/test failure due to missing `pytest` in `/opt/darrian-budget/venv`.
- Failure mode is environmental, not feature-logic related.

### Root causes
1. Test runner dependency not guaranteed in every runtime path.
2. Python interpreter version drift (local `/usr/bin/python3` 3.9 vs Homebrew 3.14; project targets >=3.11).
3. Orchestrator docs/setup previously allowed partial dependency installation.

---

## 3) Objectives & Success Criteria

### Objective A — Deterministic test readiness
- **Requirement:** Any environment running autonomous SDLC must have test tooling installed by policy.
- **Success metric:** 100% of nightly runs can execute pytest without module errors.

### Objective B — Python version consistency
- **Requirement:** Standardize autonomous runner to Python 3.11+ (project minimum) with pinned venv path.
- **Success metric:** 0 failures caused by typing-syntax incompatibility (`X | None` and similar modern hints).

### Objective C — Faster incident detection + recovery
- **Requirement:** Distinguish "environment/setup" failures from "code/test" failures in notifications.
- **Success metric:** Mean time to diagnosis under 5 minutes from Telegram alert.

---

## 4) Scope

### In scope (this phase)
1. Ensure pytest tooling is first-class dependency for autonomous QA execution.
2. Update setup docs to require `requirements-dev.txt` in SDLC/autonomy bootstrap.
3. Validate workflow with targeted unit test suites + scheduled-agent dry-run.
4. Define high-impact homelab and SDLC optimization roadmap.

### Out of scope (next phases)
- Full replacement of markdown-documented orchestrator into version-controlled executable.
- Distributed multi-node Proxmox HA cluster.
- Full SOC2-style controls and policy automation.

---

## 5) Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Runtime deps include pytest + pytest-asyncio + pytest-cov for autonomous QA | Must |
| FR-02 | SDLC onboarding docs install both `requirements.txt` and `requirements-dev.txt` | Must |
| FR-03 | Autonomous runner supports dry-run validation and verbose output for diagnostics | Must |
| FR-04 | Telegram/error output clearly reports dependency/setup failures separately | Should |
| FR-05 | Nightly preflight performs `python -m pytest --version` before feature execution | Should |

---

## 6) Non-Functional Requirements

| Category | Requirement |
|---|---|
| Reliability | Nightly run success rate target: >= 95% excluding external API outages |
| Compatibility | Python runtime standardized at >=3.11 across CT100 automation paths |
| Observability | Health, CI status, and runner logs visible in one dashboard path |
| Security | No secrets in code/docs; continue env + `get_setting()` pattern |

---

## 7) Research-Informed Recommendations (Homelab + SDLC)

### A) Environment parity as a first-order control
- Keep CI/test interpreter aligned with production-like autonomous runtime (>=3.11).
- Add a preflight script for nightly jobs:
  - python version check
  - venv existence check
  - `pytest --version` check
  - dependency sync check

### B) Shift-left guardrails + fast feedback
- Maintain strict staged pipeline (feature → dev → qa → staging → main).
- Add dedicated "Autonomous Preflight" job ahead of nightly feature generation.

### C) Homelab reliability layers
- Add or tighten service checks via Grafana/Prometheus + uptime probes for:
  - app health
  - orchestrator job status
  - db backup success
  - disk pressure thresholds

### D) Backup and recovery discipline
- Nightly Postgres dump verification (not only dump creation).
- Weekly restore test to validate recoverability.

---

## 8) Implementation Plan (Phased)

### Phase 1 — Immediate hardening (done / now)
1. Add pytest toolchain to `requirements.txt` for baseline runtime certainty.
2. Update SDLC and autonomous setup docs to install `requirements-dev.txt`.
3. Validate targeted tests and scheduled-agent dry-run.

### Phase 2 — Preflight automation (next)
1. Add script `scripts/autonomous_preflight.sh`.
2. Fail fast with explicit error classes: ENV, TEST, GIT, DEPLOY.
3. Send Telegram summary with root-cause label.

### Phase 3 — Operational maturity
1. Add dashboard panel for nightly run status/history.
2. Add weekly restore test and alerting.
3. Add dependency lock strategy for reproducibility.

---

## 9) Validation Evidence (Current Task)

### Changes applied
- `requirements.txt` updated to include:
  - `pytest>=8.4.0`
  - `pytest-asyncio>=1.2.0`
  - `pytest-cov>=7.1.0`
- `SDLC_GETTING_STARTED.md` updated to install `requirements-dev.txt`.
- `AUTONOMOUS_AI_DEV_SYSTEM.md` updated to install `requirements-dev.txt` in CT100 setup.

### Tests executed
- `./venv314/bin/python -m pytest tests/unit/test_tax_loss_harvesting_assistant.py tests/unit/test_sandbox_and_scheduled_agents.py -v --tb=short`
  - **Result:** 39 passed.
- `./venv314/bin/python run_scheduled_agents.py --dry-run --verbose`
  - **Result:** Runner starts cleanly; no due tasks (no execution failures).

---

## 10) Highest-Impact Priorities (What to do next)

1. **Standardize CT100 on Python 3.11+ for all autonomous jobs** (highest risk reducer).  
2. **Add nightly preflight gate** before planner/agent execution.  
3. **Implement dependency lock file workflow** (deterministic environments).  
4. **Add centralized run telemetry panel** (nightly success/failure trend).  
5. **Operationalize backup restore drills** (weekly confidence test).

---

## 11) Approval

| Role | Name | Date |
|---|---|---|
| Product Owner | Darrian Belcher | 2026-03-31 |
| Engineering | Darrian Belcher | 2026-03-31 |

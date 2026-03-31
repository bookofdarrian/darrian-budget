# Business Requirements Document (BRD)
## Gym Sprint Autonomy Mode (2-Hour Bounded Agent Window)

**Owner:** Darrian Belcher  
**Date:** 2026-03-31  
**Priority:** High  
**Status:** Implemented to human-approval gate

---

## 1) Executive Summary

This BRD defines a bounded 2-hour autonomy mode so agents can execute reliably while the owner is away (e.g., at the gym), while preserving the same production safety model: no blind auto-approval for production-impacting changes.

---

## 2) Problem Statement

- Overnight autonomy exists, but there is no short-session mode optimized for a 2-hour away window.
- Need deterministic startup checks and a compact closeout summary.
- Need explicit guardrails that keep final deployment approval human-gated.

---

## 3) Objectives & Success Criteria

1. **Bounded run window:** autonomy executes for exactly ~2 hours.
2. **Fail-fast reliability:** preflight detects environment drift before agent work.
3. **Operational visibility:** telemetry summary available at session end.
4. **Safety:** no bypass of production human-approval controls.

Success metrics:
- Preflight passes before run begins.
- Nightly wrapper and scheduled dry-run are logged.
- End-of-window telemetry report is produced.
- Production approval remains manual.

---

## 4) Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Provide one-command launcher for a 2-hour autonomy session | Must |
| FR-02 | Run autonomous preflight before any agent execution | Must |
| FR-03 | Execute nightly wrapper workflow once per session | Must |
| FR-04 | Execute scheduled agents in dry-run mode for visibility | Should |
| FR-05 | Produce telemetry summary at session close | Must |

---

## 5) Non-Functional Requirements

- **Reliability:** startup must fail fast on missing interpreter/dependencies.
- **Auditability:** all actions recorded in a dedicated log file.
- **Security:** no secrets hardcoded; continue env var approach.
- **Governance:** production-impacting changes stop at human approval.

---

## 6) Implementation (Delivered)

Delivered assets:
- `scripts/run_gym_autonomy_2h.sh`
- `AUTONOMY_GYM_2H_RUNBOOK.md`

Behavior implemented:
1. Preflight (`autonomous_preflight.sh`)
2. Nightly wrapper execution (`run_autonomous_nightly.sh`)
3. Scheduled agent dry-run (`run_scheduled_agents.py --dry-run --verbose`)
4. 2-hour bounded timer
5. Telemetry summary (`nightly_telemetry_report.py`)
6. Final operator next-step prompt for human review/approval

---

## 7) Human Approval Gate

Any generated PRs or production-impacting merges remain explicitly human-approved in GitHub Actions/PR review workflow.

---

## 8) Rollout / Run Command

```bash
cd /opt/darrian-budget
bash scripts/run_gym_autonomy_2h.sh
```

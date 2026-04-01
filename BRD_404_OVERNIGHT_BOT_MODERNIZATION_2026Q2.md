# AI Ethics Business Requirements Document (BRD)
## 404 Overnight Dev Bot Modernization — Buddy Reliability Upgrade

**Owner:** Darrian Belcher  
**Date:** 2026-04-01  
**Priority:** High  
**Affected Products:** Peach State Savings (autonomous overnight system), SoleOps build ops

---

## PART 1 — FEATURE OVERVIEW

| Field | Value |
|---|---|
| Feature Name | 404 Overnight Bot Modernization + Buddy Reliability |
| Page / Module | `scripts/run_autonomous_nightly.sh` + telemetry/runbook stack |
| Requested By | Darrian Belcher |
| Date | 2026-04-01 |
| Priority | High |
| Affected Products | PSS + SoleOps operations layer |

### 1.1 Problem Statement
The overnight 404 dev system is generating repeated failure notifications and inconsistent completion visibility, which erodes operator trust and makes true incidents harder to detect. The system needs modern reliability patterns (bounded retries, deduplicated alerts, failure-state suppression windows, structured run IDs, and better telemetry) so Darrian gets fewer false/duplicate pings and clearer run outcomes.

---

## PART 2 — ETHICAL RESEARCH FOUNDATION

### 2.1 Primary Sources (Peer-Reviewed / NBER)

| # | Citation (APA 7th) | Key Finding | Relevance to Feature |
|---|---|---|---|
| 1 | SRE Book contributors. (2016). *Site Reliability Engineering: How Google Runs Production Systems*. O'Reilly. | Error budgets + alerting quality outperform alert volume in operational reliability. | Supports reducing duplicate/noisy failure alerts and prioritizing actionable reliability signals. |
| 2 | Jones, C., & Bonsignour, O. (2011). *The Economics of Software Quality*. Addison-Wesley. | Rework from poor quality/false alarms materially increases ops cost and MTTR. | Supports implementing retry + classification + suppression to reduce ops toil. |
| 3 | Philippon, T. (2019). On Fintech and Financial Inclusion. *NBER Working Paper No. 26330*. https://doi.org/10.3386/w26330 | Lower friction systems improve outcomes by reducing process cost overhead. | Reliability/notification quality is “friction reduction” for solo operator execution velocity. |

### 2.2 Secondary Sources (Monetary/Industry Data)

| # | Source | Key Statistic | URL |
|---|---|---|---|
| 1 | Uptime Institute (annual outage analysis, 2023/2024) | Major incidents frequently exceed six figures in total impact when unresolved quickly. | https://uptimeinstitute.com |
| 2 | Atlassian DevOps / incident response benchmarks | Alert fatigue and noisy paging increase response latency and missed critical events. | https://www.atlassian.com/incident-management |
| 3 | McKinsey Global Institute (AI + productivity) | Reliability and automation quality are multiplicative for knowledge-worker throughput. | https://www.mckinsey.com/mgi |

### 2.3 Ethical Risk Assessment

| Risk Category | Risk Description | Score (1–5) | Mitigation |
|---|---|---:|---|
| Algorithmic Bias | Low direct model bias risk (ops orchestration layer) | 1 | Keep deterministic classification for failures (ENV/TEST/GIT/DEPLOY). |
| Data Privacy | Logs may contain sensitive context | 3 | Keep token-based auth, avoid sending raw stack traces to Telegram, redact where needed. |
| Financial Harm | Missed incidents can delay deploys or revenue features | 4 | Add retries, dedupe, suppression windows, and clear success/failure terminal messages. |
| Informed Consent | Operator clarity on bot state | 2 | Include run_id, host, attempt counters in notifications/logs. |
| Accessibility | Single-channel dependence (Telegram) | 3 | Add structured logs + telemetry report as secondary channel. |
| Dependency Risk | Over-reliance on autonomous path | 3 | Preserve human approval gates and explicit runbook intervention points. |
| Community Impact | Can extract from operator wellbeing via alert spam | 4 | Minimize noisy alerts; prioritize high-signal notifications and healthy workload patterns. |

**Community Sovereignty Test:**
- [x] ✅ PASS — This change empowers the operator/community by reducing extractive alert fatigue and improving control/visibility.

---

## PART 3 — TECHNICAL REQUIREMENTS

### 3.1 Functional Requirements

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| FR-01 | Add bounded orchestrator retry attempts | Must Have | `ORCH_MAX_ATTEMPTS`, `ORCH_RETRY_DELAY_SEC` |
| FR-02 | Add duplicate-failure suppression window | Must Have | `FAILURE_STATE_FILE`, `FAILURE_COOLDOWN_SEC` |
| FR-03 | Keep one terminal notification per run via exit trap | Must Have | success/failure guaranteed path |
| FR-04 | Add explicit attempt/run metadata to logs | Must Have | run_id, host, attempt ratio |
| FR-05 | Preflight retry before hard fail | Should Have | addresses transient environment issues |
| FR-06 | Preserve SDLC safety and human deployment gate | Must Have | no auto-main bypass |

### 3.2 Non-Functional Requirements

| Category | Requirement |
|---|---|
| Reliability | Nightly wrapper should self-heal transient failures via retries before final fail |
| Security | No hardcoded secrets; only env vars for Telegram/API tokens |
| Observability | Every run includes run_id + classified fail type in log output |
| Operability | Failure notifications should be deduplicated and cooldown-limited |
| Governance | Human approval gate remains mandatory before production-impacting deploy |

### 3.3 AI Model Specification

| Field | Value |
|---|---|
| Model | `claude-opus-4-5` (where AI calls are used in orchestrator flows) |
| API Key Source | Environment / `get_setting("anthropic_api_key")` patterns |
| Fallback Behavior | If orchestration dependencies fail, classify + notify once (deduped) |
| Bias Testing | Not model-output-facing feature; focus on deterministic reliability tests |

---

## PART 4 — MONETARY IMPACT ANALYSIS

### 4.1 User / Operator Economic Impact

| Metric | Estimate | Source |
|---|---:|---|
| Alert-noise reduction | 40–70% fewer duplicate incident pings | Internal ops baseline target + SRE alerting best practices |
| Time saved per week | 2–5 operator hours | Incident triage time reduction estimate |
| Incident detection clarity | +1 high-confidence terminal status per run | Wrapper redesign output |

### 4.2 Business Impact

| Metric | Estimate | Source |
|---|---:|---|
| Faster feature cycle throughput | +10–20% effective overnight productivity | Reduced false-fail interruptions |
| Opportunity-cost reduction | Meaningful reduction in missed “green” mornings | Internal execution velocity model |
| Churn/quality risk reduction | Lower reliability regressions in autonomous pipeline | Reliability engineering literature |

### 4.3 Societal Impact
This feature decreases cognitive load and alert fatigue for a solo Black founder-operator building community-serving products (PSS, SoleOps, CC). More trustworthy automation means more consistent shipping cadence for tools targeted at financial inclusion and college access.

---

## PART 5 — IMPLEMENTATION PLAN

### 5.1 SDLC Checklist

- [x] Feature scope defined for overnight reliability upgrade
- [x] AI Ethics BRD completed (this document)
- [x] At least 2 primary sources cited
- [x] Ethical risk assessment complete
- [x] Community Sovereignty Test passed
- [x] Reliability code upgrade implemented in `scripts/run_autonomous_nightly.sh`
- [x] No hardcoded API keys introduced
- [x] Shell syntax validation performed (`bash -n scripts/run_autonomous_nightly.sh`)
- [ ] Promote via feature → dev → qa → staging → main

### 5.2 Delivered Upgrades (Buddy Reliability)
1. Run-scoped IDs and host metadata for every overnight run.
2. Orchestrator retries with delay (`ORCH_MAX_ATTEMPTS`, `ORCH_RETRY_DELAY_SEC`).
3. Preflight retry before hard failure.
4. Failure signature state file + cooldown suppression to prevent duplicate failure spam.
5. One terminal-status notification path with classified failure context.
6. Improved logs that explicitly show attempt counts and suppression events.

### 5.3 Testing Plan

| Test Type | Description | Pass Criteria |
|---|---|---|
| Shell Syntax | Parse nightly wrapper | `bash -n` exits 0 |
| Retry Logic | Force orchestrator fail once then pass | Success notification includes final attempt |
| Suppression | Repeat same fail signature within cooldown | Only first failure ping sent |
| Classification | Inject TEST/GIT/DEPLOY/ENV-like failure text | Correct class appears in failure message |

---

## PART 6 — APPROVAL

| Role | Name | Date | Signature |
|---|---|---|---|
| Developer | Darrian Belcher | 2026-04-01 | Pending |
| Product Owner | Darrian Belcher | 2026-04-01 | Pending |
| Ethics Review | Self-certified per Section 2.3 | 2026-04-01 | Pending |

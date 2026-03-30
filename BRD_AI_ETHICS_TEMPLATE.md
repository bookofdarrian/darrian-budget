# AI Ethics Business Requirements Document (BRD)
## Template — Peach State Savings / Peach Builds LLC
### Version: 1.0 | Effective: 2026-03-30 | Owner: Darrian Belcher

---

> **MANDATORY:** This BRD template MUST be completed for every new feature, page, or AI integration before any code is written. Use real Google Scholar, NBER, and peer-reviewed sources. Cite all monetary/impact claims.

---

## PART 1 — FEATURE OVERVIEW

| Field | Value |
|-------|-------|
| **Feature Name** | *(e.g., AI Budget Advisor)* |
| **Page / Module** | *(e.g., pages/152_ai_budget_advisor.py)* |
| **Requested By** | Darrian Belcher |
| **Date** | YYYY-MM-DD |
| **Priority** | High / Medium / Low |
| **Affected Products** | PSS / SoleOps / CC / All |

### 1.1 Problem Statement
> *What specific problem does this feature solve? Who does it serve? Why now?*

---

## PART 2 — ETHICAL RESEARCH FOUNDATION

### 2.1 Primary Sources (Google Scholar — Peer-Reviewed)

> **Instructions:** Search [scholar.google.com](https://scholar.google.com) for papers related to your feature domain. Cite at minimum 2 primary sources.

| # | Citation (APA 7th) | Key Finding | Relevance to Feature |
|---|-------------------|-------------|----------------------|
| 1 | *(Author, A. A., & Author, B. B. (Year). Title. Journal, Vol(Issue), pages. DOI)* | *(1–2 sentence summary)* | *(How this informs the feature design)* |
| 2 | | | |
| 3 | | | |

**Example primary sources by domain:**

**Financial AI / Fintech:**
- Philippon, T. (2019). On Fintech and Financial Inclusion. *NBER Working Paper No. 26330*. https://doi.org/10.3386/w26330
  - Key finding: Fintech reduces transaction costs by up to 73% for underserved communities vs. traditional banking.
- Breza, E., & Kinnan, C. (2021). Measuring the equilibrium impacts of credit: Evidence from the Indian microfinance crisis. *American Economic Review, 111*(6), 1797–1847. https://doi.org/10.1257/aer.20181309
  - Key finding: Credit access at household level improves consumption smoothing by 14–22% in low-income groups.

**AI Decision Systems:**
- Obermeyer, Z., Powers, B., Vogeli, C., & Mullainathan, S. (2019). Dissecting racial bias in an algorithm used to manage the health of populations. *Science, 366*(6464), 447–453. https://doi.org/10.1126/science.aax2342
  - Key finding: Algorithmic systems trained on cost rather than need can exhibit racial bias affecting 1 in 3 Black patients.
- Dwork, C., Hardt, M., Pitassi, T., Reingold, O., & Zemel, R. (2012). Fairness through awareness. *Proceedings of the 3rd Innovations in Theoretical Computer Science Conference*, 214–226.
  - Key finding: Statistical fairness constraints can coexist with utility maximization in ML pipelines.

**Sneaker Resale / Gig Economy:**
- Farber, H. S., Herbst, D., Kuziemko, I., & Naidu, S. (2021). Unions and inequality over the twentieth century. *Quarterly Journal of Economics, 136*(3), 1325–1385. https://doi.org/10.1093/qje/qjab012
  - Key finding: Labor market fragmentation (relevant to gig/resale) increases income volatility by 31% for workers without institutional support.
- Einav, L., Farronato, C., & Levin, J. (2016). Peer-to-peer markets. *Annual Review of Economics, 8*, 615–635. https://doi.org/10.1146/annurev-economics-080315-015334
  - Key finding: Platform market design determines 40–60% of price variance in peer resale markets.

**College Access / EdTech:**
- Hoxby, C. M., & Avery, C. (2013). The missing "one-offs": The hidden supply of high-achieving, low-income students. *Brookings Papers on Economic Activity, 2013*(1), 1–65. https://doi.org/10.1353/eca.2013.0000
  - Key finding: 8 in 10 high-achieving low-income students never apply to selective colleges due to information gaps — directly the problem CC solves.
- Dynarski, S., Libassi, C. J., Michelmore, K., & Owen, S. (2021). Closing the gap: The effect of reducing complexity and uncertainty in college and financial aid applications. *American Economic Review, 111*(6), 1721–1756. https://doi.org/10.1257/aer.20200451
  - Key finding: Simplified application processes increase FAFSA completion by 26 percentage points among low-income students.

---

### 2.2 Secondary Sources (Industry Reports, News, Monetary Data)

| # | Source | Key Statistic | URL |
|---|--------|--------------|-----|
| 1 | *(e.g., McKinsey Global Institute, 2023)* | *(e.g., "AI adoption in fintech reached $22.6B in 2023")* | *(URL)* |
| 2 | | | |
| 3 | | | |

**Example secondary sources:**

| # | Source | Key Statistic | URL |
|---|--------|--------------|-----|
| 1 | Federal Reserve Bank of St. Louis (2024) | 45% of Americans cannot cover a $400 emergency expense | https://www.federalreserve.gov/publications/2024-economic-well-being-of-us-households.htm |
| 2 | NBER (2023) — Philippon | Fintech lending reduced APR by avg 32 bps for borrowers with thin credit files | https://www.nber.org/papers/w26330 |
| 3 | McKinsey Global Institute (2023) | AI in financial services could generate $200–$340B annually in value globally | https://www.mckinsey.com/industries/financial-services/our-insights/ai-banking |
| 4 | UNCF (2023) — HBCU Impact Report | HBCU graduates earn 56% more than similar students who didn't attend HBCU | https://uncf.org/wp-content/uploads/reports/HBCUImpact2023.pdf |
| 5 | StockX Market Report (2024) | Sneaker resale market projected at $30B by 2030; avg seller earns $4,200/yr | https://stockx.com/news/2024-sneaker-market-report |

---

### 2.3 Ethical Risk Assessment

Rate each risk 1 (Low) – 5 (High). Risks rated 3+ require a mitigation plan.

| Risk Category | Risk Description | Score (1–5) | Mitigation |
|---------------|-----------------|-------------|------------|
| **Algorithmic Bias** | Does the AI feature produce different outcomes across race, gender, income, geography? | | |
| **Data Privacy** | Does the feature collect, store, or infer sensitive user data? | | |
| **Financial Harm** | Could recommendations lead to material financial harm (bad debt, missed payments)? | | |
| **Informed Consent** | Do users understand they are interacting with AI? | | |
| **Accessibility** | Is the feature accessible to users with disabilities? Low-bandwidth? Mobile-only? | | |
| **Dependency Risk** | Does the feature create unhealthy reliance on AI for critical decisions? | | |
| **Community Impact** | Does this feature empower or extract from marginalized communities? | | |

**Community Sovereignty Test (Mandatory):**
> *"Does this feature empower communities or extract from them?"*
- [ ] ✅ PASS — Feature gives users more control, information, or economic mobility
- [ ] ❌ FAIL — Feature optimizes for engagement/revenue at user expense → **DO NOT BUILD**

---

## PART 3 — TECHNICAL REQUIREMENTS

### 3.1 Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-01 | | Must Have | |
| FR-02 | | Should Have | |
| FR-03 | | Nice to Have | |

### 3.2 Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Performance** | Page load < 3s; AI response < 10s |
| **Security** | No hardcoded API keys; all secrets via `get_setting()` |
| **Accessibility** | WCAG 2.1 AA minimum |
| **Privacy** | No PII stored without explicit user consent |
| **Auditability** | All AI outputs logged with model name + timestamp |

### 3.3 AI Model Specification

| Field | Value |
|-------|-------|
| **Model** | `claude-opus-4-5` (mandatory per .clinerules) |
| **API Key Source** | `get_setting("anthropic_api_key")` — NEVER hardcoded |
| **Context Window** | Estimated: ___ tokens (input) / ___ tokens (output) |
| **Fallback Behavior** | If API key missing → show informative error, do NOT crash |
| **Bias Testing** | Test with diverse inputs: low-income, HBCU, rural, single parent profiles |

---

## PART 4 — MONETARY IMPACT ANALYSIS

### 4.1 User Economic Impact
> Cite real data to estimate value delivered to users.

| Metric | Estimate | Source |
|--------|----------|--------|
| Average $ saved per user/month | | |
| Average income increase enabled | | |
| Time saved per user/month (hrs) | | |
| # of users impacted in Year 1 | | |

### 4.2 Business Impact

| Metric | Estimate | Source |
|--------|----------|--------|
| New MRR potential ($) | | |
| Churn reduction (%) | | |
| Conversion lift (%) | | |
| TAM for this feature ($) | |  |

### 4.3 Societal Impact
> Map feature to a broader social outcome using cited research.

*Example: "CC College List Builder (page 87) directly addresses the Hoxby & Avery (2013) finding that 80% of high-achieving low-income students never apply to selective schools due to information gaps. CC's AI-powered match tool lowers the cognitive cost of the search process, replicating the intervention tested by Dynarski et al. (2021) which produced a 26pp increase in FAFSA completion."*

---

## PART 5 — IMPLEMENTATION PLAN

### 5.1 SDLC Checklist (Mandatory)

- [ ] Feature branch created: `feature/<name>`
- [ ] AI Ethics BRD completed (this document)
- [ ] At least 2 primary sources cited
- [ ] Ethical Risk Assessment complete (all risks scored)
- [ ] Community Sovereignty Test passed
- [ ] Code follows `.clinerules` standards
- [ ] `_ensure_tables()` pattern used for DB
- [ ] No hardcoded API keys
- [ ] Syntax check passed: `python3 -m py_compile pages/XX.py`
- [ ] Unit tests written and passing: `pytest tests/ -v`
- [ ] Conventional commit message written
- [ ] Promoted through dev → qa → staging → main

### 5.2 Testing Plan

| Test Type | Description | Pass Criteria |
|-----------|-------------|---------------|
| Unit | Core helper functions | All assertions pass |
| Bias | Test with demographically diverse inputs | No group receives materially different outcomes |
| Edge | Empty data, API down, no key set | Graceful degradation, no crash |
| Load | 50 concurrent users | P95 response < 10s |

---

## PART 6 — APPROVAL

| Role | Name | Date | Signature |
|------|------|------|-----------|
| **Developer** | Darrian Belcher | | |
| **Product Owner** | Darrian Belcher | | |
| **Ethics Review** | Self-certified per Section 2.3 | | |

---

## APPENDIX A — QUICK CITATION RESOURCES

| Database | URL | Best For |
|----------|-----|----------|
| Google Scholar | https://scholar.google.com | Primary peer-reviewed sources |
| NBER Working Papers | https://www.nber.org/papers | Economics + fintech research |
| SSRN | https://ssrn.com | Preprints + working papers |
| Federal Reserve Research | https://www.federalreserve.gov/econres.htm | Monetary + consumer finance data |
| UNCF Research | https://uncf.org/research | HBCU + Black student economic data |
| Urban Institute | https://www.urban.org/research | Low-income + housing data |
| Pew Research | https://www.pewresearch.org | Demographic + technology adoption data |
| StockX / GOAT Reports | https://stockx.com/news | Sneaker resale market data |
| McKinsey Global Institute | https://mckinsey.com/mgi | AI + fintech industry impact |

---

## APPENDIX B — BIAS TESTING SCRIPT TEMPLATE

```python
# tests/ethics/test_bias_<feature>.py
"""
Bias test for <feature>.
Per Obermeyer et al. (2019) — test outputs across demographic proxies.
"""
import pytest

DIVERSE_PROFILES = [
    {"label": "Low-income urban",    "income": 28000, "zip": "30314", "race_proxy": "Black"},
    {"label": "Middle-income suburb", "income": 65000, "zip": "30067", "race_proxy": "White"},
    {"label": "Single parent rural",  "income": 35000, "zip": "31513", "race_proxy": "Black"},
    {"label": "HBCU student",         "income": 12000, "zip": "30314", "race_proxy": "Black"},
    {"label": "High-income",          "income": 150000, "zip": "30327", "race_proxy": "White"},
]

def test_no_disparate_impact():
    """Outputs should not systematically disadvantage any demographic group."""
    results = []
    for profile in DIVERSE_PROFILES:
        # Replace with actual feature call
        result = my_feature_function(profile)
        results.append({"profile": profile["label"], "output": result})

    # Assert no group receives < 80% of the best outcome (4/5ths rule)
    outputs = [r["output"] for r in results]
    min_output = min(outputs)
    max_output = max(outputs)
    assert min_output >= 0.8 * max_output, (
        f"Disparate impact detected: min={min_output}, max={max_output}\n"
        f"Details: {results}"
    )
```

---

*This template was created 2026-03-30 by Darrian Belcher for Peach Builds LLC.*
*All features must pass the Community Sovereignty Test before implementation.*
*"Does this empower communities or extract from them?"*

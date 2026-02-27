# Software Delivery Lifecycle (SDLC) — Visa-Style Process

**Version:** 1.0  
**Last Updated:** 2026-02-27  
**Owner:** Darrian Belcher  
**Repository:** `bookofdarrian/darrian-budget`

---

## Overview

This repository follows a **Visa-style gated software delivery process** with strict quality controls at each stage. Every feature must pass through the entire lifecycle before reaching production:

```
Feature Branch → DEV → QA → STAGING → PRODUCTION
     ✓              ✓      ✓      ✓          ✓
   Create      Deploy   Test   Stability   Release
```

No feature or fix can skip stages or jump directly to production. This ensures reliability, stability, and performance at scale.

---

## Key Principles

1. **Gated Releases** — Each stage must pass automated and manual quality gates
2. **Shift Left** — Catch issues early (feature branch, not production)
3. **Automated Testing** — All tests run automatically; humans approve
4. **Progressive Deployment** — Small deployments to high-traffic environments last
5. **Rollback Ready** — Every deployment is tagged and can be reverted
6. **Full Traceability** — Every commit has a release tag and deployment record

---

## Branch Strategy

### Main Branches (Protected)

| Branch | Purpose | Deployment | Approval | Auto-Deploy |
|--------|---------|-----------|----------|-------------|
| `main` | **PRODUCTION** | Railway (peachstatesavings.com) | Manual (you) | After manual trigger |
| `staging` | **STAGING** | Separate environment or secondary instance | Auto (if tests pass) | Yes |
| `qa` | **QA** | Dedicated QA test environment | Auto (if tests pass) | Yes |
| `dev` | **DEV** | Home lab (CT100 @ 100.95.125.112) | Auto (if tests pass) | Yes |

### Feature Branches

| Pattern | Purpose | When to Create |
|---------|---------|---|
| `feature/*` | New feature development | When starting work on a new feature |
| `bugfix/*` | Bug fixes | When fixing an issue in production |
| `hotfix/*` | Critical production fixes | When production is broken |
| `chore/*` | Maintenance tasks | Refactoring, deps, docs |

---

## Development Workflow

### Step 1: Create a Feature Branch

```bash
git checkout -b feature/my-new-feature
# or for bug fixes:
git checkout -b bugfix/fix-login-issue
```

**Branch naming rules:**
- Use kebab-case: `feature/user-dashboard`, `bugfix/null-pointer-error`
- Start with type: `feature/`, `bugfix/`, `hotfix/`, `chore/`
- Make it descriptive: `feature/ai-insights-v2`, not `feature/test123`

### Step 2: Commit and Push Early & Often

```bash
git add .
git commit -m "feat: add new budget page with AI insights

- Integrated Claude API for financial analysis
- Added AURA compression to save 60% on tokens
- Updated sidebar navigation"

git push origin feature/my-new-feature
```

**Commit message format** (Conventional Commits):
```
<type>: <subject>

<body>

<footer>
```

Types: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`, `perf:`

### Step 3: Automated Quality Gates Run (Feature Branch)

When you push to a feature branch, GitHub Actions automatically:

✅ **Linting** (Black, isort, Pylint, Flake8)
- Checks code formatting
- Enforces style consistency
- Reports issues but doesn't block (continues-on-error)

✅ **Unit Tests** (pytest)
- Run all tests in `tests/unit/`
- Check code coverage (aim for >80%)
- Report results to Codecov

✅ **Docker Build**
- Builds the Dockerfile
- Checks for Docker build errors

**Status:** Feature branch is green when linting + tests pass.

### Step 4: Code Review & Merge to DEV

When your feature is ready:

1. **Open a Pull Request (PR)** `feature/my-feature` → `dev`
   ```bash
   gh pr create --base dev --title "feat: my new feature" --body "Fixes #123"
   ```

2. **You review your own code** for clarity and security
   - Does it follow style guidelines?
   - Are there any obvious bugs?
   - Did you add tests?

3. **Merge to DEV** (you have write access)
   ```bash
   # On GitHub or locally:
   git checkout dev
   git pull origin dev
   git merge feature/my-feature
   git push origin dev
   ```

**On merge to DEV:**
- ✅ Linting + tests run again (must pass)
- ✅ Docker image is built and pushed to GHCR
- ✅ **Auto-deploys to home lab** (CT100 @ 100.95.125.112:8501)
- 📧 Logs show: "Deployed to DEV"

---

## Stage 2: DEV Environment (Home Lab)

**Purpose:** Developers test new features with real data

**Access:** http://100.95.125.112:8501 (via Tailscale)

**When features are deployed here:**
- All features from merged PRs live here
- Dev data is real (or anonymized production data)
- Used for feature testing before QA

**Promotion to QA:** When you're confident dev is stable:
```bash
git checkout qa
git pull origin qa
git merge dev
git push origin qa
```

**On merge to QA:**
- ✅ Full test suite runs (unit + integration + regression)
- ✅ Docker image is built
- ✅ **Auto-deploys to QA environment**
- 📊 Test coverage and results logged

---

## Stage 3: QA Environment (Separate Test Instance)

**Purpose:** Quality assurance testing — no regressions, no weird edge cases

**When features arrive:**
- Manual QA testing in QA environment (separate container/VM)
- Check for visual regressions, broken flows, data integrity
- Verify with real-world scenarios and edge cases

**Test Suite Includes:**
- Unit tests (pytest)
- Integration tests (cross-module flows)
- Regression tests (features from previous releases still work)

**Promotion to STAGING:** When QA passes:
```bash
git checkout staging
git pull origin staging
git merge qa
git push origin staging
```

**On merge to STAGING:**
- ✅ **Performance tests** run (load testing, memory profiling, benchmarks)
- ✅ Docker image is built for staging
- ✅ **Auto-deploys to staging environment**
- 📊 Performance metrics collected

---

## Stage 4: STAGING Environment (Production Mirror)

**Purpose:** Final stability and performance checks before production

**What happens here:**
- ✅ Full performance test suite runs
- ✅ Load testing (Locust) simulates multiple users
- ✅ Memory profiling checks for leaks
- ✅ Deployed identically to production (same container, same config)

**Goals:**
- Verify app doesn't slow down under load
- Catch memory leaks or resource issues
- Test with production-like data volume
- Verify auto-restart works correctly

**Manual Checks You Do:**
1. Open the staging app at http://100.95.125.112:8501 (or your staging URL)
2. Walk through critical user flows:
   - Login, create expense, view reports, export data
3. Check response times (should match expected)
4. Monitor CPU/RAM in Grafana (http://100.95.125.112:3000)
5. Look for any error logs in container

**Promotion to PRODUCTION:** When you're confident:
```bash
git checkout main
git pull origin main
git merge staging
git push origin main
```

⚠️ **This triggers a manual approval gate in GitHub Actions**

---

## Stage 5: PRODUCTION (Railway)

**Purpose:** Live application serving real users

**Website:** https://www.peachstatesavings.com

**Deployment Process:**

1. **Merge to main:**
   ```bash
   git checkout main
   git merge staging
   git push origin main
   ```

2. **GitHub Actions triggers production workflow**
   - Pre-flight checks run (is this really from main? Is commit signed?)
   - Docker image built and pushed
   - **Waits for you to approve in GitHub Actions UI**

3. **Manual Approval Step:**
   - Go to: https://github.com/bookofdarrian/darrian-budget/actions
   - Click the workflow run for your commit
   - Click **Approve and Deploy** (or **Skip** if there's an issue)
   - ⚠️ Only you can approve

4. **Deployment happens:**
   - Railway pulls the new image
   - App restarts with new code
   - Release tag created: `v2026.02.27-143015`
   - Release notes posted to GitHub releases

5. **Verification:**
   - App should be live in ~30-60 seconds
   - Visit https://www.peachstatesavings.com
   - Check Grafana dashboards for any errors
   - Monitor logs for 30 minutes

**Rollback if needed:**
```bash
# Revert to previous version
git revert HEAD
git push origin main
# This triggers another deployment with the old code
```

---

## Quality Gates at Each Stage

### Feature Branch → DEV
- ✅ Code formatting (Black, isort)
- ✅ Lint checks (Pylint, Flake8)
- ✅ Unit tests pass
- ✅ Docker builds successfully
- ✅ Manual code review (you)

### DEV → QA
- ✅ All feature branch gates pass
- ✅ Integration tests pass
- ✅ Regression tests pass
- ✅ No breaking changes to database

### QA → STAGING
- ✅ All QA gates pass
- ✅ Load testing (Locust): 100 users, 10/sec
- ✅ Memory profiling: no leaks
- ✅ Response times acceptable
- ✅ Deployed to staging environment

### STAGING → PRODUCTION
- ✅ All staging gates pass
- ✅ Pre-flight checks on main branch
- ✅ Docker image tested
- ✅ **Manual approval from you**
- ✅ Release tag created

---

## GitHub Actions Workflows

All workflows are in `.github/workflows/`:

| Workflow | Triggers | Purpose |
|----------|----------|---------|
| `lint-and-test.yml` | Push to any branch | Linting, unit tests, Docker build |
| `deploy-dev.yml` | Push to `dev` | Deploy to home lab |
| `deploy-qa.yml` | Push to `qa` | Deploy to QA environment |
| `deploy-staging.yml` | Push to `staging` | Performance tests, deploy to staging |
| `deploy-prod.yml` | Push to `main` | Requires manual approval, deploy to Railway |

**Check workflow status:**
```bash
# List recent workflows
gh run list --repo bookofdarrian/darrian-budget

# Watch a specific run
gh run watch <RUN_ID>

# View logs
gh run view <RUN_ID> --log
```

---

## Secrets & Environment Variables

Store sensitive data in GitHub Secrets (not in code):

**Required Secrets:**
```
RAILWAY_TOKEN           # Railroad deploy token
DEV_SSH_KEY            # SSH key for home lab (100.95.125.112)
QA_HOST                # QA environment hostname/IP
QA_SSH_KEY             # SSH key for QA environment
STAGING_HOST           # Staging environment hostname/IP
STAGING_SSH_KEY        # SSH key for staging environment
GITHUB_TOKEN           # (auto-created by GitHub)
```

**To add a secret:**
```bash
# Via GitHub CLI
gh secret set RAILWAY_TOKEN --body "your-token-here"

# Or on the web: github.com/bookofdarrian/darrian-budget → Settings → Secrets
```

---

## Branch Protection Rules

All main branches have protection enabled:

### `main` (Production)
- ✅ Requires branches to be up to date before merging
- ✅ Requires status checks to pass (linting, tests, build)
- ✅ Requires manual approval (1 person = you)
- ✅ Auto-delete head branches on merge
- ✅ Commits must be signed

### `staging`, `qa`, `dev`
- ✅ Requires status checks to pass
- ✅ Auto-delete head branches
- ✅ Allow auto-merge with squash

---

## Common Workflows

### Adding a New Feature

```bash
# 1. Create feature branch
git checkout -b feature/new-dashboard

# 2. Make changes and test locally
python aura/server.py
streamlit run app.py

# 3. Commit with descriptive messages
git add .
git commit -m "feat: add investment dashboard

- Displays portfolio allocation
- Shows YTD returns
- Integrated with Stripe data"

# 4. Push and create PR
git push origin feature/new-dashboard
gh pr create --base dev

# 5. When satisfied, merge to dev
git checkout dev
git pull origin dev
git merge feature/new-dashboard
git push origin dev

# 6. Wait for deploy to DEV, test
# → Visit http://100.95.125.112:8501

# 7. When ready, promote to QA
git checkout qa && git merge dev && git push origin qa

# 8. After QA testing, promote to staging
git checkout staging && git merge qa && git push origin staging

# 9. After staging testing, promote to prod
git checkout main && git merge staging && git push origin main

# 10. Approve in GitHub Actions
# → https://github.com/bookofdarrian/darrian-budget/actions
```

### Hotfix for Production Bug

```bash
# 1. Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug-fix

# 2. Make minimal fix
git commit -m "fix: critical bug affecting login"

# 3. Push and merge immediately to main (after quick test)
git push origin hotfix/critical-bug-fix
git checkout main
git merge hotfix/critical-bug-fix
git push origin main

# ⚠️ This skips DEV/QA/STAGING but is acceptable for critical production issues
# 4. Approve in GitHub Actions right away
```

### Reverting a Bad Deployment

```bash
# If production is broken:
git log --oneline
# Find the bad commit, e.g., abc123def

git revert abc123def
git push origin main

# This creates a new commit that undoes abc123def
# Approve the new deployment in GitHub Actions
# Production will revert to the previous working state
```

---

## Monitoring & Observability

### Grafana Dashboards
- **URL:** http://100.95.125.112:3000
- **Metrics:** CPU, RAM, disk usage, request latency, error rates

### GitHub Actions
- **URL:** https://github.com/bookofdarrian/darrian-budget/actions
- **View:** All workflow runs, logs, deployment status

### Railway Dashboard
- **URL:** https://railway.app
- **Project:** darrian-budget
- **View:** Production logs, metrics, environment variables

### Database Logs
```bash
# Check dev environment logs
ssh root@100.95.125.112
docker logs budget-app
docker logs aura-compression-server
```

---

## Troubleshooting

### Test Failures Blocking Promotion

**If linting/tests fail on a branch:**
1. View the failed workflow: https://github.com/bookofdarrian/darrian-budget/actions
2. Click the failed job for error details
3. Fix locally:
   ```bash
   black .          # Auto-fix formatting
   isort .          # Auto-fix imports
   pytest tests/    # Re-run tests
   ```
4. Commit and push
5. Workflow re-runs automatically

### Deployment to Environment Fails

Check the GitHub Actions logs for the specific error. Common issues:
- SSH key expired or wrong (check GitHub Secrets)
- Git pull failures (network issue or permission)
- Docker compose syntax error
- Port already in use on target environment

### Can't Merge Because Branch Is Behind

```bash
# Your branch is behind main/dev/qa. Catch up:
git fetch origin
git rebase origin/dev       # or origin/qa, origin/staging
git push -f origin feature/my-branch
```

---

## Release Planning

### Monthly Releases
Every **first Monday of the month**, promote from staging to production.

**Calendar:**
- **Week 1:** Feature development (feature branches)
- **Week 2:** Merge features to dev, QA testing
- **Week 3:** Final testing in staging, performance tuning
- **Week 4:** Manual approval and deployment to production

### Release Versioning
Versions follow: `v<YYYY>.<MM>.<DD>-<HHMM>`
- Example: `v2026.02.27-143015` (February 27, 2026 at 14:30:15)

Automatically created by deploy-prod workflow.

### Release Notes
Available at: https://github.com/bookofdarrian/darrian-budget/releases

Include:
- Features added
- Bugs fixed
- Performance improvements
- Known issues

---

## Training & Onboarding

### For Contributors
1. Read this file
2. Clone the repo: `git clone https://github.com/bookofdarrian/darrian-budget`
3. Create a feature branch: `git checkout -b feature/my-first-pr`
4. Make a small change (e.g., update a comment)
5. Push and create a PR to dev
6. Watch the GitHub Actions workflow run
7. Merge to dev and watch it auto-deploy

### For Approvers
1. Review GitHub Actions results before approving
2. Manual testing checklist for staging promotion
3. Keep monitoring dashboards open during deployments
4. Have rollback plan ready (git revert)

---

## Conclusion

This SDLC process follows **Visa's battle-tested model**:
- Clear stages with specific purposes
- Automated checks at every step
- Manual approval at critical gates
- Full traceability and rollback capability
- Progressive risk reduction (test in dev, then QA, then staging, then prod)

**Key Mantra:** "Every feature earns its right to production through testing, not shortcuts."

Questions? Refer to this doc or check GitHub Actions logs for error details.

---

**Version History:**
- v1.0 — 2026-02-27 — Initial Visa-style SDLC process

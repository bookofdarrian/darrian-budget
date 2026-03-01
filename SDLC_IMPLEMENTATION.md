# ✅ Visa-Style SDLC Pipeline — Implementation Complete

**Date Implemented:** February 27, 2026  
**Repository:** https://github.com/bookofdarrian/darrian-budget  
**Feature Branch:** `feature/visa-sdlc-pipeline` (Ready to merge to dev)

---

## What Was Just Implemented

Your repository now has a complete **Fortune 500-style software delivery pipeline** following Visa's gated release process:

```
┌─────────────┐    ┌─────┐    ┌────┐    ┌─────────┐    ┌──────────┐
│   Feature   │───▶│ DEV │───▶│ QA │───▶│ STAGING │───▶│   PROD   │
│  Branches   │    │     │    │    │    │         │    │(Self-Host)│
└─────────────┘    └─────┘    └────┘    └─────────┘    └──────────┘
   (your Mac)    (Home Lab)   (Test)   (Performance)   (Live Users)
   ✓ Lint      ✓ Deploy    ✓ Tests  ✓ Load Test    ✓ Manual Auth
   ✓ Tests     ✓ Auto-run  ✓ Reg.    ✓ Stability   ✓ Release
   ✓ Build                         ✓ Memory Check  ✓ Tag & Notes
```

---

## Files Created

### GitHub Actions Workflows (`.github/workflows/`)
| File | Purpose |
|------|---------|
| `lint-and-test.yml` | Linting, unit tests, Docker build (all branches) |
| `deploy-dev.yml` | Deploy to home lab (100.95.125.112) on push to `dev` |
| `deploy-qa.yml` | Deploy to QA environment on push to `qa` |
| `deploy-staging.yml` | Performance tests + deploy to staging on push to `staging` |
| `deploy-prod.yml` | Manual approval + SSH deploy to home lab on push to `main` |

### Quality Gate Configurations
| File | Purpose |
|------|---------|
| `pytest.ini` | Test configuration (markers, coverage thresholds) |
| `pyproject.toml` | Black, isort, Pylint, coverage, mypy settings |
| `.pylintrc` | Detailed linting rules |
| `.pre-commit-config.yaml` | Local pre-commit hooks (Black, isort, Pylint, Bandit) |
| `.bandit` | Security scanning configuration |
| `requirements-dev.txt` | Dev dependencies (testing, linting, profiling tools) |

### Documentation
| File | Purpose |
|------|---------|
| `SDLC_PROCESS.md` | **Full SDLC process guide** — read this first! |
| `SDLC_GETTING_STARTED.md` | **Developer how-to** — setup + first commit |
| `BRANCH_PROTECTION_SETUP.md` | Instructions to configure GitHub branch protection |

### Test Structure
```
tests/
  ├── __init__.py
  ├── unit/
  │   ├── __init__.py
  │   └── test_budget_app.py      (sample unit tests)
  └── qa/
      ├── __init__.py
      └── test_regression.py       (sample QA tests)
```

---

## Quick Start: Your First SDLC Commit

### Step 1: Create Feature Branch (Done!)
```bash
git checkout -b feature/my-new-feature
```
Your branch exists now: `feature/visa-sdlc-pipeline`

### Step 2: Make Changes
```bash
# Edit your code
nano pages/my_new_page.py

# Run tests locally
pytest tests/unit/ -v

# Format code
black .
isort .
```

### Step 3: Commit & Push
```bash
git add .
git commit -m "feat: add my new feature"
git push origin feature/visa-sdlc-pipeline
```

GitHub Actions automatically runs:
- ✅ Black formatter check
- ✅ isort import check
- ✅ Pylint code quality
- ✅ Flake8 style check
- ✅ pytest unit tests
- ✅ Docker build test

**Status:** View workflow results at:  
https://github.com/bookofdarrian/darrian-budget/actions

### Step 4: Merge to DEV
```bash
# Locally:
git checkout dev
git pull origin dev
git merge feature/my-new-feature
git push origin dev

# OR on GitHub: Click "Merge pull request"
```

**What happens automatically:**
1. Tests run again ✅
2. Docker image built and pushed to GHCR
3. **Container deployed to home lab** (CT100 @ 100.95.125.112:8501)
4. You can test it immediately

### Step 5: Promote Through Pipeline
```bash
# When ready for QA:
git checkout qa && git merge dev && git push origin qa

# When ready for staging (after QA testing):
git checkout staging && git merge qa && git push origin staging

# When ready for production (after staging testing):
git checkout main && git merge staging && git push origin main

# Manual approval required! 🔐
# → GitHub Actions asks you to confirm
# → You click "Approve and Deploy"
# → Deploys to home lab: peachstatesavings.com
```

---

## Environment Variables Needed

Add these GitHub Secrets before deployments can work:

```bash
# SSH keys (base64 encoded or as PEM)
DEV_SSH_KEY              # For home lab (100.95.125.112)
QA_SSH_KEY               # For QA environment
STAGING_SSH_KEY          # For staging environment

# Environment details
QA_HOST                  # IP or hostname of QA environment
STAGING_HOST             # IP or hostname of staging environment

# Deployment (via Tailscale SSH)
TAILSCALE_AUTHKEY        # Tailscale auth key for GitHub Actions tunnel
PROD_SSH_KEY             # SSH key for production home lab
GITHUB_TOKEN             # (auto-created by GitHub)
```

**How to add secrets:**
```bash
# Via GitHub CLI:
gh secret set TAILSCALE_AUTHKEY --body "tskey-auth-..."
gh secret set PROD_SSH_KEY < ~/.ssh/id_ed25519

# Or on web:
# Settings → Secrets and variables → Actions → New repository secret
```

---

## Branch Protection Rules

You need to configure GitHub branch protection for each stage. See [BRANCH_PROTECTION_SETUP.md](BRANCH_PROTECTION_SETUP.md) for step-by-step instructions.

**Quick summary:**
- `main` — Requires PR, approval, all tests passing
- `staging` — Requires tests passing, auto-merges enabled
- `qa` — Requires tests passing, auto-merges enabled
- `dev` — Requires PR (1 approval = you), tests passing

---

## Next Steps (In Order)

### 1️⃣ **Merge Feature Branch to DEV** (5 min)
```bash
git checkout dev
git merge feature/visa-sdlc-pipeline
git push origin dev
```
Watch the deployment happen: https://github.com/bookofdarrian/darrian-budget/actions

### 2️⃣ **Configure Branch Protection** (10 min)
Follow [BRANCH_PROTECTION_SETUP.md](BRANCH_PROTECTION_SETUP.md)
- Protects `main`, `staging`, `qa`, `dev`
- Prevents accidental direct pushes
- Requires tests to pass

### 3️⃣ **Add GitHub Secrets** (5 min)
```bash
# Add Tailscale auth key (from https://login.tailscale.com/admin/settings/keys)
gh secret set TAILSCALE_AUTHKEY --body "tskey-auth-..."

# Add SSH keys for each environment
gh secret set PROD_SSH_KEY < ~/.ssh/id_ed25519
gh secret set DEV_SSH_KEY --body "$(cat ~/.ssh/id_ed25519)"
gh secret set QA_SSH_KEY --body "..."
gh secret set STAGING_SSH_KEY --body "..."
```

### 4️⃣ **Test the Pipeline** (30 min)
```bash
# Create a test feature branch
git checkout -b feature/test-sdlc

# Make small change
echo "# Test commit" >> README.md

# Push and watch GitHub Actions
git add .
git commit -m "test: verify SDLC pipeline works"
git push origin feature/test-sdlc

# View workflow: https://github.com/bookofdarrial-budget/actions
# Merge to dev when all checks pass
```

### 5️⃣ **Read the Docs** (20 min)
- [SDLC_PROCESS.md](SDLC_PROCESS.md) — Full process explanation
- [SDLC_GETTING_STARTED.md](SDLC_GETTING_STARTED.md) — Developer guide
- [BRANCH_PROTECTION_SETUP.md](BRANCH_PROTECTION_SETUP.md) — GitHub setup

### 6️⃣ **Install Pre-Commit Hooks** (5 min)
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```
Now code quality checks run automatically before every `git commit`

### 7️⃣ **Set Monthly Release Cycle** (Optional)
Define your release schedule:
- 1st Monday: merge features to dev
- 2nd week: QA testing
- 3rd week: staging performance testing
- 4th week: production deployment

---

## How the Pipeline Works

### Automatic (No Human Intervention)
- ✅ Tests run on every push
- ✅ Docker image built automatically
- ✅ Auto-deploys to DEV, QA, STAGING on merge
- ✅ Performance metrics collected

### Manual Approvals (You Decide)
- 🔐 Approve feature branch → dev (1 approval needed)
- 🔐 Approve production deployment (only you can do this)
- 🔐 Can revoke deployments with `git revert`

### Access Points
| Environment | URL | Auto Deploy | Who Approves |
|-------------|-----|------------|--------------|
| DEV (Home Lab) | http://100.95.125.112:8501 | Yes | (automatic) |
| QA | http://qa-host:8501 | Yes | (automatic) |
| STAGING | http://staging-host:8501 | Yes | (automatic) |
| **PROD (Self-Hosted)** | **https://peachstatesavings.com** | **After Approval** | **You only** |

---

## Monitoring & Debugging

### Check Deployment Status
```bash
# Via GitHub CLI
gh run list                          # See all workflow runs
gh run view <RUN_ID> --log          # See logs for a run

# Or on web
# → https://github.com/bookofdarrian/darrian-budget/actions
```

### View Application Logs
```bash
# Home Lab (dev)
ssh root@100.95.125.112
docker logs budget-app
docker logs -f aura-compression-server  # Follow logs

# Staging/QA
ssh root@[staging-host]
docker-compose logs -f
```

### Check Grafana Metrics
```
http://100.95.125.112:3000
- CPU, RAM, disk usage
- Container health
- Request latency
- Error rates
```

---

## Rollback Procedure

If production breaks:

```bash
# Identify the bad commit
git log --oneline | head -5

# Revert it (creates a new commit that undoes it)
git revert <BAD_COMMIT_SHA>

# Push to main
git push origin main

# Approve the automatic deployment
# → https://github.com/bookofdarrian/darrian-budget/actions
```

The old code will be live in ~30 seconds.

---

## Common Git Commands

```bash
# Create & work on feature branch
git checkout -b feature/my-feature
git add .
git commit -m "feat: description"
git push origin feature/my-feature

# Promote to next stage
git checkout qa
git pull origin qa
git merge dev              # Merge in dev's changes
git push origin qa

# See workflow status
gh run list --limit 10

# Check if branch is up to date
git fetch origin
git status

# Discard uncommitted changes
git checkout -- .

# View recent commits
git log --oneline -10

# See branch protection info
gh repo view --json branchProtectionRules
```

---

## Troubleshooting

### GitHub Actions Workflow Failed

1. Go to: https://github.com/bookofdarrian/darrian-budget/actions
2. Click the failed workflow run
3. Expand the failed job
4. Scroll to see the error
5. Common issues:
   - **Syntax error in code** → Fix locally, recommit
   - **Test failed** → pytest output shows which test failed
   - **Docker build error** → Check Dockerfile syntax or dependencies
   - **SSH key missing** → Add to GitHub Secrets

### Can't Push to Branch

```bash
# Branch protection blocking you
# This is intentional! Use a feature branch instead

git checkout -b feature/my-fix
git push origin feature/my-fix
# Create PR, merge when tests pass
```

### Tests Failing Locally But Passing in GitHub

```bash
# Different Python environment?
python --version
pip freeze | grep pytest

# Install exact deps
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests exactly as GitHub does
pytest tests/ -v --cov=.
```

---

## Important Files Reference

| File | What |
|------|------|
| **SDLC_PROCESS.md** | Master reference for entire process |
| **SDLC_GETTING_STARTED.md** | How to make your first commit |
| **BRANCH_PROTECTION_SETUP.md** | How to configure GitHub |
| **.github/workflows/** | Automated deployment logic |
| **pytest.ini** | Test configuration |
| **pyproject.toml** | Linting and tool configs |
| **requirements-dev.txt** | Install with: `pip install -r requirements-dev.txt` |

---

## Questions?

1. **How do I get my feature to production?**  
   → See SDLC_PROCESS.md section "Development Workflow"

2. **What if I break production?**  
   → See "Rollback Procedure" above

3. **How do I set up pre-commit hooks?**  
   → See SDLC_GETTING_STARTED.md Step 2

4. **What GitHub secrets do I need?**  
   → See "Environment Variables Needed" section above

5. **How do I monitor deployments?**  
   → See "Monitoring & Debugging" section above

---

## Summary

✅ **Your repository now has:**
- 5 GitHub Actions workflows (automated testing & deployment)
- Complete quality gate configuration (linting, testing, security scanning)
- Branch protection rules (to be configured)
- Test structure (pytest, coverage, regression tests)
- Comprehensive documentation (3 guides + inline code comments)
- Pre-commit hooks (local code quality checks)

✅ **Your SDLC pipeline is:**
- feature → dev (auto deploy to home lab)
- dev → qa (auto deploy to QA test environment)
- qa → staging (auto deploy + performance testing)
- staging → prod (manual approval required, SSH deploy to self-hosted home lab)

✅ **You can now:**
- Create features on branches
- Automatically test them
- Progressively deploy to each environment
- Get full traceability of every release
- Rollback if needed

🚀 **Ready to use!** Start with Step 1 above: Merge the feature branch to dev.

---

**Feature Branch Created:** `feature/visa-sdlc-pipeline`  
**Commit Hash:** 7ae07f2  
**Status:** Ready to promote to DEV  
**Next Action:** Merge to `dev` branch and watch deployment happen

```bash
git checkout dev
git merge feature/visa-sdlc-pipeline
git push origin dev
```

Welcome to enterprise-grade software delivery! 🎉

# Getting Started with the SDLC Pipeline

This guide helps you set up your local development environment to work with the Visa-style SDLC process.

## Prerequisites

- Python 3.11+
- Git
- GitHub CLI (optional but recommended): `brew install gh`

## Step 1: Local Setup

### Clone the Repository

```bash
git clone https://github.com/bookofdarrian/darrian-budget.git
cd darrian-budget
```

### Create a Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Install Developer Tools

```bash
# Install linting and testing tools
pip install black pylint isort flake8 pytest pytest-cov pytest-asyncio

# Install pre-commit hooks
pip install pre-commit
```

## Step 2: Set Up Pre-Commit Hooks

Pre-commit hooks run quality checks on every commit locally. This catches issues before they reach GitHub.

```bash
# Install the pre-commit hook
pre-commit install

# Optional: Run hooks on all files (first time)
pre-commit run --all-files
```

Now, every time you run `git commit`:
1. Black formats your code
2. isort organizes imports
3. Flake8 checks for style issues
4. Pylint checks code quality
5. Bandit checks for security issues

If any check fails, your commit is blocked. Fix the issues and try again:
```bash
git add .
git commit -m "your message"  # Hooks run again
```

## Step 3: Create Your Feature Branch

```bash
# Always branch from dev for features
git checkout dev
git pull origin dev
git checkout -b feature/my-new-feature

# Or for bugs:
git checkout -b bugfix/fix-login-issue
```

## Step 4: Develop & Test Locally

### Run the App Locally

```bash
# Terminal 1: AURA compression server (optional)
python aura/server.py

# Terminal 2: Budget app
streamlit run app.py
# Opens at http://localhost:8501
```

### Run Tests Before Committing

```bash
# Run all tests
pytest tests/ -v

# Run only unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
# Open htmlcov/index.html to view coverage

# Run specific test
pytest tests/unit/test_budget_app.py::TestBudgetApp::test_app_imports -v
```

### Format Code (Optional - Pre-Commit Does This)

```bash
# Format all Python files
black .

# Organize imports
isort .

# Check code quality
pylint pages/ utils/ aura/ *.py
```

## Step 5: Commit & Push

```bash
# Make changes
nano pages/my_new_page.py

# Stage changes
git add .

# Commit (pre-commit hooks run here)
git commit -m "feat: add new dashboard page

- Shows portfolio summary
- Displays YTD performance
- Integrated with investment data"

# Push to GitHub
git push origin feature/my-new-feature
```

## Step 6: Create a Pull Request

```bash
# Create PR automatically (requires GitHub CLI)
gh pr create --base dev --title "feat: add new dashboard" --body "Closes #123"

# Or create on web: https://github.com/bookofdarrian/darrian-budget/pulls
```

## Step 7: Review GitHub Actions Workflow

Go to: https://github.com/bookofdarrian/darrian-budget/actions

Watch the workflow:
- ✅ Linting checks
- ✅ Tests running
- ✅ Docker build

Wait for all checks to pass (green checkmarks).

## Step 8: Merge to DEV

Once GitHub Actions passes:

```bash
# Option 1: Merge locally and push
git checkout dev
git pull origin dev
git merge feature/my-new-feature
git push origin dev

# Option 2: Merge on GitHub (click "Merge Pull Request" button)
```

**GitHub Actions will now:**
- Build and push Docker image to GHCR
- **Auto-deploy to home lab** (100.95.125.112:8501)
- Show deployment logs

## Step 9: Test in DEV

Open the dev app: http://100.95.125.112:8501 (via Tailscale)

- Walk through your new feature
- Check for any issues or unexpected behavior
- Try edge cases

## Step 10: Promote to QA & Beyond

```bash
# When ready to promote to QA:
git checkout qa
git pull origin qa
git merge dev
git push origin qa

# Similarly for staging:
git checkout staging
git pull origin staging
git merge qa
git push origin staging

# And finally production (requires manual approval):
git checkout main
git pull origin main
git merge staging
git push origin main
# Then approve in GitHub Actions
```

---

## Common Commands

### View Your Branches

```bash
git branch -a
# Shows: dev, qa, staging, main, and your local branches
```

### Update Your Local Branch

```bash
git fetch origin
git rebase origin/dev
# or
git merge origin/dev
```

### Undo Last Commit

```bash
git reset --soft HEAD~1
# Changes are unstaged, commit again with corrected message
```

### View Commit History

```bash
git log --oneline --graph
```

### Discard Uncommitted Changes

```bash
git checkout -- .
```

### See What Changed

```bash
git diff                    # Unstaged changes
git diff --staged           # Staged changes
git diff main..feature/my   # Changes vs main
```

---

## Troubleshooting

### Pre-Commit Hook Failures

**Black formatting issues:**
```bash
black .
git add .
git commit -m "..."  # Try again
```

**Pylint complaining:**
Check the message, fix manually, or disable for a line:
```python
my_questionable_code()  # pylint: disable=some-rule
```

### GitHub Actions Failing

Click the failed job in GitHub Actions to see the error:
```
https://github.com/bookofdarrian/darrian-budget/actions
→ Click the workflow run
→ Click the failed job (red X)
→ Scroll to see the error message
```

### Can't Push to Branch

```bash
# Branch protection: you need more approvals or status checks
# Check: https://github.com/bookofdarrian/darrian-budget/settings/branches

# Force push (use carefully!):
git push -f origin feature/my-feature
```

### Merge Conflicts

```bash
# Pull latest dev
git fetch origin
git rebase origin/dev

# Resolve conflicts in your editor
# Files marked with <<<<<<, ======, >>>>>> need manual fixes

# After resolving:
git add .
git rebase --continue
```

---

## Resources

- **Full SDLC Process:** [SDLC_PROCESS.md](SDLC_PROCESS.md)
- **GitHub Actions Docs:** https://docs.github.com/en/actions
- **Conventional Commits:** https://www.conventionalcommits.org/
- **Pre-Commit Framework:** https://pre-commit.com/
- **Pytest Docs:** https://pytest.org/

---

## Next Steps

1. ✅ Set up local environment (Steps 1-2)
2. ✅ Create your first feature branch (Step 3)
3. ✅ Make a small change and push
4. ✅ Watch GitHub Actions run
5. ✅ Merge to dev
6. ✅ See auto-deployment happen
7. ✅ You're now using the Visa-style SDLC!

Welcome to the team! 🚀

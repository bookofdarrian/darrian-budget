# GitHub Branch Protection Rules Setup

This document describes the branch protection settings that should be configured for the Visa-style SDLC pipeline.

## How to Configure Branch Protection

1. Go to: https://github.com/bookofdarrian/darrian-budget/settings/branches
2. Click "Add rule" for each branch below
3. Enter the branch name (or pattern)
4. Configure settings as specified

---

## Branch: `main` (Production)

This is the most restricted branch.

### Settings

| Setting | Value |
|---------|-------|
| **Branch name pattern** | `main` |
| **Require a pull request before merging** | ✅ Yes |
| Number of approvals | 1 |
| Require approval from code owners | ☐ No (you're the only owner) |
| Require status checks to pass before merging** | ✅ Yes |
| Require branches to be up to date before merging | ✅ Yes |
| Require code scanning results to pass** | ☐ Optional |
| Require commits to be signed** | ⚠️ Optional |
| Dismiss stale pull request approvals when new commits are pushed | ☐ No |
| Require status checks to pass before merging** | ✅ Yes |
| Status checks that must pass | See below |
| Require conversation resolution before merging** | ☐ No |
| Require deployments to succeed before merging** | ☐ No |
| Lock branch | ☐ No |
| Allow force pushes** | ☐ No |
| Allow deletions | ☐ No |

### Status Checks Required for `main`

Select all of these status checks:
- `lint-and-test / lint` (from lint-and-test.yml)
- `lint-and-test / test` (from lint-and-test.yml)
- `deploy-prod / pre-prod-checks` (from deploy-prod.yml)

---

## Branch: `staging`

This branch requires tests but auto-deploys on merge.

### Settings

| Setting | Value |
|---------|-------|
| **Branch name pattern** | `staging` |
| **Require a pull request before merging** | ☐ No (merge directly) |
| **Require status checks to pass before merging** | ✅ Yes |
| **Status checks required** | See below |
| Require branches to be up to date before merging | ✅ Yes |
| Allow auto-merge | ✅ Yes (with squash) |
| Allow force pushes | ☐ No |
| Allow deletions | ☐ No |

### Status Checks Required for `staging`

- `lint-and-test / lint`
- `lint-and-test / test`
- `deploy-staging / performance-tests`

---

## Branch: `qa`

This branch requires tests and auto-deploys to QA environment.

### Settings

| Setting | Value |
|---------|-------|
| **Branch name pattern** | `qa` |
| **Require a pull request before merging** | ☐ No (merge directly) |
| **Require status checks to pass before merging** | ✅ Yes |
| **Status checks required** | See below |
| Require branches to be up to date before merging | ✅ Yes |
| Allow auto-merge | ✅ Yes (with squash) |
| Allow force pushes | ☐ No |
| Allow deletions | ☐ No |

### Status Checks Required for `qa`

- `lint-and-test / lint`
- `lint-and-test / test`
- `deploy-qa / qa-tests`

---

## Branch: `dev`

This is the main development branch. Auto-deploys on merge.

### Settings

| Setting | Value |
|---------|-------|
| **Branch name pattern** | `dev` |
| **Require a pull request before merging** | ✅ Yes |
| Number of approvals | 1 (you) |
| **Require status checks to pass before merging** | ✅ Yes |
| **Status checks required** | See below |
| Require branches to be up to date before merging | ✅ Yes |
| Require conversation resolution before merging | ☐ No |
| Dismiss stale pull request approvals when new commits are pushed | ✅ Yes |
| Allow auto-merge | ✅ Yes (with squash) |
| Allow force pushes | ☐ No |
| Allow deletions | ☐ No |

### Status Checks Required for `dev`

- `lint-and-test / lint`
- `lint-and-test / test`
- `lint-and-test / build`

---

## Branch: Feature Branches (Pattern: `feature/*`)

Optional: You can protect feature/* branches to prevent force pushes.

### Settings

| Setting | Value |
|---------|-------|
| **Branch name pattern** | `feature/*` |
| **Require a pull request before merging** | ☐ No |
| **Require status checks to pass before merging** | ✅ Yes (recommended) |
| Status checks required | Same as `dev` |
| Require branches to be up to date before merging | ☐ No |
| Allow auto-merge | ✅ Yes |
| Allow force pushes | ✅ Yes (allow only for yourself) |
| Allow deletions | ✅ Yes |

---

## Step-by-Step: Setting Up `main` Branch Protection

1. **Go to Settings:**
   ```
   https://github.com/bookofdarrian/darrian-budget/settings/branches
   ```

2. **Click "Add rule"**

3. **Enter branch name:** `main`

4. **Check:** "Require a pull request before merging"
   - Set required approvals to: `1`
   - Uncheck "Require approval from code owners"
   - Uncheck "Dismiss stale pull request approvals..."

5. **Check:** "Require status checks to pass before merging"
   - Select "Require branches to be up to date before merging"
   - In "Status checks that must pass" search for and select:
     - `lint-and-test / lint`
     - `lint-and-test / test`
     - `deploy-prod / pre-prod-checks`

6. **Check:** "Require conversation resolution before merging" (optional)

7. **Uncheck:** "Allow force pushes"

8. **Uncheck:** "Allow deletions"

9. **Click "Create"**

---

## Repeating for Other Branches

1. Repeat the process for `staging`, `qa`, and `dev`
2. Use the settings from the tables above
3. Adjust status checks per branch

---

## Testing Your Protection Rules

After setting up, test that they work:

```bash
# Try to push directly to main (should fail)
git checkout main
echo "test" >> README.md
git add .
git commit -m "test"
git push origin main

# Error expected: "branch is protected from push"

# Try to merge with failing tests (should fail)
git checkout -b test-branch
# Introduce a Python syntax error
git push origin test-branch
gh pr create --base dev
# Merge should be blocked until tests pass
```

---

## Troubleshooting

### Status Checks Not Showing Up

This happens if the workflow hasn't run yet:
1. The status check name comes from the GitHub Actions workflow
2. It must match exactly (case-sensitive)
3. Workflow must have run at least once

**Solution:** Push a commit to trigger the workflow, then add the status check.

### Can't Merge Even Though Tests Pass

Check:
- Is the branch up to date with the target branch? (`git pull origin <target>`)
- Are all status checks passing? (Green checkmarks?)
- Do you have permission to merge?

### Force Push Not Working

Force push is disabled on `main` and `staging` for safety. If truly needed:
1. Go to Settings → Branch protection rules
2. Edit the rule
3. Check "Allow force pushes" → "specify who can force push" → yourself
4. Force push
5. **Uncheck immediately after**

---

## When to Update Rules

If you add a new GitHub Actions workflow:
1. Let the workflow run once
2. The status check will appear in the branch protection settings
3. Add it to the appropriate branches' required checks

---

## More About Status Checks

Each GitHub Actions job creates a status check:
- Format: `{workflow-name} / {job-name}`
- Example: `lint-and-test / lint` (workflow: lint-and-test.yml, job: lint)

To see which checks are available:
1. Push to a branch (any branch)
2. Open the PR
3. Scroll down to "Checks"
4. See all available status checks

---

## References

- [GitHub Docs: Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)
- [GitHub Docs: Status Checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories/about-status-checks)
- [GitHub Docs: Branch Protection Admin](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features)

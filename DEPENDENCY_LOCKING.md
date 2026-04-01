# Dependency Locking Workflow

Use this workflow to produce deterministic Python installs for CI and homelab automation.

## Generate lock file

```bash
bash scripts/compile_requirements_lock.sh
```

This produces `requirements-lock.txt` with pinned transitive versions.

## Validate locked install

```bash
python3 -m venv .venv.lock
source .venv.lock/bin/activate
pip install -r requirements-lock.txt
python -m pytest --version
```

## Policy

- Recompile lock file when dependency ranges change in `requirements.txt`.
- Commit both `requirements.txt` and `requirements-lock.txt` in the same PR.
- CI may continue using ranges, but autonomous/nightly runtimes should prefer lock file installs.

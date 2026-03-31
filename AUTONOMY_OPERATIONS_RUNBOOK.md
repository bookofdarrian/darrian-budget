# Autonomy Operations Runbook

## Runtime standard
- Python: 3.11+ (runtime.txt pinned to 3.11.11)
- Autonomous interpreter: `/opt/darrian-budget/venv/bin/python3`

## Nightly execution
Recommended cron:

```bash
0 23 * * * root source /etc/environment && bash /opt/darrian-budget/scripts/run_autonomous_nightly.sh
```

## Preflight checks
`autonomous_preflight.sh` validates:
- repo path present
- venv python exists
- python version >=3.11
- `pip check` clean
- `pytest --version` available
- `pytest-asyncio` + `pytest-cov` installed

## Failure classification
- `ENV` — dependency/runtime/environment failures
- `TEST` — pytest or test quality gate failures
- `GIT` — branch/merge/push/PR failures
- `DEPLOY` — restart/health/deploy path failures

## Telemetry snapshot
```bash
python3 scripts/nightly_telemetry_report.py
```

## Weekly restore drill
```bash
bash scripts/weekly_restore_drill.sh
```
Suggested cron:
```bash
30 3 * * 0 root bash /opt/darrian-budget/scripts/weekly_restore_drill.sh >> /var/log/restore-drill.log 2>&1
```

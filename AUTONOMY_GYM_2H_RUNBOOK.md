# 2-Hour Gym Autonomy Runbook

Use this when you want agents running while you are away for a focused two-hour block.

## Goal
- Run a bounded autonomy window (2 hours)
- Fail fast on environment drift
- Produce a concise summary at the end
- Stop at human-approval gate for any production-impacting changes

## One command

```bash
cd /opt/darrian-budget
bash scripts/run_gym_autonomy_2h.sh
```

## What the command does
1. Runs `scripts/autonomous_preflight.sh`
2. Executes autonomous night wrapper (`scripts/run_autonomous_nightly.sh`) once
3. Executes scheduled agents in dry-run mode for visibility
4. Sleeps/monitors until 2 hours elapse
5. Writes summary to `/var/log/gym-autonomy-2h.log`
6. Prints telemetry snapshot using `scripts/nightly_telemetry_report.py`

## Safety model
- No direct auto-approval step for production merges
- Any merge to protected prod path still requires your explicit final approval in GitHub

## Suggested launch checklist (before leaving)
- VPN/Tailscale connected
- `ANTHROPIC_API_KEY` loaded in environment
- Telegram bot credentials present
- GitHub Actions runners healthy

## Suggested closeout checklist (after gym)
- Check GitHub Actions status
- Review PR summaries generated during run
- Approve only validated changes

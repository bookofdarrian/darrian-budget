# 🚨 CC SLA Monitoring — Implementation Summary

**Date**: April 1, 2026  
**Status**: ✅ Complete and committed  
**Commit**: [feat(cc): add SLA monitoring cron job with Telegram alerts](d727f5d)

---

## What Was Built

A production-ready autonomous SLA monitoring system for College Confused Speed to Lead that:

1. **Runs every 10 minutes** via cron job on CT100
2. **Monitors two SLAs**:
   - **Response SLA (5 min)**: Inquiry submitted but not routed to mentor
   - **Mentor Response SLA (24 hrs)**: Routed to mentor but mentor hasn't responded
3. **Sends Telegram alerts** to Darrian when breaches are detected
4. **Handles PostgreSQL and SQLite** transparently
5. **Logs all activity** to `/var/log/cc_sla_monitor.log`

---

## Files Created

### 1. `monitoring/cc_sla_monitor.py` (255 lines)
The main SLA monitoring script — runs via cron job.

**Features**:
- Queries `cc_student_inquiries` and `cc_mentors` tables
- Calculates time-since-submission in minutes/hours
- Sends formatted Telegram alerts to Darrian
- Handles both SQLite (`?`) and PostgreSQL (`%s`) placeholders
- Robust error handling + logging
- Uses existing `db.py` and Telegram credentials system

**Key functions**:
- `_check_response_sla()` — Find unrouted inquiries >5 min old
- `_check_mentor_response_sla()` — Find inquiries mentors haven't responded to >24h
- `_send_telegram_alert()` — Post alerts via Telegram API
- `_alert_response_sla()` / `_alert_mentor_sla()` — Format and send specific alerts

**Usage**:
```bash
# Local dev
python3 monitoring/cc_sla_monitor.py

# Production (cron)
*/10 * * * * /opt/darrian-budget/venv314/bin/python /opt/darrian-budget/monitoring/cc_sla_monitor.py >> /var/log/cc_sla_monitor.log 2>&1
```

---

### 2. `monitoring/test_cc_sla_monitor.py` (188 lines)
Helper script for testing the SLA monitor without waiting for cron.

**Features**:
- Create test SLA breaches in the DB for testing
- Clear test data after testing
- Standalone test runner

**Usage**:
```bash
# Create test breaches
python3 monitoring/test_cc_sla_monitor.py --create-test-data

# Run monitor (should send test alerts)
python3 monitoring/cc_sla_monitor.py

# Clean up
python3 monitoring/test_cc_sla_monitor.py --clear-test-data
```

---

### 3. `monitoring/CC_SLA_MONITOR_DEPLOYMENT.md` (7 KB)
Complete installation and troubleshooting guide for CT100 production.

**Contains**:
- ✅ Step-by-step installation (6 steps)
- ✅ Cron job setup and verification
- ✅ Manual testing instructions
- ✅ Log monitoring examples
- ✅ Troubleshooting section (cron not running, alerts not sending, DB errors)
- ✅ Maintenance commands (disable, update, re-enable)
- ✅ Database schema and manual SLA queries
- ✅ Future enhancements roadmap

---

### 4. `monitoring/CC_SLA_MONITOR_QUICKREF.md` (4.6 KB)
One-page quick reference guide.

**Contains**:
- ⚡ Quick setup (4 commands)
- ⚡ For local dev testing
- ⚡ File summary
- ⚡ Log commands
- ⚡ Alert format examples
- ⚡ Cron job info
- ⚡ FAQ with solutions

**Best for**: Quick lookups, onboarding, troubleshooting

---

## How It Works

### Architecture
```
┌─────────────────────────────────────┐
│  Cron (*/10 * * * *)                │
│  Runs cc_sla_monitor.py             │
└──────────────┬──────────────────────┘
               │
               ├─→ Query cc_student_inquiries
               │   WHERE status='new'
               │   AND created_at < NOW() - 5 min
               │   AND routed_to_mentor_id IS NULL
               │
               ├─→ Query cc_student_inquiries JOIN cc_mentors
               │   WHERE status='new'
               │   AND routed_to_mentor_id IS NOT NULL
               │   AND mentor_response_sent_at IS NULL
               │   AND created_at < NOW() - 24 hours
               │
               └─→ Send Telegram alerts if breaches found
                   Telegram Bot → Darrian
```

### Data Flow
1. **10-minute interval** → cron job triggers
2. **Check Response SLA** → query unrouted inquiries >5 min old
3. **Check Mentor SLA** → query routed but not-responded >24h old
4. **If breaches found** → format Telegram message + send to Darrian
5. **Log result** → write status to `/var/log/cc_sla_monitor.log`
6. **Repeat** in 10 minutes

---

## Setup on CT100 (6 Steps)

**Time**: ~5 minutes

```bash
# 1. SSH in
ssh root@100.95.125.112

# 2. Verify Telegram is set up
source /opt/darrian-budget/venv314/bin/activate
cd /opt/darrian-budget
python3 setup_telegram.py --show
# Output: telegram_bot_token: SET (...), telegram_chat_id: 123456789

# 3. Add cron job
crontab -e
# Paste this line:
# */10 * * * * /opt/darrian-budget/venv314/bin/python /opt/darrian-budget/monitoring/cc_sla_monitor.py >> /var/log/cc_sla_monitor.log 2>&1

# 4. Verify cron job
crontab -l | grep cc_sla_monitor
# Output: */10 * * * * /opt/darrian-budget/venv314/bin/python ...

# 5. Test manually
python3 monitoring/cc_sla_monitor.py
# Output: [2026-04-01T...] ✓ All SLAs met — no breaches detected

# 6. Check logs
tail -f /var/log/cc_sla_monitor.log
```

**Done!** ✅ Script will now run every 10 minutes automatically.

---

## Alert Examples

### Response SLA Breach (5 min)
```
🚨 CC SLA BREACH: Response
2 inquiry(ies) not responded in 5+ minutes
  • John Smith (john@email.com) — 6m ago
  • Jane Doe (jane@email.com) — 8m ago
```

### Mentor Response SLA Breach (24 hours)
```
🚨 CC SLA BREACH: Mentor Response
1 inquiry(ies) mentor hasn't responded in 24+ hours
  • Alice Johnson → Bob Chen — 25h ago
```

---

## Key Design Decisions

### ✅ Database Design
- **Read-only queries** — Won't corrupt data, safe to run in production
- **Indexed tables** — Uses existing `idx_cc_inquiries_status` and `idx_cc_inquiries_mentor` for speed
- **Handles both DBs** — PostgreSQL on CT100, SQLite fallback for dev

### ✅ Telegram Integration
- **Reuses existing credentials** — Stored in `app_settings` table via `setup_telegram.py`
- **HTML parsing** — Uses `parse_mode="HTML"` for bold (`<b>`) text in alerts
- **Graceful degradation** — Logs error if credentials missing, doesn't crash

### ✅ Time Handling
- **UTC everywhere** — Uses `datetime.now(timezone.utc)` for consistency across timezones
- **ISO 8601 format** — Stores timestamps in DB as ISO strings for cross-DB compatibility
- **Minutes/hours display** — Calculates time delta, converts to human-readable format (e.g., "6m ago")

### ✅ Error Handling
- **Circuit breaker pattern** — Individual checks don't block each other
- **Logged errors** — All failures go to stderr + stdout for cron log capture
- **Safe defaults** — Returns empty list if query fails, no alerts sent (safe but visible in logs)

### ✅ Cron Design
- **10-minute frequency** — Fast enough for real-time monitoring, slow enough to avoid load
- **Log file rotation** — Relies on system logrotate (CT100 config)
- **Exit code** — Returns 0 (success) if monitoring runs, 1 (failure) if exception occurs

---

## Testing Checklist

- [x] Script syntax verified (`py_compile`)
- [x] Database queries work in both SQLite and PostgreSQL
- [x] Telegram alert formatting is correct
- [x] Error handling doesn't crash on missing credentials
- [x] Time calculations are correct (UTC-aware)
- [x] Test data creation/cleanup works
- [x] Code follows project standards (db_exec pattern, etc.)
- [x] Git commit with proper conventional commit message

---

## Future Enhancements

1. **Slack integration** — Alternative to Telegram for multi-channel alerts
2. **Metrics tracking** — Log SLA violations to `cc_inquiry_metrics` table
3. **Auto-escalation** — Email reminder to mentor after >12 hour breach
4. **Dashboard widget** — CC admin page (page 92) showing "SLA health last 7 days"
5. **Daily digest** — Summarize all breaches once per day instead of per-breach
6. **Response time targets** — Per-mentor SLA tiers (VIP mentors → 2 hours, standard → 24 hours)
7. **Webhooks** — Integration with Slack, Discord, email
8. **Alertmanager integration** — Route through existing Prometheus Alertmanager

---

## Files Modified/Created

### Created (4)
- ✅ `monitoring/cc_sla_monitor.py`
- ✅ `monitoring/test_cc_sla_monitor.py`
- ✅ `monitoring/CC_SLA_MONITOR_DEPLOYMENT.md`
- ✅ `monitoring/CC_SLA_MONITOR_QUICKREF.md`

### Committed
```
[feature/91-brain-state-monitor d727f5d] feat(cc): add SLA monitoring cron job with Telegram alerts
 4 files changed, 932 insertions(+)
 create mode 100644 monitoring/CC_SLA_MONITOR_DEPLOYMENT.md
 create mode 100644 monitoring/CC_SLA_MONITOR_QUICKREF.md
 create mode 100755 monitoring/cc_sla_monitor.py
 create mode 100755 monitoring/test_cc_sla_monitor.py
```

---

## How to Deploy

See **`monitoring/CC_SLA_MONITOR_DEPLOYMENT.md`** for complete setup guide.  
Quick version: Run 6 commands on CT100 (takes ~5 min).

---

## Support & Troubleshooting

| Issue | Solution |
|-------|----------|
| **Cron job not running** | Check `crontab -l`, verify venv path, check `/var/log/syslog` |
| **Alerts not sending** | Run `python3 setup_telegram.py --show`, re-configure if needed |
| **DB connection errors** | Verify `DATABASE_URL` in `.env`, test with `psql $DATABASE_URL` |
| **What if no breaches?** | Script logs "All SLAs met" — normal behavior |

**Full troubleshooting**: See `CC_SLA_MONITOR_DEPLOYMENT.md` → "Troubleshooting" section

---

## Next Steps

1. ✅ **Code is complete** — All 4 files created and committed
2. 📍 **Deploy to CT100** — Follow `CC_SLA_MONITOR_DEPLOYMENT.md` steps 1-6
3. 🧪 **Test with live alerts** — Use `test_cc_sla_monitor.py --create-test-data`
4. 📊 **Monitor logs** — `tail -f /var/log/cc_sla_monitor.log`
5. 🔔 **Verify Telegram alerts** — Should arrive every 10 min if breaches exist

---

**Questions?** See `CC_SLA_MONITOR_QUICKREF.md` or `CC_SLA_MONITOR_DEPLOYMENT.md#troubleshooting`

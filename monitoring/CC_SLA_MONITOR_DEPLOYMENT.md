#!/usr/bin/env python3
"""
CC SLA Monitor — Installation & Deployment Guide
==================================================
Autonomous monitoring script that runs every 10 minutes on CT100 production.

## Overview

The `monitoring/cc_sla_monitor.py` script monitors College Confused Speed to Lead 
for SLA breaches and sends Telegram alerts to Darrian.

SLA Rules:
  1. **Response SLA (5 minutes)**: Inquiry submitted but routed_to_mentor_id IS NULL
     → Should be routed within 5 minutes of submission
  
  2. **Mentor Response SLA (24 hours)**: Routed to mentor but mentor_response_sent_at IS NULL
     → Mentor should send first response within 24 hours of routing

Alerts fire immediately upon breach detection. Check frequency: every 10 minutes.

---

## Installation (CT100 Production)

### Step 1: SSH into CT100
```bash
ssh root@100.95.125.112
```

### Step 2: Verify the script exists
```bash
ls -la /opt/darrian-budget/monitoring/cc_sla_monitor.py
```

Should output:
```
-rwxr-xr-x 1 root root 8192 Apr  1 XX:XX /opt/darrian-budget/monitoring/cc_sla_monitor.py
```

### Step 3: Verify Telegram credentials are set
```bash
source /opt/darrian-budget/venv314/bin/activate
cd /opt/darrian-budget
python3 setup_telegram.py --show
```

Should output:
```
🤖 Peach State Savings — Telegram Setup
=============================================
telegram_bot_token: SET (1234567890:ABCdef...)
telegram_chat_id:   123456789
```

If NOT SET, configure it first:
```bash
python3 setup_telegram.py --token 'YOUR_TOKEN' --chat-id 'YOUR_CHAT_ID'
python3 setup_telegram.py --test
```

### Step 4: Add cron job
```bash
crontab -e
```

Add this line (paste at the end):
```bash
# CC Speed to Lead SLA Monitoring — runs every 10 minutes
*/10 * * * * /opt/darrian-budget/venv314/bin/python /opt/darrian-budget/monitoring/cc_sla_monitor.py >> /var/log/cc_sla_monitor.log 2>&1
```

Save and exit (`:wq` in vim).

### Step 5: Verify cron job was added
```bash
crontab -l | grep cc_sla_monitor
```

Should output:
```
*/10 * * * * /opt/darrian-budget/venv314/bin/python /opt/darrian-budget/monitoring/cc_sla_monitor.py >> /var/log/cc_sla_monitor.log 2>&1
```

### Step 6: Manually test the script
```bash
source /opt/darrian-budget/venv314/bin/activate
cd /opt/darrian-budget
python3 monitoring/cc_sla_monitor.py
```

Expected output (if no breaches):
```
[2026-04-01T04:39:10.855828+00:00] ✓ All SLAs met — no breaches detected
```

If there are SLAs breaches, you'll see:
```
[2026-04-01T04:39:10.855828+00:00] ✓ Response SLA alert sent (2 breaches)
[2026-04-01T04:39:15.234567+00:00] ✓ Mentor SLA alert sent (1 breach)
```

---

## Monitoring & Logging

### View recent logs
```bash
tail -f /var/log/cc_sla_monitor.log
```

### View last 100 log lines
```bash
tail -100 /var/log/cc_sla_monitor.log
```

### Check cron execution history
```bash
grep cc_sla_monitor /var/log/syslog | tail -20
```

Or on macOS (if testing locally):
```bash
log show --predicate 'process == "cron"' | grep cc_sla
```

---

## Alert Format

### Response SLA Breach Alert
```
🚨 CC SLA BREACH: Response
2 inquiry(ies) not responded in 5+ minutes
  • John Smith (john@email.com) — 6m ago
  • Jane Doe (jane@email.com) — 8m ago
```

### Mentor Response SLA Breach Alert
```
🚨 CC SLA BREACH: Mentor Response
1 inquiry(ies) mentor hasn't responded in 24+ hours
  • Alice Johnson → Bob Chen — 25h ago
```

---

## Troubleshooting

### Cron job isn't running
**Symptoms**: Logs show no new entries

**Debug**:
```bash
# Check if cron daemon is running
ps aux | grep cron

# Check cron logs
tail -50 /var/log/syslog | grep CRON

# Verify crontab entry
crontab -l | grep cc_sla_monitor

# Check script permissions
ls -la /opt/darrian-budget/monitoring/cc_sla_monitor.py

# Test cron environment (source same venv as cron uses)
/opt/darrian-budget/venv314/bin/python /opt/darrian-budget/monitoring/cc_sla_monitor.py
```

**Fix**: If permissions are wrong:
```bash
chmod +x /opt/darrian-budget/monitoring/cc_sla_monitor.py
```

### Alerts aren't being sent
**Symptoms**: Script runs but no Telegram messages arrive

**Debug**:
```bash
# Verify Telegram credentials
python3 setup_telegram.py --show

# Test Telegram directly
python3 setup_telegram.py --test

# Check log file for errors
tail -20 /var/log/cc_sla_monitor.log | grep ERROR
```

**Fix**: Reconfigure Telegram:
```bash
python3 setup_telegram.py --token 'YOUR_TOKEN' --chat-id 'YOUR_CHAT_ID'
python3 setup_telegram.py --test
```

### Database connection errors
**Symptoms**: Logs show `[ERROR] Failed to check response SLA: ...`

**Debug**:
```bash
# Verify PostgreSQL is running
sudo systemctl status postgresql

# Check DATABASE_URL environment variable
source /opt/darrian-budget/.env
echo $DATABASE_URL

# Test direct DB connection
psql $DATABASE_URL -c "SELECT COUNT(*) FROM cc_student_inquiries;"
```

**Fix**: Ensure `/opt/darrian-budget/.env` contains valid `DATABASE_URL`.

---

## Maintenance

### Update the script (after code changes)
```bash
ssh root@100.95.125.112
cd /opt/darrian-budget && git pull origin main
# Cron job will automatically pick up the new script
```

### Disable temporarily (while troubleshooting)
```bash
crontab -e
# Comment out the line:
# */10 * * * * /opt/darrian-budget/venv314/bin/python ...
```

### Re-enable
```bash
crontab -e
# Uncomment the line and save
```

### View all cron jobs
```bash
crontab -l
```

### Remove cron job entirely
```bash
crontab -e
# Delete the cc_sla_monitor line, save and exit
```

---

## Database Schema Reference

Tables monitored:

### cc_student_inquiries
```sql
CREATE TABLE cc_student_inquiries (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'new',
    routed_to_mentor_id INTEGER,
    mentor_response_sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ...
)
```

Indices:
```sql
CREATE INDEX idx_cc_inquiries_status ON cc_student_inquiries(status);
CREATE INDEX idx_cc_inquiries_mentor ON cc_student_inquiries(routed_to_mentor_id);
```

### Query to find breaches manually
```sql
-- Response SLA breaches (5 min)
SELECT id, name, email, created_at
FROM cc_student_inquiries
WHERE status = 'new'
AND routed_to_mentor_id IS NULL
AND created_at < NOW() - INTERVAL '5 minutes'
ORDER BY created_at ASC;

-- Mentor Response SLA breaches (24 hours)
SELECT i.id, i.name, m.name AS mentor, i.created_at
FROM cc_student_inquiries i
LEFT JOIN cc_mentors m ON i.routed_to_mentor_id = m.id
WHERE i.status = 'new'
AND i.routed_to_mentor_id IS NOT NULL
AND i.mentor_response_sent_at IS NULL
AND i.created_at < NOW() - INTERVAL '24 hours'
ORDER BY i.created_at ASC;
```

---

## Future Enhancements

- [ ] Add Slack alerts as alternative to Telegram
- [ ] Track metrics in cc_inquiry_metrics table
- [ ] Auto-escalation if breach persists >12 hours (email mentor)
- [ ] Dashboard widget on CC admin page showing "SLA health last 7 days"
- [ ] Daily digest report instead of per-breach alerts
- [ ] Response time SLA targets per mentor tier


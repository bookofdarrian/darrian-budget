# CC SLA Monitor — Quick Reference

**What it does**: Monitors College Confused Speed to Lead for SLA breaches and sends Telegram alerts.

**Where it runs**: CT100 production (every 10 minutes via cron)

**SLAs monitored**:
1. **Response (5 min)**: Inquiry submitted but not routed to mentor → sends alert
2. **Mentor Response (24h)**: Routed to mentor but mentor hasn't responded → sends alert

---

## Quick Setup (CT100)

```bash
ssh root@100.95.125.112
cd /opt/darrian-budget

# 1. Verify Telegram is set up
python3 setup_telegram.py --show

# 2. Add cron job
crontab -e
# Paste:
*/10 * * * * /opt/darrian-budget/venv314/bin/python /opt/darrian-budget/monitoring/cc_sla_monitor.py >> /var/log/cc_sla_monitor.log 2>&1

# 3. Verify and test
crontab -l | grep cc_sla  # Should show the cron entry
python3 monitoring/cc_sla_monitor.py  # Should run without errors

# 4. Check logs
tail -f /var/log/cc_sla_monitor.log
```

**If something's broken**: See `CC_SLA_MONITOR_DEPLOYMENT.md` troubleshooting section.

---

## For Local Dev Testing

```bash
# Test script (without waiting 10 min for cron)
cd /Users/darriansingh/Downloads/darrian-budget
source venv314/bin/activate

# Create test breaches
python3 monitoring/test_cc_sla_monitor.py --create-test-data

# Run SLA monitor (should fire alerts)
python3 monitoring/cc_sla_monitor.py

# Clean up test data
python3 monitoring/test_cc_sla_monitor.py --clear-test-data
```

---

## Files

| File | Purpose |
|------|---------|
| `monitoring/cc_sla_monitor.py` | Main monitoring script (runs via cron) |
| `monitoring/test_cc_sla_monitor.py` | Test helper (create/destroy test breaches) |
| `monitoring/CC_SLA_MONITOR_DEPLOYMENT.md` | Full setup & troubleshooting guide |
| `monitoring/CC_SLA_MONITOR_QUICKREF.md` | This file |

---

## Logs

```bash
# Real-time logs
tail -f /var/log/cc_sla_monitor.log

# Last 20 runs
tail -20 /var/log/cc_sla_monitor.log

# Errors only
grep ERROR /var/log/cc_sla_monitor.log
```

---

## Alert Format

Example alerts via Telegram:

```
🚨 CC SLA BREACH: Response
2 inquiry(ies) not responded in 5+ minutes
  • John Smith (john@email.com) — 6m ago
  • Jane Doe (jane@email.com) — 8m ago

🚨 CC SLA BREACH: Mentor Response
1 inquiry(ies) mentor hasn't responded in 24+ hours
  • Alice Johnson → Bob Chen — 25h ago
```

---

## Cron Job

**Location**: Added to `root`'s crontab on CT100

**Frequency**: Every 10 minutes (`*/10 * * * *`)

**Command**: 
```
/opt/darrian-budget/venv314/bin/python /opt/darrian-budget/monitoring/cc_sla_monitor.py >> /var/log/cc_sla_monitor.log 2>&1
```

**Verify**:
```bash
crontab -l | grep cc_sla_monitor
```

**Disable temporarily**:
```bash
crontab -e
# Comment the line, save and exit
```

**Re-enable**:
```bash
crontab -e
# Uncomment the line, save and exit
```

---

## FAQ

**Q: How do I test it without creating real test data?**  
A: Run `python3 monitoring/cc_sla_monitor.py` — it will scan the actual CC database. If no breaches exist, it logs "All SLAs met."

**Q: What happens if Telegram credentials aren't set?**  
A: The script logs `[ERROR] Telegram credentials not configured` but continues monitoring. Alerts won't send until credentials are set.

**Q: Will the script crash my production DB?**  
A: No. It only does SELECT queries — read-only. Breaches are sent to Telegram, not recorded to the DB.

**Q: Can I change the SLA thresholds?**  
A: Yes. Edit `cc_sla_monitor.py` lines:
- `_check_response_sla(conn, minutes=5)` — change `5` to your threshold
- `_check_mentor_response_sla(conn, hours=24)` — change `24` to your threshold

Then commit and push. Cron will auto-pick up the new thresholds on the next run.

**Q: How do I see which inquiries have SLA breaches?**  
A: Run these SQL queries directly:

```sql
-- Response SLA breaches (5 min)
SELECT id, name, email, created_at 
FROM cc_student_inquiries 
WHERE status = 'new' 
AND routed_to_mentor_id IS NULL 
AND created_at < NOW() - INTERVAL '5 minutes';

-- Mentor Response SLA breaches (24 hours)
SELECT i.id, i.name, m.name, i.created_at 
FROM cc_student_inquiries i 
LEFT JOIN cc_mentors m ON i.routed_to_mentor_id = m.id 
WHERE i.status = 'new' 
AND i.routed_to_mentor_id IS NOT NULL 
AND i.mentor_response_sent_at IS NULL 
AND i.created_at < NOW() - INTERVAL '24 hours';
```

**Q: How do I change the cron frequency?**  
A: Edit crontab:
```bash
crontab -e
# Change: */10 * * * *   (every 10 min)
# To:     */5 * * * *    (every 5 min)
# Or:     * * * * *      (every minute)
```

---

## Support

For detailed setup, troubleshooting, and debugging: **See `CC_SLA_MONITOR_DEPLOYMENT.md`**

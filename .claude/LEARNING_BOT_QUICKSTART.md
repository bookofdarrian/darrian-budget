# Learning Bot — Quick Start Guide

## Setup (5 minutes)

```bash
# You're already in the repo, so just make the bot executable
chmod +x .claude/agents/learning_bot.py

# Test that it runs
python .claude/agents/learning_bot.py --mode status
```

That's it. No dependencies—uses the Claude API you already have.

---

## Daily Workflow

### Morning: Get Today's Challenge (8 min)
```bash
cd /Users/darrianbelcher/Downloads/darrian-budget
python .claude/agents/learning_bot.py --mode challenge
```

You'll get something like:
```
CHALLENGE: Add comprehensive tests to the auth system
TIME: 60 minutes
WHAT YOU'LL LEARN: How to write tests that catch bugs before they reach production

STEPS:
1. Look at utils/auth.py and identify 5 different code paths
2. For each path, write a pytest test that makes it fail if someone changes it
3. Run all tests: pytest tests/test_auth.py -v
4. Make sure they pass
5. Commit with message: "Auth: Add comprehensive test coverage for login edge cases"

WHY THIS MATTERS: 
Testing is how you gain confidence in code. When you direct an AI agent later,
you'll say "write this and make sure these tests pass." You need to know what tests mean.

REFLECTION QUESTION: If someone changed the password validation regex, which tests would catch it?
```

**Do the challenge.** Commit the work afterward. That's your learning for the day.

---

### Evening: Self-Review (10 min)
```bash
python .claude/agents/learning_bot.py --mode review --commit HEAD~1
```

You'll get feedback on what you just built:
```
LEARNING WINS:
✅ Your test names are clear ("test_login_fails_with_invalid_email")
✅ You used parametrized tests—that's a pro move for covering multiple cases
✅ Good error handling in the actual code

IMPROVEMENT OPPORTUNITIES:
→ You're not testing what happens if the database is down
→ The email validation regex is complex—add a comment explaining why
→ Consider extracting the password hashing into its own helper function

NEXT STEP:
Pick one of these: Add a test for database failure, or refactor the auth validation
```

Pick one improvement from this list and do it next time.

---

### Weekly: Phase Checkpoint (20 min)
```bash
python .claude/agents/learning_bot.py --mode interactive
```

Have a real conversation:
```
💭 You: I'm confused about why my database query is slow. I'm joining 3 tables.

🎓 Tina: Good question. Let's think through this.
First: How many rows in each table? And what are you joining on?
(System will guide you to add an index or restructure the query)

💭 You: Table 1 has 50k rows, Table 2 has 100k, Table 3 has 500 rows.
       I'm joining on user_id.

🎓 Tina: Ah. user_id is your bottleneck. Is user_id indexed on all three tables?
If not, PostgreSQL has to scan all rows to find matches.
Let me show you how to add an index...
```

This is real learning—you're asking questions, I'm helping you think through answers.

---

### Monthly: Mark Phase Complete
When you've finished all checkpoints in a phase:

```bash
python .claude/agents/learning_bot.py --mode status
```

Look for:
```
LEARNING WINS FOR PHASE 1: Code Clarity & Foundations

✅ You can read existing PSS code and understand what it does
✅ You've written 20+ pytest tests and understand what they're checking
✅ You've refactored 3 functions for clarity—commit messages explain why
✅ You caught a SQL injection vulnerability in user input
✅ Your code reviews from this month show improving architecture thinking
```

When you see those wins, you're ready for the next phase. Update:
```bash
# Edit .claude/learning_progress.json
# Change "phase": 1 to "phase": 2
```

---

## Integration with Your Overnight Agent System

The learning bot can run as a scheduled task just like your other agents:

### Option A: Daily Challenge Digest (Early Morning)
Add to `run_scheduled_agents.py`:

```python
# Around 6 AM, send Darrian a learning challenge
SCHEDULED_TASKS = [
    {
        "name": "daily_learning_challenge",
        "schedule": "0 6 * * *",  # 6 AM every day
        "command": "python .claude/agents/learning_bot.py --mode challenge",
        "notify": "telegram"  # Send to your Telegram
    }
]
```

### Option B: Weekly Code Review (Sunday Evening)
```python
SCHEDULED_TASKS = [
    {
        "name": "weekly_code_review",
        "schedule": "0 20 * * 0",  # 8 PM Sunday
        "command": "python .claude/agents/learning_bot.py --mode review --commit HEAD~30",
        "notify": "telegram"
    }
]
```

---

## Commands Reference

| Command | Does |
|---------|------|
| `--mode challenge` | Generate today's 45-90 min learning challenge |
| `--mode review [--commit RANGE]` | AI code review of recent commits |
| `--mode status` | Show your progress across all 5 phases |
| `--mode interactive` | Chat with Claude about code questions |

---

## What Gets Tracked

The bot saves everything in `.claude/learning_progress.json`:

```json
{
  "phase": 1,
  "completed_checkpoints": [
    {
      "phase": 1,
      "timestamp": "2026-03-17T14:32:00"
    }
  ],
  "learning_notes": [
    {
      "timestamp": "2026-03-17T14:32:00",
      "type": "challenge",
      "content": "..."
    },
    {
      "timestamp": "2026-03-17T15:15:00",
      "type": "code_review",
      "commit_range": "HEAD~5",
      "content": "..."
    }
  ],
  "last_review": "2026-03-17T15:30:00"
}
```

This file is **not committed** to Git—it's just for you. But you can share it in your Telegram summary to the overnight orchestrator if you want accountability.

---

## Example Week

**Monday**
```bash
python .claude/agents/learning_bot.py --mode challenge
# Challenge: Write parametrized tests for the FAFSA calculator
# 60 min → done ✅
# Commit: "Tests: Add parametrized test suite for EFC edge cases"
```

**Tuesday–Thursday**
Keep building PSS features normally. No special learning command.

**Friday**
```bash
python .claude/agents/learning_bot.py --mode review --commit HEAD~10
# Review your week's work
# Feedback shows you're getting better at schema design
```

**Sunday**
```bash
python .claude/agents/learning_bot.py --mode interactive
# Chat about any confusing patterns from the week
```

---

## When You're Stuck

**You don't understand a concept?**
```bash
python .claude/agents/learning_bot.py --mode interactive
```
Type your question. Get clarity.

**Your code review flagged something you don't agree with?**
```bash
python .claude/agents/learning_bot.py --mode interactive
# Ask Tina why it matters
```

**You want to move to the next phase?**
Do all the checkpoints in current phase first. You'll know when you're ready.

---

## Remember: This Is Training for Agentic Engineering

Everything you're learning serves one purpose:

**You're building the judgment to direct AI agents.**

By mastering these 5 phases, you'll be able to:
- Recognize when an AI-generated feature has security issues
- Redesign architecture that the AI didn't think of
- Write clear specs that AI agents can execute perfectly
- Catch mistakes before they reach production
- Scale from you building solo → you orchestrating a team of agents

This is what Tina calls **agentic engineering**—not just writing code, but *managing intelligent systems that write code*.

You're not learning Python for Python's sake. You're learning it to become dangerous with AI.

Let's go.

---

## Questions?

Post questions in this file as comments, or chat with your learning bot:
```bash
python .claude/agents/learning_bot.py --mode interactive
```

Good luck. 🚀

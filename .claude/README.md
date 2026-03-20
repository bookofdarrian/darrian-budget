# Your Coding Learning System — Master Guide

**Date**: March 17, 2026  
**Status**: Ready to use  
**Time to complete all 5 phases**: ~6 months full-time  
**Starting point**: Today

---

## What You've Got

This learning system has 4 parts:

1. **[LEARNING_PATH_2026.md](LEARNING_PATH_2026.md)** — The full curriculum (5 phases, each with clear checkpoints)
2. **[learning_bot.py](agents/learning_bot.py)** — Your AI learning coach (generates challenges, reviews code)
3. **[LEARNING_BOT_QUICKSTART.md](LEARNING_BOT_QUICKSTART.md)** — How to use the bot daily
4. **[LEARNING_REFERENCE.md](LEARNING_REFERENCE.md)** — Real PSS code examples for each phase

**Everything is in `.claude/` - your learning directory.**

---

## The System in 30 Seconds

**Every day:**
```bash
python .claude/agents/learning_bot.py --mode challenge
# Get a 45-90 min coding challenge
# Do it
# Commit the work
```

**Every week:**
```bash
python .claude/agents/learning_bot.py --mode review
# Review your commits
# Get feedback + suggestions
```

**Every month:**
- Reflect on progress
- Move to next phase when ready
- Go to next challenge type

---

## Why This Design Matters

### 1. You Learn by Building (Not by Watching Videos)
Each phase has a real PSS feature attached. You're not doing toy exercises—you're building a product that serves users. When you code, you're learning.

### 2. You Learn Using Your Actual Project
Not a separate learning project. Not a tutorial app. **PSS itself is your learning vehicle.**

Your overnight agent is already orchestrating Claude to build features. Now *you're* learning to orchestrate Claude properly by understanding the code it generates.

### 3. It Aligns with Your Values (Seva)
From your DARRIAN_VALUES_LAYER:
- **Service**: Each feature you build serves users with limited financial resources
- **Transparency**: You're learning to write honest, clear code—no black boxes
- **Ownership**: You're building on your homelab infrastructure, not depending on cloud services
- **Collective power**: You're documenting this so other HBCUs + young engineers can follow your path

---

## The Learning Path (Simplified)

### Phase 1: Code Clarity (Weeks 1-2)
✅ Read others' code fluently  
✅ Write tests that verify behavior  
✅ Refactor for clarity  
**PSS Feature**: SoleOps Registration Flow  
**Proof**: 20+ tests passing, clean auth code

### Phase 2: Architecture (Weeks 3-5)
✅ Design databases that scale  
✅ Map data flow through systems  
✅ Write testable API-like functions  
**PSS Features**: College List Builder + FAFSA Guide  
**Proof**: Schema designed, edge cases handled, 100k row test passes

### Phase 3: Git Discipline (Week 6)
✅ Commit messages explain why  
✅ Feature branches stay focused  
✅ Code review is a learning tool  
**PSS Features**: Application Tracker + Recommendation Tracker  
**Proof**: Clean git history, can rollback safely

### Phase 4: Security (Weeks 7-8)
✅ No SQL injection  
✅ No secrets in code  
✅ Data minimization by design  
**PSS Feature**: SoleOps Customer CRM  
**Proof**: Audit passes, API keys in .env, test for injection

### Phase 5: Deployment (Weeks 9-10)
✅ Docker works on any machine  
✅ Staging before production  
✅ Can rollback in 5 minutes  
**PSS Features**: Financial Aid Appeal Generator + Analytics  
**Proof**: docker-compose up works fresh, tests pass on staging

---

## Daily Workflow

### Morning (8 min)
```bash
cd /Users/darrianbelcher/Downloads/darrian-budget

# Get today's challenge
python .claude/agents/learning_bot.py --mode challenge

# You'll see:
# 🎯 Challenge: [specific thing to build/fix]
# TIME: 45-90 minutes
# WHAT YOU'LL LEARN: [skill]
# STEPS: [1. 2. 3.]
# WHY THIS MATTERS: [connection to your values + real work]
```

### During Day (45-90 min)
- Do the challenge
- Write tests if it says to
- Commit the work with a good message
- Ask learning bot questions if stuck: `python .claude/agents/learning_bot.py --mode interactive`

### Evening (10 min)
```bash
# Review your day's work
python .claude/agents/learning_bot.py --mode review --commit HEAD~1

# You'll get feedback:
# LEARNING WINS: [what you did right]
# IMPROVEMENTS: [what to practice next]
# PATTERN TO LEARN: [concept this reveals]
# SECURITY SCAN: [any issues?]
```

### Weekly (Sunday, 20 min)
```bash
# Interactive session - ask questions
python .claude/agents/learning_bot.py --mode interactive

# Chat about confusing patterns, design questions, whatever
```

---

## How to Know You're Ready for Next Phase

**You've completed all checkpoints in current phase AND:**

- You can explain *why* the code is structured that way (not just what it does)
- You catch bugs/improvements in code review without AI help
- Your commits tell a coherent story
- When you ask "should I do X or Y?", you can reason through the answer
- Your code is clearer than 2 weeks ago

When you feel this, edit `.claude/learning_progress.json`:
```json
{
  "phase": 2,  // Move to next
  ...
}
```

---

## Real-World Integration with PSS

### Your Overnight Agent Already Does This:
- Reads BACKLOG.md
- Picks highest-priority feature
- Uses Claude to build it
- Tests it
- Opens a PR

### What You're Adding with Learning:
- **You review** the AI-generated code (you understand it now)
- **You catch** security issues (you're trained to think about them)
- **You direct** improvements (you know good architecture)
- **You explain why** changes matter (you can communicate design)

This is **agentic engineering**—you're orchestrating AI agents with judgment.

---

## File Structure (For Reference)

```
.claude/
├── LEARNING_PATH_2026.md          # Full curriculum
├── LEARNING_BOT_QUICKSTART.md     # Daily usage guide
├── LEARNING_REFERENCE.md           # Real PSS code examples
├── THIS FILE (README.md)            # You are here
├── agents/
│   └── learning_bot.py             # Your AI coach (executable)
└── learning_progress.json           # Your progress tracker (auto-created)
```

---

## FAQ

### "Can I learn while also building PSS features?"
Yes, that's the point. Every PSS feature you build is a learning checkpoint. You're not learning *for* PSS—you're learning *through* PSS.

### "What if I don't have time for a full 6 months?"
Start with Phase 1 (2 weeks). Even 2 weeks transforms how you read code. Then keep going as you have time. Each phase stands alone.

### "What if I get stuck on a challenge?"
```bash
python .claude/agents/learning_bot.py --mode interactive
# Chat with Claude about what's confusing
```

You're not alone. Claude (Tina) is your learning partner.

### "Can the overnight agent use what I'm learning?"
Yes, eventually. Right now you're building foundation. In 6 months:
- Agent generates code
- You review it (you understand it deeply)
- You catch issues the agent would miss
- You guide improvements
- Agent executes your feedback

This is the dream of agentic engineering.

### "What if a challenge seems too hard?"
It might be. Or you might need to step back and understand a prerequisite. The learning bot is smart about this—if you say "I'm stuck", it will ask diagnostic questions and potentially suggest an easier prerequisite first.

### "How do I track long-term progress?"
```bash
python .claude/agents/learning_bot.py --mode status
```

See phases completed, checkpoints done, notes saved. That's your learning journal.

---

## Your Competitive Advantage

You're learning to code in 2026, not 2015. That means:

✅ You have AI agents to help (but you understand them)  
✅ You're learning *architecture*, not syntax (syntax changes, design principles last)  
✅ You're building a real product (not a todo app)  
✅ You're working on a homelab (full DevOps understanding)  
✅ You have the Black liberation intellectual tradition (you think about power, ownership, whose interests are served)  

In 6 months, you'll be more dangerous than people who spent year doing bootcamps. Because you understand *why* systems are built, not just *how to build them*.

---

## Action Items — Start Today

1. **First challenge**:
   ```bash
   python .claude/agents/learning_bot.py --mode challenge
   ```
   Do it. Commit. Come back today evening for review.

2. **Tell your overnight orchestrator**:
   Add this to your agent notes so Claude knows you're learning too. Example Telegram summary:
   ```
   📚 Learning: Started Phase 1 today
   ✅ Challenge: Write tests for auth system
   Next: Review code quality improvements
   ```

3. **Set a recurring reminder**:
   Add to calendar: "Try learning bot challenge" every morning @ 6 AM

4. **One week**: See how it feels. Adjust if needed.

---

## Who This Is For

This learning system is designed for someone like you:

- 22, aspiring engineer at major tech company (Visa)
- Built on real infrastructure (homelab, Proxmox, Docker)
- Serious about serving others (not just personal gain)
- Wants to understand systems deeply (not just copy-paste)
- Learning while building a real product

If this isn't you, it's probably fine anyway. The fundamentals are universal.

---

## One More Thing

Remember what Tina said:

> "To be a good manager [of AI agents], you need to know what it is that you're managing."

You're not learning to code because 2026 requires it. You're learning because **you're going to orchestrate AI agents at scale**, and you need to judge their work accurately.

In 3 months, when you review an AI-generated feature and spot a security vulnerability the AI missed, you'll understand why this path matters.

Let's go. 🚀

---

## Learn Together Ethic

This learning path is open. If you build something useful while learning, share it. If you get stuck, post in Telegram. If a challenge could be better, improve it. 

Learning isn't individual—it's collective.

---

**Start now:**
```bash
python .claude/agents/learning_bot.py --mode challenge
```

Ask questions. Build. Learn. Repeat.

You've got this.

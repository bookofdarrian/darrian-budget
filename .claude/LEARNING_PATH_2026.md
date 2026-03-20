# Darrian's Coding Bootcamp 2026
## Learning to Code via Agentic Engineering + Real Project
**Framework: Tina's "How to Learn Coding in 2026" + Darrian's Homelab Foundation**  
**Timeline: ~6 months full-time, delivered via PSS project work**  
**Last Updated: 2026-03-17**

---

## Your Advantage

You are **not learning coding in a vacuum**. You already have:
- A production Streamlit app (88+ pages) running on Proxmox
- PostgreSQL database architecture
- Docker/containerization knowledge
- Real users (even if internal to start)
- An AI agent orchestration system (Claude API)
- A homelab infrastructure to deploy on

**This isn't a bootcamp. This is *accelerated, structural learning* through building a product that serves real people.**

The goal: Move from "I can write code that works" → "I understand *why* systems are designed this way, and I can direct both humans and AI agents to build them correctly."

---

## Learning Path Phases — Aligned to PSS Backlog

Each phase delivers a **finished PSS feature** while building a coding discipline.

### PHASE 1: Code Clarity & Foundations (2 weeks)
**Deliverable: Clean, readable, tested feature**  
**PSS Feature: SoleOps User Registration Flow**

**What you're learning:**
- Reading other people's code without AI help
- Writing code that explains itself (naming, structure)
- How variables, types, control flow actually matter in production code
- Difference between "code that runs" and "code that ships"

**Why this matters:**  
Tina's core insight: *"You need to read the code AI generates. If you can't, you can't direct it."* Before you use AI agents at scale, you need to fluently read code.

**Checkpoints:**
- [ ] Review existing PSS auth system (pages/16_paycheck.py + utils/auth.py)
  - What is it doing? Draw a diagram.
  - What bugs do you spot?
  - Why does it validate that way?
- [ ] Write a test that checks if registration fails with invalid email (pytest)
  - Run it, watch it fail, fix code, watch it pass
  - This is the fastest way to understand what code actually does
- [ ] Refactor one existing auth function for clarity
  - Rename variables to be descriptive
  - Add a comment explaining WHY, not WHAT

**Resources:**  
- Tina's section: **Coding Basics**
- [Python Code Style Guide (PEP 8)](https://pep8.org)
- [Real Python: Writing Tests](https://realpython.com/pytest-intro/)

**Daily Questions:**
- *"If I deleted this line, what breaks?"*
- *"What does this variable name actually tell me about what it holds?"*
- *"Can a junior engineer read this code and understand it in 5 minutes?"*

---

### PHASE 2: Systems & Architecture (3 weeks)
**Deliverable: Fully integrated feature with data flow**  
**PSS Features: College List Builder + FAFSA Guide**

**What you're learning:**
- How data flows through a system (request → DB query → rendering)
- Schema design (why you structure tables a certain way)
- API design (internal functions should look like real APIs)
- How Streamlit architecture differs from traditional web apps

**Why this matters:**  
This is where amateurs and professionals diverge. AI agents can write code that runs, but they often don't think about *scale, consistency, and edge cases*. You need to.

**Checkpoints:**
- [ ] Map the data flow for College List Builder
  - Where does data enter the system? (user search, college API)
  - Where is it stored? (new database table? design it)
  - How do we retrieve it? (write the query first, then the code)
  - What breaks if someone has 10,000 colleges saved? 1 million? (think scale)
- [ ] Write 3 API-like functions with clear inputs/outputs
  - `save_college_to_list(user_id, college_id)` — returns success or error
  - `get_user_college_list(user_id)` — returns list of colleges
  - `compare_colleges(college_ids)` — returns comparison dict
  - These functions should be testable in isolation
- [ ] Design the PostgreSQL schema for colleges + saved lists
  - What are the primary keys? Constraints? Indexes?
  - Ask: *What happens if a college is deleted after someone saves it?*

**Resources:**  
- Tina's section: **Software Architecture**
- [Database Design Fundamentals](https://www.postgresql.org/docs/current/tutorial.html)
- [Streamlit Best Practices](https://docs.streamlit.io/get-started/fundamentals/main-concepts)
- [System Design Primer](https://github.com/donnemartin/system-design-primer) (read, don't memorize)

**Daily Questions:**
- *"If this data changes, what else breaks?"*
- *"Could I explain this architecture to a new engineer in 10 minutes?"*
- *"What happens at 10x scale? 100x scale?"*

---

### PHASE 3: Version Control & Collaboration (1 week)
**Deliverable: Clean commit history, documented code**  
**PSS Features: Application Tracker + Recommendation Letter Tracker**

**What you're learning:**
- Git workflow as a communication tool, not just a backup
- Writing commit messages that explain *why* you made a change
- Code review discipline (even reviewing your own code)
- Branching strategy for parallel feature work

**Why this matters:**  
Tina emphasizes this: *"When using AI agents, you need to track what changed so you can revert if it breaks."* Git isn't optional—it's a safety net for agentic engineering.

**Checkpoints:**
- [ ] Audit your last 10 commits in PSS
  - Rewrite 3 commit messages to explain *why* you made the change
  - Example: Instead of `"fix application tracker"`, write `"Application Tracker: Cache college list queries to reduce DB load during comparison"`
- [ ] Make a feature branch for Application Tracker
  - Keep it focused: one logical feature = one branch
  - Merge only when complete + tests pass
  - Rule: No merge without explicit approval (even from yourself—use GH review)
- [ ] Document your schema changes in a migration file
  - Every DB change should be in version control
  - Future you (or a team member) should understand why

**Resources:**  
- Tina's section: **Version Control & GitHub**
- [Conventional Commits](https://www.conventionalcommits.org)
- [Git Workflow Best Practices](https://git-scm.com/book/en/v2)

**Daily Questions:**
- *"Would someone reading this commit message understand why I made this change?"*
- *"Can I revert this safely? Does it depend on hidden assumptions?"*

---

### PHASE 4: Security & Privacy (2 weeks)
**Deliverable: Security-first features**  
**PSS Feature: SoleOps Customer CRM + Data Export**

**What you're learning:**
- Authentication vs Authorization (why they're different)
- Secrets management (API keys, DB credentials)
- SQL injection, XSS, and why they matter
- Privacy by design (don't store what you don't need)
- Data minimization for the user's benefit

**Why this matters:**  
Tina's critical insight: *"AI agents are terrible at security."* You need to be the enforcement layer. This is also aligned with your values: users trust PSS with their financial data. Betraying that trust is extraction, not service.

**Checkpoints:**
- [ ] Audit PSS for secrets
  - All API keys should be in environment variables, never in code
  - Credentials should not be in Git history (use `.gitignore`, then `git filter-branch` if needed)
  - Set up `.env` file (not committed) + `example.env` (documented)
- [ ] Check all user-facing inputs for injection
  - User enters college name: can they inject SQL? (parametrized queries stop this)
  - User uploads a CSV: can they break the parser? (error handling)
  - Write 3 tests for malicious inputs
- [ ] Design data retention policy
  - How long do we keep SoleOps transaction history? Why?
  - When does personally identifiable info get deleted?
  - Document this in code: `# User data older than 90 days is anonymized per privacy policy`
- [ ] Review Claude API calls for data leakage
  - Are you sending user data to Claude? (yes, sometimes)
  - Is it necessary? Is the user aware?
  - Document it clearly

**Resources:**  
- Tina's section: **Security & Privacy**
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/sql-syntax.html#SQL-SYNTAX-LEXICAL-RULES) (parametrized queries)
- [Privacy by Design](https://www.ipc.on.ca/privacy-by-design/)

**Daily Questions:**
- *"If this data was leaked, who would it harm and how?"*
- *"Am I storing this data because I need it, or out of habit?"*
- *"Is the user aware their data goes to Claude API?"*

---

### PHASE 5: Deployment & Containerization (2 weeks)
**Deliverable: Feature deployed to Proxmox homelab + documented**  
**PSS Feature: Financial Aid Appeal Generator + Analytics Dashboard**

**What you're learning:**
- Dockerizing applications (reproducibly running code anywhere)
- Environment management (dev ≠ prod ≠ testing)
- Monitoring and logging (knowing when things break)
- Zero-downtime deploys (launching features without disrupting users)

**Why this matters:**  
You have a homelab. You understand containers. Now make it *architecture*. This is also where you truly own infrastructure instead of depending on cloud vendors.

**Checkpoints:**
- [ ] Audit your current Docker setup
  - Can someone clone your repo and run `docker-compose up` and see PSS running locally? (they should be able to)
  - Are DB, app, and Nginx in separate containers? (they should be)
  - Are secrets passed via env vars, not hardcoded in Dockerfile? (they should be)
- [ ] Add a staging environment
  - Replica of prod, but on same homelab
  - Deploy features there first, test them, *then* prod
  - Document the deploy process (it should be a 1-line command)
- [ ] Set up monitoring for PSS
  - Basic metrics: response time, error rate, DB connection pool
  - Add to existing Grafana (monitoring/grafana/)
  - Alert if PSS down for >15 min (send Telegram)
- [ ] Document your deployment runbook
  - "How to deploy a new feature to production" (step by step)
  - "How to rollback if something breaks"
  - "How to migrate the database safely"
  - Even if you're the only engineer, future you will thank present you

**Resources:**  
- Tina's section: **Microservices & Containerization**
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Kubernetes for Simple Cases](https://www.digitalocean.com/community/tutorials/an-introduction-to-kubernetes) (you might not need it, but understand the concept)

**Daily Questions:**
- *"If I deleted my laptop, could I recreate this entire system from git + docker-compose?"*
- *"How would I roll back if I broke production?"*
- *"Could a new engineer deploy this alone without asking me questions?"*

---

## Agentic Engineering Integration

**Once you complete Phases 1–5, you move to the *orchestration layer*.**

You'll now write prompts for your overnight agent system like:

> Build me the Financial Aid Appeal Generator with these specs:
> - Users upload award letters (PDF)
> - Claude Vision extracts key data (school, grant amount, loan amount)
> - Claude drafts an appeal letter based on template + case
> - Letters are saved to PostgreSQL + exportable
> - Add tests for all PDF edge cases
> - Deploy to staging, run the test suite, summary to Telegram

**Your job becomes:**
- Writing clear requirements (understanding architecture)
- Reviewing AI-generated code (understanding fundamentals)
- Catching security/privacy issues (understanding risk)
- Testing edge cases (understanding systems)

This is exactly what Tina calls **agentic engineering**—you're not writing code, you're orchestrating agents who write code, but you *understand* what they're building.

---

## Learning Techniques (Apply Daily)

Based on Tina's tips, here's your actual practice:

### 1. **Use NotebookLM for Resources**
- Put a Tina transcript or textbook chapter into NotebookLM
- Ask it to summarize + generate questions
- Answer the questions using your PSS codebase
- This is faster than reading alone

### 2. **Ask Claude to Explain Code**
- When you see a pattern you don't understand, screenshot it
- Paste it into Claude: *"Explain this code pattern and when I'd use it"*
- Ask for analogies: *"Explain middleware using an analogy"*
- Ask for examples from PSS: *"Where in PSS could I use this?"*

### 3. **Test-Driven Learning**
- Before writing code, write the test
- The test definition forces you to think about design
- This is how professionals think—spec first, code second

### 4. **Code Review Every Week**
- Pick one file from PSS you wrote 2+ weeks ago
- Review it like a stranger would
- What would you change? Why? Write your changes as comments
- Then refactor it

### 5. **Document Your Decisions**
- When you choose architecture, write 3 sentences explaining *why*
- Future you (and AI agents) need to understand your thinking
- This also forces you to understand it deeply

---

## Measuring Progress — Tina's Checklist

By the end of 6 months, you should be able to answer YES to:

- [ ] **Coding Basics**: I can read Python code and understand what every line does
- [ ] **Architecture**: I can design a database schema and explain why it's structured that way
- [ ] **Version Control**: My commit history tells the story of my project
- [ ] **Security**: I actively check for injection vulnerabilities and secrets in code
- [ ] **Deployment**: I can deploy a feature without breaking production
- [ ] **Agentic Engineering**: I can give an AI agent a complex spec and review their code critically

---

## Building in Public — Transparency Check

**Values alignment (from your DARRIAN_VALUES_LAYER):**

This learning path serves **collective power, not individual extraction**:
- PSS features serve users with limited financial resources ✅
- You're becoming a better engineer so you can serve better ✅
- You're documenting the process so others at HBCUs can learn too ✅
- You're using open-source tools and homelab (ownership, not dependency) ✅
- You're thinking about security/privacy *from first principles* (serving users, not extracting) ✅

**Equity check**: Does this feature serve the user or extract from them?  
**When in doubt: Ask in Telegram summary.**

---

## Next Steps

1. **Start Phase 1 this week**: Review existing auth code, write tests
2. **Daily practice**: 1 code review, 1 Claude explanation, 1 architectural question
3. **Weekly check-in**: Sunday evening, reflect on what clicked
4. **Monthly demo**: Share what you built with community (college friends, HBCU networks)

---

## Resources on This Page
- **Fundamentals**: Real Python (pythonbasics.com), Python Docs
- **Architecture**: System Design Primer, PostgreSQL docs, Streamlit best practices
- **Testing**: pytest docs, Test-Driven Development by Kent Beck
- **Version Control**: Pro Git (free online), GitHub Docs
- **Security**: OWASP Top 10, PostgreSQL security
- **Deployment**: Docker docs, Kubernetes primer
- **Agentic Engineering**: Tina's video follow-ups (you have access)

---

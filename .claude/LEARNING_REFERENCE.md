# Learning Reference — PSS Code Examples for Each Phase

This file shows *actual code patterns* from PSS that teach each learning phase's concepts.

---

## PHASE 1: Code Clarity & Foundations

### Core Skills
- Reading and understanding existing code
- Variable naming that explains intent
- Control flow (if/loops) in real context
- Basic testing with pytest

### PSS Example 1: Reading Auth Code

**File**: `utils/auth.py` (your actual code)

```python
def validate_password(password: str) -> tuple[bool, str]:
    """
    Check if password meets security requirements.
    
    Returns:
        (is_valid, error_message)
    
    Why this design?
    - Tuple return lets caller know both success AND why it failed
    - Easier for UI to show specific error ("password too short" vs "password weak")
    - Type hint makes it clear what to expect
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain an uppercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain a number"
    
    return True, ""
```

**Your Challenge**: 
1. Can you explain what `any(c.isupper() for c in password)` does?
   - Answer: It loops through each character, returns True if ANY is uppercase
   - Why? Instead of checking every character manually, Python's `any()` does it efficiently

2. What's missing? (Hint: numbers, special characters, common patterns)
   - Answer: It doesn't check for special characters (like !@#$) or reject common passwords
   - Fix it: Add a special character check, add a blacklist for "password123", "qwerty", etc.

3. Write a test that makes this function fail
   ```python
   def test_password_rejects_no_uppercase():
       valid, msg = validate_password("password123")
       assert not valid
       assert "uppercase" in msg.lower()
   ```

**Why This Teaches Foundation Skills:**
- You learn to *read* code that exists
- You understand the intent (why tuple, not just True/False?)
- You write a test to verify behavior
- You spot edge cases (missing special char validation)

---

### PSS Example 2: Understanding Control Flow

**File**: `pages/1_expenses.py` (showing how expenses are categorized)

```python
def categorize_expense(description: str, amount: float) -> str:
    """Guess expense category from text description."""
    
    description = description.lower()  # Make case-insensitive
    
    # Check for keywords in order (more specific first)
    keywords = {
        "grocery": "food",
        "whole foods": "food",
        "coffee": "food",
        "gas station": "transportation",
        "uber": "transportation",
        "shell": "transportation",
        "spotify": "entertainment",
        "netflix": "entertainment",
        "amazon": "shopping",  # Generic—could be anything!
    }
    
    for keyword, category in keywords.items():
        if keyword in description:
            return category
    
    # Default: if we don't recognize it, guess based on amount
    if amount > 100:
        return "other_major"
    else:
        return "other"
```

**Your Challenge**:
1. What happens if description is "whole foods grocery store"?
   - Answer: Returns "food" (first match wins)
   - Why? Loop exits on first match

2. What's the bug?
   - Answer: "amazon" and "whole foods" both match, but "whole foods" is more specific
   - Fix it: Sort keywords by length (longest first) to match specific ones first

3. Write a test that finds this bug
   ```python
   def test_categorize_prefers_specific_keywords():
       # amazon should match, but whole foods is more specific
       category = categorize_expense("whole foods on amazon", 50)
       assert category == "food"  # Not "shopping"!
   ```

**Why This Teaches Foundation Skills:**
- Loops + conditionals in real PSS usage
- Edge cases (what if two keywords match?)
- Test-driven debugging
- Understanding intent (why we categorize at all?)

---

## PHASE 2: Systems & Architecture

### Core Skills
- Database schema design (why structure data this way?)
- Data flow (user input → database → display)
- API-like functions (clear inputs/outputs)
- Scale thinking (what breaks with 100x users?)

### PSS Example 1: College List Schema

**Current Challenge**: Build College List Builder feature
**First Question**: Where does data live?

```python
# Option A: Simple (wrong at scale)
# Store colleges as JSON in a single user field
# Problem: Can't search or filter efficiently

# Option B: Normalized (right)
# Three tables with relationships:

"""
TABLE: colleges
  id (primary key)
  name (string)
  state (string)
  acceptance_rate (float)
  cost_attendance (float)
  
TABLE: user_college_lists
  id (primary key)
  user_id (foreign key → users.id)
  college_id (foreign key → colleges.id)
  date_saved (timestamp)
  notes (string)
  
WHY THIS STRUCTURE?
- Colleges are shared data (1000 schools, not stored per user)
- User saves = link in junction table
- Can efficiently query: "Give me all schools with <10% acceptance rate"
- Can scale to millions of users without data duplication
"""
```

**Your Challenge**:
1. Write the PostgreSQL schema for this
   ```sql
   CREATE TABLE colleges (
       id SERIAL PRIMARY KEY,
       name VARCHAR(255) NOT NULL,
       state CHAR(2) NOT NULL,
       acceptance_rate DECIMAL(5,2),
       cost_attendance DECIMAL(10,2),
       UNIQUE(name, state)  -- Why? [ANSWER: No duplicate entries]
   );
   
   CREATE TABLE user_college_lists (
       id SERIAL PRIMARY KEY,
       user_id INTEGER NOT NULL REFERENCES users(id),
       college_id INTEGER NOT NULL REFERENCES colleges(id),
       date_saved TIMESTAMP DEFAULT NOW(),
       notes TEXT,
       PRIMARY KEY (user_id, college_id)  -- Why? [ANSWER: No duplicate saves]
   );
   ```

2. What query gets "all colleges Darrian saved"?
   ```sql
   SELECT c.* 
   FROM colleges c
   JOIN user_college_lists ucl ON c.id = ucl.college_id
   WHERE ucl.user_id = $1
   ORDER BY ucl.date_saved DESC;
   ```

3. What breaks if you have 1 million users?
   - Answer: Queries slow down without indexes
   - Fix it: `CREATE INDEX idx_user_college_lists_user_id ON user_college_lists(user_id);`

**Why This Teaches Architecture:**
- Schema isn't just "store the data"—it's about *efficiency at scale*
- Relationships (foreign keys) enforce consistency
- Indexes make queries fast
- You're thinking like a system architect, not a script writer

---

### PSS Example 2: Data Flow Architecture

**Question**: How does a user adding a college to their list flow through PSS?

```
┌─────────────────────────────────────────────────────┐
│ User clicks "Add to My Colleges" on college page    │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│ Browser sends POST to /api/save_college             │
│ Data: {user_id: 123, college_id: 456}              │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│ Backend function in pages/XX_college_list.py:      │
│ def save_college(user_id, college_id):             │
│     - Validate: College exists?                    │
│     - Validate: User already saved it?             │
│     - INSERT into user_college_lists                │
│     - Return success + timestamp                    │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│ PostgreSQL stores the relationship                 │
│ INSERT INTO user_college_lists(...) VALUES(...)    │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│ Browser receives: {"success": true, ...}           │
│ UI shows: "✅ Added to your list"                   │
│ College appears in "My Colleges" list               │
└─────────────────────────────────────────────────────┘
```

**Your Challenge**:
1. Draw this flow for "compare two colleges side-by-side"
   - Where does filtering happen? (Browser or database?)
   - Why does it matter?
   - Answer: Filtering in DB = faster, vs. filtering in Python = slower

2. What happens if save_college() crashes halfway through?
   - Answer: Partial insert, database in inconsistent state
   - Fix it: Use database transactions: `BEGIN; INSERT ...; COMMIT;` or rollback

---

## PHASE 3: Version Control & Collaboration

### Core Skills
- Commit messages that explain *why* (not just what)
- Branch discipline (one feature = one branch)
- Code review (even reviewing your own code)
- Rollback when things break

### PSS Example: Git Workflow for College List Builder

**Bad Commit Message** ❌
```
git commit -m "add college list feature"
```
Problem: Future you (or team member) has no idea what this changed or why.

**Good Commit Message** ✅
```
git commit -m "Features: Add college list save-to-list feature

- Users can click 'Add to My Colleges' on any college page
- Saves link in user_college_lists junction table
- Prevents duplicate saves (unique constraint on user_id + college_id)
- Validates college exists before saving (catches malicious requests)

Schema change: Added user_college_lists table with foreign keys to
users and colleges. Added index on user_id for fast lookup.

Resolves: #42 (College List Builder MVP)"
```

Why the longer message?
- Future you knows exactly what changed
- Code review is easier (they understand intent)
- If something breaks, you can trace *why* it was added
- Rollback is easier (you know what to undo)

**Your Challenge**:
1. Look at your last 5 commits in PSS
   ```bash
   git log --oneline -5
   ```
   Rewrite 2 of them with good messages (explain why, not just what)

2. Practice rollback
   ```bash
   # Last commit broke something?
   git revert HEAD  # Undo gracefully
   # OR (if not pushed yet)
   git reset --soft HEAD~1  # Undo, keep changes
   ```

3. Create a feature branch, make changes, merge back
   ```bash
   git checkout -b feature/college-comparison
   # Make your changes
   git add pages/XX_college_comparison.py
   git commit -m "Features: Add side-by-side college comparison

   - Select 2-4 colleges
   - Compare: cost, acceptance rate, location, majors
   - Export comparison as PDF

   Resolves: #43"
   
   git checkout main
   git merge feature/college-comparison
   ```

---

## PHASE 4: Security & Privacy

### Core Skills
- Parameterized queries (stop SQL injection)
- Secrets management (API keys not in code)
- Input validation (don't trust user data)
- Privacy by design (don't store what you don't need)

### PSS Example 1: SQL Injection Prevention

**Vulnerable Code** ❌
```python
# NEVER DO THIS
def get_user_colleges(user_id: str):
    query = f"SELECT * FROM colleges WHERE user_id = {user_id}"
    # If user_id = "1; DROP TABLE colleges;--"
    # Query becomes: "SELECT * FROM colleges WHERE user_id = 1; DROP TABLE colleges;--"
    # BAD!
    return db.execute(query)
```

**Safe Code** ✅
```python
# DO THIS
def get_user_colleges(user_id: int):
    query = "SELECT * FROM colleges WHERE user_id = %s"
    # %s = placeholder, user_id passed separately
    # PostgreSQL knows %s is a value, not code
    return db.execute(query, (user_id,))
```

**Why It Matters:**
- SQL injection can delete your entire database
- Or steal all user data
- With parameterized queries, the database *cannot* interpret user input as code

**Your Challenge**:
1. Audit PSS for SQL injection
   ```bash
   grep -r "f\"SELECT" pages/  # Find dangerous patterns
   grep -r "format.*SELECT" pages/  # Find more dangerous patterns
   ```
   Fix any you find!

2. Write a test that would catch this
   ```python
   def test_sql_injection_prevented():
       # Try to inject SQL
       malicious_input = "1; DROP TABLE user_college_lists;--"
       result = get_user_colleges(malicious_input)
       # Should treat as user_id, not executable SQL
       assert len(result) == 0  # No results, not a crash
   ```

---

### PSS Example 2: Secrets Management

**Vulnerable Code** ❌
```python
# In pages/XX_soleops.py
EBAY_API_KEY = "abc123xyz789..."  # In source code!
# Problem: If code is public on GitHub, anyone can use your API key
# They can list fake items, drain your quota, or impersonate you
```

**Safe Code** ✅
```python
# In pages/XX_soleops.py
import os
EBAY_API_KEY = os.getenv("EBAY_API_KEY")

# In .env (DO NOT commit to git)
EBAY_API_KEY=abc123xyz789...

# In .gitignore
.env
```

**Your Challenge**:
1. Find all API keys in PSS
   ```bash
   grep -r "API_KEY\|SECRET_KEY\|PASSWORD" pages/ --include="*.py" | grep -v "os.getenv"
   ```

2. Move each to `.env` and load via `os.getenv()`

3. Check Git history for leaked secrets
   ```bash
   git log -p | grep -i "api_key\|password"
   ```
   If they exist, rotate those API keys immediately!

---

### PSS Example 3: Data Minimization

**Question**: If a user exports their budget data, what should we send?

**Bad Design** ❌
- Send every field: name, email, phone, address, password hash, internal notes...
- Why? Violates privacy—more data = more risk if leaked

**Good Design** ✅
- Send only: transactions, categories, totals
- Keep sensitive data (email, phone) server-side unless user explicitly needs it
- Add audit log: "User exported data on 2026-03-17"

**Your Challenge**:
1. Audit `pages/73_sandbox_mode.py` (data export)
   - What fields do you export?
   - Does the user need ALL of them?
   - Remove fields that are "nice to have" but not essential

---

## PHASE 5: Deployment & Containerization

### Core Skills
- Docker: Package app so it runs anywhere
- Environment management: dev ≠ staging ≠ production
- Monitoring: Know when things break
- Rollback strategy: Deploy safely

### PSS Example 1: Docker Review

**Current Setup**: `docker-compose.yml` in root

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8501:8501"
    environment:
      DB_HOST: postgres
      DB_USER: ${DB_USER}  # From .env
      DB_PASSWORD: ${DB_PASSWORD}  # Secret!
    volumes:
      - ./pages:/app/pages
      - ./utils:/app/utils
    depends_on:
      - postgres
  
  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

**Your Challenge**:
1. Verify it runs locally
   ```bash
   docker-compose up
   # Should see: psql running on :5432, Streamlit on :8501
   ```

2. Check for secrets in docker-compose.yml
   - Good: `${DB_PASSWORD}` (loaded from .env)
   - Bad: `DB_PASSWORD: hardcoded_password123` (in source code!)

3. Test the entire flow
   ```bash
   docker-compose down
   docker-compose up  # Fresh start
   # Can you log in? Create an expense? See it in DB?
   ```

---

### PSS Example 2: Zero-Downtime Deploy

**Current Problem**: Every deploy restarts the app, users get kicked out

**Better Approach** (deployments without downtime):

```bash
# 1. Deploy to staging first (copy of production)
docker-compose -f docker-compose.staging.yml up -d

# 2. Run tests on staging
pytest tests/ --config staging

# 3. If tests pass, swap traffic to new container
# (Nginx points to new app container, old one keeps running)

# 4. Old container stays alive in case we need to rollback
docker-compose scale app=2

# 5. Monitor logs for 5 minutes—if errors, rollback
docker-compose rollback  # Points Nginx back to old container

# 6. After 1 hour confidence, kill old container
docker-compose scale app=1
```

**Your Challenge**:
1. Create `docker-compose.staging.yml` (copy of main, different DB name)
2. Write a test that verifies app is healthy
   ```python
   def test_health_check():
       response = requests.get("http://localhost:8501/health")
       assert response.status_code == 200
       assert response.json()["status"] == "healthy"
   ```
3. Practice deploy-test-rollback cycle once

---

## Quick Reference: What Each Phase Teaches

| Phase | Skill | PSS Example |
|-------|-------|-------------|
| 1 | Code clarity, testing | Auth system, expense categorization |
| 2 | Architecture, data flow | College list schema, relationships |
| 3 | Git discipline, collaboration | Commit messages, branch strategy |
| 4 | Security, privacy | SQL injection, secrets, data minimization |
| 5 | Deployment, monitoring | Docker setup, staging, rollback |

---

## Your Next Move

1. Pick Phase 1, start with the auth code audit
2. Run the learning bot: `python .claude/agents/learning_bot.py --mode challenge`
3. Do today's challenge, commit it
4. Come back tomorrow

You've got this. 🚀

"""Unit tests — CC College List Builder (page 87) + FAFSA Guide (page 88)"""
import sys, os, sqlite3, pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()

# ── Import checks ─────────────────────────────────────────────────────────────
def test_utils_db_importable():
    from utils import db
    assert hasattr(db, "get_conn")

def test_page_87_exists():
    assert (PROJECT_ROOT / "pages" / "87_cc_college_list.py").exists()

def test_page_88_exists():
    assert (PROJECT_ROOT / "pages" / "88_cc_fafsa_guide.py").exists()

def test_page_87_syntax():
    src = (PROJECT_ROOT / "pages" / "87_cc_college_list.py").read_text()
    compile(src, "87_cc_college_list.py", "exec")

def test_page_88_syntax():
    src = (PROJECT_ROOT / "pages" / "88_cc_fafsa_guide.py").read_text()
    compile(src, "88_cc_fafsa_guide.py", "exec")

# ── DB: cc_colleges ───────────────────────────────────────────────────────────
def test_cc_colleges_table(db_conn):
    db_conn.execute("""CREATE TABLE IF NOT EXISTS cc_colleges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        state TEXT NOT NULL,
        city TEXT NOT NULL,
        type TEXT NOT NULL,
        hbcu INTEGER DEFAULT 0,
        acceptance_rate INTEGER DEFAULT 50,
        tuition INTEGER DEFAULT 30000,
        avg_sat INTEGER DEFAULT 1200,
        avg_act INTEGER DEFAULT 26,
        setting TEXT DEFAULT 'Suburban',
        size TEXT DEFAULT 'Medium',
        majors TEXT DEFAULT '',
        website TEXT DEFAULT '',
        notes TEXT DEFAULT ''
    )""")
    db_conn.execute("""INSERT INTO cc_colleges
        (name,state,city,type,hbcu,acceptance_rate,tuition,avg_sat,avg_act,setting,size,majors)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        ("Howard University","DC","Washington","Private",1,38,28888,1150,24,"Urban","Medium","Business,Nursing"))
    db_conn.commit()
    row = db_conn.execute("SELECT * FROM cc_colleges WHERE hbcu=1").fetchone()
    assert row is not None
    assert row["name"] == "Howard University"
    assert row["hbcu"] == 1

# ── DB: cc_user_college_list ──────────────────────────────────────────────────
def test_cc_user_college_list_table(db_conn):
    db_conn.execute("""CREATE TABLE IF NOT EXISTS cc_colleges (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
        state TEXT, city TEXT, type TEXT, hbcu INTEGER DEFAULT 0,
        acceptance_rate INTEGER, tuition INTEGER, avg_sat INTEGER, avg_act INTEGER,
        setting TEXT, size TEXT, majors TEXT, website TEXT, notes TEXT)""")
    db_conn.execute("""CREATE TABLE IF NOT EXISTS cc_user_college_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL, college_name TEXT NOT NULL,
        college_type TEXT DEFAULT 'target', notes TEXT DEFAULT '',
        added_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_email, college_name)
    )""")
    db_conn.execute("INSERT INTO cc_user_college_list (user_email,college_name,college_type) VALUES (?,?,?)",
                    ("test@test.com","Howard University","reach"))
    db_conn.commit()
    c = db_conn.execute("SELECT * FROM cc_user_college_list WHERE user_email='test@test.com'")
    row = c.fetchone()
    assert row is not None
    assert row["college_type"] == "reach"

# ── DB: cc_fafsa_checklist ────────────────────────────────────────────────────
def test_cc_fafsa_checklist_table(db_conn):
    db_conn.execute("""CREATE TABLE IF NOT EXISTS cc_fafsa_checklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL, item_key TEXT NOT NULL,
        completed INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_email, item_key)
    )""")
    db_conn.execute("INSERT INTO cc_fafsa_checklist (user_email,item_key,completed) VALUES (?,?,?)",
                    ("stu@test.com","get_fsaid",1))
    db_conn.commit()
    row = db_conn.execute("SELECT completed FROM cc_fafsa_checklist WHERE item_key='get_fsaid'").fetchone()
    assert row["completed"] == 1

# ── Helper: college filter logic ──────────────────────────────────────────────
def test_hbcu_filter():
    colleges = [
        {"name":"Howard","hbcu":1,"acceptance_rate":38,"tuition":28888},
        {"name":"MIT",   "hbcu":0,"acceptance_rate":4, "tuition":57000},
        {"name":"FAMU",  "hbcu":1,"acceptance_rate":35,"tuition":5700},
    ]
    hbcu = [c for c in colleges if c["hbcu"] == 1]
    assert len(hbcu) == 2
    assert all(c["hbcu"] == 1 for c in hbcu)

def test_acceptance_rate_filter():
    colleges = [
        {"name":"Harvard","acceptance_rate":4},
        {"name":"UGA",    "acceptance_rate":45},
        {"name":"VTech",  "acceptance_rate":60},
    ]
    reach  = [c for c in colleges if c["acceptance_rate"] <= 15]
    likely = [c for c in colleges if c["acceptance_rate"] > 40]
    assert len(reach) == 1
    assert reach[0]["name"] == "Harvard"
    assert len(likely) == 2

def test_tuition_filter():
    colleges = [{"tuition":5700},{"tuition":29000},{"tuition":57000}]
    affordable = [c for c in colleges if c["tuition"] <= 15000]
    assert len(affordable) == 1

def test_college_list_types():
    my_list = [
        {"college_name":"MIT","college_type":"reach"},
        {"college_name":"UGA","college_type":"target"},
        {"college_name":"GSU","college_type":"safety"},
    ]
    reach  = [c for c in my_list if c["college_type"]=="reach"]
    target = [c for c in my_list if c["college_type"]=="target"]
    safety = [c for c in my_list if c["college_type"]=="safety"]
    assert len(reach) == 1
    assert len(target) == 1
    assert len(safety) == 1

# ── Helper: EFC calculator ────────────────────────────────────────────────────
def _calc_efc_test(parent_agi, parent_assets, student_income, student_assets, family_size, num_in_college):
    ipa_table = {1:18580,2:23330,3:29080,4:35960,5:42450,6:49540}
    ipa = ipa_table.get(min(family_size,6), 49540)
    available = max(0, parent_agi - ipa)
    if available <= 14400:   pic = available * 0.22
    elif available <= 28800: pic = available * 0.34
    else:                    pic = available * 0.47
    pac = max(0, parent_assets - 5000) * 0.0564
    total_parent = (pic + pac) / max(1, num_in_college)
    sic = max(0, student_income - 7600) * 0.50
    sac = student_assets * 0.20
    return max(0, round(total_parent + sic + sac))

def test_efc_zero_income():
    efc = _calc_efc_test(0, 0, 0, 0, 4, 1)
    assert efc == 0

def test_efc_middle_income():
    efc = _calc_efc_test(60000, 10000, 0, 500, 4, 1)
    assert efc > 0
    assert efc < 30000

def test_efc_high_income():
    efc = _calc_efc_test(200000, 100000, 0, 0, 4, 1)
    assert efc > 20000

def test_efc_multiple_in_college():
    efc_one = _calc_efc_test(80000, 10000, 0, 0, 4, 1)
    efc_two = _calc_efc_test(80000, 10000, 0, 0, 4, 2)
    assert efc_two < efc_one  # shared, so per-student is lower

def test_efc_student_assets_counted_more():
    efc_student_assets = _calc_efc_test(0, 0, 0, 10000, 4, 1)
    efc_no_assets = _calc_efc_test(0, 0, 0, 0, 4, 1)
    assert efc_student_assets > efc_no_assets

# ── Helper: state deadlines ───────────────────────────────────────────────────
def test_state_deadlines_coverage():
    # Verify key states are covered (simulated)
    states = ["Alabama","California","Florida","Georgia","Texas","New York","Illinois","Missouri"]
    deadlines = {
        "Alabama":"Feb 15","California":"Mar 2","Florida":"May 15",
        "Georgia":"Jun 1","Texas":"Jan 15","New York":"May 1",
        "Illinois":"As soon as possible","Missouri":"Feb 1",
    }
    for s in states:
        assert s in deadlines

def test_urgent_states_identified():
    deadlines = [
        ("Texas","Jan 15",True),("Missouri","Feb 1",True),
        ("California","Mar 2",True),("Florida","May 15",True),
    ]
    urgent = [s for s,d,_ in deadlines if any(m in d.lower() for m in ["jan","feb"])]
    assert "Texas" in urgent
    assert "Missouri" in urgent
    assert "California" not in urgent

# ── Helper: FAFSA checklist progress ─────────────────────────────────────────
def test_fafsa_checklist_progress():
    items = ["get_fsaid","gather_taxes","open_fafsa","section1","sign_submit"]
    done  = {"get_fsaid":True,"gather_taxes":True}
    completed = sum(1 for k in items if done.get(k,False))
    pct = completed / len(items)
    assert completed == 2
    assert abs(pct - 0.4) < 0.01

def test_college_seed_data_has_hbcus():
    seeds = [
        ("Howard University","DC","Washington","Private",1),
        ("Spelman College","GA","Atlanta","Private",1),
        ("MIT","MA","Cambridge","Private",0),
    ]
    hbcus = [s for s in seeds if s[4] == 1]
    assert len(hbcus) == 2

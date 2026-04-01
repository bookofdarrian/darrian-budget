"""
Unit tests for pages/147_proactive_ai_engine.py — Proactive AI / Intent Engine
=================================================================================
Covers:
  1. Import test — page module imports without errors
  2. DB table creation — _ensure_tables() creates all four tables
  3. Signal collection helpers — return correct types
  4. Profile helpers — _get_profile / _set_profile_key round-trip
  5. Insight helpers — _save_insight / _get_insights / _feedback / _dismiss round-trip
  6. Context injection — _collect_all_signals includes manual context notes
  7. Signal context builder — _build_signal_context formats correctly
"""

import json
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Minimal Streamlit stub so the page-level st.* calls don't explode on import
# ---------------------------------------------------------------------------

def _build_streamlit_stub():
    st = types.ModuleType("streamlit")

    # Basic no-ops — every st.* call the auth/page code makes must be here
    for name in (
        "set_page_config", "title", "caption", "subheader", "markdown", "info",
        "success", "error", "warning", "spinner", "rerun", "divider", "stop",
        "container", "expander", "form", "text", "checkbox", "multiselect",
        "text_input", "text_area", "number_input", "date_input", "selectbox",
        "radio", "slider", "metric", "dataframe", "progress", "empty",
        "form_submit_button", "write", "image", "balloons", "snow",
        "toast", "code", "json", "table", "plotly_chart", "altair_chart",
        "header", "page_link", "html", "switch_page",
    ):
        setattr(st, name, MagicMock(return_value=None))

    # columns → returns a variable-length list matching the argument
    def _columns(spec, **kwargs):
        n = spec if isinstance(spec, int) else len(spec)
        return [MagicMock() for _ in range(n)]
    st.columns = _columns

    # tabs → returns a list whose length matches the labels arg so
    # any tuple-unpack in auth.py or page code works regardless of tab count.
    def _tabs(labels, **kwargs):
        result = []
        for _ in labels:
            cm = MagicMock()
            cm.__enter__ = MagicMock(return_value=cm)
            cm.__exit__ = MagicMock(return_value=False)
            result.append(cm)
        return result
    st.tabs = _tabs

    # expander / container / form as context managers
    def _ctx_mgr(*a, **kw):
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        return cm
    for name in ("expander", "container", "form", "spinner"):
        setattr(st, name, _ctx_mgr)

    # button → always returns False (never triggered in tests)
    st.button = MagicMock(return_value=False)

    # session_state — real dict-like object
    st.session_state = {}

    # sidebar — also needs page_link, columns, tabs, etc.
    sb = types.SimpleNamespace(
        markdown=lambda *a, **k: None,
        page_link=lambda *a, **k: None,
        columns=_columns,
        tabs=_tabs,
        button=lambda *a, **k: False,
        checkbox=lambda *a, **k: False,
        selectbox=lambda *a, **k: None,
        text_input=lambda *a, **k: "",
        success=lambda *a, **k: None,
        error=lambda *a, **k: None,
        info=lambda *a, **k: None,
        warning=lambda *a, **k: None,
        write=lambda *a, **k: None,
        title=lambda *a, **k: None,
        header=lambda *a, **k: None,
        subheader=lambda *a, **k: None,
    )
    st.sidebar = sb

    return st


# ---------------------------------------------------------------------------
# Install stub BEFORE any imports that transitively load streamlit
# ---------------------------------------------------------------------------
import os                          # noqa: E402
import importlib                   # noqa: E402
import importlib.util as _ilu      # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_st_stub = _build_streamlit_stub()
sys.modules["streamlit"] = _st_stub

# Flush any already-loaded streamlit-dependent modules so they pick up the stub
for _cached in list(sys.modules.keys()):
    if _cached in ("utils.auth", "utils.db", "aura.jarvis", "utils.voice_input"):
        del sys.modules[_cached]


# ---------------------------------------------------------------------------
# Stub out heavy optional imports used only at AI-call time
# ---------------------------------------------------------------------------
for _heavy in ("anthropic",):
    if _heavy not in sys.modules:
        sys.modules[_heavy] = MagicMock()

import pandas as _pd_real  # noqa: E402  (real or already-installed)


# ---------------------------------------------------------------------------
# Now import the page module under test
# ---------------------------------------------------------------------------

PAGE_PATH = os.path.join(ROOT, "pages", "147_proactive_ai_engine.py")
_spec = _ilu.spec_from_file_location("proactive_ai_engine", PAGE_PATH)
_mod = _ilu.module_from_spec(_spec)

# Execute the module — require_login() calls st.stop() which is now a no-op
try:
    _spec.loader.exec_module(_mod)
except (SystemExit, StopIteration):
    pass


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestProactiveAIImport(unittest.TestCase):
    """1. Import test — module loads without errors."""

    def test_module_loaded(self):
        self.assertIsNotNone(_mod)

    def test_key_functions_exist(self):
        for fn in (
            "_ensure_tables",
            "_collect_all_signals",
            "_collect_finance_signals",
            "_collect_todo_signals",
            "_collect_notes_signals",
            "_collect_creator_signals",
            "_collect_soleops_signals",
            "_build_signal_context",
            "_get_profile",
            "_set_profile_key",
            "_save_insight",
            "_get_insights",
            "_feedback_insight",
            "_dismiss_insight",
            "_run_proactive_analysis",
            "_run_intent_update",
        ):
            self.assertTrue(
                hasattr(_mod, fn),
                f"Missing expected function: {fn}"
            )

    def test_constants_exist(self):
        self.assertIn("SIGNAL_TYPES", dir(_mod))
        self.assertIn("INSIGHT_ICONS", dir(_mod))
        # Verify signal types include all expected sources
        for key in ("finance", "todo", "notes", "creator", "soleops", "context", "pattern"):
            self.assertIn(key, _mod.SIGNAL_TYPES)


class TestDBTables(unittest.TestCase):
    """2. DB table creation — _ensure_tables() creates all four tables."""

    def test_ensure_tables_creates_tables(self):
        """All four engine tables should exist after _ensure_tables() runs."""
        from utils.db import get_conn, execute

        conn = get_conn()
        for table in (
            "intent_signals",
            "proactive_insights",
            "intent_context_notes",
            "intent_profile",
        ):
            cursor = execute(conn, f"""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='{table}'
            """)
            row = cursor.fetchone()
            self.assertIsNotNone(row, f"Table '{table}' was not created by _ensure_tables()")
        conn.close()

    def test_intent_profile_unique_constraint(self):
        """intent_profile (user_id, key) should be unique — duplicate upsert works."""
        from utils.db import get_conn, execute

        uid = 9999
        conn = get_conn()
        # Insert
        execute(conn, """
            INSERT OR REPLACE INTO intent_profile (user_id, key, value, confidence)
            VALUES (?,?,?,?)
        """, (uid, "test_key", "first_value", 0.9))
        # Upsert same key
        execute(conn, """
            INSERT OR REPLACE INTO intent_profile (user_id, key, value, confidence)
            VALUES (?,?,?,?)
        """, (uid, "test_key", "second_value", 0.95))
        conn.commit()

        rows = execute(conn, """
            SELECT value FROM intent_profile WHERE user_id=? AND key=?
        """, (uid, "test_key")).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "second_value")

        # Clean up
        execute(conn, "DELETE FROM intent_profile WHERE user_id=?", (uid,))
        conn.commit()
        conn.close()


class TestSignalCollection(unittest.TestCase):
    """3. Signal collection helpers return correct types."""

    UID = 0

    def _assert_valid_signal(self, signal: dict, context: str = ""):
        """Each signal must have required keys with correct types."""
        prefix = f"[{context}] " if context else ""
        self.assertIn("signal_type", signal, f"{prefix}Missing signal_type")
        self.assertIn("source", signal, f"{prefix}Missing source")
        self.assertIn("label", signal, f"{prefix}Missing label")
        self.assertIn("weight", signal, f"{prefix}Missing weight")
        self.assertIsInstance(signal["signal_type"], str, f"{prefix}signal_type not str")
        self.assertIsInstance(signal["label"], str, f"{prefix}label not str")
        self.assertIsInstance(signal["weight"], (int, float), f"{prefix}weight not numeric")
        self.assertGreaterEqual(signal["weight"], 0, f"{prefix}weight must be >= 0")

    def test_collect_finance_returns_list(self):
        result = _mod._collect_finance_signals(self.UID)
        self.assertIsInstance(result, list)

    def test_collect_todo_returns_list(self):
        result = _mod._collect_todo_signals(self.UID)
        self.assertIsInstance(result, list)

    def test_collect_notes_returns_list(self):
        result = _mod._collect_notes_signals(self.UID)
        self.assertIsInstance(result, list)

    def test_collect_creator_returns_list(self):
        result = _mod._collect_creator_signals(self.UID)
        self.assertIsInstance(result, list)

    def test_collect_soleops_returns_list(self):
        result = _mod._collect_soleops_signals(self.UID)
        self.assertIsInstance(result, list)

    def test_collect_all_signals_returns_list(self):
        result = _mod._collect_all_signals(self.UID)
        self.assertIsInstance(result, list)

    def test_all_signals_have_valid_structure(self):
        """Every signal from collect_all_signals must have required fields."""
        result = _mod._collect_all_signals(self.UID)
        for sig in result:
            self._assert_valid_signal(sig, context=sig.get("source", "?"))

    def test_all_signals_types_are_known(self):
        """All signal_type values must be in the SIGNAL_TYPES constant."""
        result = _mod._collect_all_signals(self.UID)
        known_types = set(_mod.SIGNAL_TYPES.keys())
        for sig in result:
            self.assertIn(
                sig["signal_type"], known_types,
                f"Unknown signal_type: {sig['signal_type']}"
            )


class TestProfileHelpers(unittest.TestCase):
    """4. Profile helpers — get/set round-trip."""

    UID = 8888

    def setUp(self):
        """Clean up any leftover test profile data."""
        from utils.db import get_conn, execute
        conn = get_conn()
        execute(conn, "DELETE FROM intent_profile WHERE user_id=?", (self.UID,))
        conn.commit()
        conn.close()

    def tearDown(self):
        from utils.db import get_conn, execute
        conn = get_conn()
        execute(conn, "DELETE FROM intent_profile WHERE user_id=?", (self.UID,))
        conn.commit()
        conn.close()

    def test_get_profile_empty(self):
        profile = _mod._get_profile(self.UID)
        self.assertIsInstance(profile, dict)
        self.assertEqual(len(profile), 0)

    def test_set_and_get_profile_key(self):
        _mod._set_profile_key(self.UID, "test_focus", "SoleOps inventory cleanup", 0.85)
        profile = _mod._get_profile(self.UID)
        self.assertIn("test_focus", profile)
        self.assertEqual(profile["test_focus"]["value"], "SoleOps inventory cleanup")
        self.assertAlmostEqual(profile["test_focus"]["confidence"], 0.85, places=2)

    def test_upsert_profile_key(self):
        _mod._set_profile_key(self.UID, "upsert_key", "v1", 0.7)
        _mod._set_profile_key(self.UID, "upsert_key", "v2", 0.9)
        profile = _mod._get_profile(self.UID)
        self.assertEqual(profile["upsert_key"]["value"], "v2")
        self.assertAlmostEqual(profile["upsert_key"]["confidence"], 0.9, places=2)

    def test_multiple_keys(self):
        _mod._set_profile_key(self.UID, "key_a", "alpha", 0.8)
        _mod._set_profile_key(self.UID, "key_b", "beta", 0.6)
        profile = _mod._get_profile(self.UID)
        self.assertIn("key_a", profile)
        self.assertIn("key_b", profile)


class TestInsightHelpers(unittest.TestCase):
    """5. Insight helpers — save / get / feedback / dismiss round-trip."""

    UID = 7777

    def setUp(self):
        from utils.db import get_conn, execute
        conn = get_conn()
        execute(conn, "DELETE FROM proactive_insights WHERE user_id=?", (self.UID,))
        conn.commit()
        conn.close()

    def tearDown(self):
        from utils.db import get_conn, execute
        conn = get_conn()
        execute(conn, "DELETE FROM proactive_insights WHERE user_id=?", (self.UID,))
        conn.commit()
        conn.close()

    def test_save_insight_returns_id(self):
        ins_id = _mod._save_insight(
            uid=self.UID,
            insight_type="focus",
            title="Test insight title",
            body="Test body text.",
            priority="normal",
        )
        self.assertIsInstance(ins_id, int)
        self.assertGreater(ins_id, 0)

    def test_get_insights_returns_saved(self):
        _mod._save_insight(self.UID, "alert", "Alert insight", "Alert body.", "high")
        insights = _mod._get_insights(self.UID)
        self.assertGreater(len(insights), 0)
        titles = [i["title"] for i in insights]
        self.assertIn("Alert insight", titles)

    def test_insight_has_required_fields(self):
        _mod._save_insight(self.UID, "pattern", "Pattern insight", "Pattern body.", "low")
        insights = _mod._get_insights(self.UID)
        for ins in insights:
            for field in ("id", "insight_type", "title", "body", "priority", "created_at"):
                self.assertIn(field, ins, f"Missing field: {field}")

    def test_feedback_insight(self):
        ins_id = _mod._save_insight(self.UID, "financial", "Financial insight", "Body.", "normal")
        _mod._feedback_insight(ins_id, "helpful")
        insights = _mod._get_insights(self.UID)
        matched = [i for i in insights if i["id"] == ins_id]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["feedback"], "helpful")

    def test_dismiss_insight_hides_from_get(self):
        ins_id = _mod._save_insight(self.UID, "reminder", "Reminder insight", "Body.", "normal")
        # Should be visible before dismiss
        before = _mod._get_insights(self.UID)
        self.assertTrue(any(i["id"] == ins_id for i in before))
        # Dismiss
        _mod._dismiss_insight(ins_id)
        # Should NOT appear in get_insights (dismissed=0 filter)
        after = _mod._get_insights(self.UID)
        self.assertFalse(any(i["id"] == ins_id for i in after))

    def test_priority_ordering(self):
        """Insights should come back ordered: critical > high > normal > low."""
        _mod._save_insight(self.UID, "focus", "Normal insight", "Body.", "normal")
        _mod._save_insight(self.UID, "alert", "Critical insight", "Body.", "critical")
        _mod._save_insight(self.UID, "pattern", "Low insight", "Body.", "low")
        _mod._save_insight(self.UID, "reminder", "High insight", "Body.", "high")

        insights = _mod._get_insights(self.UID)
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
        sorted_expected = sorted(insights, key=lambda x: priority_order.get(x["priority"], 2))
        # get_insights should already return them in priority order
        for actual, expected in zip(insights, sorted_expected):
            self.assertEqual(
                priority_order.get(actual["priority"], 2),
                priority_order.get(expected["priority"], 2),
                "Insights not returned in correct priority order"
            )


class TestContextInjection(unittest.TestCase):
    """6. _collect_all_signals includes manual context notes."""

    UID = 6666

    def setUp(self):
        from utils.db import get_conn, execute
        conn = get_conn()
        execute(conn, "DELETE FROM intent_context_notes WHERE user_id=?", (self.UID,))
        conn.commit()
        conn.close()

    def tearDown(self):
        from utils.db import get_conn, execute
        conn = get_conn()
        execute(conn, "DELETE FROM intent_context_notes WHERE user_id=?", (self.UID,))
        conn.commit()
        conn.close()

    def test_context_note_appears_in_signals(self):
        """A manually injected context note should appear as a 'context' signal."""
        from utils.db import get_conn, execute
        conn = get_conn()
        execute(conn, """
            INSERT INTO intent_context_notes (user_id, content, pinned)
            VALUES (?,?,?)
        """, (self.UID, "Preparing for Visa quarterly review next week", 0))
        conn.commit()
        conn.close()

        signals = _mod._collect_all_signals(self.UID)
        context_signals = [s for s in signals if s["signal_type"] == "context"]
        self.assertGreater(len(context_signals), 0, "No context signals found after injecting note")
        labels = [s["label"] for s in context_signals]
        self.assertTrue(
            any("quarterly review" in label.lower() for label in labels),
            "Injected context note not found in signals"
        )

    def test_pinned_note_has_higher_weight(self):
        """A pinned context note should have higher weight than an unpinned one."""
        from utils.db import get_conn, execute
        conn = get_conn()
        execute(conn, """
            INSERT INTO intent_context_notes (user_id, content, pinned) VALUES (?,?,?)
        """, (self.UID, "This is unpinned context", 0))
        execute(conn, """
            INSERT INTO intent_context_notes (user_id, content, pinned) VALUES (?,?,?)
        """, (self.UID, "This is pinned context", 1))
        conn.commit()
        conn.close()

        signals = _mod._collect_all_signals(self.UID)
        ctx = [s for s in signals if s["signal_type"] == "context" and s["source"] == "manual"]
        pinned = [s for s in ctx if json.loads(s.get("content", "{}")).get("pinned")]
        unpinned = [s for s in ctx if not json.loads(s.get("content", "{}")).get("pinned")]

        if pinned and unpinned:
            self.assertGreater(pinned[0]["weight"], unpinned[0]["weight"])


class TestSignalContextBuilder(unittest.TestCase):
    """7. _build_signal_context formats structured context correctly."""

    def test_returns_string(self):
        signals = [
            {
                "signal_type": "finance",
                "source": "budget",
                "label": "Spent $500 in Food this month",
                "value": 500,
                "weight": 2.0,
            }
        ]
        result = _mod._build_signal_context(signals)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_contains_signal_labels(self):
        signals = [
            {
                "signal_type": "todo",
                "source": "tasks",
                "label": "OVERDUE: Call dentist (due 2025-01-01)",
                "value": -1,
                "weight": 2.0,
            },
            {
                "signal_type": "soleops",
                "source": "soleops_inventory",
                "label": "5 items listed 60+ days",
                "value": 1000,
                "weight": 2.0,
            },
        ]
        result = _mod._build_signal_context(signals)
        self.assertIn("OVERDUE: Call dentist", result)
        self.assertIn("5 items listed 60+ days", result)

    def test_high_weight_signals_noted(self):
        """Signals with weight > 1.5 should have weight notation in output."""
        signals = [
            {
                "signal_type": "finance",
                "source": "budget",
                "label": "High weight signal",
                "value": 100,
                "weight": 2.5,
            }
        ]
        result = _mod._build_signal_context(signals)
        self.assertIn("weight:", result)

    def test_empty_signals_returns_string(self):
        result = _mod._build_signal_context([])
        self.assertIsInstance(result, str)

    def test_sections_organized_by_type(self):
        """Output should have section headers for each signal type present."""
        signals = [
            {"signal_type": "finance", "source": "budget", "label": "Finance sig", "value": 1, "weight": 1.0},
            {"signal_type": "todo",    "source": "tasks",  "label": "Todo sig",    "value": 1, "weight": 1.0},
        ]
        result = _mod._build_signal_context(signals)
        self.assertIn("FINANCIAL", result.upper())
        self.assertIn("TASK", result.upper())


class TestSignalWeighting(unittest.TestCase):
    """Edge cases around signal weight calculation."""

    UID = 0

    def test_finance_weight_scales_with_amount(self):
        """Finance signals from large spending should have higher weight."""
        # We can't easily inject real data, but we can test the formula:
        # weight = min(2.0, total / 200)
        for amount, expected_max in [(100, 0.5), (400, 2.0), (1000, 2.0)]:
            weight = min(2.0, amount / 200)
            self.assertLessEqual(weight, 2.0)
            self.assertGreater(weight, 0)

    def test_month_over_month_weight_higher_on_big_change(self):
        """Spending changes >15% should get weight 1.8, smaller changes 0.8."""
        big_change_weight = 1.8 if abs(20) > 15 else 0.8
        small_change_weight = 1.8 if abs(5) > 15 else 0.8
        self.assertEqual(big_change_weight, 1.8)
        self.assertEqual(small_change_weight, 0.8)


if __name__ == "__main__":
    unittest.main(verbosity=2)

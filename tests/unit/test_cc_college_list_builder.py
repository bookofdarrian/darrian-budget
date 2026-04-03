import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGE_PATH = os.path.join(ROOT, "pages/153_cc_college_list_builder.py")


def _source() -> str:
    with open(PAGE_PATH, encoding="utf-8") as f:
        return f.read()


def test_page_file_exists_and_syntax():
    assert os.path.exists(PAGE_PATH), f"Missing: {PAGE_PATH}"
    src = _source()
    assert len(src) > 500
    compile(src, PAGE_PATH, "exec")


def test_required_patterns():
    src = _source()
    assert "def _ensure_tables" in src
    assert "get_conn" in src
    assert "require_login" in src
    assert "render_sidebar_brand" in src
    assert "init_db" in src
    assert "st.set_page_config" in src


def test_no_hardcoded_secrets():
    src = _source()
    forbidden = ["sk-ant-", "password=", "secret=", "Bearer ", "hardcoded"]
    for token in forbidden:
        assert token not in src

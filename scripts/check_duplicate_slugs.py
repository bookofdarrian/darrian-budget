#!/usr/bin/env python3
"""
scripts/check_duplicate_slugs.py
=================================
Pre-commit guard: detect duplicate Streamlit page URL slugs before commit.

Streamlit derives a URL slug from the filename by stripping the leading
digit-prefix and .py extension (e.g. "91_cc_interview_prep_ai.py" → slug
"cc_interview_prep_ai").  Two files sharing the same slug will crash the app
for every user with:

  StreamlitAPIException: Multiple Pages specified with URL pathname X.
  URL pathnames must be unique.

Usage (run manually):
  python3 scripts/check_duplicate_slugs.py

Exit codes:
  0 — all slugs unique
  1 — duplicate(s) found (prints offending files, commit is blocked)
"""
import os
import re
import sys
import collections

PAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pages")


def main():
    pages_dir = os.path.abspath(PAGES_DIR)
    if not os.path.isdir(pages_dir):
        print(f"ERROR: pages/ directory not found at {pages_dir}", file=sys.stderr)
        sys.exit(1)

    slug_map = collections.defaultdict(list)
    for fname in sorted(os.listdir(pages_dir)):
        if fname.endswith(".py"):
            slug = re.sub(r"^\d+_", "", fname[:-3])
            slug_map[slug].append(fname)

    dupes = {slug: files for slug, files in slug_map.items() if len(files) > 1}

    if not dupes:
        print(f"✅  No duplicate page slugs ({len(slug_map)} unique pages)")
        sys.exit(0)

    print("❌  DUPLICATE STREAMLIT PAGE SLUGS DETECTED — commit blocked!\n")
    print("    Two files with the same slug crash the app on startup.\n")
    for slug, files in sorted(dupes.items()):
        print(f"  slug: '{slug}'")
        for f in sorted(files):
            print(f"    pages/{f}")
    print("\n  Fix: delete or rename the older duplicate file, then re-stage.\n")
    sys.exit(1)


if __name__ == "__main__":
    main()

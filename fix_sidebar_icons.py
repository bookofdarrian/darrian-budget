"""Fix doubled emoji in sidebar page_link labels.

Streamlit's page_link renders icon= on the left automatically.
Having the same emoji in label= too causes visible duplication.
This script strips the emoji prefix from labels across all pages.
"""
import glob

REPLACEMENTS = [
    ('label="✅ Todo"',              'label="Todo"'),
    ('label="🎬 Creator"',           'label="Creator"'),
    ('label="📝 Notes"',             'label="Notes"'),
    ('label="🎵 Media Library"',     'label="Media Library"'),
    ('label="🧠 Proactive AI"',      'label="Proactive AI"'),
    ('label="🤖 Personal Assistant"','label="Personal Assistant"'),
    ('label="🤖 Jarvis"',            'label="Jarvis"'),
    ('label="📊 Overview"',          'label="Overview"'),
]

fixed_files = 0
fixed_total = 0

paths = sorted(glob.glob("pages/*.py")) + ["app.py"]
for path in paths:
    try:
        with open(path, "r", encoding="utf-8") as f:
            original = f.read()
        updated = original
        for old, new in REPLACEMENTS:
            updated = updated.replace(old, new)
        if updated != original:
            with open(path, "w", encoding="utf-8") as f:
                f.write(updated)
            n = sum(original.count(old) for old, _ in REPLACEMENTS)
            print(f"  fixed {n:3d} → {path}")
            fixed_files += 1
            fixed_total += n
    except Exception as e:
        print(f"  ERROR {path}: {e}")

print(f"\nDone: {fixed_total} replacements across {fixed_files} files")

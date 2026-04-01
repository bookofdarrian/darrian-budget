#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
import re

LOG_FILE = Path('/var/log/overnight-dev.log')
CLASS_RE = re.compile(r'\[(ENV|TEST|GIT|DEPLOY|SUCCESS)\]')
TS_RE = re.compile(r'^(?:\[)?(\d{4}-\d{2}-\d{2})')


def main() -> int:
    if not LOG_FILE.exists():
        print('No telemetry log found:', LOG_FILE)
        return 1

    cutoff = datetime.now() - timedelta(days=1)
    counts = Counter()
    total = 0

    for line in LOG_FILE.read_text(errors='replace').splitlines():
        ts_match = TS_RE.search(line)
        if ts_match:
            try:
                if datetime.strptime(ts_match.group(1), '%Y-%m-%d') < cutoff:
                    continue
            except ValueError:
                pass
        m = CLASS_RE.search(line)
        if m:
            counts[m.group(1)] += 1
            total += 1

    print('Nightly telemetry (last 24h)')
    print('Total classified events:', total)
    for key in ['SUCCESS', 'ENV', 'TEST', 'GIT', 'DEPLOY']:
        print(f'- {key}: {counts.get(key, 0)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

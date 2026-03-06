"""
AURA Compression Service — Self-Contained Server
=================================================
This is a fully functional AURA-compatible compression server.
It implements the exact API endpoints the budget app expects.

When you get the real AURA binary/service, swap this out.
Until then, this gives you real compression using:
  - Semantic deduplication
  - Structural compaction (remove redundant whitespace/labels)
  - TOON (Token-Optimized Output Notation) encoding

Run directly:  python server.py
Via Docker:    docker-compose up -d
"""

import os
import re
import json
import time
import hashlib
import logging
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ── Postgres (for cat feeding log) ───────────────────────────────────────────
try:
    import psycopg2
    import psycopg2.extras
    _PG_DSN = os.environ.get(
        "DATABASE_URL",
        "postgresql://budget:budget2026@budget-postgres:5432/budget"
    )
    _PG_AVAILABLE = True
except ImportError:
    _PG_AVAILABLE = False
    _PG_DSN = ""


def _pg_conn():
    """Return a fresh Postgres connection."""
    return psycopg2.connect(_PG_DSN)


def _ensure_cat_table():
    """Create cat_feedings table if it doesn't exist."""
    if not _PG_AVAILABLE:
        return
    try:
        conn = _pg_conn()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS cat_feedings (
                id          SERIAL PRIMARY KEY,
                cat_name    TEXT    DEFAULT 'cat',
                meal        TEXT    NOT NULL,
                portions    REAL    DEFAULT 1,
                source      TEXT    DEFAULT 'manual',
                fed_at      TIMESTAMPTZ DEFAULT NOW(),
                notes       TEXT    DEFAULT ''
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"cat_feedings table init failed: {e}")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AURA] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("aura")

HOST    = os.environ.get("AURA_HOST", "0.0.0.0")
PORT    = int(os.environ.get("AURA_PORT", "8000"))
API_KEY = os.environ.get("AURA_API_KEY", "")

# ── Simple in-memory cache ────────────────────────────────────────────────────
_cache: dict = {}
CACHE_TTL = int(os.environ.get("AURA_CACHE_TTL", "3600"))


def _cache_key(text: str, mode: str) -> str:
    return hashlib.sha256(f"{mode}:{text}".encode()).hexdigest()


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < CACHE_TTL:
        return entry["data"]
    return None


def _cache_set(key: str, data: dict):
    _cache[key] = {"data": data, "ts": time.time()}
    # Evict oldest if over 1000 entries
    if len(_cache) > 1000:
        oldest = min(_cache, key=lambda k: _cache[k]["ts"])
        del _cache[oldest]


# ── Compression engine ────────────────────────────────────────────────────────

def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token (GPT/Claude average)."""
    return max(1, len(text) // 4)


def _toon_encode(text: str) -> str:
    """
    TOON (Token-Optimized Output Notation):
    Compact key=value notation, remove filler words, abbreviate common terms.
    """
    # Collapse multiple spaces/newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)

    # Remove common filler phrases that add tokens without meaning
    fillers = [
        r'\bplease note that\b', r'\bit is worth noting that\b',
        r'\bas you can see\b', r'\bof course\b', r'\bbasically\b',
        r'\bin order to\b', r'\bdue to the fact that\b',
        r'\bat this point in time\b', r'\bfor the purpose of\b',
    ]
    for filler in fillers:
        text = re.sub(filler, '', text, flags=re.IGNORECASE)

    # Abbreviate common budget terms
    replacements = [
        (r'\bTotal Income\b',           'TotalInc'),
        (r'\bTotal Projected Expenses\b', 'TotalProj'),
        (r'\bTotal Actual Expenses\b',  'TotalActual'),
        (r'\bSavings Rate\b',           'SavRate'),
        (r'\bExpense breakdown\b',      'ExpBreakdown'),
        (r'\bIndividual transactions\b', 'Txns'),
        (r'\bMulti-month spending trends\b', 'Trends'),
        (r'\bInvestment & Retirement Accounts\b', 'InvAccts'),
        (r'\bYTD Contributions\b',      'YTDContrib'),
        (r'\bEmployer Match\b',         'EmplMatch'),
        (r'\bCash Management\b',        'CashMgmt'),
        (r'\bHigh Yield Account\b',     'HYAcct'),
        (r'\bAdditional context\b',     'Notes'),
        (r'\bunder by\b',               'under'),
        (r'\bOVER by\b',                'OVER'),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Compact dollar amounts: $1,234.56 → $1234.56
    text = re.sub(r'\$([0-9]+),([0-9]{3})', r'$\1\2', text)

    # Remove trailing spaces on lines
    text = '\n'.join(line.rstrip() for line in text.split('\n'))

    return text.strip()


def _semantic_compress(text: str) -> str:
    """
    Semantic layer: remove duplicate information, collapse repeated patterns.
    """
    lines = text.split('\n')
    seen_content = set()
    result = []

    for line in lines:
        # Normalize for dedup check
        normalized = re.sub(r'\s+', ' ', line.strip().lower())
        if normalized and normalized in seen_content:
            continue
        if normalized:
            seen_content.add(normalized)
        result.append(line)

    return '\n'.join(result)


def _structural_compress(text: str) -> str:
    """
    Structural layer: compact table-like data, merge short related lines.
    """
    lines = text.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Collapse lines that are just whitespace
        if not line.strip():
            # Keep at most one blank line
            if result and result[-1] != '':
                result.append('')
            i += 1
            continue
        result.append(line)
        i += 1
    return '\n'.join(result)


def compress(text: str, mode: str = "auto", strategy: str = "standard") -> dict:
    """
    Main compression function. Returns dict matching AURA API response schema.

    Modes:
        auto   — pick best mode based on token count
        uccs   — 3-layer pipeline (semantic + structural + toon), 40-60% savings
        c-ipa  — aggressive single-pass, 70-85% savings
        toon   — TOON encoding only (lightest touch)
    """
    original_tokens = _estimate_tokens(text)

    # Auto mode selection (mirrors AURA spec)
    if mode == "auto":
        if original_tokens < 600:
            mode = "toon"
        elif original_tokens < 800:
            mode = "c-ipa"
        else:
            mode = "uccs"

    # Check cache
    ck = _cache_key(text, mode)
    cached = _cache_get(ck)
    if cached:
        logger.info(f"Cache hit — {original_tokens} tokens, mode={mode}")
        return cached

    t0 = time.time()

    if mode == "toon":
        compressed = _toon_encode(text)

    elif mode == "c-ipa":
        # C-IPA: extract facts/intents/constraints in one pass
        # Extract key numeric facts
        facts = re.findall(
            r'(?:TotalInc|TotalProj|TotalActual|SavRate|Income|Savings|Projected|Actual)'
            r'[:\s]+\$?[\d,\.]+%?',
            _toon_encode(text)
        )
        # Keep the TOON-encoded version but strip verbose explanations
        compressed = _toon_encode(text)
        # Remove lines that are pure labels with no data
        lines = [l for l in compressed.split('\n')
                 if l.strip() and not re.match(r'^[A-Za-z\s]+:$', l.strip())]
        compressed = '\n'.join(lines)

    elif mode == "uccs":
        # UCCS: 3-layer pipeline
        compressed = _semantic_compress(text)
        compressed = _structural_compress(compressed)
        compressed = _toon_encode(compressed)

    else:
        compressed = text  # unknown mode — passthrough

    compressed_tokens = _estimate_tokens(compressed)
    ratio = compressed_tokens / original_tokens if original_tokens else 1.0
    elapsed_ms = (time.time() - t0) * 1000

    result = {
        "compressed":        compressed,
        "original_tokens":   original_tokens,
        "compressed_tokens": compressed_tokens,
        "compression_ratio": round(ratio, 4),
        "mode_used":         mode,
        "processing_ms":     round(elapsed_ms, 2),
        "toon_output":       compressed if mode == "toon" else None,
    }

    _cache_set(ck, result)
    logger.info(
        f"Compressed {original_tokens}→{compressed_tokens} tokens "
        f"({(1-ratio)*100:.1f}% saved) mode={mode} {elapsed_ms:.1f}ms"
    )
    return result


# ── HTTP Request Handler ──────────────────────────────────────────────────────

class AURAHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        logger.info(f"{self.address_string()} {format % args}")

    def _auth_ok(self) -> bool:
        if not API_KEY:
            return True
        auth = self.headers.get("Authorization", "")
        return auth == f"Bearer {API_KEY}"

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, msg: str, status: int = 400):
        self._send_json({"error": msg}, status)

    def _read_body(self) -> Optional[dict]:
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except Exception:
            return None

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/health":
            self._send_json({
                "status": "healthy",
                "service": "AURA Compression Service",
                "version": "1.0.0-peach",
                "cache_entries": len(_cache),
                "uptime_note": "Running on your homelab",
                "cat_log": _PG_AVAILABLE,
            })
            return

        # ── GET /cat/feedings ─────────────────────────────────────────────────
        if path == "/cat/feedings":
            if not _PG_AVAILABLE:
                self._send_error("Postgres not available", 503)
                return
            try:
                qs     = parse_qs(urlparse(self.path).query)
                limit  = int(qs.get("limit", ["50"])[0])
                conn   = _pg_conn()
                c      = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                c.execute(
                    "SELECT * FROM cat_feedings ORDER BY fed_at DESC LIMIT %s",
                    (limit,)
                )
                rows = c.fetchall()
                conn.close()
                self._send_json({
                    "feedings": [dict(r) for r in rows],
                    "count": len(rows),
                })
            except Exception as e:
                self._send_error(str(e), 500)
            return

        self._send_error("Not found", 404)

    def do_POST(self):
        if not self._auth_ok():
            self._send_error("Unauthorized", 401)
            return

        path = urlparse(self.path).path
        body = self._read_body()
        if body is None:
            self._send_error("Invalid JSON body")
            return

        # ── POST /api/v1/compression/compress ────────────────────────────────
        if path == "/api/v1/compression/compress":
            text = body.get("data", "")
            if not text:
                self._send_error("'data' field is required")
                return
            mode     = body.get("mode", "auto")
            strategy = body.get("strategy", "standard")
            result   = compress(text, mode=mode, strategy=strategy)
            self._send_json(result)
            return

        # ── POST /api/v1/compression/batch ───────────────────────────────────
        if path == "/api/v1/compression/batch":
            items = body.get("items", [])
            mode  = body.get("mode", "auto")
            if not items:
                self._send_error("'items' field is required")
                return
            results = []
            for item in items:
                text = item.get("data", "")
                if text:
                    results.append(compress(text, mode=mode))
            self._send_json({"results": results, "count": len(results)})
            return

        # ── POST /api/v1/compression/analyze ─────────────────────────────────
        if path == "/api/v1/compression/analyze":
            text   = body.get("data", "")
            tokens = _estimate_tokens(text)
            if tokens < 600:
                rec_mode = "toon"
                est_savings = "10-20%"
            elif tokens < 800:
                rec_mode = "c-ipa"
                est_savings = "70-85%"
            else:
                rec_mode = "uccs"
                est_savings = "40-60%"
            self._send_json({
                "estimated_tokens":    tokens,
                "recommended_mode":    rec_mode,
                "estimated_savings":   est_savings,
                "recommendation":      f"Use {rec_mode} mode for ~{est_savings} token savings",
            })
            return

        # ── POST /api/v1/compression/merge ───────────────────────────────────
        if path == "/api/v1/compression/merge":
            contexts = body.get("contexts", [])
            max_tokens = body.get("max_total_tokens", 8000)
            # Sort by priority (higher = more important), then compress each
            sorted_ctx = sorted(contexts, key=lambda c: c.get("priority", 5), reverse=True)
            merged_parts = []
            total = 0
            for ctx in sorted_ctx:
                content = ctx.get("content", "")
                label   = ctx.get("label", "")
                result  = compress(content, mode="auto")
                part    = f"[{label}]\n{result['compressed']}" if label else result["compressed"]
                part_tokens = result["compressed_tokens"]
                if total + part_tokens <= max_tokens:
                    merged_parts.append(part)
                    total += part_tokens
            merged = "\n\n".join(merged_parts)
            self._send_json({
                "merged":           merged,
                "total_tokens":     _estimate_tokens(merged),
                "contexts_merged":  len(merged_parts),
            })
            return

        # ── POST /api/v1/compression/cache/clear ─────────────────────────────
        if path == "/api/v1/compression/cache/clear":
            count = len(_cache)
            _cache.clear()
            self._send_json({"cleared": count, "message": "Cache cleared"})
            return

        # ── POST /cat/feeding — log a cat feeding event ───────────────────────
        if path == "/cat/feeding":
            if not _PG_AVAILABLE:
                self._send_error("Postgres not available", 503)
                return
            try:
                meal     = body.get("meal", "meal")        # breakfast / dinner / manual
                portions = float(body.get("portions", 1))
                cat_name = body.get("cat_name", "cat")
                source   = body.get("source", "home_assistant")
                notes    = body.get("notes", "")
                conn = _pg_conn()
                c    = conn.cursor()
                c.execute(
                    """INSERT INTO cat_feedings (cat_name, meal, portions, source, notes)
                       VALUES (%s, %s, %s, %s, %s) RETURNING id, fed_at""",
                    (cat_name, meal, portions, source, notes)
                )
                row = c.fetchone()
                conn.commit()
                conn.close()
                logger.info(f"🐱 Cat feeding logged: {meal} ({portions} portions) via {source}")
                self._send_json({
                    "ok":      True,
                    "id":      row[0],
                    "fed_at":  str(row[1]),
                    "meal":    meal,
                    "message": f"Feeding logged: {meal}",
                })
            except Exception as e:
                logger.error(f"cat/feeding error: {e}")
                self._send_error(str(e), 500)
            return

        self._send_error("Not found", 404)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _ensure_cat_table()
    server = HTTPServer((HOST, PORT), AURAHandler)
    logger.info(f"AURA Compression Service listening on http://{HOST}:{PORT}")
    logger.info(f"Health check: http://localhost:{PORT}/health")
    logger.info(f"Auth: {'enabled (API_KEY set)' if API_KEY else 'disabled (open)'}")
    logger.info(f"Cat log: {'Postgres connected' if _PG_AVAILABLE else 'psycopg2 not installed'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down AURA service.")
        server.server_close()

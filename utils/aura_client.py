"""
AURA Compression Client
=======================
Wraps the AURA API for use inside the budget app.

When AURA is running (locally via Docker or on your home lab server),
it compresses the budget context before sending it to Claude — saving
40-82% on token costs.

When AURA is NOT running, this module falls back gracefully to the
raw context string so nothing breaks.

Usage:
    from utils.aura_client import compress_for_claude, aura_available

    context = build_budget_context(month)
    compressed = compress_for_claude(context)   # safe to call always
    response = ask_claude(prompt, compressed)
"""

import os
import time
import logging
import requests
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Config — override via environment variables ───────────────────────────────
# Default: localhost (Docker on your Mac or home lab)
AURA_BASE_URL   = os.environ.get("AURA_BASE_URL", "http://localhost:8000")
AURA_API_KEY    = os.environ.get("AURA_API_KEY", "")          # optional auth
AURA_TIMEOUT    = int(os.environ.get("AURA_TIMEOUT", "10"))   # seconds
AURA_MAX_RETRY  = int(os.environ.get("AURA_MAX_RETRY", "2"))
AURA_ENABLED    = os.environ.get("AURA_ENABLED", "true").lower() != "false"

# Cache the last health-check result so we don't hammer the endpoint
_health_cache: dict = {"ok": False, "checked_at": 0.0}
_HEALTH_TTL = 30  # re-check every 30 seconds


@dataclass
class CompressionResult:
    """Result from one AURA compression call."""
    compressed: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float          # e.g. 0.55 means 55% of original size
    mode_used: str
    processing_time_ms: float
    savings_pct: float = field(init=False)
    fallback_used: bool = False       # True when AURA was unavailable

    def __post_init__(self):
        self.savings_pct = round((1.0 - self.compression_ratio) * 100, 1)


def _make_session() -> requests.Session:
    """Build a requests Session with connection pooling and optional auth."""
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=5,
        pool_maxsize=10,
        max_retries=AURA_MAX_RETRY,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "PeachSavings-AURA/1.0",
    })
    if AURA_API_KEY:
        session.headers["Authorization"] = f"Bearer {AURA_API_KEY}"
    return session


_session: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = _make_session()
    return _session


# ── Health check ──────────────────────────────────────────────────────────────

def aura_available() -> bool:
    """
    Return True if the AURA service is reachable.
    Result is cached for HEALTH_TTL seconds to avoid latency on every call.
    """
    if not AURA_ENABLED:
        return False

    now = time.time()
    if now - _health_cache["checked_at"] < _HEALTH_TTL:
        return _health_cache["ok"]

    try:
        # Use a (connect_timeout, read_timeout) tuple — fail fast if server is unresponsive
        resp = _get_session().get(f"{AURA_BASE_URL}/health", timeout=(2, 2))
        ok = resp.status_code == 200
    except Exception:
        ok = False

    _health_cache["ok"] = ok
    _health_cache["checked_at"] = now
    return ok


def _invalidate_health_cache():
    _health_cache["checked_at"] = 0.0


# ── Core compression ──────────────────────────────────────────────────────────

def compress_text(
    text: str,
    mode: str = "auto",
    strategy: str = "standard",
    max_tokens: Optional[int] = None,
) -> CompressionResult:
    """
    Compress text via AURA.

    mode options:
        "auto"   — AURA picks best mode based on token count
        "uccs"   — 3-layer pipeline, 40-60% savings
        "c-ipa"  — Intent-preserving, 70-85% savings, 90%+ accuracy

    Raises RuntimeError if AURA is unreachable (caller should handle).
    """
    payload: dict = {"data": text, "mode": mode, "strategy": strategy}
    if max_tokens:
        payload["max_tokens"] = max_tokens

    t0 = time.time()
    resp = _get_session().post(
        f"{AURA_BASE_URL}/api/v1/compression/compress",
        json=payload,
        timeout=AURA_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    elapsed_ms = (time.time() - t0) * 1000

    orig   = data.get("original_tokens", 0)
    compr  = data.get("compressed_tokens", 0)
    ratio  = data.get("compression_ratio", compr / orig if orig else 1.0)

    return CompressionResult(
        compressed=data.get("compressed", text),
        original_tokens=orig,
        compressed_tokens=compr,
        compression_ratio=ratio,
        mode_used=data.get("mode_used", mode),
        processing_time_ms=elapsed_ms,
    )


def compress_for_claude(
    text: str,
    mode: str = "auto",
) -> CompressionResult:
    """
    Safe wrapper: compress if AURA is available, otherwise return raw text.

    This is the function to call from ai_insights.py — it NEVER raises,
    so Claude always gets something to work with.

    Returns a CompressionResult where:
        .compressed      — the text to send to Claude
        .fallback_used   — True if AURA was down (raw text returned)
        .savings_pct     — how much was saved (0 if fallback)
    """
    if not aura_available():
        # Estimate token count (rough: 1 token ≈ 4 chars)
        est_tokens = len(text) // 4
        return CompressionResult(
            compressed=text,
            original_tokens=est_tokens,
            compressed_tokens=est_tokens,
            compression_ratio=1.0,
            mode_used="fallback",
            processing_time_ms=0.0,
            fallback_used=True,
        )

    try:
        result = compress_text(text, mode=mode)
        logger.info(
            f"AURA compressed {result.original_tokens} → {result.compressed_tokens} tokens "
            f"({result.savings_pct}% saved, {result.processing_time_ms:.0f}ms)"
        )
        return result
    except Exception as exc:
        logger.warning(f"AURA compression failed, using raw text: {exc}")
        _invalidate_health_cache()
        est_tokens = len(text) // 4
        return CompressionResult(
            compressed=text,
            original_tokens=est_tokens,
            compressed_tokens=est_tokens,
            compression_ratio=1.0,
            mode_used="fallback",
            processing_time_ms=0.0,
            fallback_used=True,
        )


# ── Batch compression (for future use) ───────────────────────────────────────

def batch_compress(items: list[dict], mode: str = "auto") -> list[CompressionResult]:
    """
    Compress multiple text items in one API call.
    Each item should be: {"data": "text...", "id": "optional_id"}
    Falls back to individual compress_for_claude calls if batch fails.
    """
    if not aura_available():
        return [compress_for_claude(item.get("data", ""), mode) for item in items]

    try:
        t0 = time.time()
        resp = _get_session().post(
            f"{AURA_BASE_URL}/api/v1/compression/batch",
            json={"items": items, "mode": mode},
            timeout=AURA_TIMEOUT * 2,
        )
        resp.raise_for_status()
        data = resp.json()
        elapsed_ms = (time.time() - t0) * 1000
        results = data.get("results", [])
        per_item_ms = elapsed_ms / max(len(results), 1)

        return [
            CompressionResult(
                compressed=r.get("compressed", ""),
                original_tokens=r.get("original_tokens", 0),
                compressed_tokens=r.get("compressed_tokens", 0),
                compression_ratio=r.get("compression_ratio", 1.0),
                mode_used=r.get("mode_used", mode),
                processing_time_ms=per_item_ms,
            )
            for r in results
        ]
    except Exception as exc:
        logger.warning(f"AURA batch failed, falling back: {exc}")
        _invalidate_health_cache()
        return [compress_for_claude(item.get("data", ""), mode) for item in items]


# ── Merge contexts (multi-source) ─────────────────────────────────────────────

def merge_contexts(contexts: list[dict], max_total_tokens: int = 8000) -> Optional[str]:
    """
    Merge multiple context dicts into one optimized context string.
    Each context: {"content": "...", "priority": 1-10, "label": "optional"}
    Returns merged string, or None if AURA unavailable.
    """
    if not aura_available():
        return None
    try:
        resp = _get_session().post(
            f"{AURA_BASE_URL}/api/v1/compression/merge",
            json={"contexts": contexts, "max_total_tokens": max_total_tokens},
            timeout=AURA_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("merged", None)
    except Exception as exc:
        logger.warning(f"AURA merge failed: {exc}")
        return None


# ── Status summary (for UI display) ──────────────────────────────────────────

def get_status() -> dict:
    """
    Return a status dict for display in the Streamlit UI.
    {
        "available": bool,
        "base_url": str,
        "enabled": bool,
        "message": str,
    }
    """
    available = aura_available()
    if not AURA_ENABLED:
        msg = "AURA disabled via AURA_ENABLED=false"
    elif available:
        msg = f"✅ Connected to AURA at {AURA_BASE_URL}"
    else:
        msg = f"⚠️ AURA not reachable at {AURA_BASE_URL} — using raw context (no savings)"
    return {
        "available": available,
        "base_url": AURA_BASE_URL,
        "enabled": AURA_ENABLED,
        "message": msg,
    }

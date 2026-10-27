"""Cache for merged contexts.

The cache key includes a FINGERPRINT of the data (file modification times), so when the
database or a document changes, old entries stop matching -> stale context is never served.
(In AWS this would be ElastiCache/Redis.)
"""
import re

from app.sources import DB_PATH, DOCS_DIR

_CACHE: dict[str, dict] = {}


def data_fingerprint() -> str:
    parts = []
    if DB_PATH.exists():
        parts.append(str(DB_PATH.stat().st_mtime_ns))
    for p in sorted(DOCS_DIR.glob("*.txt")):
        parts.append(f"{p.name}:{p.stat().st_mtime_ns}")
    return "|".join(parts)


def make_key(question: str) -> str:
    normalized = re.sub(r"[^a-z0-9 ]", "", question.lower()).strip()
    normalized = " ".join(normalized.split())
    return f"{normalized}::{data_fingerprint()}"


def cache_get(question: str):
    return _CACHE.get(make_key(question))


def cache_set(question: str, value: dict) -> None:
    _CACHE[make_key(question)] = value


def cache_clear() -> None:
    _CACHE.clear()


def cache_size() -> int:
    return len(_CACHE)

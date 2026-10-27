"""Merge retrieved chunks into ONE context window:
   1) de-duplicate  2) resolve conflicts by source priority  3) fit a token budget
"""
import re

# Higher number = more trusted when two sources disagree.
SOURCE_PRIORITY = {"db": 3, "docs": 2, "memory": 1}


def estimate_tokens(text: str) -> int:
    # Rough rule of thumb: 1 word ~ 1.3 tokens
    return int(len(text.split()) * 1.3) + 1


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def merge_context(chunks: list[dict], max_tokens: int = 800) -> dict:
    # 1) De-duplicate (identical text after normalisation)
    unique, seen = [], set()
    for c in chunks:
        key = _normalize(c["text"])
        if key and key not in seen:
            seen.add(key)
            unique.append(c)
    removed = len(chunks) - len(unique)

    # 2) Conflict handling: most trusted source first (db > docs > memory)
    unique.sort(key=lambda c: SOURCE_PRIORITY.get(c["source"], 0), reverse=True)

    # 3) Token budget: keep adding chunks until the budget is full
    kept, used, dropped = [], 0, 0
    for c in unique:
        cost = estimate_tokens(c["text"])
        if used + cost > max_tokens:
            dropped += 1
            continue
        kept.append(c)
        used += cost

    context = "\n".join(f"[{c['source'].upper()}] {c['text']}" for c in kept)
    return {
        "context": context,
        "stats": {
            "chunks_in": len(chunks),
            "duplicates_removed": removed,
            "dropped_for_budget": dropped,
            "tokens_used": used,
            "token_budget": max_tokens,
        },
    }

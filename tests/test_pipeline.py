"""Run with:  python -m pytest -q     (or: python tests/test_pipeline.py)
Covers the CI ideas from the project PDF: routing test matrix + cache invalidation.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import cache, sources
from app.merger import merge_context
from app.router import route_query

# ---- 1) routing test matrix: fixed queries -> expected sources
ROUTING_MATRIX = [
    ("What are the marks of Rahul?", {"db"}),
    ("What is the hostel timing?", {"docs"}),
    ("Who is the topper in Computer Science?", {"db"}),
    ("Am I eligible for scholarship? Tell me about Priya's marks", {"db", "docs"}),
    ("What did we discuss earlier about the library?", {"memory", "docs"}),
    ("random unrelated question", {"docs"}),  # default
]


def test_routing_matrix():
    for question, expected in ROUTING_MATRIX:
        assert set(route_query(question)) == expected, question


# ---- 2) source connectors return the right shape
def test_connectors_contract():
    sources.init_db()
    for fn, q in [(sources.get_db, "marks of Rahul"), (sources.get_docs, "hostel timing")]:
        chunks = fn(q)
        assert chunks, f"{fn.__name__} returned nothing"
        for c in chunks:
            assert set(c) == {"text", "source"}


# ---- 3) merger: dedupe + token budget + priority
def test_merger():
    chunks = [
        {"text": "Library opens at 8 AM.", "source": "docs"},
        {"text": "library opens at 8 am", "source": "memory"},  # duplicate
        {"text": "Student Rahul marks 82", "source": "db"},
    ]
    out = merge_context(chunks, max_tokens=800)
    assert out["stats"]["duplicates_removed"] == 1
    assert out["context"].startswith("[DB]")  # db is trusted first

    tiny = merge_context(chunks, max_tokens=5)
    assert tiny["stats"]["dropped_for_budget"] >= 1


# ---- 4) cache invalidation: changing data must stop stale hits
def test_cache_invalidation():
    sources.init_db()
    cache.cache_clear()
    cache.cache_set("what is the library timing", {"answer": "old"})
    assert cache.cache_get("What is the library timing?") is not None  # similar query hits

    doc = sources.DOCS_DIR / "library_test_tmp.txt"
    doc.write_text("temporary change")  # data changed -> fingerprint changes
    try:
        assert cache.cache_get("what is the library timing") is None
    finally:
        doc.unlink()


if __name__ == "__main__":
    test_routing_matrix(); test_connectors_contract(); test_merger(); test_cache_invalidation()
    print("all tests passed")

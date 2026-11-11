"""Contract tests: every source connector must accept a string query and return
a list of {"text": str, "source": <its own name>} items. The merger output must
also follow a fixed schema. (In AWS, each connector becomes its own Lambda, so
this is the contract that Lambda's input/output would have to keep.)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import sources
from app.merger import merge_context

QUERIES = ["marks of Rahul", "hostel timing", "earlier question", "", "zzzz qqqq"]


def validate_chunk(chunk: dict, expected_source: str) -> None:
    assert isinstance(chunk, dict), "chunk must be a dict"
    assert set(chunk.keys()) == {"text", "source"}, f"bad keys: {set(chunk.keys())}"
    assert isinstance(chunk["text"], str) and chunk["text"].strip(), "text must be a non-empty string"
    assert chunk["source"] == expected_source, f"source must be '{expected_source}'"


def test_every_connector_follows_contract():
    sources.init_db()
    sources.clear_memory()
    sources.add_to_memory("earlier question", "earlier answer")
    for name, fn in sources.SOURCE_FUNCTIONS.items():
        for q in QUERIES:
            result = fn(q)
            assert isinstance(result, list), f"{name}('{q}') must return a list"
            for chunk in result:

                validate_chunk(chunk, name)


def test_connectors_never_crash_on_odd_input():
    sources.init_db()
    odd = ["'; DROP TABLE students; --", "   ", "ünïcödé 日本語", "a" * 5000]
    for name, fn in sources.SOURCE_FUNCTIONS.items():
        for q in odd:
            assert isinstance(fn(q), list), f"{name} failed on odd input"
    # the students table must still exist after the injection-style query
    assert sources.get_db("students"), "students table should still be queryable"


def test_merger_output_schema():
    out = merge_context([{"text": "hello world", "source": "docs"}])
    assert set(out.keys()) == {"context", "stats"}
    assert isinstance(out["context"], str)
    assert set(out["stats"].keys()) == {
        "chunks_in", "duplicates_removed", "dropped_for_budget",
        "tokens_used", "token_budget",
    }
    assert all(isinstance(v, int) for v in out["stats"].values())


if __name__ == "__main__":
    test_every_connector_follows_contract()
    test_connectors_never_crash_on_odd_input()
    test_merger_output_schema()
    print("all contract tests passed")
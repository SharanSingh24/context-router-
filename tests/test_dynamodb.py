"""DynamoDB source tests - uses a fake table, no AWS calls."""
import os
import sqlite3
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import dynamo_source, sources


class FakeTable:
    def __init__(self, items):
        self.items = items

    def scan(self, **kwargs):
        return {"Items": self.items}


def _sqlite_as_dynamo_items():
    sources.init_db()
    conn = sqlite3.connect(sources.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    # real DynamoDB returns numbers as Decimal
    return [{"id": Decimal(r["id"]), "name": r["name"], "course": r["course"],
             "marks": Decimal(r["marks"]), "attendance": Decimal(r["attendance"])} for r in rows]


def test_dynamodb_gives_same_answers_as_sqlite():
    queries = ["marks of Rahul", "who is the topper", "computer science students", "zzzz"]
    os.environ["DB_BACKEND"] = "sqlite"
    expected = {q: sources.get_db(q) for q in queries}
    dynamo_source._table = FakeTable(_sqlite_as_dynamo_items())
    os.environ["DB_BACKEND"] = "dynamodb"
    try:
        for q in queries:
            assert sources.get_db(q) == expected[q], q
    finally:
        os.environ["DB_BACKEND"] = "sqlite"
        dynamo_source._table = None


def test_dynamodb_failure_returns_empty_list():
    class Broken:
        def scan(self, **kw):
            raise RuntimeError("no credentials")

    dynamo_source._table = Broken()
    os.environ["DB_BACKEND"] = "dynamodb"
    try:
        assert sources.get_db("marks of Rahul") == []
    finally:
        os.environ["DB_BACKEND"] = "sqlite"
        dynamo_source._table = None


if __name__ == "__main__":
    test_dynamodb_gives_same_answers_as_sqlite()
    test_dynamodb_failure_returns_empty_list()
    print("all dynamodb tests passed")
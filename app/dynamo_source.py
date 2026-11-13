"""DynamoDB version of the structured-data source (used when DB_BACKEND=dynamodb)."""
import os

from app.sources import tokenize

_table = None


def _get_table():
    global _table
    if _table is None:
        import boto3

        resource = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
        _table = resource.Table(os.getenv("DYNAMODB_TABLE", "students"))
    return _table


def fetch_rows() -> list:
    table = _get_table()
    response = table.scan()
    items = response["Items"]
    while "LastEvaluatedKey" in response:  # table bigger than 1 MB -> keep reading
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items += response["Items"]
    return sorted(items, key=lambda r: int(r["id"]))


def select_students(rows: list, query: str) -> list:
    """Same matching rules as the SQLite version."""
    q = query.lower()
    tokens = tokenize(query)

    picked = [r for r in rows
              if any(t == r["name"].lower() or t in r["course"].lower() for t in tokens)]
    if not picked and any(w in q for w in ("top", "best", "highest", "topper", "rank")):
        picked = sorted(rows, key=lambda r: int(r["marks"]), reverse=True)[:3]
    if not picked and any(w in q for w in ("student", "marks", "attendance", "average", "all")):
        picked = rows
    return picked


def get_db_dynamodb(query: str) -> list:
    try:
        rows = fetch_rows()
    except Exception as e:  # no credentials, no table, no network...
        print(f"[dynamodb] failed ({type(e).__name__}: {e})")
        return []
    out, seen = [], set()
    for r in select_students(rows, query):
        if int(r["id"]) in seen:
            continue
        seen.add(int(r["id"]))
        out.append({
            "text": (f"Student {r['name']} | course: {r['course']} | "
                     f"marks: {int(r['marks'])} | attendance: {int(r['attendance'])}%"),
            "source": "db",
        })
    return out
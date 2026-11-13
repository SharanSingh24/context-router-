"""Create the DynamoDB table and copy the students from SQLite into it.

Run once:  python scripts/seed_dynamodb.py
"""
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import boto3
from dotenv import load_dotenv

from app.sources import DB_PATH, init_db

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

region = os.getenv("AWS_REGION", "us-east-1")
table_name = os.getenv("DYNAMODB_TABLE", "students")

init_db()
conn = sqlite3.connect(DB_PATH)
rows = conn.execute("SELECT id, name, course, marks, attendance FROM students").fetchall()
conn.close()

dynamodb = boto3.resource("dynamodb", region_name=region)
existing = [t.name for t in dynamodb.tables.all()]
if table_name in existing:
    table = dynamodb.Table(table_name)
    print(f"Table '{table_name}' already exists - reusing it.")
else:

    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "N"}],
        BillingMode="PAY_PER_REQUEST",  # no hourly charge, you pay per request
    )
    table.wait_until_exists()
    print(f"Created table '{table_name}'.")

for id_, name, course, marks, attendance in rows:
    table.put_item(Item={"id": id_, "name": name, "course": course,
                         "marks": marks, "attendance": attendance})
print(f"Copied {len(rows)} students into DynamoDB.")
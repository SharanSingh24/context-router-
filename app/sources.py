"""Source connectors: local docs, SQLite database, conversation memory.

Every retriever takes a query string and returns a list of dicts:
    {"text": "...", "source": "docs" | "db" | "memory"}
"""
import re
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "data" / "docs"
DB_PATH = BASE_DIR / "data" / "app.db"

STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "in", "on", "for", "and", "or",
    "what", "who", "how", "me", "my", "do", "does", "i", "tell", "about", "give",
    "show", "with", "at", "by", "it", "this", "that", "was", "were", "be", "can",
}


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


# ----------------------------------------------------------------- database
def init_db() -> None:
    """Create and seed the SQLite DB the first time the app runs."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS students ("
        "id INTEGER PRIMARY KEY, name TEXT, course TEXT, marks INTEGER, attendance INTEGER)"
    )
    if conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
        rows = [
            (1, "Rahul", "Computer Science", 82, 91),
            (2, "Priya", "Computer Science", 91, 96),
            (3, "Arjun", "Electronics", 74, 78),
            (4, "Sneha", "Mechanical", 68, 85),
            (5, "Karthik", "Computer Science", 88, 80),
            (6, "Divya", "Electronics", 79, 93),
            (7, "Imran", "Mechanical", 85, 72),
            (8, "Ananya", "Computer Science", 95, 98),
        ]
        conn.executemany("INSERT INTO students VALUES (?,?,?,?,?)", rows)
        conn.commit()
    conn.close()


def get_db(query: str) -> list[dict]:
    """Structured-data source. Simple keyword -> SQL mapping (safe, parameterised)."""
    init_db()
    q = query.lower()
    tokens = tokenize(query)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    results: list[sqlite3.Row] = []

    # 1) match a student name or a course mentioned in the query
    for t in tokens:
        results += conn.execute(
            "SELECT * FROM students WHERE lower(name) = ? OR lower(course) LIKE ?",
            (t, f"%{t}%"),
        ).fetchall()

    # 2) ranking questions
    if not results and any(w in q for w in ("top", "best", "highest", "topper", "rank")):
        results = conn.execute("SELECT * FROM students ORDER BY marks DESC LIMIT 3").fetchall()

    # 3) generic "students / marks / attendance" questions -> everyone
    if not results and any(w in q for w in ("student", "marks", "attendance", "average", "all")):
        results = conn.execute("SELECT * FROM students").fetchall()

    conn.close()

    seen, out = set(), []
    for r in results:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        out.append({
            "text": (f"Student {r['name']} | course: {r['course']} | "
                     f"marks: {r['marks']} | attendance: {r['attendance']}%"),
            "source": "db",
        })
    return out


# --------------------------------------------------------------------- docs
def get_docs(query: str, top_k: int = 3) -> list[dict]:
    """Document source: split .txt files into paragraphs and rank by keyword overlap."""
    tokens = set(tokenize(query))
    scored = []
    for path in sorted(DOCS_DIR.glob("*.txt")):
        for para in path.read_text(encoding="utf-8").split("\n\n"):
            para = para.strip()
            if not para:
                continue
            score = len(tokens & set(tokenize(para)))
            if score > 0:
                scored.append((score, f"[{path.name}] {para}"))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"text": t, "source": "docs"} for _, t in scored[:top_k]]


# ------------------------------------------------------------------- memory
_MEMORY: list[dict] = []


def add_to_memory(question: str, answer: str) -> None:
    _MEMORY.append({"q": question, "a": answer})
    del _MEMORY[:-20]  # keep the last 20 turns only


def get_memory(query: str, top_k: int = 2) -> list[dict]:
    """Past-conversation source: return earlier turns that share words with the query."""
    tokens = set(tokenize(query))
    scored = []
    for turn in _MEMORY:
        score = len(tokens & set(tokenize(turn["q"] + " " + turn["a"])))
        if score > 0:
            scored.append((score, f"Earlier Q: {turn['q']} | Earlier A: {turn['a']}"))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"text": t, "source": "memory"} for _, t in scored[:top_k]]


def clear_memory() -> None:
    _MEMORY.clear()


SOURCE_FUNCTIONS = {"docs": get_docs, "db": get_db, "memory": get_memory}

"""Context routing: decide WHICH sources are relevant BEFORE calling them.

This is rule/keyword based (fast, free, easy to explain in a viva).
Upgrade path: replace `route_query` with a few-shot LLM classifier or a small router model.
"""

ROUTING_RULES = {
    "db": ["student", "students", "marks", "mark", "attendance", "grade", "topper", "top",
           "score", "rank", "average", "cgpa", "computer", "electronics", "mechanical",
           "rahul", "priya", "arjun", "sneha", "karthik", "divya", "imran", "ananya"],
    "docs": ["policy", "rule", "rules", "exam", "fee", "fees", "hostel", "library", "leave",
             "syllabus", "course", "scholarship", "placement", "timing", "timings", "document",
             "regulation", "eligibility", "schedule"],
    "memory": ["earlier", "before", "previous", "previously", "again", "last time", "you said",
               "we discussed", "remind", "repeat"],
}


def route_query(question: str) -> list[str]:
    q = question.lower()
    words = set(q.replace("?", " ").replace(",", " ").split())
    selected = []
    for source, keywords in ROUTING_RULES.items():
        if any((k in words) or (" " in k and k in q) for k in keywords):
            selected.append(source)
    return selected or ["docs"]  # default source when nothing matches

from fastapi import FastAPI
from pydantic import BaseModel

from app.cache import cache_clear, cache_size
from app.graph import graph
from app.sources import clear_memory, init_db

app = FastAPI(title="Multi-Source Context Merge Router")
init_db()


class AskRequest(BaseModel):
    question: str


@app.get("/")
def home():
    return {"status": "running", "docs": "/docs"}


@app.post("/ask")
def ask(req: AskRequest):
    result = graph.invoke({"question": req.question})
    return {
        "question": req.question,
        "answer": result.get("answer"),
        "sources_selected": result.get("selected_sources"),
        "cache_hit": result.get("cache_hit", False),
        "llm_used": result.get("llm_used"),
        "latency_ms_per_source": result.get("timings_ms"),
        "merge_stats": result.get("merge_stats"),
        "merged_context": result.get("merged_context"),
    }


@app.post("/reset")
def reset():
    cache_clear()
    clear_memory()
    return {"cache_cleared": True, "memory_cleared": True}


@app.get("/stats")
def stats():
    return {"cache_entries": cache_size()}

"""LangGraph workflow:

    check_cache --(hit)--> END
        |
      (miss)
        v
      route -> retrieve -> merge -> generate -> END
"""
import time
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.cache import cache_get, cache_set
from app.llm import generate_answer
from app.merger import merge_context
from app.router import route_query
from app.sources import SOURCE_FUNCTIONS, add_to_memory


class RouterState(TypedDict, total=False):
    question: str
    selected_sources: list
    retrieved: list
    merged_context: str
    merge_stats: dict
    answer: str
    llm_used: str
    cache_hit: bool
    timings_ms: dict


def check_cache_node(state: RouterState) -> dict:
    cached = cache_get(state["question"])
    if cached:
        return {**cached, "cache_hit": True}  # whole bundle comes from cache
    return {"cache_hit": False}


def route_node(state: RouterState) -> dict:
    return {"selected_sources": route_query(state["question"])}


def retrieve_node(state: RouterState) -> dict:
    chunks, timings = [], {}
    for source in state["selected_sources"]:
        start = time.perf_counter()
        chunks += SOURCE_FUNCTIONS[source](state["question"])
        timings[source] = round((time.perf_counter() - start) * 1000, 2)  # latency per source
    return {"retrieved": chunks, "timings_ms": timings}


def merge_node(state: RouterState) -> dict:
    merged = merge_context(state["retrieved"])
    return {"merged_context": merged["context"], "merge_stats": merged["stats"]}


def generate_node(state: RouterState) -> dict:
    answer, llm_used = generate_answer(state["question"], state["merged_context"])
    result = {"answer": answer, "llm_used": llm_used}
    # store the finished bundle so repeated/similar questions are served from cache
    cache_set(state["question"], {
        "selected_sources": state["selected_sources"],
        "retrieved": state["retrieved"],
        "merged_context": state["merged_context"],
        "merge_stats": state["merge_stats"],
        "timings_ms": state["timings_ms"],
        **result,
    })
    add_to_memory(state["question"], answer[:200])
    return result


def after_cache(state: RouterState) -> str:
    """Conditional edge: cache hit -> finish, miss -> run the full pipeline."""
    return "done" if state.get("cache_hit") else "route"


def build_graph():
    g = StateGraph(RouterState)
    g.add_node("check_cache", check_cache_node)
    g.add_node("route", route_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("merge", merge_node)
    g.add_node("generate", generate_node)

    g.set_entry_point("check_cache")
    g.add_conditional_edges("check_cache", after_cache, {"done": END, "route": "route"})
    g.add_edge("route", "retrieve")
    g.add_edge("retrieve", "merge")
    g.add_edge("merge", "generate")
    g.add_edge("generate", END)
    return g.compile()


graph = build_graph()

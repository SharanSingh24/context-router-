# Multi-Source Context Merge Router

Question -> **route** (pick sources) -> **retrieve** (docs / SQLite / memory) -> **merge** (dedupe + token budget) -> **LLM** -> answer.
Repeated questions are served from a **cache**; the cache is invalidated when data changes.

## Run in VS Code
```
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # Mac/Linux: cp .env.example .env
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs -> POST /ask -> "Try it out".

Sample questions:
- `What are the marks of Rahul?`            (DB only)
- `What is the hostel gate timing?`         (docs only)
- `Is Priya eligible for the scholarship?`  (DB + docs merged)
- Ask any one twice -> `cache_hit: true`

Run tests: `python tests/test_pipeline.py`

## Turn on real AWS Bedrock
1. AWS console -> Bedrock -> **Model access** -> enable a model (e.g. Amazon Nova Lite).
2. `pip install awscli`, then `aws configure` (access key, secret, region `us-east-1`).
3. In `.env` set `USE_BEDROCK=true` (and `BEDROCK_MODEL_ID` if you chose another model).
4. Restart uvicorn. The response field `llm_used` should say `bedrock`.
If it fails, it silently falls back to the mock LLM and prints the reason in the terminal.

## Files
| File | Job |
|---|---|
| app/router.py | decides which sources are relevant (context routing) |
| app/sources.py | docs, SQLite and memory connectors |
| app/merger.py | de-duplication, source-priority conflict resolution, token budget |
| app/cache.py | cache of merged contexts + data-fingerprint invalidation |
| app/graph.py | LangGraph: check_cache -> route -> retrieve -> merge -> generate (conditional edge on cache hit) |
| app/llm.py | Bedrock with mock fallback |
| app/main.py | FastAPI endpoints: /ask, /reset, /stats |

## Mapping to the full AWS design (viva answer)
| Project PDF | This MVP | Production version |
|---|---|---|
| Bedrock | llm.py | same |
| Lambda connectors | sources.py functions | one Lambda per source |
| Step Functions / LangGraph on ECS | graph.py | same graph, containerised (Dockerfile) |
| ElastiCache Redis | cache.py dict | Redis |
| OpenSearch / RDS | docs keyword search / SQLite | vector search / RDS |
| CloudWatch | `latency_ms_per_source` in response | CloudWatch metrics |
# context-router-
# context-router-

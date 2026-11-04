# ShopAssist — Mini-Project 1

<!-- TODO MP1-T6: replace every line marked TODO in this file. Delete this comment when done. -->

Order support for Northwind Store (a fictional online store): a FastAPI service with per-session memory, three
validated tools, a defended system prompt and streamed answers. The model is reached only through a LiteLLM
gateway, and both run together with Docker Compose.

**Author:** TODO (name, GitHub username)
**Model tested:** TODO (the model group and the real model behind it, e.g. `shopassist` → `groq/openai/gpt-oss-20b`)

## Architecture

```
browser / client ──► app (FastAPI, :8000) ──► litellm gateway (:4000) ──► Groq
                     memory · prompt · tools    master key · fallback · cost      API_KEY lives only here
```

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Liveness, plus the running model, gateway, memory strategy and tools |
| POST | `/chat` | `{"session_id", "message"}` → `{"answer", "tool_steps", "turns"}` |
| POST | `/chat/stream` | The same, streamed as Server-Sent Events: `tool`, `token`…, `done` |
| DELETE | `/sessions/{id}` | Forget one conversation |

## Run with Docker Compose (Path A)

```powershell
docker compose up --build        # gateway + app; Ctrl+C to stop, docker compose down to remove
```
Then open http://localhost:8000/docs. TODO: one sentence on how to check it's working (which URL, what you see).

## Run without Docker (Path B)

```powershell
uv sync
# terminal 1 - the gateway
uv run --with "litellm[proxy]==1.80.0" litellm --config gateway/config.yaml --port 4000
# terminal 2 - the app
uv run uvicorn app.main:app --port 8000
```

## Evidence

```powershell
uv run python eval/run_eval.py      # needs the gateway running; writes experiments/mp1_results.md
```
Results: TODO (copy the four summary lines from `experiments/mp1_results.md`). Discussion: `experiments/mp1_report.md`.

## Design

TODO: 4-6 sentences. Which memory strategy and why, what the three tools do and how bad arguments are handled,
how the prompt defends itself, what the gateway adds, and the biggest limit you know about.

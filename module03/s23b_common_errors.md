# S23b common errors — gateway + Docker

| You see | What it means | Fix |
|---|---|---|
| `docker : The term 'docker' is not recognized` | Docker Desktop isn't installed, or the install is half-finished | Install Docker Desktop, restart, **open Docker Desktop once**. Or use Path B / Codespaces |
| `error during connect` / `Is the docker daemon running?` | Docker Desktop is installed but not running | Start Docker Desktop and wait for "Engine running" |
| Build stops at `pip install` with a network error | Wi-Fi / proxy blocked the download | Retry on a better network; or use Path B |
| `env file ../../.env not found` | You're not in the course repo, or `.env` is missing | `cd <course repo>\module03\s23b_gateway`; check `..\..\.env` exists |
| `Bind for 0.0.0.0:4000 failed: port is already allocated` | Something already uses port 4000 (another gateway?) | `docker compose down`; close other gateway terminals; or change `"4000:4000"` to `"4001:4000"` |
| `curl ... 401` with the key | The key doesn't match the gateway's master key | Use `sk-class-1234`; Path B: `LITELLM_MASTER_KEY=sk-class-1234` must be in `.env` |
| `AuthenticationError` / `Invalid API Key` in the gateway log | `API_KEY` in your `.env` isn't a valid Groq key (Ollama users have `API_KEY=ollama`) | Put your Groq key in `API_KEY` for this session |
| `NotFoundError` ... model on BOTH groups | Groq retired a model | `uv run python list_models.py`; put two available models in `config.yaml`; restart |
| Client says `The gateway is not reachable at http://localhost:4000` | The gateway isn't running, or still starting | Wait for `Uvicorn running on ...:4000` in the gateway terminal |
| App's `/ask` returns 500, log says `Connection refused` to `localhost:4000` | The app is using localhost inside its container | `PROXY_URL` must be `http://litellm:4000` (the service name) |
| `/ask` returns 422 | The request body didn't match: it must be `{"question": "..."}` | Fix the JSON — your code never ran, no tokens spent |
| Changed `config.yaml` but nothing happens | The gateway reads it only at start | `docker compose restart litellm` (Path B: Ctrl+C and start again) |
| `curl` in PowerShell shows a table, not text | PowerShell's `curl` is a different command | Type `curl.exe` |

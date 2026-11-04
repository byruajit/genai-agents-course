# Session 23b · Gateway + Docker
## Run the LiteLLM proxy as your company's LLM gateway — in containers

Today is a **terminal** session, not a notebook. You type every command yourself. Each step says **what you type**,
**what you should see**, and **why**.

---

## Part A · Read before you start (10 minutes)

### A1. Why this session matters
In S22 you used LiteLLM as a **library** inside one Python program. Real companies run LiteLLM as a **server** — a
**gateway** — that every app talks to:

```
 BEFORE (S22)                                   TODAY (S23b)
 your app ─► LiteLLM library ─► Groq            any app ─► LiteLLM GATEWAY (:4000) ─► Groq (primary)
 (keys + fallbacks inside each app)                         keys · fallbacks · logs     └► Groq (backup)
                                                (apps know ONE url and ONE key — nothing else)
```
And real companies ship apps in **containers** — the same box runs on your laptop, a colleague's laptop and the
cloud. Mini-Project 1 (ShopAssist) uses **both**: your app + the gateway, started with one command.

### A2. The words you need today
| Term | What it is | Say it as |
|---|---|---|
| **Gateway (LiteLLM proxy)** | LiteLLM running as a server. Apps call one OpenAI-style URL; it routes, falls back, logs. | "One front door to every model." |
| **`config.yaml`** | The gateway's settings: which models, under which names, fallbacks, timeouts, the master key. | "The gateway's rule book." |
| **Model group** | A name apps ask for (`shopassist`), mapped to a real model in `config.yaml`. | "Ask for the role, not the person." |
| **Master key** | The key every app must send to the gateway. Without it: **401**. | "The building pass." |
| **Virtual key** | Per-team keys with budgets. Needs a database (Postgres) — **concept only today**. | "A pass with a spending limit." |
| **Image** | A packaged app + everything it needs, built from a `Dockerfile`. | "The recipe, baked." |
| **Container** | A running copy of an image. | "The dish, served." |
| **Dockerfile** | The step-by-step recipe for an image. | "The recipe card." |
| **Port mapping** `4000:4000` | Laptop port : container port. | "The door number outside : inside." |
| **Docker Compose** | Starts several containers together from `docker-compose.yml`. | "One switch for the whole kitchen." |
| **Service name** | Inside Compose, containers reach each other by name: `http://litellm:4000`. | "Call the colleague by name, not 'me'." |

### A3. What's in the folder (all GIVEN — you read, run and change; you don't write it from scratch)
```
module03/s23b_gateway/
├─ config.yaml          the gateway's rule book (shopassist → gpt-oss-20b, backup → gpt-oss-120b)
├─ docker-compose.yml   two services: litellm (gateway) + app
├─ proxy/Dockerfile     builds the gateway image (python:3.12-slim + litellm[proxy]==1.80.0)
└─ hello_app/           a 30-line FastAPI app that ONLY knows the gateway's URL and key
   ├─ app.py
   └─ Dockerfile
module03/s23b_client.py talks to the gateway and prints what it reports (model used, fallbacks, cost)
```

### A4. Rules
- Your Groq key stays in your course `.env` as `API_KEY`. It is **never** written into `config.yaml`, a Dockerfile or an image.
- `sk-class-1234` is a **classroom** master key for your laptop only.
- ChatGPT: paste the version card first (litellm 1.80.0, Docker Compose v2); never paste your `.env`.

---

## Part B · Lab

### Step 0 · Before class (homework from S23) — 2 minutes to check
```powershell
docker --version
docker compose version
docker run hello-world
```
**You should see:** versions, then "Hello from Docker!". **No Docker?** Use **Path B** (no Docker) in steps 2–5, and
GitHub Codespaces for step 6.

### Step 1 · Pull and look (5 min)
```powershell
cd <your course repo folder>
git pull
code module03\s23b_gateway\config.yaml
```
**Read it together:** two model groups, one fallback rule, the master key read from the environment.
**Check yourself:** what does an app put in `model=` — `groq/openai/gpt-oss-20b` or `shopassist`? (**shopassist**.)

### Step 2 · Start the gateway (10 min)
**Path A — Docker (recommended):**
```powershell
cd module03\s23b_gateway
docker compose up --build litellm
```
First time: it downloads Python and builds the image (2–5 minutes). Wait for a line like
`Uvicorn running on http://0.0.0.0:4000`. **Leave this terminal open** — it's the gateway's log.

**Path B — no Docker:** add one line to your course `.env`: `LITELLM_MASTER_KEY=sk-class-1234`, then from the course repo folder:
```powershell
uv run --with "litellm[proxy]==1.80.0" litellm --config module03\s23b_gateway\config.yaml --port 4000
```

### Step 3 · Is it alive? Who may use it? (5 min) — in a SECOND terminal, course repo folder
```powershell
curl.exe http://localhost:4000/health/liveliness
curl.exe http://localhost:4000/v1/models -H "Authorization: Bearer sk-class-1234"
curl.exe -s -o NUL -w "%{http_code}" http://localhost:4000/v1/models
```
**You should see:** `"I'm alive!"`, then the two groups `shopassist` and `shopassist-backup`, then **401** (no key → refused).
(Windows: type `curl.exe`, not `curl` — in PowerShell `curl` is a different command.)

### Step 4 · Talk to it (10 min)
```powershell
uv run python module03/s23b_client.py
```
**You should see:** PART 1 — an answer, tokens, **model group used: shopassist**, fallbacks tried: 0, a cost;
PART 2 — the same answer through LangChain; PART 3 — **401**.
**Point at PART 2:** it's your S21 `ChatOpenAI`, unchanged except `model`, `base_url` and `api_key`.
**Watch the first terminal:** every request appears in the gateway's log.

### Step 5 · Break the primary — watch the gateway save you (10 min)
In `config.yaml`, change the first model to `groq/model-that-does-not-exist`. Save. Restart the gateway:
- Path A: `docker compose restart litellm` (no rebuild needed — the file is mounted)
- Path B: Ctrl+C in the gateway terminal, run the step 2 command again

Run the client again. **You should see:** `model group used: shopassist-backup`, `fallbacks tried: 1`, a slower answer.
**The app changed nothing.** The fallback lives in the gateway now, for every app at once.
**Put the model back** to `groq/openai/gpt-oss-20b` and restart.

### Step 6 · Two containers, one command (15 min)
Stop the gateway (Ctrl+C). Then:
```powershell
cd module03\s23b_gateway
docker compose up --build
```
Open **http://localhost:8000/docs** → `POST /ask` → *Try it out* → `{"question": "Can I return shoes after 5 days?"}` → Execute.
**You should see:** an answer from ShopAssist. Read `docker-compose.yml`: the app calls **`http://litellm:4000`** — the
**service name**. `localhost` inside the app container would mean *the app container itself*.
Stop everything: Ctrl+C, then `docker compose down`.

### Step 7 · Checkpoint (5 min)
```powershell
uv run pytest tests/test_s23b.py -rs
```
Offline checks pass anywhere; the live check runs only while the gateway is up on port 4000.

---

## Part C · Wrap-up

### C1. Summary
- A **gateway** is LiteLLM as a server: apps send `model="shopassist"` + a key to one URL; the gateway picks the real model.
- **`config.yaml`** holds model groups, fallbacks, timeouts and the master key — change it, restart, every app gets the change.
- **Images** are built from Dockerfiles; **containers** run them; **Compose** starts several together.
- Inside Compose, containers call each other **by service name** (`litellm:4000`), never `localhost`.
- Keys come in at **run time** (`env_file`, `environment`) — never baked into an image.

### C2. Honest limits
- Virtual keys, budgets and spend dashboards need **Postgres** next to the gateway — next step in a real deployment (Module 13).
- One gateway container is a single point of failure — production runs two or more behind a load balancer.
- Both models here are on Groq: a Groq outage takes both down. Real fallbacks cross providers.

### C3. Interview questions
1. **Why put a gateway in front of LLMs?** One place for keys, routing, fallbacks, budgets and logs; apps stay thin and provider-agnostic.
2. **Image vs container?** An image is the packaged recipe; a container is a running instance of it.
3. **Why does the app call `litellm:4000`, not `localhost:4000`?** Inside a container, localhost is the container itself; Compose gives each service a hostname.
4. **How do you keep API keys out of images?** `.dockerignore` excludes `.env`; keys are passed at run time via env vars or a secrets manager.
5. **What happens if the gateway goes down?** Every app loses model access — so run replicas with health checks.

### C4. Homework (before the Mini-Project 1 weekend)
1. Make Step 6 work end to end on your laptop (or Codespaces).
2. Add a third model group `shopassist-cheap` in `config.yaml` and call it from `s23b_client.py` with `model="shopassist-cheap"`.
3. Read `module03/s23b_common_errors.md` once — you will meet these errors in Mini-Project 1.

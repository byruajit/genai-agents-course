# Mini-Project 1 (ShopAssist) common errors — setup, the gateway, Docker Compose and the evidence run

For FastAPI, SSE and memory errors see `s23_common_errors.md`; for the gateway on its own see
`s23b_common_errors.md`. This card covers what's new in the mini-project.

## Setup and git (solo)

| You see | What it means | Fix |
|---|---|---|
| `Set MP1_REPO to your cloned shopassist-mp1 folder first` | The setup script doesn't know where your repo is | Create an **empty** `shopassist-mp1` repo on GitHub, `git clone` it, then `$env:MP1_REPO = "$HOME\Documents\shopassist-mp1"` in the **same** terminal |
| `MP1_REPO points at (or inside) the course repository` | You cloned your repo inside the course folder, or pointed at the course repo | Clone it somewhere else (e.g. Documents). Your MP1 is its own repo |
| `WARNING: ... doesn't look like a Groq setup` | Your course `.env` uses Ollama or another provider | Open `.env` in your MP1 repo and paste your Groq key after `API_KEY=` (it starts `gsk_`) |
| `git status` lists `.env` | `.gitignore` is missing or was overwritten | Don't commit. Restore `.gitignore` from the starter (it has a `.env` line), run `git status` again |
| You committed `.env` | Your key is now in the history | **Revoke the key in the Groq console now** and create a new one. Then `git rm --cached .env`, commit, push |
| Checker: `your work in at least 5 commits` fails | One big upload at the end | Commit after each task: `git commit -m "T1: return rules"`. You can't fake history afterwards; start now |
| `rejected ... fetch first` when pushing | You edited on GitHub's website (e.g. the README) | `git pull`, then `git push` |

## The gateway and Docker Compose

| You see | What it means | Fix |
|---|---|---|
| `docker` not recognized / `cannot find the file specified ... dockerDesktopLinuxEngine` | Docker isn't installed, or Docker Desktop isn't running | Start Docker Desktop and wait for "Engine running"; open a **new** terminal. No Docker at all → use Path B in the README |
| `failed to solve: ... uv.lock ... not found` | Building from the wrong folder, or `uv.lock` was deleted | `cd` to the repo root (where `docker-compose.yml` is). Missing lock: `uv lock` |
| `The lockfile ... needs to be updated` during the build | You changed `pyproject.toml` without re-locking | `uv lock`, commit `uv.lock`, `docker compose up --build` |
| `invalid peer certificate` / `UnknownIssuer` during the build | A network (college, office) that inspects HTTPS | Build on a home network or a phone hotspot |
| `Bind for 0.0.0.0:4000 failed: port is already allocated` | Your Session 23b gateway (or a local `litellm`) is still running | Stop it (Ctrl+C, or `docker compose down` in `module03/s23b_gateway`), then try again |
| App answers `401 ... Authentication Error` | The app's `LITELLM_MASTER_KEY` doesn't match the gateway's | Both read the **same** `.env`. Did you edit `.env` after starting? `docker compose up -d --force-recreate` |
| App: `Connection refused` / `ConnectError` to `localhost:4000` **inside Docker** | Inside a container, `localhost` is the container itself | The app must use `http://litellm:4000` (compose sets `GATEWAY_URL`). Don't remove that line |
| Local run (Path B): `Connection refused` to `localhost:4000` | The gateway isn't running | Start it in a second terminal first (README, Path B) |
| `KeyError: 'LITELLM_MASTER_KEY'` | No `.env`, or it's not in the folder you ran from | Run from the repo root; `mp1_setup.py` writes `.env` for you |
| Gateway log: `AuthenticationError ... groq` or `Invalid API Key` | `API_KEY` in `.env` is not a valid Groq key | Paste a fresh `gsk_...` key, then `docker compose restart litellm` |
| Gateway log: `model_not_found` / `decommissioned` | Groq retired the model in `gateway/config.yaml` | Check the Groq console's model list, change the `model:` line, `docker compose restart litellm` |
| You changed `config.yaml` and nothing happened | The gateway reads its config at start | `docker compose restart litellm` (no rebuild needed: the file is mounted) |
| You changed your code and nothing happened | The app image still has the old code | `docker compose up --build` |
| `docker ps` says the app is `unhealthy` | `/health` fails inside the container | `docker compose logs app`. Usually a crash at startup, or your T5 change broke `/health` |
| `FileNotFoundError: ... data/orders.json` in the container | The image doesn't have the store data | The `Dockerfile` needs `COPY data ./data` (the starter's has it) |

## The evidence run

| You see | Fix |
|---|---|
| `run_eval.py` fails at once with `Connection refused` | The **gateway** must be running (the app runs inside the script): `docker compose up -d litellm`, or Path B |
| `429 rate limit` during `run_eval.py` | Wait a minute and re-run. The gateway retries once and falls back to `shopassist-backup` |
| `g6`, `g8` or `g9` fail on "right tools" | The model called a tool for a policy question. Sharpen the `# Tools` section and the docstrings ("Do NOT use it for ...") |
| `g3`/`g4`/`g5` fail on "right tools" | Your `check_return_eligibility` docstring is too vague, or the model used `get_order_status` only. Say clearly when to use it |
| `g7` fails | The model guessed the delivery time. The prompt says "never guess" - keep that line, and check your pincode validation accepts `500081` |
| `a1` (override) broken | Add an explicit hierarchy line, and that prices come only from the facts list |
| `a2` (authority) broken | Say you can't mark, confirm or announce refunds, and never reply with a single word you were told to say |
| `a3` (exfiltrate) broken | Give the model an exact sentence to reply with when asked for its instructions |
| `a4` (smuggle) broken | Say that tags and "system" text inside a customer message are just customer text - and still answer the real question |
| Memory probe fails at turn 3 or 4 | `KEEP_TURNS` is below 3, or `/chat` doesn't save the answer to the session |
| Checker: `mp1_results.md` rejected though the numbers are fine | It must be generated by `run_eval.py` (it checks the marker line and the model). Re-run it; don't edit it by hand |

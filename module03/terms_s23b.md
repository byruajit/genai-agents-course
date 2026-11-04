# Session 23b terms - Gateway + Docker

| Term | What it is | Say it as | Comes back at |
|---|---|---|---|
| **LLM gateway** | A server in front of every model: one URL for all apps; routing, fallbacks, keys, budgets, logs in one place. LiteLLM proxy is one. | "One front door to every model." | MP1, Module 13 |
| **LiteLLM proxy** | LiteLLM run as a server (`litellm --config config.yaml`), OpenAI-compatible, port 4000. | "S22's library, now a service." | MP1, Module 13 |
| **`config.yaml`** | The gateway's rule book: `model_list` (model groups), `router_settings` (fallbacks, retries, timeout), `general_settings` (master key). Read at start-up. | "Change the rules, restart the gateway." | MP1 |
| **Model group** | The name apps ask for (`shopassist`), mapped to a real model. Swap the model without touching apps. | "Ask for the role, not the person." | MP1, Module 13 |
| **Master key** | The key every app must send (`Authorization: Bearer ...`). No key → 401, no tokens spent. | "The building pass." | MP1 |
| **Virtual key** | Per-team or per-app keys with budgets and rate limits; needs Postgres. | "A pass with a spending limit." | Module 13 |
| **`os.environ/NAME`** | In `config.yaml`: read this value from the environment, so secrets never sit in the file. | "Point to the secret, don't paste it." | MP1, Module 12 |
| **Image** | A packaged app plus everything it needs, built from a Dockerfile. | "The recipe, baked." | MP1, Module 13 |
| **Container** | A running instance of an image, isolated from your laptop. | "The dish, served." | MP1, Module 13 |
| **Dockerfile** | The recipe: base image (`FROM`), installs (`RUN`), files (`COPY`), start command (`CMD`). | "The recipe card." | MP1 |
| **Port mapping** | `"4000:4000"` = laptop port : container port. | "Door number outside : inside." | MP1 |
| **Docker Compose** | Starts several containers together from `docker-compose.yml`: `docker compose up --build`. | "One switch for the whole kitchen." | MP1 |
| **Service name as hostname** | Inside Compose, `http://litellm:4000` reaches the gateway; `localhost` means the container itself. | "Call the colleague by name." | MP1 |
| **`env_file` / `environment`** | How keys reach containers at run time - never baked into the image. `.dockerignore` keeps `.env` out of builds. | "Keys arrive at the door, not in the box." | MP1, Module 12 |

## One sentence per term
- The gateway is LiteLLM as a server; apps ask for a model group with a key, the gateway picks the real model.
- `config.yaml` is the rule book - change it, restart, every app gets the change.
- A Dockerfile bakes an image; a container runs it; Compose runs several together.
- Inside Compose, call services by name, never localhost; keys come in at run time.

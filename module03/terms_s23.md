# Session 23 terms - serving BankAssist: an API, memory, streaming

Read this before the notebook. Each term: what it is, how to say it out loud, and where it comes back.

| Term | What it is | Say it as | Comes back at |
|---|---|---|---|
| **API (web API)** | A program that other programs talk to over HTTP. Until today BankAssist was a script only you could run; now a website, an app or a teammate's code can use it. | "A counter with a window: hand in a request, get a reply." | S23 (Mini-Project 1), MCP servers, cloud deployment |
| **Endpoint / route** | One URL + one HTTP method that does one job: `GET /health`, `POST /chat`. In FastAPI, a decorator (`@app.get`, `@app.post`) on a normal function. | "One window at the counter." | MP1 |
| **GET vs POST** | GET asks for something and sends no body. POST sends a body (here: JSON with `session_id` and `message`). | "Asking vs handing in a form." | MP1 |
| **FastAPI** | The Python framework that turns functions into endpoints, checks requests with Pydantic, and writes the `/docs` page for you. | "Flask with type hints and free documentation." | MP1, MCP servers, cloud deployment |
| **uvicorn** | The server program that runs a FastAPI app and listens on a port (8000 today). FastAPI describes the app; uvicorn runs it. | "The shop building; FastAPI is the shop." | S23 (inside Docker) |
| **Request / response model** | Pydantic classes (`ChatRequest`, `ChatResponse`) that describe exactly what comes in and goes out. A bad request is rejected before your code runs. | "The form, with required boxes." | MP1, agents (structured output) |
| **Status code** | The number on every HTTP reply. 200 OK, 404 no such endpoint, **422 the request didn't match the model**, 500 your code crashed. | "The traffic light on the reply." | MP1 |
| **Session** | One conversation, named by a `session_id` the client sends. The server keeps one history per session in `SESSIONS`. | "One customer's file." | MP1, agents (LangGraph checkpoints) |
| **Server-side memory** | The API is still stateless (S19). Now the SERVER keeps the list and resends it - not the notebook, not the client. In RAM: a restart forgets everyone. | "The clerk's notebook, not the customer's." | MP1, agents (persistent memory) |
| **Streaming** | Sending the answer in pieces as the model writes it (`llm.stream(...)`), so the first words appear in about a second instead of after the whole answer. Total time is the same; *waiting* time is not. | "A tap, not a bucket." | MP1, cloud deployment |
| **SSE (Server-Sent Events)** | A simple format for streaming over HTTP: blocks of `event: ...` and `data: ...` lines, each ended by a blank line. Media type `text/event-stream`. One direction only: server to client. | "A ticker tape." | MP1 |
| **TestClient** | FastAPI's way to send real HTTP requests to your app inside Python, without starting a server. The checker uses it. | "A rehearsal with no audience." | S23 (your project's tests) |
| **LiteLLM** (from S22) | One call format for ~100 providers, with fallbacks and cost tracking; also runs as a gateway server. Plugs into this server only through `make_llm()`. | "One plug adapter for every country." | S23b (as a gateway), MP1 |

## One sentence per term, if you only have thirty seconds
- An endpoint is a decorated function; FastAPI describes the app and uvicorn runs it.
- Pydantic models reject bad requests with a 422 before they cost a token.
- The server now keeps each session's history and resends a window of it - in RAM, so a restart forgets.
- Streaming doesn't make the answer faster; it makes the *wait* shorter.
- SSE is `event:` + `data:` + a blank line, sent as `text/event-stream`.

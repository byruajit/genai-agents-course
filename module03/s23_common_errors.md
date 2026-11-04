# S23 common errors — read the LAST line of the error first, then find it here

Two terminals today: the **server** terminal (where `app.py` runs) shows your code's errors; the **client** terminal
only shows the status code. When the client says 500, look at the server terminal.

| You see | What it means | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'fastapi'` (or `'uvicorn'`) | Today's packages aren't installed | In the course repo folder: `git pull` then `uv sync` |
| `KeyError: 'MODEL'` when the server starts | Your `.env` wasn't found | Start the server from the **course repo folder**: `uv run python $env:WORK_REPO\s23\app.py` |
| Client: `Nothing is listening on http://127.0.0.1:8000` | The server isn't running, or it crashed at start | Start it in the other terminal; read its last line if it stopped |
| `[Errno 10048] ... only one usage of each socket address` / `address already in use` | A server from earlier is still running on port 8000 | Find the old terminal and press Ctrl+C. Can't find it? Close all VS Code terminals and start again |
| You changed `app.py` but nothing changed | The server still runs the old code | Ctrl+C in the server terminal, then start it again — after **every** change |
| Client: `500 Internal Server Error` | Your code crashed inside an endpoint | Read the server terminal. `NotImplementedError: TODO 4` = not done yet |
| `422 Unprocessable Entity` | The request didn't match `ChatRequest` (empty message, missing `session_id`, wrong spelling) | Often the point (TODO 2). If not: check the JSON keys are exactly `session_id` and `message` |
| `404 Not Found` | No endpoint with that URL **and** method | Check the spelling (`/chat/stream`) and the decorator (`@app.post`, not `@app.get`) |
| `405 Method Not Allowed` | The URL exists, but with a different method | You sent GET to a POST endpoint — e.g. opened `/chat` in a browser. Use `/docs` or the client |
| `pydantic ... ValidationError: ... tool_steps Field required` (a 500) | You added `tool_steps`/`turns` to `ChatResponse` but didn't fill them in `chat()` | `return ChatResponse(session_id=..., answer=..., tool_steps=steps, turns=len(history) // 2)` |
| The second message doesn't remember the first | The turn wasn't saved, or each call made a new list | `history = SESSIONS.setdefault(req.session_id, [])` then `history += [HumanMessage(...), AIMessage(answer)]` |
| Every session remembers everyone | You used one shared list instead of `SESSIONS[session_id]` | One list **per** `session_id` |
| The stream arrives all at once, at the end | Wrong media type, or your client buffers | `media_type="text/event-stream"`. In your own client: `print(..., flush=True)` |
| Stream works but `/chat` afterwards doesn't remember it | The stream didn't save the turn | In `events()`, extend `history` when `kind == "done"` |
| `json.decoder.JSONDecodeError` in the client | `sse()` sent `data: {'text': ...}` (a Python dict, single quotes) | `json.dumps(data)`, not `data` or `str(data)` |
| The model calls `get_rate` for "Hi, my name is Priya" | A small model over-using tools — S20's problem, not your bug | Normal on llama3.2:3b. It's one of the things you'll measure in Mini-Project 1 |
| The model says "you mentioned earlier..." in a brand-new session | The model **invented** a memory it doesn't have | Not a leak: check `SESSIONS` — that session's list is empty. Models fill gaps confidently |

**Still stuck after 5 minutes?** Paste the **last 15 lines of the server terminal** (never your `.env`) into ChatGPT
*after* the version card, or put your hand up.

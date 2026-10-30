# S21 common errors — read the LAST line of the error first, then find it here

| You see (last line of the error) | What it means | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'langchain_openai'` | The new S21 packages aren't installed | In the course repo folder: `git pull` then `uv sync` |
| `KeyError: 'MODEL'` (or `'BASE_URL'`, `'API_KEY'`) | Your `.env` wasn't found | Run from the **course repo folder**: `uv run python $env:WORK_REPO\s21\bankassist_lc.py` — not from inside your work repo |
| `STEP 3: not done yet (TODO 3)` | Not an error: that TODO still has `raise NotImplementedError` | Replace the `raise ...` line with your code |
| `ImportError: cannot import name 'LLMChain'` / `No module named 'langchain.chat_models'` / `langchain_community` | Old LangChain code, usually from ChatGPT | Paste `s21_version_card.md` into ChatGPT first; use only the imports already at the top of your file |
| `NameError: name 'get_rate' is not defined` | You used a name on a line *above* the place it's defined — Python reads the file top to bottom | Move the `@tool def get_rate(...)` block **above** the line that uses it (e.g. `TOOLS[...] = get_rate`), or remove it from that line if you haven't written it yet |
| `openai.NotFoundError: ... model ... not found` (404) | `MODEL` in `.env` doesn't match a model your provider has | Ollama: `ollama list` and copy the name exactly. Groq: `uv run python list_models.py` |
| `openai.APIConnectionError` / `Connection refused` | Ollama isn't running (if `BASE_URL` is localhost) | Start the Ollama app, or run `ollama serve` |
| `AttributeError: 'str' object has no attribute 'tool_calls'` | You called the **chain** (which returns text) inside `ask()` | `ask()` must call `llm_with_tools.invoke(messages)`, which returns an `AIMessage` |
| `KeyError: 'some_name'` inside `ask()` | The model asked for a tool that isn't in `TOOLS` — an invented tool name (small models do this) | Not your bug. Homework: check `call["name"] in TOOLS` and send an error back instead of crashing |
| `pydantic ... ValidationError ... Input should be a valid number` | The model sent a bad argument (e.g. `"abc"`) — your type hints caught it | Not your bug. It shows type hints give you part of S20's Fix B for free |
| `ZeroDivisionError` | The model sent `0` (or `"0"`) as the rate | Not your bug. Type hints don't check *ranges* — validation in code is still your job (homework) |
| `openai.BadRequestError ... tool_call_id` | A tool result was sent without the model's request before it | In `ask()`, `messages.append(ai)` must come **before** the tool results |
| The script never ends / repeats `step` lines forever | Your loop has no cap | Use `for step in range(1, max_steps + 1):`, not `while True:` |
| `STEP 4:` prints an answer but no `step 1: calculate_emi(...)` line | The model answered in words without calling the tool | Normal sometimes, especially on small models. Run again; check the docstring says when to use the tool |

**Still stuck after 5 minutes?** Paste the **last 15 lines** of the error (never your `.env`) into ChatGPT *after* the version card, or put your hand up.

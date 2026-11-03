# S22 common errors — read the LAST line of the error first, then find it here

| You see | What it means | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'litellm'` | Today's package isn't installed | In the course repo folder: `git pull` then `uv sync` |
| `STEP n: not done yet (TODO n)` | Not an error: that TODO still has `raise NotImplementedError` | Replace the `raise ...` line with your code |
| `STEP 4: not done yet (TODO 1)` | Step 4 needs `ask_once()` from TODO 1 | Finish TODO 1 first |
| `KeyError: 'MODEL'` / everything says "not set" | Your `.env` wasn't found | Run from the **course repo folder**: `uv run python $env:WORK_REPO\s22\bankassist_llm.py` |
| `AuthenticationError` ... `Invalid API Key` | Wrong or missing Groq key for that model | Check `API_KEY` in `.env`. On Ollama with a Groq fallback, add `GROQ_API_KEY=...` |
| `NotFoundError` / `model_not_found` / `decommissioned` on the FALLBACK | That Groq model was retired | `uv run python list_models.py`, pick another small model, add `LLM_FALLBACK=groq/<name>` to `.env` |
| `BadRequestError: LLM Provider NOT provided` | The model string has no provider prefix | Use `groq/...` or `ollama_chat/...`, never just `gpt-oss-20b` |
| `APIConnectionError` / `Connection refused` on `ollama_chat/...` | Ollama isn't running | Start the Ollama app, or `ollama serve` |
| `RateLimitError` (429) | Groq's free-tier limit for that model | Wait a minute, or let STEP 3's fallback handle it — that's the point of today |
| STEP 3 says `answered by groq/model-that-does-not-exist` | Your Router has no fallback | Check `fallbacks=[{"bankassist": ["bankassist-backup"]}]` — names must match `model_name` exactly |
| STEP 3 takes several seconds | Normal: the primary fails, LiteLLM retries once (`num_retries=1`), then falls back | Set `num_retries=0` to see the difference — and discuss why retries help in production |
| `Exception: This model isn't mapped yet` | No price for that model (Ollama, new models) | In `cost_line`, wrap `cost_per_token` in `try/except` and use `0.0` |
| `$0.000000` for a Groq model | The model string you priced isn't the one that answered | Price `answered_by(response)`, not the name you asked for |
| ChatGPT's code uses `acompletion`, `async`, proxy or callbacks | It ignored the version card | Paste `s22_version_card.md` again: "use only the APIs on the card" |

**Still stuck after 5 minutes?** Paste the **last 15 lines** of the error (never your `.env`) into ChatGPT *after* the version card, or put your hand up.

"""Session 22 - BankAssist with LiteLLM: one call format, many models, fallbacks and cost.

This is YOUR file. Copy it into your work repository (the notebook's Section 1 does this for you):
    <your genai-course-work>/s22/bankassist_llm.py
then fill in the TODOs, one at a time, in order.

Run it after every TODO, from the COURSE repository folder (so your .env is found):
    uv run python $env:WORK_REPO\\s22\\bankassist_llm.py        (Windows PowerShell)
    uv run python $WORK_REPO/s22/bankassist_llm.py              (macOS / Linux)

Each step prints its result or "not done yet". You never have to finish everything before running.

Same three ChatGPT rules as Session 21: paste module03/s22_version_card.md first, NEVER paste your .env or
API key, and ask it to explain or fix YOUR code - you must be able to explain every line you hand in.
"""
import logging
import os
import time

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")   # use the price list shipped with litellm 1.80.0

import litellm  # noqa: E402
from dotenv import find_dotenv, load_dotenv  # noqa: E402
from litellm import Router, completion, cost_per_token  # noqa: E402

load_dotenv(find_dotenv(usecwd=True), override=True)
litellm.suppress_debug_info = True
logging.getLogger("LiteLLM Router").setLevel(logging.CRITICAL)   # STEP 3 fails ON PURPOSE - hide the long traceback

SYSTEM = ("You are BankAssist, Northwind Bank's assistant. Branches are open 10am-4pm Monday to Friday "
          "and 10am-1pm on Saturday. Home loan rates: 8.5% floating, 9.0% fixed. Answer in 2-3 sentences.")

# ---------------------------------------------------------------- model strings (given - read, don't change)
# LiteLLM names every model as "provider/model". Your .env already says which model you use:
#   Groq   : MODEL=openai/gpt-oss-20b  -> "groq/openai/gpt-oss-20b"
#   Ollama : MODEL=llama3.2:3b         -> "ollama_chat/llama3.2:3b"
# You can override either one in .env with LLM_PRIMARY=... and LLM_FALLBACK=...
_on_ollama = "11434" in os.getenv("BASE_URL", "")
PRIMARY = os.getenv("LLM_PRIMARY") or (("ollama_chat/" if _on_ollama else "groq/") + os.getenv("MODEL", "openai/gpt-oss-20b"))
FALLBACK = os.getenv("LLM_FALLBACK") or "groq/openai/gpt-oss-120b"   # a second Groq model (check: uv run python list_models.py)


def params(model: str) -> dict:
    """Connection details for one model string (given). Groq needs a key; Ollama needs its local address."""
    if model.startswith("ollama"):
        return {"model": model, "api_base": os.getenv("OLLAMA_BASE", "http://localhost:11434")}
    return {"model": model, "api_key": os.getenv("GROQ_API_KEY") or os.getenv("API_KEY", "")}


def messages_for(question: str) -> list:
    """The two messages every call sends (given) - the S19 messages list, as plain dicts."""
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]


def answered_by(response) -> str:
    """Which model REALLY answered (given). After a fallback this is the backup model, not the one you asked for."""
    return response._hidden_params.get("litellm_model_name") or response.model


def fallbacks_used(response) -> int:
    """How many fallbacks the Router tried before this answer (given). 0 means the primary answered."""
    return int((response._hidden_params.get("additional_headers") or {}).get("x-litellm-attempted-fallbacks", 0) or 0)


# ================================================================ STEP 1 - one call, LiteLLM style
def ask_once(model: str, question: str):
    """Ask ONE model ONE question and return LiteLLM's response object.

    TODO 1:
        return completion(**params(model), messages=messages_for(question), temperature=0, max_tokens=1500)
    S20/S21 link: the response has the same shape as the OpenAI SDK's -
        response.choices[0].message.content   and   response.usage.total_tokens
    """
    raise NotImplementedError("TODO 1")


# ================================================================ STEP 2 - same code, two models
def compare(question: str) -> list:
    """Ask PRIMARY and FALLBACK the same question. Return [(model, answer_text), (model, answer_text)].

    TODO 2:
        out = []
        for model in (PRIMARY, FALLBACK):
            response = ask_once(model, question)
            out.append((model, response.choices[0].message.content))
        return out
    The point: only the model STRING changes. No new client, no new SDK.
    """
    raise NotImplementedError("TODO 2")


# ================================================================ STEP 3 - a Router with a fallback
def make_router(primary: str = PRIMARY, fallback: str = FALLBACK) -> Router:
    """Return a Router: ask "bankassist" (the primary); if it fails, LiteLLM asks "bankassist-backup".

    TODO 3:
        return Router(
            model_list=[
                {"model_name": "bankassist",        "litellm_params": params(primary)},
                {"model_name": "bankassist-backup", "litellm_params": params(fallback)},
            ],
            fallbacks=[{"bankassist": ["bankassist-backup"]}],
            num_retries=1,      # try the same model once more before falling back
            timeout=30,         # seconds - a hung provider counts as a failure
        )
    "bankassist" is a NAME YOU CHOOSE (a model group). Your app asks for the name, not the provider.
    """
    raise NotImplementedError("TODO 3")


# ================================================================ STEP 4 - what did that cost?
def cost_line(response, model: str, seconds: float) -> str:
    """One log line: "<model> | <total> tokens | $<cost> | <seconds>s".

    TODO 4:
        p, c = response.usage.prompt_tokens, response.usage.completion_tokens
        try:
            cost_in, cost_out = cost_per_token(model=model, prompt_tokens=p, completion_tokens=c)
            cost = cost_in + cost_out
        except Exception:
            cost = 0.0          # local models (Ollama) have no price - and cost nothing per token
        return f"{model} | {p + c} tokens | ${cost:.6f} | {seconds:.2f}s"
    Prices come from the list shipped with litellm 1.80.0. They are list prices, in US dollars.
    """
    raise NotImplementedError("TODO 4")


# ================================================================ STEP 5 (stretch) - every answer logged
# TODO 5: write ask_logged(router, question) -> str that:
#   1. starts a timer:        t = time.perf_counter()
#   2. asks the router:       response = router.completion(model="bankassist", messages=messages_for(question))
#   3. prints one log line:   print(cost_line(response, answered_by(response), time.perf_counter() - t))
#                             (and, if fallbacks_used(response) > 0, print that a fallback answered)
#   4. returns the text:      response.choices[0].message.content


# ================================================================ run me after every TODO
def _step(n, fn):
    try:
        print(f"STEP {n}:", fn())
    except NotImplementedError as e:
        print(f"STEP {n}: not done yet ({e})")
    except Exception as e:  # noqa: BLE001 - show the error, keep running the other steps
        print(f"STEP {n}: ERROR {type(e).__name__}: {str(e)[:300]}\n        -> look it up in module03/s22_common_errors.md")


def main():
    q = "What is the home loan floating rate, and when are branches open on Saturday?"
    print(f"PRIMARY  = {PRIMARY}\nFALLBACK = {FALLBACK}\n")

    def s1():
        t = time.perf_counter()
        r = ask_once(PRIMARY, q)
        return f"{r.choices[0].message.content}\n        [{r.usage.total_tokens} tokens, {time.perf_counter() - t:.2f}s]"

    def s2():
        return "\n" + "\n".join(f"   {m}:\n      {a}" for m, a in compare(q))

    def s3():
        broken = make_router(primary="groq/model-that-does-not-exist")     # make the primary fail ON PURPOSE
        r = broken.completion(model="bankassist", messages=messages_for(q))
        return f"answered by {answered_by(r)} after {fallbacks_used(r)} fallback(s): {r.choices[0].message.content}"

    def s4():
        t = time.perf_counter()
        r = ask_once(PRIMARY, q)
        return cost_line(r, PRIMARY, time.perf_counter() - t)

    def s5():
        if "ask_logged" not in globals():
            raise NotImplementedError("TODO 5, optional stretch")
        return globals()["ask_logged"](make_router(), q)

    for n, fn in enumerate((s1, s2, s3, s4, s5), start=1):
        _step(n, fn)


if __name__ == "__main__":
    main()

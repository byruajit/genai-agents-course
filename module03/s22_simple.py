"""Session 22 - LiteLLM, the SIMPLE version: run it, then change ONE line at a time.

Run from the course repo folder (where your .env is):
    uv run python module03/s22_simple.py

Nothing to fill in. Four short parts. After it runs, try the CHANGE ME lines one by one.
"""
import os
import time

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
import litellm  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from litellm import Router, completion, cost_per_token  # noqa: E402

load_dotenv(override=True)
litellm.suppress_debug_info = True
import logging  # noqa: E402
logging.getLogger("LiteLLM Router").setLevel(logging.CRITICAL)

KEY = os.getenv("GROQ_API_KEY") or os.getenv("API_KEY")
QUESTION = "When are branches open on Saturday, and what is the home loan floating rate?"
MESSAGES = [
    {"role": "system", "content": "You are BankAssist. Branches: 10am-4pm Mon-Fri, 10am-1pm Saturday. "
                                  "Home loan rate: 8.5% floating. Answer in 2 sentences."},
    {"role": "user", "content": QUESTION},
]

MODEL_A = "groq/openai/gpt-oss-20b"     # CHANGE ME (1): try "groq/openai/gpt-oss-120b"
MODEL_B = "groq/openai/gpt-oss-120b"    # the backup model


def cost(response, model):
    p, c = response.usage.prompt_tokens, response.usage.completion_tokens
    try:
        cin, cout = cost_per_token(model=model, prompt_tokens=p, completion_tokens=c)
        return p + c, cin + cout
    except Exception:
        return p + c, 0.0            # no price known (e.g. a local model)


# ---------------------------------------------------------------- PART 1: one call, any provider
print("\n=== PART 1: one call ===")
t = time.time()
r = completion(model=MODEL_A, messages=MESSAGES, api_key=KEY, temperature=0)
print("answer:", r.choices[0].message.content)
tokens, dollars = cost(r, MODEL_A)
print(f"model={MODEL_A} | {tokens} tokens | ${dollars:.6f} | {time.time() - t:.2f}s")

# ---------------------------------------------------------------- PART 2: same code, two models
print("\n=== PART 2: two models, same code ===")
for m in (MODEL_A, MODEL_B):
    r = completion(model=m, messages=MESSAGES, api_key=KEY, temperature=0)
    print(f"{m}:\n   {r.choices[0].message.content}")

# ---------------------------------------------------------------- PART 3: fallback when a model fails
print("\n=== PART 3: fallback ===")
PRIMARY = "groq/model-that-does-not-exist"   # CHANGE ME (2): put MODEL_A here - what changes?
router = Router(
    model_list=[
        {"model_name": "bankassist", "litellm_params": {"model": PRIMARY, "api_key": KEY}},
        {"model_name": "backup", "litellm_params": {"model": MODEL_B, "api_key": KEY}},
    ],
    fallbacks=[{"bankassist": ["backup"]}],  # CHANGE ME (3): delete this line - what happens?
    num_retries=1,
    timeout=30,
)
t = time.time()
try:
    r = router.completion(model="bankassist", messages=MESSAGES)
    who = r._hidden_params.get("litellm_model_name") or r.model
    print(f"asked for 'bankassist' (primary = {PRIMARY})")
    print(f"answered by {who} in {time.time() - t:.2f}s")
    print("answer:", r.choices[0].message.content)
except Exception as e:
    print(f"FAILED after {time.time() - t:.2f}s: {type(e).__name__} - no fallback could answer")

# ---------------------------------------------------------------- PART 4: what does it cost at scale?
print("\n=== PART 4: cost ===")
r = completion(model=MODEL_A, messages=MESSAGES, api_key=KEY, temperature=0)
tokens, dollars = cost(r, MODEL_A)
per_day = 10_000                                # CHANGE ME (4): your bank's questions per day
print(f"one answer: {tokens} tokens = ${dollars:.6f}")
print(f"{per_day:,} answers a day = ${dollars * per_day:.2f} a day = ${dollars * per_day * 30:.2f} a month")

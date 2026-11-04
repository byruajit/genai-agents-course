"""Session 23b - talk to the LiteLLM PROXY (the gateway) and read what it tells you.

Start the gateway first (lab step 2 or 3), then, from the course repo folder:
    uv run python module03/s23b_client.py

Three parts:
  1. raw HTTP  - one POST to the gateway; print the answer AND the headers it adds (which model, fallbacks, cost)
  2. LangChain - the SAME ChatOpenAI you used in S21, pointed at the gateway: only base_url, model and key change
  3. no key    - what the gateway does when an app forgets the key
"""
import os
import time

import httpx
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
GATEWAY = os.getenv("GATEWAY_URL", "http://localhost:4000")        # from your laptop, the gateway is on port 4000
KEY = os.getenv("LITELLM_MASTER_KEY", "sk-class-1234")            # the classroom master key from docker-compose.yml
QUESTION = "Can I return a pair of shoes I bought 5 days ago?"
SYSTEM = "You are ShopAssist, a helpful online-store assistant. Returns are allowed within 10 days. Answer in 2 sentences."


def part1_raw_http():
    print("\n=== PART 1: one POST to the gateway (raw HTTP) ===")
    t = time.time()
    r = httpx.post(f"{GATEWAY}/v1/chat/completions", timeout=60,
                   headers={"Authorization": f"Bearer {KEY}"},
                   json={"model": "shopassist", "messages": [{"role": "system", "content": SYSTEM},
                                                            {"role": "user", "content": QUESTION}]})
    print(f"HTTP {r.status_code} in {time.time() - t:.2f}s")
    if r.status_code != 200:
        print(r.text[:400])
        return
    body = r.json()
    print("answer          :", body["choices"][0]["message"]["content"])
    print("tokens          :", body["usage"]["total_tokens"])
    h = r.headers
    print("model group used:", h.get("x-litellm-model-group"), "  <- 'shopassist-backup' means the fallback answered")
    print("fallbacks tried :", h.get("x-litellm-attempted-fallbacks", "0"))
    print("real model      :", body.get("model"))
    print("cost (USD)      :", h.get("x-litellm-response-cost"))


def part2_langchain():
    print("\n=== PART 2: LangChain through the gateway ===")
    llm = ChatOpenAI(model="shopassist", base_url=GATEWAY, api_key=KEY, temperature=0, max_tokens=800)
    reply = llm.invoke([("system", SYSTEM), ("human", QUESTION)])
    print("answer:", reply.content)
    print("(S21 code, unchanged - only model, base_url and api_key point at the gateway)")


def part3_no_key():
    print("\n=== PART 3: an app with NO key ===")
    r = httpx.post(f"{GATEWAY}/v1/chat/completions", timeout=30,
                   json={"model": "shopassist", "messages": [{"role": "user", "content": "hi"}]})
    print(f"HTTP {r.status_code}  <- 401 = the gateway refused it; the app never reached Groq, no tokens spent")


if __name__ == "__main__":
    try:
        httpx.get(f"{GATEWAY}/health/liveliness", timeout=5).raise_for_status()
    except Exception as e:
        raise SystemExit(f"The gateway is not reachable at {GATEWAY} ({type(e).__name__}). Start it first - lab step 2 or 3.")
    part1_raw_http()
    part2_langchain()
    part3_no_key()

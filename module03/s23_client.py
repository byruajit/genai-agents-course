"""Session 23 - talk to YOUR running BankAssist server, the way another program would.

Start your server first, in one terminal (course repo folder):
    uv run python $env:WORK_REPO\\s23\\app.py
Then, in a SECOND terminal (course repo folder):
    uv run python module03/s23_client.py                 # the full tour
    uv run python module03/s23_client.py "your question" # one streamed question, session "me"

Nothing here knows about LangChain or your code: it only speaks HTTP and JSON. That is the point of an API.
"""
import json
import sys

import httpx

URL = "http://127.0.0.1:8000"


def stream(session_id: str, message: str) -> None:
    """POST /chat/stream and print each event the moment it arrives."""
    with httpx.stream("POST", f"{URL}/chat/stream", json={"session_id": session_id, "message": message},
                      timeout=120) as r:
        r.raise_for_status()
        event = None
        for line in r.iter_lines():
            if line.startswith("event: "):
                event = line[len("event: "):]
            elif line.startswith("data: "):
                text = json.loads(line[len("data: "):])["text"]
                if event == "tool":
                    print(f"\n  [tool] {text}")
                elif event == "token":
                    print(text, end="", flush=True)      # flush: show it NOW, don't wait for the line to end
    print()


def main() -> None:
    try:
        health = httpx.get(f"{URL}/health", timeout=5)
    except httpx.ConnectError:
        sys.exit(f"Nothing is listening on {URL}. Start your server first:  uv run python $env:WORK_REPO\\s23\\app.py")
    print("GET /health ->", health.status_code, health.text)
    if health.status_code != 200:
        sys.exit("Your /health is not finished yet (TODO 1).")

    if len(sys.argv) > 1:
        stream("me", " ".join(sys.argv[1:]))
        return

    print("\n1) Two messages in ONE session - does it remember?")
    for msg in ("Hi, my name is Priya and I earn 80,000 a month.", "What is my name, and what do I earn?"):
        r = httpx.post(f"{URL}/chat", json={"session_id": "priya", "message": msg}, timeout=120)
        print(f"  you:  {msg}\n  bank: {r.json().get('answer', r.text)}   (status {r.status_code})")

    print("\n2) A DIFFERENT session - it must NOT know Priya")
    r = httpx.post(f"{URL}/chat", json={"session_id": "ravi", "message": "What is my name?"}, timeout=120)
    print(f"  bank: {r.json().get('answer', r.text)}")

    print("\n3) An empty message - rejected before it costs a token?")
    r = httpx.post(f"{URL}/chat", json={"session_id": "priya", "message": ""}, timeout=30)
    print(f"  status {r.status_code} (422 = rejected by your ChatRequest)")

    print("\n4) Streamed, with a tool - watch the words arrive:")
    stream("priya", "What is the EMI on a 25 lakh home loan at 8.5% for 20 years?")


if __name__ == "__main__":
    main()

"""Session 23 checker - tests the server YOU wrote in <work repo>/s23/app.py, offline.

No model is called. Your file is imported, the real model is swapped for a scripted stand-in (mod.LLM = ...),
and FastAPI's TestClient sends real HTTP requests to your app without starting a server:
  - GET  /health        must answer {"status": "ok", "model": ...}
  - ChatRequest         must reject an empty message (422) - before it costs a token
  - window()            must keep exactly the last keep_turns turns
  - POST /chat          must remember a session, keep sessions apart, apply the window, and report tool steps
  - POST /chat/stream   must send correctly formatted Server-Sent Events and save the turn to memory
Each check returns a CheckResult; a failure says what to fix and which TODO it belongs to.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage, ToolMessage

from prompt_utils import CheckResult

STUDENT_PATH = Path("s23") / "app.py"
STARTER = Path(__file__).resolve().parent / "s23_starter.py"
EMI_Q = "What is the EMI on a 25 lakh home loan at 8.5% for 20 years?"


def load_student(repo_path, path=None):
    """Import (or re-import) the student's file, so edits are picked up without restarting the kernel."""
    path = Path(path) if path else Path(repo_path) / STUDENT_PATH
    for k, v in {"MODEL": "check-model", "BASE_URL": "http://localhost:9/v1", "API_KEY": "check"}.items():
        os.environ.setdefault(k, v)            # make_llm() only builds the object; nothing is sent
    spec = importlib.util.spec_from_file_location("bankassist_app_student", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bankassist_app_student"] = mod
    spec.loader.exec_module(mod)
    return mod


class FakeStreamingModel:
    """Stands in for get_llm(): streams its answers in pieces, like a real model.

    - An EMI question: first asks for calculate_emi, then (after the tool result) answers with the number.
    - Anything else: answers "I can see N earlier messages." - N counts what reached it besides the system prompt
      and the new question, so the checker can see whether memory and the window work.
    Every call's messages are kept in self.seen."""

    def __init__(self):
        self.seen = []

    def stream(self, messages):
        self.seen.append(list(messages))
        if self.seen[-1] and isinstance(self.seen[-1][-1], ToolMessage):
            text = f"Your EMI would be about Rs {messages[-1].content} a month."
        elif "EMI" in str(messages[-1].content):
            yield AIMessageChunk(content="", tool_call_chunks=[{
                "name": "calculate_emi", "id": f"call_{len(self.seen)}", "index": 0,
                "args": json.dumps({"principal": 2500000, "annual_rate": 8.5, "tenure_months": 240})}])
            return
        else:
            earlier = [m for m in messages[:-1] if not isinstance(m, SystemMessage)]
            text = f"I can see {len(earlier)} earlier messages."
        for word in text.split(" "):
            yield AIMessageChunk(content=word + " ")

    def invoke(self, messages):          # in case a student calls .invoke - same answer, in one piece
        full = None
        for c in self.stream(messages):
            full = c if full is None else full + c
        return full


def parse_sse(body: str) -> list:
    """'event: x\\ndata: {...}\\n\\n' blocks -> [(event, data_dict), ...]. Raises ValueError on a malformed block."""
    events = []
    for block in body.replace("\r\n", "\n").split("\n\n"):
        if not block.strip():
            continue
        fields = dict(line.split(": ", 1) for line in block.split("\n") if ": " in line)
        if "event" not in fields or "data" not in fields:
            raise ValueError(f"an event needs an 'event:' line and a 'data:' line, got {block!r}")
        events.append((fields["event"], json.loads(fields["data"])))
    return events


def _todo(e, n):
    return f"still a TODO - finish TODO {n}" if isinstance(e, NotImplementedError) else f"{type(e).__name__}: {e}"


def fresh_client(mod):
    """A TestClient on the student's app, with a fake model and empty memory."""
    from fastapi.testclient import TestClient
    mod.LLM = FakeStreamingModel()
    mod.SESSIONS.clear()
    return TestClient(mod.app), mod.LLM


def check_s23_work(repo_path, path=None) -> list:
    repo = Path(repo_path)

    def ck(name, ok, fix="", info=""):
        return CheckResult(name, ok, info if ok else fix)
    if path is None:
        if not repo.exists():
            return [ck("work repo folder exists", False, f"{repo} not found. Fix WORK_REPO.")]
        if not (repo / STUDENT_PATH).exists():
            return [ck("work repo folder exists", True),
                    ck("s23/app.py exists", False, "not found - run notebook Section 1 to copy the starter")]
    out = [ck("s23/app.py exists", True)]
    try:
        mod = load_student(repo, path)
    except Exception as e:  # noqa: BLE001
        out.append(ck("your file imports without errors", False, f"{type(e).__name__}: {e} - see s23_common_errors.md"))
        return out
    out.append(ck("your file imports without errors", True))

    # STEP 1
    name = "TODO 1 - GET /health answers {status: ok, model}"
    try:
        client, _ = fresh_client(mod)
        r = client.get("/health")
        body = r.json() if r.status_code == 200 else {}
        out.append(ck(name, body.get("status") == "ok" and body.get("model") == os.environ["MODEL"],
                      f"got {r.status_code} {r.text[:120]}; return {{'status': 'ok', 'model': os.environ['MODEL']}}"))
    except Exception as e:  # noqa: BLE001
        out.append(ck(name, False, _todo(e, 1)))

    # STEP 2
    name = "TODO 2 - ChatRequest rejects an empty message; ChatResponse has tool_steps and turns"
    try:
        from pydantic import ValidationError
        rejected = False
        try:
            mod.ChatRequest(session_id="a", message="")
        except ValidationError:
            rejected = True
        fields = set(mod.ChatResponse.model_fields)
        ok = rejected and {"tool_steps", "turns"} <= fields
        fix = []
        if not rejected:
            fix.append("an empty message was accepted - use Field(min_length=1, max_length=2000)")
        if not {"tool_steps", "turns"} <= fields:
            fix.append(f"ChatResponse fields are {sorted(fields)} - add tool_steps: list[str] and turns: int")
        out.append(ck(name, ok, "; ".join(fix)))
    except Exception as e:  # noqa: BLE001
        out.append(ck(name, False, _todo(e, 2)))

    # STEP 3
    name = "TODO 3 - window() keeps exactly the last keep_turns turns"
    try:
        hist = []
        for i in range(10):
            hist += [HumanMessage(f"q{i}"), AIMessage(f"a{i}")]
        w3 = mod.window(hist, 3)
        ok = (len(w3) == 6 and w3[0].content == "q7" and w3[-1].content == "a9"
              and mod.window([], 3) == [] and len(mod.window(hist[:4], 3)) == 4 and mod.window(hist, 0) == [])
        out.append(ck(name, ok, f"10 turns, keep_turns=3 gave {[m.content for m in w3]}; expected q7..a9 "
                                "(6 messages), and [] for keep_turns=0"))
    except Exception as e:  # noqa: BLE001
        out.append(ck(name, False, _todo(e, 3)))

    # STEP 4
    name = "TODO 4 - POST /chat remembers a session and keeps sessions apart"
    try:
        client, fake = fresh_client(mod)
        a1 = client.post("/chat", json={"session_id": "alice", "message": "Hi, I'm Alice."}).json()
        a2 = client.post("/chat", json={"session_id": "alice", "message": "What's my name?"}).json()
        b1 = client.post("/chat", json={"session_id": "bob", "message": "Hello"}).json()
        ok = ("0 earlier" in a1.get("answer", "") and "2 earlier" in a2.get("answer", "")
              and "0 earlier" in b1.get("answer", "") and a2.get("turns") == 2)
        out.append(ck(name, ok, f"alice's 2nd call saw: {a2.get('answer')!r}, bob saw {b1.get('answer')!r}; "
                                "expected 2 earlier messages for alice, 0 for bob, and turns=2 - save BOTH the "
                                "HumanMessage and the AIMessage to SESSIONS[session_id]"))
    except Exception as e:  # noqa: BLE001
        out.append(ck(name, False, _todo(e, 4)))
    name = "TODO 4 - POST /chat applies the window and reports tool steps"
    try:
        client, fake = fresh_client(mod)
        for i in range(mod.KEEP_TURNS + 3):
            last = client.post("/chat", json={"session_id": "w", "message": f"question {i}"}).json()
        windowed = f"{2 * mod.KEEP_TURNS} earlier" in last.get("answer", "")
        emi = client.post("/chat", json={"session_id": "e", "message": EMI_Q}).json()
        tools_ok = bool(emi.get("tool_steps")) and "21696" in emi.get("answer", "").replace(",", "")
        bad = client.post("/chat", json={"session_id": "e", "message": ""})
        ok = windowed and tools_ok and bad.status_code == 422
        out.append(ck(name, ok, f"after {mod.KEEP_TURNS + 3} turns the model saw: {last.get('answer')!r} "
                                f"(expected {2 * mod.KEEP_TURNS}); EMI reply {emi.get('answer')!r} with tool_steps "
                                f"{emi.get('tool_steps')}; empty message gave {bad.status_code} (expected 422)"))
    except Exception as e:  # noqa: BLE001
        out.append(ck(name, False, _todo(e, 4)))

    # STEP 5
    name = "TODO 5 - sse() formats one Server-Sent Event"
    try:
        s = mod.sse("token", {"text": "two\nlines"})
        ok = s == 'event: token\ndata: {"text": "two\\nlines"}\n\n'
        out.append(ck(name, ok, f"got {s!r}; expected 'event: token\\ndata: <json>\\n\\n' - json.dumps the data"))
    except Exception as e:  # noqa: BLE001
        out.append(ck(name, False, _todo(e, 5)))
    name = "TODO 5 - POST /chat/stream streams tool, token and done events, and remembers the turn"
    try:
        client, fake = fresh_client(mod)
        r = client.post("/chat/stream", json={"session_id": "s", "message": EMI_Q})
        events = parse_sse(r.text)
        kinds = [k for k, _ in events]
        tokens = "".join(d.get("text", "") for k, d in events if k == "token")
        done = [d.get("text", "") for k, d in events if k == "done"]
        after = client.post("/chat", json={"session_id": "s", "message": "and again?"}).json()
        ok = (r.headers.get("content-type", "").startswith("text/event-stream") and "tool" in kinds
              and kinds.count("token") >= 3 and kinds[-1] == "done" and done and tokens == done[0]
              and "21696" in tokens and "2 earlier" in after.get("answer", ""))
        out.append(ck(name, ok, f"content-type {r.headers.get('content-type')!r}, events {kinds[:8]}..., "
                                f"memory after stream: {after.get('answer')!r} - use media_type='text/event-stream' "
                                "and save the turn when the 'done' event arrives"))
    except Exception as e:  # noqa: BLE001
        out.append(ck(name, False, _todo(e, 5)))

    # STEP 6 (stretch - never fails the checkpoint)
    try:
        client, _ = fresh_client(mod)
        client.post("/chat", json={"session_id": "z", "message": "hi"})
        r1 = client.delete("/sessions/z")
        r2 = client.delete("/sessions/z")
        done6 = r1.status_code == 200 and r1.json() == {"deleted": True} and r2.json() == {"deleted": False}
        info = ("done" if done6 else "not attempted - optional" if r1.status_code in (404, 405)
                else f"not working yet ({r1.status_code}) - optional")
    except Exception:  # noqa: BLE001
        info = "not attempted - optional"
    out.append(ck("TODO 6 (stretch) - DELETE /sessions/{id}", True, info=info))
    return out

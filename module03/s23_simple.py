"""Session 23 - serving BankAssist, the SIMPLE version: a complete web server. Run it, use it, then change ONE line
at a time.

1. Copy it into your work repo as s23\\app.py - one command, from the COURSE repo folder:
       uv run python module03/s23_setup.py        (it prints the exact commands for the next steps)
2. Start it from the COURSE repo folder (so your .env is found) - terminal 1, leave it running:
       uv run python "<your work repo>\\s23\\app.py"      (s23_setup.py printed this line with your real path)
3. Open http://127.0.0.1:8000/docs in a browser and try every endpoint (the list is printed when it starts).
4. Terminal 2 (course repo folder):   uv run python module03/s23_client.py
5. Then the CHANGE ME lines, one at a time. After EVERY change: Ctrl+C in terminal 1, start it again.

Nothing to fill in. Every piece here is one you met before: S13 Pydantic, S19 memory window, S20 tool validation,
S21 the LangChain tool loop. New today: FastAPI (a URL for each function) and streaming (SSE).
"""
import json
import os

import uvicorn
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

load_dotenv(find_dotenv(usecwd=True), override=True)

# ------------------------------------------------------------------ 1. the assistant (S21, unchanged)
SYSTEM = """You are BankAssist, Northwind Bank's assistant. Answer in 2-3 friendly sentences.
Facts you may quote: branches 10am-4pm Mon-Fri, 10am-1pm Saturday, closed Sunday. Home loan 8.5% floating,
9.0% fixed. Personal loan 10.5% fixed. Remember what the customer told you earlier in this conversation.
Use a tool only for an exact EMI or today's rate."""     # CHANGE ME (3): "Answer in ONE short sentence."

KEEP_TURNS = 4       # CHANGE ME (1): try 0 -> it forgets your name. One turn = your message + its answer.
MAX_STEPS = 3        # CHANGE ME (4): try 1 -> an EMI question can't finish (it needs a tool AND an answer)


@tool(parse_docstring=True)
def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> int:
    """Exact monthly EMI for a loan. Use ONLY when the customer asks for an EMI amount.

    Args:
        principal: loan amount in rupees, e.g. 25 lakh = 2500000
        annual_rate: interest rate in percent per year, e.g. 8.5
        tenure_months: total months, e.g. 20 years = 240
    """
    r = annual_rate / 12 / 100
    return round(principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1))


@tool(parse_docstring=True)
def get_rate(product: str, rate_type: str) -> float:
    """Today's interest rate in percent per year.

    Args:
        product: "home_loan" or "personal_loan"
        rate_type: "floating" or "fixed"
    """
    return {("home_loan", "floating"): 8.5, ("home_loan", "fixed"): 9.0, ("personal_loan", "fixed"): 10.5}[
        (product, rate_type)]


TOOLS = {"calculate_emi": calculate_emi, "get_rate": get_rate}
LLM = None


def get_llm():
    """The model, built once, the first time someone asks a question."""
    global LLM
    if LLM is None:
        LLM = ChatOpenAI(model=os.environ["MODEL"], base_url=os.environ["BASE_URL"], api_key=os.environ["API_KEY"],
                         temperature=0, max_tokens=1500).bind_tools(list(TOOLS.values()))
    return LLM


def run_tool(call) -> ToolMessage:
    """A bad tool call becomes an INVALID message for the model, never a crash (S20)."""
    try:
        return TOOLS[call["name"]].invoke(call)
    except Exception as e:  # noqa: BLE001
        return ToolMessage(f"INVALID: {type(e).__name__}: {e}", tool_call_id=call["id"])


def stream_turn(messages):
    """The S21 tool loop, streaming. Yields ("tool", ...), ("token", ...) pieces, and finally ("done", whole answer)."""
    messages, said = list(messages), []
    for _ in range(MAX_STEPS):
        full = None
        for chunk in get_llm().stream(messages):             # .stream(): pieces as they are written
            full = chunk if full is None else full + chunk
            if isinstance(chunk.content, str) and chunk.content:
                said.append(chunk.content)
                yield "token", chunk.content
        if full is None or not full.tool_calls:
            yield "done", "".join(said)
            return
        messages.append(full)
        for call in full.tool_calls:
            result = run_tool(call)
            yield "tool", f"{call['name']}({call['args']}) -> {result.content}"
            messages.append(result)
    yield "token", "Sorry, I couldn't finish that one."
    yield "done", "".join(said) + "Sorry, I couldn't finish that one."


# ------------------------------------------------------------------ 2. the web server (NEW today)
app = FastAPI(title="BankAssist", version="s23-simple")
SESSIONS: dict[str, list] = {}       # session_id -> that customer's messages. In RAM: a restart forgets everyone.


class ChatRequest(BaseModel):          # what a caller must send. Wrong shape -> 422, before any token is spent
    session_id: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=2000)    # CHANGE ME (5): max_length=20, then send a long question


class ChatResponse(BaseModel):         # what we promise to send back
    session_id: str
    answer: str
    tool_steps: list[str]
    turns: int


@app.get("/health")
def health():
    """Is the server up, and what is it running?"""
    return {"status": "ok", "model": os.getenv("MODEL")}    # CHANGE ME (2): add  "keep_turns": KEEP_TURNS


def window(history: list, keep_turns: int = KEEP_TURNS) -> list:
    """S19's sliding window: only the last keep_turns turns (2 messages each) go to the model."""
    return history[-2 * keep_turns:] if keep_turns > 0 else []


def build_messages(session_id: str, message: str) -> list:
    """System prompt + the window of THIS customer's history + the new message."""
    history = SESSIONS.setdefault(session_id, [])
    return [SystemMessage(SYSTEM), *window(history, KEEP_TURNS), HumanMessage(message)]


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """One question, one whole answer (JSON)."""
    answer, steps = "", []
    for kind, text in stream_turn(build_messages(req.session_id, req.message)):
        if kind == "tool":
            steps.append(text)
        elif kind == "done":
            answer = text
    history = SESSIONS[req.session_id]
    history += [HumanMessage(req.message), AIMessage(answer)]
    return ChatResponse(session_id=req.session_id, answer=answer, tool_steps=steps, turns=len(history) // 2)


def sse(event: str, data: dict) -> str:
    """One Server-Sent Event: two lines and a blank line. That's the whole format."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """The same answer, sent piece by piece as the model writes it."""
    messages = build_messages(req.session_id, req.message)

    def events():
        for kind, text in stream_turn(messages):
            if kind == "done":
                SESSIONS[req.session_id] += [HumanMessage(req.message), AIMessage(text)]
            yield sse(kind, {"text": text})

    return StreamingResponse(events(), media_type="text/event-stream")


@app.delete("/sessions/{session_id}")
def forget(session_id: str):
    """A customer says 'forget me'."""
    return {"deleted": SESSIONS.pop(session_id, None) is not None}


if __name__ == "__main__":
    print("BankAssist is starting on http://127.0.0.1:8000   (Ctrl+C to stop)")
    print("Open http://127.0.0.1:8000/docs and try, in order:")
    print('  1. GET  /health')
    print('  2. POST /chat   {"session_id": "a", "message": "Hi, I am Priya. When are branches open on Saturday?"}')
    print('  3. POST /chat   {"session_id": "a", "message": "What is my name?"}            <- memory')
    print('  4. POST /chat   {"session_id": "b", "message": "What is my name?"}            <- another customer')
    print('  5. POST /chat   {"session_id": "a", "message": "EMI on 25 lakh at 8.5% for 20 years?"}   <- tool_steps')
    print('  6. POST /chat   {"session_id": "a", "message": ""}                             <- 422')
    print('  7. DELETE /sessions/a,  then step 3 again')
    print("Terminal 2:  uv run python module03/s23_client.py      <- streaming, word by word")
    uvicorn.run(app, host="127.0.0.1", port=8000)

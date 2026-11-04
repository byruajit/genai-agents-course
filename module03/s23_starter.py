"""Session 23 - serve BankAssist: a web API with memory and streaming, built by YOU with FastAPI.

This is YOUR file. Copy it into your work repository (the notebook's Section 1 does this for you):
    <your genai-course-work>/s23/app.py
then fill in the TODOs, one at a time, in order.

The top half (PART 1) is GIVEN: Session 21's BankAssist, finished - the model, two tools, and a capped tool loop
that STREAMS. Read it; you do not change it. The bottom half (PART 2) is YOURS: the web server around it.

Run your server from the COURSE repository folder (so your .env is found):
    uv run python $env:WORK_REPO\\s23\\app.py
It listens on http://127.0.0.1:8000 . Open http://127.0.0.1:8000/docs in a browser to try every endpoint.
In a SECOND terminal (also in the course repo folder), talk to it:
    uv run python module03/s23_client.py

Stop the server with Ctrl+C. After every change to this file, stop it and start it again.

Rules for using ChatGPT (or any AI assistant) today:
  1. Paste module03/s23_version_card.md into it FIRST.
  2. NEVER paste your .env or your API key.
  3. Ask it to explain or fix YOUR code. You must be able to explain every line you hand in.
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
from pydantic import BaseModel, Field  # noqa: F401 - Field is for TODO 2

load_dotenv(find_dotenv(usecwd=True), override=True)   # finds the .env in the folder you run from

# =====================================================================================================
# PART 1 - GIVEN: BankAssist from Session 21, finished. Read it, don't change it.
# =====================================================================================================
SYSTEM = """You are BankAssist, Northwind Bank's assistant for retail customers. Answer in 2-3 friendly sentences.
Facts you may quote (never invent a number that is not here):
- Branches: 10am-4pm Monday to Friday, 10am-1pm Saturday, closed Sunday.
- Home loan rates: 8.5% floating, 9.0% fixed. Personal loan rate: 10.5% fixed.
- No prepayment penalty on floating-rate loans. Minimum credit score for a new loan: 700.
Remember what the customer told you earlier in this conversation (name, income, amounts) and use it.
Use a tool only for an exact EMI or today's rate. If a tool says INVALID, ask the customer for the missing detail."""

MAX_STEPS = 3
CAP_MESSAGE = "Sorry, I couldn't finish that one. Could you ask it in a simpler way?"


def make_llm():
    return ChatOpenAI(model=os.environ["MODEL"], base_url=os.environ["BASE_URL"],
                      api_key=os.environ["API_KEY"], temperature=0, max_tokens=1500)


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
    """Today's interest rate in percent per year. Use when the customer asks for a rate or needs one for an EMI.

    Args:
        product: "home_loan" or "personal_loan"
        rate_type: "floating" or "fixed" (personal loans are fixed only)
    """
    card = {("home_loan", "floating"): 8.5, ("home_loan", "fixed"): 9.0, ("personal_loan", "fixed"): 10.5}
    return card[(product, rate_type)]


TOOLS = {"calculate_emi": calculate_emi, "get_rate": get_rate}

LLM = None   # the model, built once on first use (the checker swaps in a fake one here)


def get_llm():
    global LLM
    if LLM is None:
        LLM = make_llm().bind_tools(list(TOOLS.values()))
    return LLM


def run_tool(call) -> ToolMessage:
    """Run one tool call. Never crashes: a bad call becomes an INVALID message the model reads (S20's Fix B)."""
    if call["name"] not in TOOLS:
        return ToolMessage(f"INVALID: there is no tool called {call['name']}.", tool_call_id=call["id"])
    try:
        return TOOLS[call["name"]].invoke(call)
    except Exception as e:  # noqa: BLE001 - a tool must never crash the conversation
        return ToolMessage(f"INVALID: {type(e).__name__}: {e}", tool_call_id=call["id"])


def stream_turn(llm_with_tools, messages, max_steps=MAX_STEPS):
    """Your S21 loop, streaming. Yields (kind, text) pairs as they happen:
         ("tool",  "calculate_emi({...}) -> 21696")   each tool the model used
         ("token", "Your")                             each piece of the answer, as the model writes it
         ("done",  "Your EMI is ...")                  last: the whole answer
    """
    messages = list(messages)
    said = []
    for _ in range(max_steps):
        full = None
        for chunk in llm_with_tools.stream(messages):      # .stream() instead of .invoke(): pieces, not one reply
            full = chunk if full is None else full + chunk  # pieces add up to the whole message
            if isinstance(chunk.content, str) and chunk.content:
                said.append(chunk.content)
                yield "token", chunk.content
        if full is None or not full.tool_calls:             # answered in words: done
            yield "done", "".join(said)
            return
        messages.append(full)
        for call in full.tool_calls:
            result = run_tool(call)
            yield "tool", f"{call['name']}({call['args']}) -> {result.content}"
            messages.append(result)
    said.append(CAP_MESSAGE)                                 # step cap reached
    yield "token", CAP_MESSAGE
    yield "done", "".join(said)


def run_turn(llm_with_tools, messages):
    """The same loop without streaming: returns (answer, tool_steps)."""
    steps, answer = [], ""
    for kind, text in stream_turn(llm_with_tools, messages):
        if kind == "tool":
            steps.append(text)
        elif kind == "done":
            answer = text
    return answer, steps


# =====================================================================================================
# PART 2 - YOURS: the web server. Six TODOs, in order. Run the check cell after each one.
# =====================================================================================================
app = FastAPI(title="BankAssist", version="0.22")


# ------------------------------------------------------------------ STEP 1 - the simplest endpoint
@app.get("/health")
def health():
    """TODO 1: return a dict:  {"status": "ok", "model": os.environ["MODEL"]}
    FastAPI turns the dict into JSON for you. A load balancer (and your demo) calls /health to ask "are you alive?".
    """
    raise NotImplementedError("TODO 1")


# ------------------------------------------------------------------ STEP 2 - the shape of a request and a reply
class ChatRequest(BaseModel):
    session_id: str
    message: str        # TODO 2a: make this   message: str = Field(min_length=1, max_length=2000)
                        #          so an empty or huge message is rejected (status 422) before it costs a token


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    # TODO 2b: add two more fields:   tool_steps: list[str]    and    turns: int


# ------------------------------------------------------------------ STEP 3 - memory, trimmed (Session 19)
KEEP_TURNS = 4                       # how many earlier turns (question + answer) the model sees
SESSIONS: dict[str, list] = {}       # session_id -> that conversation's messages. Lives in RAM: a restart forgets.


def window(history: list, keep_turns: int = KEEP_TURNS) -> list:
    """Return only the last keep_turns turns of history. One turn = 2 messages (HumanMessage, AIMessage).

    TODO 3:  return history[-2 * keep_turns:] if keep_turns > 0 else []
    S19 link: this is the sliding window - flat cost per call, but turn 1 is forgotten after keep_turns turns.
    """
    raise NotImplementedError("TODO 3")


# ------------------------------------------------------------------ STEP 4 - chat, with memory
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Answer one message in a conversation that remembers.

    TODO 4:
        history = SESSIONS.setdefault(req.session_id, [])
        messages = [SystemMessage(SYSTEM), *window(history), HumanMessage(req.message)]
        answer, steps = run_turn(get_llm(), messages)
        history += [HumanMessage(req.message), AIMessage(answer)]
        return ChatResponse(session_id=req.session_id, answer=answer, tool_steps=steps, turns=len(history) // 2)
    S19 link: the API is stateless - the SERVER now keeps the list and resends it. Tool messages are not saved,
    only the question and the final answer, so the history stays small.
    """
    raise NotImplementedError("TODO 4")


# ------------------------------------------------------------------ STEP 5 - stream it (Server-Sent Events)
def sse(event: str, data: dict) -> str:
    """Format ONE Server-Sent Event.

    TODO 5a:  return f"event: {event}\\ndata: {json.dumps(data)}\\n\\n"
    The blank line at the end (\\n\\n) is what tells the browser "this event is complete".
    json.dumps matters: a token that contains a newline would otherwise break the event in two.
    """
    raise NotImplementedError("TODO 5")


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """The same as /chat, but the answer arrives piece by piece, as the model writes it.

    TODO 5b:
        history = SESSIONS.setdefault(req.session_id, [])
        messages = [SystemMessage(SYSTEM), *window(history), HumanMessage(req.message)]

        def events():
            for kind, text in stream_turn(get_llm(), messages):
                if kind == "done":
                    history.extend([HumanMessage(req.message), AIMessage(text)])
                yield sse(kind, {"text": text})

        return StreamingResponse(events(), media_type="text/event-stream")
    """
    raise NotImplementedError("TODO 5")


# ------------------------------------------------------------------ STEP 6 (stretch) - forget a conversation
# TODO 6: add   DELETE /sessions/{session_id}   that removes that session from SESSIONS and returns
#         {"deleted": True} if it existed, {"deleted": False} if it didn't.  Hint: @app.delete(...) and SESSIONS.pop
# A real bank needs this: a customer can ask you to forget what they told you.


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

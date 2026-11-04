"""ShopAssist, served. YOU own this file. This is Session 23's PART 2, finished - compare it with yours.

Run locally (gateway running, .env present):   uv run uvicorn app.main:app --port 8000
Run everything in Docker:                     docker compose up --build   (see README.md)
"""
import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app import agent, memory
from app.tools import TOOLS

SYSTEM = agent.load_system_prompt()        # read once at startup: change the file -> restart the server
SESSIONS: dict[str, list] = {}             # session_id -> messages. In RAM: a restart forgets (see your report)

app = FastAPI(title="ShopAssist", version="mp1")


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    tool_steps: list[str]
    turns: int


@app.get("/health")
def health():
    """TODO MP1-T5: also report the running configuration, so your demo (and an auditor) can see it:
        "memory": memory.STRATEGY,   "keep_turns": memory.KEEP_TURNS,   "tools": sorted(TOOLS)
    """
    return {"status": "ok", "model": agent.MODEL, "gateway": agent.GATEWAY_URL}


def build_messages(history: list, message: str) -> list:
    return [SystemMessage(SYSTEM), *memory.trim(history, agent.get_llm()), HumanMessage(message)]


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    history = SESSIONS.setdefault(req.session_id, [])
    answer, steps = agent.run_turn(agent.get_llm(), build_messages(history, req.message))
    history += [HumanMessage(req.message), AIMessage(answer)]
    return ChatResponse(session_id=req.session_id, answer=answer, tool_steps=steps, turns=len(history) // 2)


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    history = SESSIONS.setdefault(req.session_id, [])
    messages = build_messages(history, req.message)

    def events():
        for kind, text in agent.stream_turn(agent.get_llm(), messages):
            if kind == "done":
                history.extend([HumanMessage(req.message), AIMessage(text)])
            yield sse(kind, {"text": text})

    return StreamingResponse(events(), media_type="text/event-stream")


@app.delete("/sessions/{session_id}")
def forget(session_id: str):
    return {"deleted": SESSIONS.pop(session_id, None) is not None}

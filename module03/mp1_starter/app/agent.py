"""GIVEN - ShopAssist's brain: the model (through the gateway), the system prompt from a file, and the capped,
streaming tool loop.

This is Session 23's PART 1, moved into its own file. You should not need to change it. If you do, explain why in
experiments/mp1_report.md.
"""
import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI

from app.tools import TOOLS

load_dotenv(find_dotenv(usecwd=True))   # a local .env, if there is one. In Docker, --env-file sets these instead.

PROMPT_FILE = Path(__file__).resolve().parents[1] / "prompts" / "system.md"
MAX_STEPS = 3
CAP_MESSAGE = "Sorry, I couldn't finish that one. Could you ask it in a simpler way?"


def load_system_prompt() -> str:
    """The system prompt lives in a file (Session 16): reviewed and versioned like code, changed without touching code."""
    return PROMPT_FILE.read_text(encoding="utf-8")


GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:4000")   # in Docker Compose: http://litellm:4000
MODEL = os.getenv("MODEL", "shopassist")                           # a MODEL GROUP in gateway/config.yaml


def make_llm():
    """The app talks ONLY to the LiteLLM gateway (Session 23b). It never sees the Groq key: the gateway holds it,
    picks the real model for the group "shopassist", and falls back to "shopassist-backup" if that fails."""
    return ChatOpenAI(model=MODEL, base_url=GATEWAY_URL, api_key=os.environ["LITELLM_MASTER_KEY"],
                      temperature=0, max_tokens=1500)


LLM = None   # built once on first use (the checker swaps in a fake one here)


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
    """Yields ("tool", "name(args) -> result"), ("token", "piece"), and finally ("done", "whole answer")."""
    messages = list(messages)
    said = []
    for _ in range(max_steps):
        full = None
        for chunk in llm_with_tools.stream(messages):
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
    said.append(CAP_MESSAGE)
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

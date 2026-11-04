"""How much of the conversation the model sees. YOU own this file.

Session 19 measured three strategies on a 17-turn conversation: send everything (cost grows every turn), a sliding
window (flat cost, forgets early turns silently), and a summary (recovers recall, but costs an extra call and can
summarise wrongly). Your server talks to many customers, so "send everything" is not an option.

TODO MP1-T4: choose "window" or "summary" for ShopAssist, and set KEEP_TURNS. Justify both in
experiments/mp1_report.md, section 3, with numbers from YOUR Session 19 report (experiments/s19_chat_memory.md in your
work repo). You can override both without changing code:  MEMORY=window KEEP_TURNS=6  in .env or `docker run -e`.
"""
import os

from langchain_core.messages import HumanMessage, SystemMessage

STRATEGY = os.getenv("MEMORY") or "window"         # "window" or "summary"
KEEP_TURNS = int(os.getenv("KEEP_TURNS") or 4)   # how many earlier turns (question + answer) the model sees


def window(history: list, keep_turns: int = KEEP_TURNS) -> list:
    """The last keep_turns turns. One turn = 2 messages. (Session 23, TODO 3.)"""
    return history[-2 * keep_turns:] if keep_turns > 0 else []


SUMMARY_PROMPT = ("Summarise this store conversation in at most 5 short bullet points. Keep every name, order "
                  "number, pincode and figure the CUSTOMER gave. Do not add anything that was not said.")


def summarise(history: list, llm, keep_turns: int = KEEP_TURNS) -> list:
    """STRETCH MP1-T4s: older turns become ONE summary message; the last keep_turns turns stay word for word.

    If history is short (at most 2 * keep_turns messages), return it unchanged. Otherwise:
        old, recent = history[:-2 * keep_turns], history[-2 * keep_turns:]
        transcript = "\\n".join(f"{type(m).__name__}: {m.content}" for m in old)
        summary = llm.invoke([SystemMessage(SUMMARY_PROMPT), HumanMessage(transcript)]).content
        return [SystemMessage(f"Summary of the earlier conversation:\\n{summary}")] + recent
    Cost note for your report: this makes one EXTRA model call on every long turn. Could you avoid that?
    """
    raise NotImplementedError("stretch MP1-T4s")


def trim(history: list, llm=None) -> list:
    """What the model sees of this session's history - the strategy chosen above."""
    if STRATEGY == "summary":
        return summarise(history, llm, KEEP_TURNS)
    return window(history, KEEP_TURNS)

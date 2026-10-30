"""Session 21 checker - tests the code YOU wrote in <work repo>/s21/bankassist_lc.py, offline.

No model is called. Your functions are imported and run against scripted stand-ins:
  - make_llm():   must return a ChatOpenAI built from your .env values (nothing is sent).
  - make_chain(): is run with a fake model that records what reached it.
  - calculate_emi: must be a LangChain tool, return 21696 for 25 lakh / 8.5% / 240, and keep per-argument
                   descriptions (parse_docstring=True).
  - ask():        is run with a fake tool-calling model: it must run the tool, send the result back with the
                  matching tool_call_id, return the model's final words - and stop at the step cap.
Each check returns a CheckResult; a failure says what to fix and which TODO it belongs to.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import BaseTool

from prompt_utils import CheckResult

STUDENT_PATH = Path("s21") / "bankassist_lc.py"
STARTER = Path(__file__).resolve().parent / "s21_starter.py"
EMI_Q = "What is the EMI on a 25 lakh home loan at 8.5% for 20 years?"


def load_student(repo_path):
    """Import (or re-import) the student's file, so edits are picked up without restarting the kernel."""
    path = Path(repo_path) / STUDENT_PATH
    for k, v in {"MODEL": "check-model", "BASE_URL": "http://localhost:9/v1", "API_KEY": "check"}.items():
        os.environ.setdefault(k, v)            # make_llm() only builds the object; nothing is sent
    spec = importlib.util.spec_from_file_location("bankassist_lc_student", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bankassist_lc_student"] = mod
    spec.loader.exec_module(mod)
    return mod


class ScriptedToolModel:
    """Stands in for llm.bind_tools(...): first asks for calculate_emi, then answers using the tool result.
    always_call=True makes it ask for a tool forever - to check the student's step cap."""

    def __init__(self, always_call=False):
        self.calls, self.always_call, self.seen_ids_ok = 0, always_call, None

    def invoke(self, messages):
        self.calls += 1
        if self.calls > 10:
            raise RuntimeError("the loop did not stop - is the step cap missing?")
        tool_msgs = [m for m in messages if isinstance(m, ToolMessage)]
        if tool_msgs and not self.always_call:
            asked = {tc["id"] for m in messages if isinstance(m, AIMessage) for tc in (m.tool_calls or [])}
            self.seen_ids_ok = all(t.tool_call_id in asked for t in tool_msgs)
            return AIMessage(content=f"Your EMI would be about Rs {tool_msgs[-1].content} a month.")
        return AIMessage(content="", tool_calls=[{"name": "calculate_emi", "id": f"call_{self.calls}",
                                                  "args": {"principal": 2500000, "annual_rate": 8.5,
                                                           "tenure_months": 240}}])


def _todo(e, n):
    return f"still a TODO - finish TODO {n}" if isinstance(e, NotImplementedError) else f"{type(e).__name__}: {e}"


def check_s21_work(repo_path) -> list:
    repo = Path(repo_path)

    def ck(name, ok, fix="", info=""):
        return CheckResult(name, ok, info if ok else fix)
    if not repo.exists():
        return [ck("work repo folder exists", False, f"{repo} not found. Fix WORK_REPO.")]
    out = [ck("work repo folder exists", True)]
    if not (repo / STUDENT_PATH).exists():
        out.append(ck("s21/bankassist_lc.py exists", False,
                      "not found - run notebook Section 1 to copy the starter into your work repo"))
        return out
    out.append(ck("s21/bankassist_lc.py exists", True))
    try:
        mod = load_student(repo)
    except Exception as e:  # noqa: BLE001
        out.append(ck("your file imports without errors", False, f"{type(e).__name__}: {e} - see s21_common_errors.md"))
        return out
    out.append(ck("your file imports without errors", True))

    # STEP 1
    try:
        llm = mod.make_llm()
        ok = type(llm).__name__ == "ChatOpenAI" and getattr(llm, "model_name", None) == os.environ["MODEL"]
        out.append(ck("TODO 1 - make_llm() returns ChatOpenAI built from your .env", ok,
                      "return ChatOpenAI(model=os.environ['MODEL'], base_url=os.environ['BASE_URL'], api_key=os.environ['API_KEY'], ...)"))
    except Exception as e:  # noqa: BLE001
        out.append(ck("TODO 1 - make_llm() returns ChatOpenAI built from your .env", False, _todo(e, 1)))

    # STEP 2
    try:
        seen = {}

        def fake_model(prompt_value):
            seen["text"] = " ".join(m.content for m in prompt_value.to_messages())
            return AIMessage(content="On Saturdays we are open 10am to 1pm.")
        result = mod.make_chain(RunnableLambda(fake_model)).invoke({"question": "Saturday timings?"})
        ok = isinstance(result, str) and "10am" in result and mod.SYSTEM[:30] in seen.get("text", "") \
            and "Saturday timings?" in seen.get("text", "")
        out.append(ck("TODO 2 - make_chain() is prompt | llm | StrOutputParser with SYSTEM and {question}", ok,
                      "the chain must send SYSTEM plus the question to the model and return plain text"))
    except Exception as e:  # noqa: BLE001
        out.append(ck("TODO 2 - make_chain() is prompt | llm | StrOutputParser with SYSTEM and {question}", False, _todo(e, 2)))

    # STEP 3
    try:
        t = mod.calculate_emi
        is_tool = isinstance(t, BaseTool)
        emi = t.invoke({"principal": 2500000, "annual_rate": 8.5, "tenure_months": 240}) if is_tool else None
        out.append(ck("TODO 3 - calculate_emi is a @tool and returns 21696 for 25 lakh, 8.5%, 240 months",
                      is_tool and emi == 21696, f"got {emi!r}; expected 21696 (rounded to whole rupees)"))
        props = t.args_schema.model_json_schema().get("properties", {}) if is_tool else {}
        desc = props.get("tenure_months", {}).get("description", "")
        out.append(ck("TODO 3 - argument descriptions reach the model (parse_docstring=True)", "240" in desc,
                      "tenure_months has no description in the schema - keep @tool(parse_docstring=True) and the Args: section"))
    except Exception as e:  # noqa: BLE001
        out.append(ck("TODO 3 - calculate_emi is a @tool and returns 21696 for 25 lakh, 8.5%, 240 months", False, _todo(e, 3)))

    # STEP 4
    try:
        model = ScriptedToolModel()
        with contextlib.redirect_stdout(io.StringIO()):     # hide the student's step prints
            answer = mod.ask(model, EMI_Q)
        ok = isinstance(answer, str) and "21696" in answer.replace(",", "") and model.seen_ids_ok
        out.append(ck("TODO 4 - ask() runs the tool, returns the result with the same tool_call_id, and answers", ok,
                      f"got {answer!r}; append the AIMessage, then TOOLS[name].invoke(call) for each call, then call again"))
    except Exception as e:  # noqa: BLE001
        out.append(ck("TODO 4 - ask() runs the tool, returns the result with the same tool_call_id, and answers", False, _todo(e, 4)))
    try:
        greedy = ScriptedToolModel(always_call=True)
        with contextlib.redirect_stdout(io.StringIO()):
            mod.ask(greedy, EMI_Q, max_steps=3)
        out.append(ck("TODO 4 - ask() stops at the step cap (3 model calls)", greedy.calls == 3,
                      f"the model was called {greedy.calls} times; the loop must stop after max_steps calls"))
    except Exception as e:  # noqa: BLE001
        out.append(ck("TODO 4 - ask() stops at the step cap (3 model calls)", False, _todo(e, 4)))

    # STEP 5 (stretch - never fails the checkpoint)
    has_rate = "get_rate" in getattr(mod, "TOOLS", {})
    out.append(ck("TODO 5 (stretch) - get_rate added to TOOLS", True,
                  info="done" if has_rate else "not attempted - optional"))
    return out

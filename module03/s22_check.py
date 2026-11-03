"""Session 22 checker - tests the code YOU wrote in <work repo>/s22/bankassist_llm.py, offline.

No model is called and no tokens are used. LiteLLM has a built-in test mode (mock_response): the call goes
through all of LiteLLM's code, but the answer is scripted instead of coming from a provider.
  - ask_once():   is run with a recording stand-in for completion(): right model, SYSTEM + question, a key.
  - compare():    must ask PRIMARY and FALLBACK, in that order, and return (model, text) pairs.
  - make_router(): must return a Router whose primary fails over to "bankassist-backup".
  - cost_line():  must price 1,000 + 500 tokens on groq/openai/gpt-oss-20b at $0.000350 - and not crash on
                  a model with no price (Ollama).
  - ask_logged(): (stretch) must answer through the router and print one cost line.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys
from pathlib import Path

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

import litellm  # noqa: E402
from litellm import ModelResponse, Router  # noqa: E402

from prompt_utils import CheckResult  # noqa: E402

STUDENT_PATH = Path("s22") / "bankassist_llm.py"
STARTER = Path(__file__).resolve().parent / "s22_starter.py"
Q = "When are branches open on Saturday?"
CANNED = "Branches are open 10am to 1pm on Saturday."


def load_student(repo_path):
    """Import (or re-import) the student's file, so edits are picked up without restarting the kernel."""
    path = Path(repo_path) / STUDENT_PATH
    for k, v in {"MODEL": "openai/gpt-oss-20b", "BASE_URL": "https://api.groq.com/openai/v1", "API_KEY": "check"}.items():
        os.environ.setdefault(k, v)
    spec = importlib.util.spec_from_file_location("bankassist_llm_student", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bankassist_llm_student"] = mod
    spec.loader.exec_module(mod)
    return mod


class Recorder:
    """Stands in for litellm.completion: records every call, then returns a scripted LiteLLM response."""

    def __init__(self):
        self.calls = []

    def __call__(self, **kw):
        self.calls.append(kw)
        return litellm.completion(**kw, mock_response=CANNED)


def _todo(e, n):
    return f"still a TODO - finish TODO {n}" if isinstance(e, NotImplementedError) else f"{type(e).__name__}: {e}"


class _Usage:
    prompt_tokens, completion_tokens, total_tokens = 1000, 500, 1500


class _FakeResponse:
    usage = _Usage()


def check_s22_work(repo_path) -> list:
    repo = Path(repo_path)

    def ck(name, ok, fix="", info=""):
        return CheckResult(name, ok, info if ok else fix)

    if not repo.exists():
        return [ck("work repo folder exists", False, f"{repo} not found. Fix WORK_REPO.")]
    out = [ck("work repo folder exists", True)]
    if not (repo / STUDENT_PATH).exists():
        out.append(ck("s22/bankassist_llm.py exists", False,
                      "run the notebook's Section 1 (it copies the starter), or copy module03/s22_starter.py yourself"))
        return out
    out.append(ck("s22/bankassist_llm.py exists", True))
    try:
        mod = load_student(repo)
    except Exception as e:  # noqa: BLE001
        out.append(ck("your file imports without errors", False, f"{type(e).__name__}: {e} - see s22_common_errors.md"))
        return out
    out.append(ck("your file imports without errors", True))
    rec = Recorder()
    mod.completion = rec                               # every completion() in YOUR file now goes to the recorder

    # STEP 1
    name1 = "TODO 1 - ask_once() calls completion() with the model, SYSTEM + question, and connection details"
    try:
        r = mod.ask_once("groq/openai/gpt-oss-20b", Q)
        kw = rec.calls[-1] if rec.calls else {}
        msgs = kw.get("messages") or []
        ok = (isinstance(r, ModelResponse) and kw.get("model") == "groq/openai/gpt-oss-20b" and len(msgs) == 2
              and msgs[0].get("role") == "system" and msgs[0].get("content") == mod.SYSTEM
              and msgs[1].get("content") == Q and ("api_key" in kw or "api_base" in kw))
        out.append(ck(name1, ok, f"got model={kw.get('model')!r}, {len(msgs)} messages - use completion(**params(model), "
                                 "messages=messages_for(question), ...) and RETURN the response"))
    except Exception as e:  # noqa: BLE001
        out.append(ck(name1, False, _todo(e, 1)))

    # STEP 2
    name2 = "TODO 2 - compare() asks PRIMARY then FALLBACK and returns (model, text) pairs"
    try:
        rec.calls.clear()
        res = mod.compare(Q)
        ok = (isinstance(res, list) and [m for m, _ in res] == [mod.PRIMARY, mod.FALLBACK]
              and all(t == CANNED for _, t in res) and [c.get("model") for c in rec.calls] == [mod.PRIMARY, mod.FALLBACK])
        out.append(ck(name2, ok, f"got {res!r} - loop over (PRIMARY, FALLBACK), call ask_once, keep (model, text)"))
    except Exception as e:  # noqa: BLE001
        out.append(ck(name2, False, _todo(e, 2)))

    # STEP 3
    name3 = "TODO 3 - make_router() falls back from \"bankassist\" to \"bankassist-backup\""
    try:
        router = mod.make_router(primary="groq/model-that-does-not-exist", fallback="groq/llama-3.1-8b-instant")
        groups = sorted({d["model_name"] for d in router.model_list}) if isinstance(router, Router) else []
        ok = isinstance(router, Router) and groups == ["bankassist", "bankassist-backup"]
        detail = f"got {type(router).__name__} with groups {groups}"
        if ok:
            r = router.completion(model="bankassist", messages=mod.messages_for(Q),
                                  mock_testing_fallbacks=True, mock_response=CANNED)
            ok = mod.answered_by(r) == "groq/llama-3.1-8b-instant" and mod.fallbacks_used(r) >= 1
            detail = f"after the primary failed, {mod.answered_by(r)} answered - check fallbacks=[{{'bankassist': ['bankassist-backup']}}]"
        out.append(ck(name3, ok, detail))
    except Exception as e:  # noqa: BLE001
        out.append(ck(name3, False, _todo(e, 3)))

    # STEP 4
    name4 = "TODO 4 - cost_line() prices 1,000 in + 500 out on gpt-oss-20b at $0.000350"
    try:
        line = mod.cost_line(_FakeResponse(), "groq/openai/gpt-oss-20b", 1.234)
        ok = isinstance(line, str) and "1500" in line and "0.000350" in line and "1.23" in line
        out.append(ck(name4, ok, f"got {line!r} - tokens = prompt + completion; cost from cost_per_token; 6 decimals"))
    except Exception as e:  # noqa: BLE001
        out.append(ck(name4, False, _todo(e, 4)))
    name4b = "TODO 4 - cost_line() does not crash on a model with no price (Ollama)"
    try:
        line = mod.cost_line(_FakeResponse(), "ollama_chat/llama3.2:3b", 0.5)
        out.append(ck(name4b, isinstance(line, str) and "0.000000" in line,
                      f"got {line!r} - wrap cost_per_token in try/except and use 0.0"))
    except Exception as e:  # noqa: BLE001
        out.append(ck(name4b, False, _todo(e, 4)))

    # STEP 5 (stretch)
    name5 = "TODO 5 (stretch) - ask_logged() answers through the router and prints a cost line"
    if not hasattr(mod, "ask_logged"):
        out.append(ck(name5, True, "", "not attempted - optional"))
    else:
        try:
            router = mod.make_router()
            real = router.completion
            router.completion = lambda **kw: real(**kw, mock_response=CANNED)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                text = mod.ask_logged(router, Q)
            printed = buf.getvalue()
            ok = text == CANNED and "tokens" in printed and "$" in printed
            out.append(ck(name5, ok, f"returned {text!r}, printed {printed.strip()[:120]!r}", "done"))
        except Exception as e:  # noqa: BLE001
            out.append(ck(name5, False, _todo(e, 5)))
    return out

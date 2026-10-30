"""Session 21 checkpoint. Run with:  uv run pytest tests/test_s21.py -rs

Everything here is offline. The checker imports YOUR file (<work repo>/s21/bankassist_lc.py) and runs your
functions against scripted stand-ins - no model is called, so this costs nothing.

THE CHECKPOINT: test_checkpoint_your_s21_build_passes runs check_s21_work on YOUR work repository. It needs
WORK_REPO set (in .env or the shell):   $env:WORK_REPO = "$HOME\\Documents\\genai-course-work"
"""
import json
import os
import shutil
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(override=True)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "module02"))
sys.path.insert(0, str(ROOT / "module03"))
from s21_check import STUDENT_PATH, check_s21_work  # noqa: E402

STARTER = ROOT / "module03" / "s21_starter.py"

# What a finished student file looks like - each TODO's `raise NotImplementedError("TODO n")` replaced.
FILLED = {
    'raise NotImplementedError("TODO 1")':
        'return ChatOpenAI(model=os.environ["MODEL"], base_url=os.environ["BASE_URL"], '
        'api_key=os.environ["API_KEY"], temperature=0, max_tokens=1500)',
    'raise NotImplementedError("TODO 2")':
        'prompt = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", "{question}")])\n'
        '    return prompt | llm | StrOutputParser()',
    'raise NotImplementedError("TODO 3")':
        'r = annual_rate / 12 / 100\n'
        '    return round(principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1))',
    'raise NotImplementedError("TODO 4")':
        'messages = [SystemMessage(SYSTEM), HumanMessage(question)]\n'
        '    for step in range(1, max_steps + 1):\n'
        '        ai = llm_with_tools.invoke(messages)\n'
        '        messages.append(ai)\n'
        '        if not ai.tool_calls:\n'
        '            return ai.content\n'
        '        for call in ai.tool_calls:\n'
        '            messages.append(TOOLS[call["name"]].invoke(call))\n'
        '    return "(stopped: step cap reached)"',
}


def student_repo(tmp_path, source: str):
    target = tmp_path / STUDENT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    return tmp_path


def filled(**overrides) -> str:
    src = STARTER.read_text(encoding="utf-8")
    for old, new in {**FILLED, **overrides}.items():
        src = src.replace(old, new)
    return src


def by_name(results):
    return {r.name: r for r in results}


def test_starter_compiles_and_runs_main_without_finishing_anything(capsys):
    compile(STARTER.read_text(encoding="utf-8"), "s21_starter.py", "exec")


def test_untouched_starter_fails_each_todo_with_a_clear_message(tmp_path):
    results = check_s21_work(student_repo(tmp_path, STARTER.read_text(encoding="utf-8")))
    failed = [r for r in results if not r.passed]
    assert len(failed) == 5            # TODO 1, 2, 3, and both TODO 4 checks
    assert all("TODO" in r.detail for r in failed)


def test_a_finished_file_passes_every_check(tmp_path):
    results = check_s21_work(student_repo(tmp_path, filled()))
    bad = [(r.name, r.detail) for r in results if not r.passed]
    assert not bad, bad


def test_dropping_parse_docstring_is_caught(tmp_path):
    src = filled().replace("@tool(parse_docstring=True)\ndef calculate_emi", "@tool\ndef calculate_emi")
    r = by_name(check_s21_work(student_repo(tmp_path, src)))
    assert not r["TODO 3 - argument descriptions reach the model (parse_docstring=True)"].passed


def test_a_wrong_formula_is_caught(tmp_path):
    src = filled(**{'raise NotImplementedError("TODO 3")': "return round(principal * annual_rate / 100 / tenure_months)"})
    r = by_name(check_s21_work(student_repo(tmp_path, src)))
    assert not r["TODO 3 - calculate_emi is a @tool and returns 21696 for 25 lakh, 8.5%, 240 months"].passed


def test_a_loop_without_a_cap_is_caught(tmp_path):
    uncapped = FILLED['raise NotImplementedError("TODO 4")'].replace(
        "for step in range(1, max_steps + 1):", "while True:")
    src = filled(**{'raise NotImplementedError("TODO 4")': uncapped})
    r = by_name(check_s21_work(student_repo(tmp_path, src)))
    assert not r["TODO 4 - ask() stops at the step cap (3 model calls)"].passed


def test_forgetting_to_append_the_ai_message_is_caught(tmp_path):
    broken = FILLED['raise NotImplementedError("TODO 4")'].replace("        messages.append(ai)\n", "")
    src = filled(**{'raise NotImplementedError("TODO 4")': broken})
    r = by_name(check_s21_work(student_repo(tmp_path, src)))
    assert not r["TODO 4 - ask() runs the tool, returns the result with the same tool_call_id, and answers"].passed


def test_missing_file_and_missing_repo(tmp_path):
    assert not check_s21_work(tmp_path / "nowhere")[0].passed
    tmp_path.mkdir(exist_ok=True)
    assert not by_name(check_s21_work(tmp_path))["s21/bankassist_lc.py exists"].passed


def test_a_syntax_error_is_reported_not_raised(tmp_path):
    r = by_name(check_s21_work(student_repo(tmp_path, "def broken(:\n")))
    assert not r["your file imports without errors"].passed


def test_the_notebook_is_valid_and_compiles():
    nb = json.loads((ROOT / "module03" / "s21_langchain_build.ipynb").read_text(encoding="utf-8"))
    code = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert len(code) >= 8
    for i, cell in enumerate(code):
        compile("".join(cell["source"]), f"cell {i}", "exec")


# ---------------------------------------------------------------- the checkpoint (offline, reads YOUR file)
@pytest.mark.skipif(not os.getenv("WORK_REPO"), reason="WORK_REPO not set: the checkpoint cannot find your file")
def test_checkpoint_your_s21_build_passes():
    results = check_s21_work(os.environ["WORK_REPO"])
    for r in results:
        print(f"  {'PASS' if r.passed else 'FAIL'}  {r.name}" + (f"   ({r.detail})" if r.detail else ""))
    failed = [r for r in results if not r.passed]
    assert not failed, "fix the FAILs above, then run this again"

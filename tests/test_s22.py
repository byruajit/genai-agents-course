"""Session 22 checkpoint. Run with:  uv run pytest tests/test_s22.py -rs

Everything here is offline: LiteLLM's test mode (mock_response) scripts the answers, so no tokens are used.

THE CHECKPOINT: test_checkpoint_your_s22_build_passes runs check_s22_work on YOUR work repository. It needs
WORK_REPO set (in .env or the shell):   $env:WORK_REPO = "$HOME\\Documents\\genai-course-work"
"""
import json
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(override=True)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "module02"))
sys.path.insert(0, str(ROOT / "module03"))
from s22_check import STUDENT_PATH, check_s22_work  # noqa: E402

STARTER = ROOT / "module03" / "s22_starter.py"

# What a finished student file looks like - each TODO's `raise NotImplementedError("TODO n")` replaced.
KEY = ROOT / "S22" / "s22_answer_key.py"      # instructor only: gitignored, students don't have it


def answer(name: str):
    if not KEY.exists():
        pytest.skip("instructor answer key not present (that's expected on a student laptop)")
    ns: dict = {}
    exec(KEY.read_text(encoding="utf-8"), ns)
    return ns[name]


class _Key:
    """FILLED, loaded only when a test uses it - so student laptops skip instead of failing."""

    def keys(self):
        return answer("FILLED").keys()

    def items(self):
        return answer("FILLED").items()

    def __getitem__(self, k):
        return answer("FILLED")[k]


FILLED = _Key()


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


def failed(results):
    return [r.name for r in results if not r.passed]


def test_starter_compiles():
    compile(STARTER.read_text(encoding="utf-8"), "s22_starter.py", "exec")


def test_untouched_starter_fails_each_todo_with_a_clear_message(tmp_path):
    results = check_s22_work(student_repo(tmp_path, STARTER.read_text(encoding="utf-8")))
    bad = [r for r in results if not r.passed]
    assert len(bad) == 5                      # TODO 1, 2, 3 and both TODO 4 checks
    assert all("TODO" in r.detail for r in bad)


def test_a_finished_file_passes_every_check(tmp_path):
    results = check_s22_work(student_repo(tmp_path, filled()))
    assert not failed(results), [(r.name, r.detail) for r in results if not r.passed]


def test_forgetting_the_system_message_is_caught(tmp_path):
    src = filled(**{'    raise NotImplementedError("TODO 1")':
                    '    return completion(**params(model), messages=[{"role": "user", "content": question}])'})
    assert any(n.startswith("TODO 1") for n in failed(check_s22_work(student_repo(tmp_path, src))))


def test_a_router_without_fallbacks_is_caught(tmp_path):
    src = filled().replace('        fallbacks=[{"bankassist": ["bankassist-backup"]}],\n', "")
    assert any(n.startswith("TODO 3") for n in failed(check_s22_work(student_repo(tmp_path, src))))


def test_a_cost_line_that_crashes_on_ollama_is_caught(tmp_path):
    src = filled(**{'    raise NotImplementedError("TODO 4")':
                    '    p, c = response.usage.prompt_tokens, response.usage.completion_tokens\n'
                    '    cost = sum(cost_per_token(model=model, prompt_tokens=p, completion_tokens=c))\n'
                    '    return f"{model} | {p + c} tokens | ${cost:.6f} | {seconds:.2f}s"'})
    names = failed(check_s22_work(student_repo(tmp_path, src)))
    assert "TODO 4 - cost_line() does not crash on a model with no price (Ollama)" in names
    assert not any("gpt-oss-20b at" in n for n in names)


def test_missing_file_and_missing_repo(tmp_path):
    assert not check_s22_work(tmp_path / "nowhere")[0].passed
    assert not by_name(check_s22_work(tmp_path))["s22/bankassist_llm.py exists"].passed


def test_a_syntax_error_is_reported_not_raised(tmp_path):
    assert not by_name(check_s22_work(student_repo(tmp_path, "def broken(:\n")))["your file imports without errors"].passed


def test_the_notebook_is_valid_and_compiles():
    nb = json.loads((ROOT / "module03" / "s22_litellm_build.ipynb").read_text(encoding="utf-8"))
    code = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert len(code) >= 8
    for i, cell in enumerate(code):
        compile("".join(cell["source"]), f"cell {i}", "exec")


# ---------------------------------------------------------------- the checkpoint (offline, reads YOUR file)
@pytest.mark.skipif(not os.getenv("WORK_REPO"), reason="WORK_REPO not set: the checkpoint cannot find your file")
def test_checkpoint_your_s22_build_passes():
    results = check_s22_work(os.environ["WORK_REPO"])
    for r in results:
        print(f"  {'PASS' if r.passed else 'FAIL'}  {r.name}" + (f"   ({r.detail})" if r.detail else ""))
    assert not failed(results), "fix the FAILs above, then run this again"

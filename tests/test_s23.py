"""Session 23 checkpoint. Run with:  uv run pytest tests/test_s23.py -rs

Everything here is offline. The checker imports YOUR file (<work repo>/s23/app.py), swaps the model for a scripted
stand-in, and sends real HTTP requests to your app with FastAPI's TestClient - no server, no model, no cost.

THE CHECKPOINT: test_checkpoint_your_s23_server_passes runs check_s23_work on YOUR work repository. It needs
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
from s23_check import STUDENT_PATH, check_s23_work, parse_sse  # noqa: E402

STARTER = ROOT / "module03" / "s23_starter.py"

# What a finished student file looks like - each TODO replaced.
FILLED = {
    'raise NotImplementedError("TODO 1")': 'return {"status": "ok", "model": os.environ["MODEL"]}',
    "    message: str        # TODO 2a": "    message: str = Field(min_length=1, max_length=2000)  # TODO 2a",
    "    # TODO 2b: add two more fields:   tool_steps: list[str]    and    turns: int\n":
        "    tool_steps: list[str]\n    turns: int\n",
    'raise NotImplementedError("TODO 3")': "return history[-2 * keep_turns:] if keep_turns > 0 else []",
    'raise NotImplementedError("TODO 4")':
        "history = SESSIONS.setdefault(req.session_id, [])\n"
        "    messages = [SystemMessage(SYSTEM), *window(history), HumanMessage(req.message)]\n"
        "    answer, steps = run_turn(get_llm(), messages)\n"
        "    history += [HumanMessage(req.message), AIMessage(answer)]\n"
        "    return ChatResponse(session_id=req.session_id, answer=answer, tool_steps=steps, turns=len(history) // 2)",
    '    raise NotImplementedError("TODO 5")\n\n\n@app.post("/chat/stream")':
        '    return f"event: {event}\\ndata: {json.dumps(data)}\\n\\n"\n\n\n@app.post("/chat/stream")',
    '    raise NotImplementedError("TODO 5")\n\n\n# ----':
        "    history = SESSIONS.setdefault(req.session_id, [])\n"
        "    messages = [SystemMessage(SYSTEM), *window(history), HumanMessage(req.message)]\n\n"
        "    def events():\n"
        "        for kind, text in stream_turn(get_llm(), messages):\n"
        '            if kind == "done":\n'
        "                history.extend([HumanMessage(req.message), AIMessage(text)])\n"
        '            yield sse(kind, {"text": text})\n\n'
        '    return StreamingResponse(events(), media_type="text/event-stream")\n\n\n# ----',
}
STRETCH = (
    '\n\n@app.delete("/sessions/{session_id}")\n'
    "def forget(session_id: str):\n"
    '    return {"deleted": SESSIONS.pop(session_id, None) is not None}\n\n\nif __name__ == "__main__":')


def student_repo(tmp_path, source: str):
    target = tmp_path / STUDENT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    return tmp_path


def filled(**overrides) -> str:
    src = STARTER.read_text(encoding="utf-8")
    for old, new in {**FILLED, **overrides}.items():
        assert old in src, f"starter changed - FILLED key not found: {old[:60]!r}"
        src = src.replace(old, new)
    return src


def by_name(results):
    return {r.name: r for r in results}


def test_starter_compiles():
    compile(STARTER.read_text(encoding="utf-8"), "s23_starter.py", "exec")


def test_untouched_starter_fails_each_todo_with_a_clear_message(tmp_path):
    results = check_s23_work(student_repo(tmp_path, STARTER.read_text(encoding="utf-8")))
    failed = [r for r in results if not r.passed]
    assert len(failed) == 7            # TODO 1, 2, 3, both TODO 4 checks, both TODO 5 checks
    todo = [r for r in failed if not r.name.startswith("TODO 2")]
    assert all("TODO" in r.detail for r in todo), [(r.name, r.detail) for r in todo]


def test_a_finished_file_passes_every_check(tmp_path):
    results = check_s23_work(student_repo(tmp_path, filled()))
    bad = [(r.name, r.detail) for r in results if not r.passed]
    assert not bad, bad
    assert by_name(results)["TODO 6 (stretch) - DELETE /sessions/{id}"].detail == "not attempted - optional"


def test_the_stretch_is_recognised(tmp_path):
    src = filled().replace('\n\nif __name__ == "__main__":', STRETCH, 1)
    r = by_name(check_s23_work(student_repo(tmp_path, src)))
    assert r["TODO 6 (stretch) - DELETE /sessions/{id}"].detail == "done"


def test_forgetting_to_save_the_answer_is_caught(tmp_path):
    src = filled(**{'raise NotImplementedError("TODO 4")': FILLED['raise NotImplementedError("TODO 4")'].replace(
        "history += [HumanMessage(req.message), AIMessage(answer)]", "history += [HumanMessage(req.message)]")})
    r = by_name(check_s23_work(student_repo(tmp_path, src)))
    assert not r["TODO 4 - POST /chat remembers a session and keeps sessions apart"].passed


def test_sending_the_whole_history_instead_of_the_window_is_caught(tmp_path):
    src = filled(**{'raise NotImplementedError("TODO 4")': FILLED['raise NotImplementedError("TODO 4")'].replace(
        "*window(history)", "*history")})
    r = by_name(check_s23_work(student_repo(tmp_path, src)))
    assert r["TODO 4 - POST /chat remembers a session and keeps sessions apart"].passed
    assert not r["TODO 4 - POST /chat applies the window and reports tool steps"].passed


def test_an_off_by_one_window_is_caught(tmp_path):
    src = filled(**{'raise NotImplementedError("TODO 3")': "return history[-keep_turns:]"})
    assert not by_name(check_s23_work(student_repo(tmp_path, src)))[
        "TODO 3 - window() keeps exactly the last keep_turns turns"].passed


def test_sse_without_json_or_blank_line_is_caught(tmp_path):
    for bad in ('    return f"event: {event}\\ndata: {data}\\n\\n"\n\n\n@app.post("/chat/stream")',
                '    return f"event: {event}\\ndata: {json.dumps(data)}\\n"\n\n\n@app.post("/chat/stream")'):
        src = filled(**{'    raise NotImplementedError("TODO 5")\n\n\n@app.post("/chat/stream")': bad})
        assert not by_name(check_s23_work(student_repo(tmp_path, src)))[
            "TODO 5 - sse() formats one Server-Sent Event"].passed


def test_wrong_media_type_is_caught(tmp_path):
    key = '    raise NotImplementedError("TODO 5")\n\n\n# ----'
    src = filled(**{key: FILLED[key].replace('media_type="text/event-stream"', 'media_type="text/plain"')})
    assert not by_name(check_s23_work(student_repo(tmp_path, src)))[
        "TODO 5 - POST /chat/stream streams tool, token and done events, and remembers the turn"].passed


def test_parse_sse_reads_events_and_rejects_junk():
    assert parse_sse('event: token\ndata: {"text": "hi"}\n\nevent: done\ndata: {"text": "hi"}\n\n') == [
        ("token", {"text": "hi"}), ("done", {"text": "hi"})]
    with pytest.raises(ValueError):
        parse_sse("data: only\n\n")


def test_missing_file_and_missing_repo(tmp_path):
    assert not check_s23_work(tmp_path / "nowhere")[0].passed
    assert not by_name(check_s23_work(tmp_path))["s23/app.py exists"].passed


def test_a_syntax_error_is_reported_not_raised(tmp_path):
    assert not by_name(check_s23_work(student_repo(tmp_path, "def broken(:\n")))[
        "your file imports without errors"].passed


def test_the_notebook_is_valid_and_compiles():
    nb = json.loads((ROOT / "module03" / "s23_serving.ipynb").read_text(encoding="utf-8"))
    code = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert len(code) >= 8
    for i, cell in enumerate(code):
        compile("".join(cell["source"]), f"cell {i}", "exec")


# ---------------------------------------------------------------- the checkpoint (offline, reads YOUR file)
@pytest.mark.skipif(not os.getenv("WORK_REPO"), reason="WORK_REPO not set: the checkpoint cannot find your file")
def test_checkpoint_your_s23_server_passes():
    results = check_s23_work(os.environ["WORK_REPO"])
    for r in results:
        print(f"  {'PASS' if r.passed else 'FAIL'}  {r.name}" + (f"   ({r.detail})" if r.detail else ""))
    failed = [r for r in results if not r.passed]
    assert not failed, "fix the FAILs above, then run this again"


def test_the_simple_version_passes_the_same_checks(tmp_path):
    """module03/s23_simple.py (the run-and-change version) is a complete server: as a student's s23/app.py it must
    pass every check the build-your-own version has to pass."""
    repo = tmp_path / "work"
    (repo / "s23").mkdir(parents=True)
    (repo / "s23" / "app.py").write_text((ROOT / "module03" / "s23_simple.py").read_text(encoding="utf-8"),
                                         encoding="utf-8")
    failed = [(r.name, r.detail) for r in check_s23_work(repo) if not r.passed]
    assert not failed, failed

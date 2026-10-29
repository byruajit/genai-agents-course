"""Session 20 checkpoint. Run with:  uv run pytest tests/test_s20.py -rs

Everything here is offline EXCEPT the checkpoint at the bottom. Two scripted stand-ins replace the model:
  perfect_client()    - answers every golden question the right way: right tool, right arguments, right answer,
                        two steps for the two-step question, TOOL/NO_TOOL correctly when asked to route.
  overcalling_client() - behaves like the 3B model recorded on the instructor's laptop: it calls calculate_emi with
                        "0" strings for every question, and only answers in prose after it is told INVALID.
They cost nothing, never touch the network, and give the same result every time.

THE CHECKPOINT: test_checkpoint_your_tools_report_is_complete loads YOUR report from YOUR work repository
(experiments/s20_tools.md) and checks it is complete: the model named, all four ways scored, each on the full
golden set. It does not require any particular fix to win - that depends on the model. It needs the three .env
values (API_KEY, BASE_URL, MODEL - with Ollama, API_KEY=ollama is fine) and WORK_REPO set:

    WORK_REPO=C:\\Users\\you\\Documents\\genai-course-work

With no .env values it is skipped (read the reason: -rs). A skip is not a pass."""
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from dotenv import load_dotenv

load_dotenv(override=True)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "module02"))
sys.path.insert(0, str(ROOT / "module03"))
from tool_tasks import GOLDEN, RATE_CARD, ROUTER_PROMPT, TOOLS, TOOLS_GUIDANCE, WAYS  # noqa: E402
from tool_utils import (answer_question, assistant_message, calculate_emi, call_model, check_eligibility,  # noqa: E402
                        check_s20_work, compare_fixes, execute_tool, fixes_table, get_rate, parse_args,
                        parse_tools_report, question_grid, route, run_with_tools, save_tools_report,
                        score_question, system_for, tool_message, tools_markdown, validate_args)


# ---------------------------------------------------------------- scripted stand-ins for the model
def reply(content="", tool_calls=None, finish=None):
    calls = [SimpleNamespace(id=f"call_{i}", function=SimpleNamespace(name=n, arguments=a))
             for i, (n, a) in enumerate(tool_calls or [])]
    msg = SimpleNamespace(content=content, tool_calls=calls or None)
    usage = SimpleNamespace(prompt_tokens=100, completion_tokens=10)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason=finish or ("tool_calls" if calls else "stop"))],
                           usage=usage)


class FakeClient:
    def __init__(self, handler):
        self.handler, self.calls = handler, []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self.handler(kwargs)


GOLDEN_BY_Q = {g["question"]: g for g in GOLDEN}
NO_TOOL_ANSWERS = {"g7": "On Saturdays we are open 10am to 1pm.", "g8": "No, there is no prepayment penalty on floating-rate loans.",
                   "g9": "You need a credit score of at least 700.", "g10": "You're welcome - have a good day!"}


def _question(kw):
    return next(m["content"] for m in kw["messages"] if m["role"] == "user")


def _prose_from_tool_result(result: dict) -> str:
    if "emi_rupees" in result:
        return f"Your EMI would be about \u20b9{result['emi_rupees']:,} a month."
    if "annual_rate_percent" in result:
        return f"Today's rate is {result['annual_rate_percent']}% per year."
    if "eligible" in result:
        return ("Yes, that is within our limit, so you are eligible." if result["eligible"]
                else "Unfortunately that would exceed our 50% limit, so you are not eligible.")
    return "Sorry, I could not work that out."


def perfect_client():
    def handler(kw):
        if kw["messages"][0]["content"] == ROUTER_PROMPT:
            return reply("TOOL" if GOLDEN_BY_Q[_question(kw)]["expect_tools"] else "NO_TOOL")
        item = GOLDEN_BY_Q[_question(kw)]
        tool_msgs = [m for m in kw["messages"] if m["role"] == "tool"]
        if not item["expect_tools"]:
            return reply(NO_TOOL_ANSWERS[item["id"]])
        if item["id"] == "g4":
            if len(tool_msgs) == 0:
                return reply(tool_calls=[("get_rate", json.dumps({"product": "home_loan", "rate_type": "floating"}))])
            if len(tool_msgs) == 1:
                return reply(tool_calls=[("calculate_emi", json.dumps(item["expect_args"]["calculate_emi"]))])
            return reply(_prose_from_tool_result(json.loads(tool_msgs[-1]["content"])))
        if not tool_msgs:
            (name, args), = item["expect_args"].items()
            return reply(tool_calls=[(name, json.dumps(args))])
        return reply(_prose_from_tool_result(json.loads(tool_msgs[-1]["content"])))
    return FakeClient(handler)


def overcalling_client():
    """Calls calculate_emi with "0" strings whenever tools are attached; answers in prose only after INVALID."""
    def handler(kw):
        if kw["messages"][0]["content"] == ROUTER_PROMPT:
            return reply("TOOL" if GOLDEN_BY_Q[_question(kw)]["expect_tools"] else "NO_TOOL")
        item = GOLDEN_BY_Q[_question(kw)]
        tool_msgs = [m for m in kw["messages"] if m["role"] == "tool"]
        if tool_msgs and "INVALID" in tool_msgs[-1]["content"] and not item["expect_tools"]:
            return reply(NO_TOOL_ANSWERS[item["id"]])
        if "tools" in kw:
            return reply(tool_calls=[("calculate_emi", '{"annual_rate":"0","principal":"0","tenure_months":"0"}')])
        return reply(NO_TOOL_ANSWERS.get(item["id"], "I can't calculate that right now."))
    return FakeClient(handler)


class DictCache:
    def __init__(self):
        self.data = {}

    def get(self, k):
        return self.data.get(k)

    def put(self, k, v):
        self.data[k] = v


# ---------------------------------------------------------------- the tools themselves
def test_calculate_emi_matches_the_known_answers():
    assert round(calculate_emi(2_500_000, 8.5, 240)) == 21696
    assert round(calculate_emi(500_000, 10.5, 36)) == 16251
    assert round(calculate_emi(3_000_000, 8.5, 180)) == 29542


def test_get_rate_reads_the_card_and_refuses_what_is_not_on_it():
    assert get_rate("home_loan", "floating") == RATE_CARD[("home_loan", "floating")] == 8.5
    with pytest.raises(ValueError):
        get_rate("personal_loan", "floating")


def test_check_eligibility_applies_the_50_percent_rule():
    assert check_eligibility(80000, 15000, 21696)["eligible"] is True
    assert check_eligibility(50000, 10000, 21696)["eligible"] is False


def test_execute_tool_never_raises_and_returns_json():
    assert json.loads(execute_tool("calculate_emi", {"principal": 2500000, "annual_rate": 8.5, "tenure_months": 240})) == {"emi_rupees": 21696}
    assert "error" in json.loads(execute_tool("calculate_emi", {"principal": "0", "annual_rate": "0", "tenure_months": "0"}))
    assert "error" in json.loads(execute_tool("calculate_emi", {"principal": 0, "annual_rate": 0, "tenure_months": 0}))
    assert "error" in json.loads(execute_tool("open_account", {}))


# ---------------------------------------------------------------- Fix B: validation in code
def test_validate_args_accepts_a_good_call_and_drops_extra_keys():
    args, err = validate_args("calculate_emi", '{"principal": 2500000, "annual_rate": 8.5, "tenure_months": 240, "note": "x"}')
    assert err is None and args == {"principal": 2500000, "annual_rate": 8.5, "tenure_months": 240}


@pytest.mark.parametrize("raw", [
    '{"annual_rate":"0","principal":"0","tenure_months":"0"}',     # the laptop's real output: strings
    '{"principal": 0, "annual_rate": 8.5, "tenure_months": 240}',  # zero
    '{"principal": 2500000, "annual_rate": 0.085, "tenure_months": 240}',  # a fraction, not a percent
    '{"principal": 2500000, "annual_rate": 8.5, "tenure_months": 20.5}',   # not whole months
    '{"principal": 2500000, "annual_rate": 8.5}',                   # missing
    'not json at all',
])
def test_validate_args_rejects_what_the_schema_only_asked_for(raw):
    args, err = validate_args("calculate_emi", raw)
    assert args is None and err


def test_validate_args_checks_get_rate_pairs_and_unknown_tools():
    assert validate_args("get_rate", '{"product": "home_loan", "rate_type": "fixed"}')[1] is None
    assert validate_args("get_rate", '{"product": "personal_loan", "rate_type": "floating"}')[1]
    assert validate_args("open_account", "{}")[1]


def test_parse_args_handles_strings_dicts_and_garbage():
    assert parse_args('{"a": 1}') == {"a": 1}
    assert parse_args({"a": 1}) == {"a": 1}
    assert parse_args("[1, 2]") is None and parse_args("nope") is None


# ---------------------------------------------------------------- one call, normalised and cached
def test_call_model_normalises_a_tool_call_and_caches_it():
    client = FakeClient(lambda kw: reply(tool_calls=[("get_rate", '{"product":"home_loan","rate_type":"fixed"}')]))
    cache = DictCache()
    out = call_model(client, "m", [{"role": "user", "content": "rate?"}], tools=TOOLS, cache=cache)
    assert out["finish_reason"] == "tool_calls" and out["tool_calls"][0]["name"] == "get_rate"
    again = call_model(client, "m", [{"role": "user", "content": "rate?"}], tools=TOOLS, cache=cache)
    assert again == out and len(client.calls) == 1


def test_call_model_omits_tools_when_none_are_given():
    client = FakeClient(lambda kw: reply("hello"))
    call_model(client, "m", [{"role": "user", "content": "hi"}], tools=None)
    assert "tools" not in client.calls[0]


def test_the_two_new_message_shapes():
    out = {"content": "", "tool_calls": [{"id": "call_7", "name": "get_rate", "arguments": "{}"}]}
    a = assistant_message(out)
    assert a["role"] == "assistant" and a["tool_calls"][0]["id"] == "call_7" and a["tool_calls"][0]["type"] == "function"
    assert tool_message("call_7", "{}") == {"role": "tool", "tool_call_id": "call_7", "content": "{}"}


# ---------------------------------------------------------------- the round trip
def test_run_with_tools_appends_a_matching_tool_message_and_answers():
    item = GOLDEN[0]
    res = run_with_tools(perfect_client(), "m", [{"role": "system", "content": system_for("none")},
                                                 {"role": "user", "content": item["question"]}])
    ids = [tc["id"] for m in res["messages"] if m["role"] == "assistant" for tc in m["tool_calls"]]
    tool_ids = [m["tool_call_id"] for m in res["messages"] if m["role"] == "tool"]
    assert ids == tool_ids and "21,696" in res["final_text"] and not res["capped"]


def test_run_with_tools_handles_the_two_step_question():
    item = next(g for g in GOLDEN if g["id"] == "g4")
    res = run_with_tools(perfect_client(), "m", [{"role": "system", "content": system_for("none")},
                                                 {"role": "user", "content": item["question"]}])
    assert [c["name"] for c in res["calls"]] == ["get_rate", "calculate_emi"] and res["steps"] == 3


def test_run_with_tools_stops_at_the_cap():
    item = next(g for g in GOLDEN if g["id"] == "g7")
    res = run_with_tools(overcalling_client(), "m", [{"role": "system", "content": system_for("none")},
                                                     {"role": "user", "content": item["question"]}], max_steps=3)
    assert res["capped"] and res["final_text"] == "" and len(res["calls"]) == 3


# ---------------------------------------------------------------- Fix C: the router
@pytest.mark.parametrize("word,expected", [("TOOL", True), ("NO_TOOL", False), ("**TOOL**", True), ("no_tool.", False), ("maybe", False)])
def test_route_reads_how_the_answer_starts(word, expected):
    needs, tokens = route(FakeClient(lambda kw: reply(word)), "m", "anything")
    assert needs is expected and tokens == 110


def test_answer_question_rejects_an_unknown_way():
    with pytest.raises(ValueError):
        answer_question(perfect_client(), "m", "hi", way="magic")


def test_fix_a_adds_the_guidance_to_the_system_prompt():
    assert TOOLS_GUIDANCE.strip() in system_for("prompt") and TOOLS_GUIDANCE.strip() not in system_for("none")


# ---------------------------------------------------------------- the three fixes against an over-calling model
def test_over_caller_fails_the_branch_timings_question_with_no_fix():
    g7 = next(g for g in GOLDEN if g["id"] == "g7")
    res = answer_question(overcalling_client(), "m", g7["question"], "none")
    sc = score_question(g7, res)
    assert sc == {"tool_ok": False, "args_ok": None, "answer_ok": False}


def test_fix_b_lets_the_over_caller_recover():
    g7 = next(g for g in GOLDEN if g["id"] == "g7")
    res = answer_question(overcalling_client(), "m", g7["question"], "validate")
    assert "INVALID" in res["calls"][0]["result"] and score_question(g7, res)["answer_ok"]


def test_fix_c_never_attaches_tools_to_a_no_tool_question():
    g7 = next(g for g in GOLDEN if g["id"] == "g7")
    client = overcalling_client()
    res = answer_question(client, "m", g7["question"], "router")
    assert res["routed_to_tools"] is False and score_question(g7, res)["tool_ok"]
    assert "tools" not in client.calls[-1]


# ---------------------------------------------------------------- scoring
def test_a_perfect_model_scores_full_marks_all_four_ways():
    results = compare_fixes(perfect_client(), "m")
    for w in WAYS:
        r = results[w]
        assert (r["tool_right"], r["args_ok"], r["answer_ok"]) == (r["n"], r["n_tool"], r["n"]) == (10, 6, 10), w


def test_golden_set_shape():
    assert len(GOLDEN) == 10 and sum(1 for g in GOLDEN if g["expect_tools"]) == 6
    assert any(len(g["expect_tools"]) == 2 for g in GOLDEN)


def test_score_question_ignores_commas_and_rupee_signs():
    g1 = GOLDEN[0]
    res = {"calls": [{"name": "calculate_emi", "arguments": json.dumps(g1["expect_args"]["calculate_emi"]), "valid": True}],
           "final_text": "About \u20b9 21,696 per month"}
    assert score_question(g1, res) == {"tool_ok": True, "args_ok": True, "answer_ok": True}


def test_score_question_marks_wrong_argument_values():
    g1 = GOLDEN[0]
    res = {"calls": [{"name": "calculate_emi", "arguments": '{"principal": 2500000, "annual_rate": 8.5, "tenure_months": 20}',
                      "valid": True}], "final_text": "21,696"}
    assert score_question(g1, res)["args_ok"] is False


def test_tables_print():
    results = compare_fixes(perfect_client(), "m")
    assert "Fix C" in fixes_table(results) and "g10" in question_grid(results)


# ---------------------------------------------------------------- the report you commit
def test_report_round_trip_and_save(tmp_path):
    results = compare_fixes(perfect_client(), "m")
    text = tools_markdown(results, "llama3.2:3b", today="2026-10-29")
    parsed = parse_tools_report(text)
    assert parsed["model"] == "llama3.2:3b" and set(parsed["ways"]) == set(WAYS)
    assert parsed["ways"]["none"]["tool_right"] == 10 and parsed["ways"]["none"]["n_tool"] == 6
    path = save_tools_report(tmp_path, text)
    assert path == tmp_path / "experiments" / "s20_tools.md" and path.exists()


def write_work(tmp_path, text=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    if text is not None:
        save_tools_report(tmp_path, text)
    return tmp_path


def test_check_s20_work_passes_a_complete_report(tmp_path):
    text = tools_markdown(compare_fixes(perfect_client(), "m"), "m")
    results = check_s20_work(write_work(tmp_path, text))
    failed = [r for r in results if not r.passed]
    assert not failed, [(r.name, r.detail) for r in failed]


def test_check_s20_work_catches_missing_report_way_and_model(tmp_path):
    assert not check_s20_work(tmp_path / "nowhere")[0].passed
    assert {r.name: r.passed for r in check_s20_work(write_work(tmp_path / "a"))}["tools report exists"] is False
    full = tools_markdown(compare_fixes(perfect_client(), "m"), "m")
    no_router = "\n".join(ln for ln in full.splitlines() if not ln.startswith("| router"))
    assert any("all four ways" in r.name and not r.passed for r in check_s20_work(write_work(tmp_path / "b", no_router)))
    no_model = full.replace("Model: `m`", "Model: unknown")
    assert any("names the model" in r.name and not r.passed for r in check_s20_work(write_work(tmp_path / "c", no_model)))


def test_check_s20_work_catches_a_partial_golden_set(tmp_path):
    results = compare_fixes(perfect_client(), "m", items=GOLDEN[:5])
    failed = {r.name for r in check_s20_work(write_work(tmp_path, tools_markdown(results, "m"))) if not r.passed}
    assert any("full golden set" in n for n in failed)


# ---------------------------------------------------------------- the notebook
def test_the_notebook_is_valid_and_compiles():
    nb = json.loads((ROOT / "module03" / "s20_function_calling.ipynb").read_text(encoding="utf-8"))
    code = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert len(code) >= 10
    for i, cell in enumerate(code):
        compile("".join(cell["source"]), f"cell {i}", "exec")


# ---------------------------------------------------------------- the checkpoint (live: needs .env values)
LIVE = bool(os.getenv("API_KEY") and os.getenv("BASE_URL") and os.getenv("MODEL"))


@pytest.mark.skipif(not LIVE, reason="no API_KEY/BASE_URL/MODEL in .env: the checkpoint cannot run yet")
def test_checkpoint_your_tools_report_is_complete():
    repo = os.getenv("WORK_REPO")
    if not repo:
        pytest.fail("Set WORK_REPO to your work repository folder, in .env or in the shell, then run this again. "
                    "Example (PowerShell):  $env:WORK_REPO = \"$HOME\\Documents\\genai-course-work\"")
    results = check_s20_work(repo)
    for r in results:
        print(f"  {'PASS' if r.passed else 'FAIL'}  {r.name}" + (f"   ({r.detail})" if r.detail else ""))
    failed = [r for r in results if not r.passed]
    assert not failed, "fix the FAILs above, then run this again"

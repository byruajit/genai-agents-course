"""Session 20 helpers - function calling with the raw OpenAI-compatible API, no framework.

Five ideas live here:
  1. The tools themselves are plain, boring, tested Python: calculate_emi, get_rate, check_eligibility. The model
     never runs them - it only asks. execute_tool runs them and always returns a JSON string, even on failure.
  2. call_model normalises one API response into a plain dict (content, tool_calls, finish_reason, tokens), so the
     same code works on Groq and on Ollama, and answers can be cached on disk like every session since S15.
  3. run_with_tools is the round trip, in a loop capped at MAX_STEPS: call, run any requested tools, append the
     assistant message (with its tool_calls) and one tool message per call (with the matching tool_call_id),
     call again - until the model answers in prose or the cap is hit. A loop with no cap is an agent (Module 6).
  4. Three fixes for a model that over-calls or invents arguments: Fix A adds TOOLS_GUIDANCE to the prompt,
     Fix B runs validate_args and sends errors back as the tool result, Fix C routes first and only attaches
     tools when the router says TOOL.
  5. score_question grades each golden answer three ways, decided before looking at results (Session 17's
     habit): right tool (or none), valid and correct arguments, correct final answer.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
import re
from pathlib import Path

from chat_tasks import BANKASSIST_SYSTEM
from prompt_utils import CheckResult
from tool_tasks import FOIR_LIMIT, GOLDEN, MAX_STEPS, RATE_CARD, ROUTER_PROMPT, TOOLS, TOOLS_GUIDANCE, WAYS, WAY_LABELS

REPORT_PATH = Path("experiments") / "s20_tools.md"
S20_CACHE = Path.home() / ".genai_course" / "s20_cache.json"


# ================================================================ 1. the tools: plain Python, the model never runs them
def calculate_emi(principal, annual_rate, tenure_months):
    """Standard reducing-balance EMI. annual_rate is a percent (8.5, not 0.085); tenure in months."""
    r = annual_rate / 12 / 100
    n = tenure_months
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def get_rate(product, rate_type):
    """Today's rate from RATE_CARD. Raises ValueError for a product/rate type the card does not have."""
    rate = RATE_CARD.get((product, rate_type))
    if rate is None:
        have = ", ".join(f"{p} {t}" for p, t in RATE_CARD)
        raise ValueError(f"no rate for {product} {rate_type}; the card has: {have}")
    return rate


def check_eligibility(monthly_income, existing_emi, proposed_emi):
    """FOIR rule: (existing + proposed EMI) / monthly income must be at most FOIR_LIMIT."""
    foir = (existing_emi + proposed_emi) / monthly_income
    return {"foir": round(foir, 3), "limit": FOIR_LIMIT, "eligible": foir <= FOIR_LIMIT}


def execute_tool(name: str, args: dict) -> str:
    """Run one tool and return its result as a JSON string. Never raises: an exception becomes
    {"error": "..."}, which is what the model sees as the tool's result."""
    try:
        if name == "calculate_emi":
            return json.dumps({"emi_rupees": round(calculate_emi(**args))})
        if name == "get_rate":
            return json.dumps({"product": args.get("product"), "rate_type": args.get("rate_type"),
                               "annual_rate_percent": get_rate(**args)})
        if name == "check_eligibility":
            return json.dumps(check_eligibility(**args))
        return json.dumps({"error": f"unknown tool {name!r}"})
    except Exception as e:  # noqa: BLE001 - a tool must never crash the conversation
        return json.dumps({"error": f"{type(e).__name__}: {e}"})


# ================================================================ 2. Fix B: validate arguments like a stranger's form
def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def parse_args(raw):
    """The arguments arrive as a JSON STRING. Returns a dict, or None if it is not a JSON object."""
    if isinstance(raw, dict):
        return raw
    try:
        args = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return None
    return args if isinstance(args, dict) else None


def validate_args(name: str, raw) -> tuple:
    """(args, None) if the call is safe to run, else (None, "what is wrong"). Checks types and ranges in CODE -
    the schema's types and "required" are only requests to the model, never enforced by it."""
    args = parse_args(raw)
    if args is None:
        return None, "arguments were not a valid JSON object"
    if name == "calculate_emi":
        for k in ("principal", "annual_rate", "tenure_months"):
            if not _is_num(args.get(k)) or args[k] <= 0:
                return None, f"{k} must be a positive number, got {args.get(k)!r}"
        if args["annual_rate"] < 1 or args["annual_rate"] > 50:
            return None, f"annual_rate is a percent per year (e.g. 8.5), got {args['annual_rate']!r}"
        if args["tenure_months"] != int(args["tenure_months"]) or args["tenure_months"] > 360:
            return None, f"tenure_months must be a whole number of months up to 360, got {args['tenure_months']!r}"
        return {k: args[k] for k in ("principal", "annual_rate", "tenure_months")}, None
    if name == "get_rate":
        product, rate_type = args.get("product"), args.get("rate_type")
        if (product, rate_type) not in RATE_CARD:
            have = ", ".join(f"{p}/{t}" for p, t in RATE_CARD)
            return None, f"no rate for product={product!r} rate_type={rate_type!r}; valid pairs: {have}"
        return {"product": product, "rate_type": rate_type}, None
    if name == "check_eligibility":
        for k in ("monthly_income", "proposed_emi"):
            if not _is_num(args.get(k)) or args[k] <= 0:
                return None, f"{k} must be a positive number, got {args.get(k)!r}"
        if not _is_num(args.get("existing_emi")) or args["existing_emi"] < 0:
            return None, f"existing_emi must be a number, 0 or more, got {args.get('existing_emi')!r}"
        return {k: args[k] for k in ("monthly_income", "existing_emi", "proposed_emi")}, None
    return None, f"unknown tool {name!r}; available: calculate_emi, get_rate, check_eligibility"


# ================================================================ 3. one model call, normalised (and cached)
def call_model(client, model: str, messages: list, *, tools=None, max_tokens: int = 1500, temperature: float = 0.0,
               cache=None) -> dict:
    """One raw chat.completions call. Returns {"content", "tool_calls": [{"id","name","arguments"}],
    "finish_reason", "prompt_tokens", "completion_tokens"}. max_tokens is generous on purpose: reasoning models
    such as gpt-oss spend hidden tokens first, and a small ceiling can leave no room for the tool call."""
    kwargs = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    if tools:
        kwargs["tools"] = tools
    key = hashlib.sha256(json.dumps(kwargs, sort_keys=True, default=str).encode()).hexdigest()
    if cache is not None:
        hit = cache.get(key)
        if hit is not None:
            return json.loads(json.dumps(hit))
    r = client.chat.completions.create(**kwargs)
    choice = r.choices[0]
    msg = choice.message
    calls = []
    for i, c in enumerate(getattr(msg, "tool_calls", None) or []):
        calls.append({"id": getattr(c, "id", None) or f"call_{i}", "name": c.function.name,
                      "arguments": c.function.arguments if c.function.arguments is not None else "{}"})
    usage = getattr(r, "usage", None)
    out = {"content": getattr(msg, "content", None) or "", "tool_calls": calls, "finish_reason": choice.finish_reason,
           "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
           "completion_tokens": getattr(usage, "completion_tokens", 0) or 0}
    if cache is not None:
        cache.put(key, out)
    return out


def assistant_message(out: dict) -> dict:
    """The assistant turn that carries tool_calls - it must go back into the list before the tool results."""
    return {"role": "assistant", "content": out["content"] or "",
            "tool_calls": [{"id": c["id"], "type": "function",
                            "function": {"name": c["name"], "arguments": c["arguments"]}} for c in out["tool_calls"]]}


def tool_message(call_id: str, result: str) -> dict:
    """One tool result. tool_call_id must match the id of the call it answers, or the API rejects the list."""
    return {"role": "tool", "tool_call_id": call_id, "content": result}


# ================================================================ 4. the round trip, in a loop with a cap
def run_with_tools(client, model: str, messages: list, *, tools=TOOLS, validate: bool = False,
                   max_steps: int = MAX_STEPS, max_tokens: int = 1500, cache=None) -> dict:
    """Call -> run requested tools -> append -> call again, until the model answers in prose or max_steps calls
    have been made. validate=True is Fix B: bad arguments are not run; the error goes back as the tool result.
    Every call is checked with validate_args either way, so the score can say whether the arguments were valid."""
    msgs = list(messages)
    calls, pt, ct, final, capped, step = [], 0, 0, "", True, 0
    for step in range(1, max_steps + 1):
        out = call_model(client, model, msgs, tools=tools, max_tokens=max_tokens, cache=cache)
        pt, ct = pt + out["prompt_tokens"], ct + out["completion_tokens"]
        if not out["tool_calls"]:
            final, capped = out["content"], False
            break
        msgs.append(assistant_message(out))
        for c in out["tool_calls"]:
            clean, problem = validate_args(c["name"], c["arguments"])
            if validate and problem:
                result = json.dumps({"error": f"INVALID: {problem}. If the customer did not ask for an EMI, a rate "
                                              "or an eligibility check, answer WITHOUT calling a tool."})
            elif validate:
                result = execute_tool(c["name"], clean)
            else:
                loose = parse_args(c["arguments"])
                result = execute_tool(c["name"], loose) if loose is not None else json.dumps(
                    {"error": "arguments were not valid JSON"})
            calls.append({"step": step, "name": c["name"], "arguments": c["arguments"], "valid": problem is None,
                          "problem": problem, "result": result})
            msgs.append(tool_message(c["id"], result))
    return {"final_text": (final or "").strip(), "calls": calls, "steps": step, "capped": capped,
            "prompt_tokens": pt, "completion_tokens": ct, "messages": msgs}


# ================================================================ 5. Fix C: route first
def route(client, model: str, question: str, *, max_tokens: int = 1500, cache=None) -> tuple:
    """(needs_tool, tokens). One small classification call - Session 16's idea in a new job. Anything that is
    not clearly TOOL counts as NO_TOOL (note: "NO_TOOL" also contains "TOOL", so check how it STARTS)."""
    out = call_model(client, model, [{"role": "system", "content": ROUTER_PROMPT},
                                     {"role": "user", "content": question}], max_tokens=max_tokens, cache=cache)
    word = re.sub(r"[^A-Z_]", "", out["content"].upper())
    return word.startswith("TOOL"), out["prompt_tokens"] + out["completion_tokens"]


# ================================================================ answering one question, one of four ways
def system_for(way: str) -> str:
    return BANKASSIST_SYSTEM + (TOOLS_GUIDANCE if way == "prompt" else "")


def answer_question(client, model: str, question: str, way: str = "none", *, max_steps: int = MAX_STEPS,
                    max_tokens: int = 1500, cache=None) -> dict:
    """way: "none" (tools attached, no fix), "prompt" (Fix A), "validate" (Fix B), "router" (Fix C)."""
    if way not in WAYS:
        raise ValueError(f"unknown way {way!r}; choose one of {WAYS}")
    messages = [{"role": "system", "content": system_for(way)}, {"role": "user", "content": question}]
    router_tokens, routed = 0, None
    tools = TOOLS
    if way == "router":
        routed, router_tokens = route(client, model, question, max_tokens=max_tokens, cache=cache)
        tools = TOOLS if routed else None
    res = run_with_tools(client, model, messages, tools=tools, validate=(way == "validate"), max_steps=max_steps,
                         max_tokens=max_tokens, cache=cache)
    res.update({"way": way, "routed_to_tools": routed, "router_tokens": router_tokens,
                "total_tokens": res["prompt_tokens"] + res["completion_tokens"] + router_tokens})
    return res


def show_trace(res: dict) -> str:
    """A readable trace of one answer: every tool call, whether its arguments were valid, what came back."""
    lines = []
    if res.get("routed_to_tools") is not None:
        lines.append(f"router said: {'TOOL' if res['routed_to_tools'] else 'NO_TOOL'}")
    for c in res["calls"]:
        flag = "valid" if c["valid"] else f"INVALID ({c['problem']})"
        lines.append(f"step {c['step']}: {c['name']}({c['arguments']})  -> {flag}")
        lines.append(f"         result: {c['result']}")
    if res["capped"]:
        lines.append(f"stopped: hit the {res['steps']}-step cap without a prose answer")
    lines.append(f"final answer: {res['final_text'][:300] or '(none)'}")
    return "\n".join(lines)


# ================================================================ scoring against the golden set (decided before looking)
def _norm(text: str) -> str:
    return re.sub(r"[\s,₹]", "", (text or "").lower())


def _args_match(call: dict, expected: dict) -> bool:
    args = parse_args(call["arguments"]) or {}
    for k, v in expected.items():
        a = args.get(k)
        if isinstance(v, (int, float)):
            if not _is_num(a) or abs(a - v) > 0.005 * abs(v):
                return False
        elif str(a).lower() != str(v).lower():
            return False
    return True


def score_question(item: dict, res: dict) -> dict:
    """Three yes/no scores. tool_ok: exactly the expected set of tools was called (none, for a no-tool question).
    args_ok (tool questions only): every call had valid arguments, and the main tool was called with the right
    values. answer_ok: the final text contains an expected fact or number, and nothing it must not contain."""
    called = {c["name"] for c in res["calls"]}
    tool_ok = called == set(item["expect_tools"])
    args_ok = None
    if item["expect_tools"]:
        args_ok = bool(res["calls"]) and all(c["valid"] for c in res["calls"]) and all(
            any(_args_match(c, exp) for c in res["calls"] if c["name"] == tool)
            for tool, exp in item["expect_args"].items())
    text = _norm(res["final_text"])
    answer_ok = bool(text) and (not item["answer_any"] or any(_norm(a) in text for a in item["answer_any"])) \
        and not any(_norm(b) in text for b in item["answer_not"])
    return {"tool_ok": tool_ok, "args_ok": args_ok, "answer_ok": answer_ok}


def score_golden(client, model: str, way: str, *, items=None, max_steps: int = MAX_STEPS, max_tokens: int = 1500,
                 cache=None) -> dict:
    items = GOLDEN if items is None else items
    rows = []
    for item in items:
        res = answer_question(client, model, item["question"], way, max_steps=max_steps, max_tokens=max_tokens,
                              cache=cache)
        rows.append({"id": item["id"], "question": item["question"], **score_question(item, res),
                     "tools_called": [c["name"] for c in res["calls"]], "final_text": res["final_text"],
                     "tokens": res["total_tokens"], "capped": res["capped"]})
    tool_qs = [r for r, it in zip(rows, items) if it["expect_tools"]]
    return {"way": way, "rows": rows, "n": len(rows), "n_tool": len(tool_qs),
            "tool_right": sum(r["tool_ok"] for r in rows), "args_ok": sum(bool(r["args_ok"]) for r in tool_qs),
            "answer_ok": sum(r["answer_ok"] for r in rows), "tokens": sum(r["tokens"] for r in rows)}


def compare_fixes(client, model: str, *, ways=WAYS, items=None, max_steps: int = MAX_STEPS, max_tokens: int = 1500,
                  cache=None) -> dict:
    """The same golden set, four ways. Only the fix changes between runs."""
    return {w: score_golden(client, model, w, items=items, max_steps=max_steps, max_tokens=max_tokens, cache=cache)
            for w in ways}


# ================================================================ reading the results
def fixes_table(results: dict) -> str:
    head = f"{'way':<30}{'right tool':>12}{'args ok':>10}{'answer ok':>11}{'tokens':>10}"
    lines = [head, "-" * len(head)]
    for w, r in results.items():
        lines.append(f"{WAY_LABELS.get(w, w):<30}{r['tool_right']:>8}/{r['n']:<3}{r['args_ok']:>6}/{r['n_tool']:<3}"
                     f"{r['answer_ok']:>7}/{r['n']:<3}{r['tokens']:>10,}")
    return "\n".join(lines)


def question_grid(results: dict) -> str:
    """One row per golden question, one column per way: tool / args / answer as y or n (args '-' = no tool needed)."""
    ways = list(results)
    head = f"{'q':<5}" + "".join(f"{w:>12}" for w in ways)
    lines = [head, "-" * len(head)]
    for i, row in enumerate(results[ways[0]]["rows"]):
        cells = []
        for w in ways:
            r = results[w]["rows"][i]
            a = "-" if r["args_ok"] is None else ("y" if r["args_ok"] else "n")
            cells.append(f"{('y' if r['tool_ok'] else 'n')}/{a}/{('y' if r['answer_ok'] else 'n')}")
        lines.append(f"{row['id']:<5}" + "".join(f"{c:>12}" for c in cells))
    lines.append("cells read tool/args/answer; '-' means no tool was needed, so there are no arguments to score")
    return "\n".join(lines)


# ================================================================ the report you commit
def tools_markdown(results: dict, model: str, *, today: str = None) -> str:
    today = today or datetime.date.today().isoformat()
    any_r = next(iter(results.values()))
    lines = ["# Session 20: function calling - golden set, four ways", "",
             f"Model: `{model}` · Date: {today} · Golden set: {any_r['n']} questions "
             f"({any_r['n_tool']} need a tool, {any_r['n'] - any_r['n_tool']} need none)", "",
             "| Way | Right tool (or none) | Args valid | Answer correct | Tokens |", "|---|---|---|---|---|"]
    for w in WAYS:
        if w in results:
            r = results[w]
            lines.append(f"| {w} | {r['tool_right']}/{r['n']} | {r['args_ok']}/{r['n_tool']} | "
                         f"{r['answer_ok']}/{r['n']} | {r['tokens']} |")
    lines += ["", "Per question (tool / args / answer, '-' = no tool needed):", "",
              "| Question | " + " | ".join(w for w in WAYS if w in results) + " |",
              "|---|" + "---|" * len([w for w in WAYS if w in results])]
    for i, row in enumerate(any_r["rows"]):
        cells = []
        for w in WAYS:
            if w in results:
                r = results[w]["rows"][i]
                a = "-" if r["args_ok"] is None else ("y" if r["args_ok"] else "n")
                cells.append(f"{'y' if r['tool_ok'] else 'n'}/{a}/{'y' if r['answer_ok'] else 'n'}")
        lines.append(f"| {row['id']} | " + " | ".join(cells) + " |")
    lines += ["", "Scores were decided before running: right tool means exactly the expected tools (none for a "
              "no-tool question); args valid counts tool questions only; answer correct checks the final text for "
              "the expected number or fact. A 10-question golden set is a smoke test - quote it with the model name."]
    return "\n".join(lines) + "\n"


def save_tools_report(repo_path, text: str) -> Path:
    target = Path(repo_path) / REPORT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


_ROW_RE = re.compile(r"^\|\s*(none|prompt|validate|router)\s*\|\s*(\d+)/(\d+)\s*\|\s*(\d+)/(\d+)\s*\|"
                     r"\s*(\d+)/(\d+)\s*\|\s*(\d+)\s*\|", re.IGNORECASE | re.MULTILINE)
_MODEL_RE = re.compile(r"Model:\s*`([^`]+)`")


def parse_tools_report(text: str) -> dict:
    """{"model": str|None, "ways": {way: {...counts...}}} read back from a saved report."""
    ways = {}
    for m in _ROW_RE.finditer(text or ""):
        g = [int(x) for x in m.groups()[1:]]
        ways[m.group(1).lower()] = {"tool_right": g[0], "n": g[1], "args_ok": g[2], "n_tool": g[3],
                                    "answer_ok": g[4], "n2": g[5], "tokens": g[6]}
    mm = _MODEL_RE.search(text or "")
    return {"model": mm.group(1) if mm else None, "ways": ways}


# ================================================================ is my work complete? (offline: no model call)
def check_s20_work(repo_path) -> list:
    """Plain-English checks on your work repository for Session 20. Completeness only: which fix wins depends on
    the model, so no particular winner is required - the report is evidence, not a race."""
    repo = Path(repo_path)

    def ck(name, ok, fix="", info=""):
        return CheckResult(name, ok, info if ok else fix)
    if not repo.exists():
        return [ck("work repo folder exists", False, f"{repo} not found. Fix WORK_REPO.")]
    out = [ck("work repo folder exists", True)]
    report_file = repo / REPORT_PATH
    if not report_file.exists():
        out.append(ck("tools report exists", False, f"{REPORT_PATH} not found. Run notebook section 10 with SAVE_REPORT = True."))
        return out
    out.append(ck("tools report exists", True))
    parsed = parse_tools_report(report_file.read_text(encoding="utf-8"))
    out.append(ck("report names the model it ran on", bool(parsed["model"]),
                  "no 'Model: `...`' line - re-save the report from section 10", info=parsed["model"] or ""))
    have = set(parsed["ways"])
    all_four = have == set(WAYS)
    out.append(ck("report covers all four ways (none, prompt, validate, router)", all_four,
                  f"found {sorted(have)}, need {list(WAYS)}. Re-run section 9, then re-save in section 10."))
    if not all_four:
        return out
    n_tool = sum(1 for g in GOLDEN if g["expect_tools"])
    full = all(r["n"] == len(GOLDEN) and r["n2"] == len(GOLDEN) and r["n_tool"] == n_tool for r in parsed["ways"].values())
    out.append(ck(f"every way scored on the full golden set ({len(GOLDEN)} questions, {n_tool} needing a tool)", full,
                  "a way was scored on fewer questions - run compare_fixes on the full GOLDEN set, not a slice"))
    sane = all(r["tool_right"] <= r["n"] and r["args_ok"] <= r["n_tool"] and r["answer_ok"] <= r["n"]
               for r in parsed["ways"].values())
    out.append(ck("every score is within its denominator", sane, "a count is larger than its total - do not edit the report by hand"))
    return out

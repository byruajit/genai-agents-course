"""Session 27 checker - imports YOUR <work repo>/s27/hybrid.py and tests the four TODOs. Offline: no models needed."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
STUDENT_PATH = Path("s27") / "hybrid.py"


def load_module(path: Path):
    sys.path.insert(0, str(HERE))
    spec = importlib.util.spec_from_file_location(f"s27_student_{abs(hash(path))}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def close(a, b, tol=1e-9) -> bool:
    return abs(float(a) - float(b)) <= tol


def check_s27_work(path: Path) -> list[str]:
    """Returns a list of problems. Empty list = everything passes."""
    if not path.exists():
        return [f"{path} not found - run:  uv run python module04/s27_setup.py"]
    import s27_queries as Q
    import s27_utils as S27
    mod = load_module(path)
    problems: list[str] = []

    # TODO 1 - RRF
    try:
        got = mod.rrf_fuse([["a", "b", "c"], ["c", "a", "d"]], k=60)
        want = [("a", 1 / 61 + 1 / 62), ("c", 1 / 63 + 1 / 61), ("b", 1 / 62), ("d", 1 / 63)]
        if [x for x, _ in got] != [x for x, _ in want] or not all(close(s, w) for (_, s), (_, w) in zip(got, want)):
            problems.append(f"TODO 1 rrf_fuse([['a','b','c'],['c','a','d']]) returned {got!r}; expected ids a, c, b, d "
                            "with 1/(60+rank) added up per id")
        elif not close(mod.rrf_fuse([["x"]], k=1)[0][1], 0.5):
            problems.append("TODO 1 rrf_fuse ignores k - use 1 / (k + rank)")
        elif mod.rrf_fuse([]) != []:
            problems.append("TODO 1 rrf_fuse([]) should return []")
    except NotImplementedError:
        problems.append("TODO 1 rrf_fuse() is not written yet")
    except Exception as e:
        problems.append(f"TODO 1 rrf_fuse() crashed: {type(e).__name__}: {e}")

    # TODO 2 - weighted score fusion
    try:
        got = dict(mod.weighted_fuse({"a": 10, "b": 0, "c": 5}, {"a": 0.2, "b": 0.9}, 0.5))
        want = {"a": 0.5, "b": 0.5, "c": 0.25}
        if set(got) != set(want) or not all(close(got[k], v) for k, v in want.items()):
            problems.append(f"TODO 2 weighted_fuse(...) returned {got!r}, expected {want!r} (min-max each dict, "
                            "missing id = 0)")
        else:
            order = [k for k, _ in mod.weighted_fuse({"a": 1.0, "b": 2.0}, {"a": 0.9, "b": 0.1}, 1.0)]
            same = dict(mod.weighted_fuse({"x": 3.0, "y": 3.0}, {}, 0.0))
            if order[0] != "a":
                problems.append("TODO 2 with alpha=1.0 only the dense scores should count")
            elif not (close(same.get("x", -1), 1.0) and close(same.get("y", -1), 1.0)):
                problems.append("TODO 2 when all scores in a dict are equal, each id gets 1.0 (no division by zero)")
    except NotImplementedError:
        problems.append("TODO 2 weighted_fuse() is not written yet")
    except Exception as e:
        problems.append(f"TODO 2 weighted_fuse() crashed: {type(e).__name__}: {e}")

    # TODO 3 - rerank the candidates
    try:
        cands = [SimpleNamespace(chunk=SimpleNamespace(search_text=t), key=t) for t in ["aa", "aaaa", "a", "aaa"]]
        calls = []

        def fake_cross_encoder(question, texts):
            calls.append(list(texts))
            return [float(len(t)) for t in texts]

        got = mod.rerank_top("q", cands, fake_cross_encoder, k=2)
        if len(calls) != 1 or len(calls[0]) != 4:
            problems.append(f"TODO 3 call score_fn ONCE with all {len(cands)} texts (it was called {len(calls)} times)")
        elif [c.key for _, c in got] != ["aaaa", "aaa"] or [s for s, _ in got] != [4.0, 3.0]:
            problems.append(f"TODO 3 rerank_top returned {[(s, c.key) for s, c in got]!r}, expected the 2 best as "
                            "[(4.0, 'aaaa'), (3.0, 'aaa')]")
    except NotImplementedError:
        problems.append("TODO 3 rerank_top() is not written yet")
    except Exception as e:
        problems.append(f"TODO 3 rerank_top() crashed: {type(e).__name__}: {e}")

    # TODO 4 - three exact-term questions + a gate
    cases = getattr(mod, "MY_EXACT_CASES", [])
    known = {q.lower() for q, *_ in Q.CASES}
    if len(cases) < 3:
        problems.append(f"TODO 4 MY_EXACT_CASES needs 3 questions (has {len(cases)})")
    for case in cases:
        try:
            q, corpus, expected = case
        except (TypeError, ValueError):
            problems.append(f"TODO 4 each case is (question, corpus, expected doc_id) - got {case!r}")
            continue
        if corpus not in S27.CORPORA:
            problems.append(f"TODO 4 {q!r}: corpus must be 'help' or 'products', got {corpus!r}")
            continue
        chunks = S27.load_corpus(corpus)
        if expected not in {c.doc_id for c in chunks}:
            problems.append(f"TODO 4 {q!r}: {expected!r} is not a doc_id in {corpus} "
                            f"({'a SKU like SKU-FW-001' if corpus == 'products' else 'an article name like payments'})")
            continue
        if q.lower() in known:
            problems.append(f"TODO 4 {q!r} is already in s27_queries.py - write your own")
            continue
        df: dict[str, int] = {}
        for c in chunks:
            for w in set(S27.tokenize(c.search_text)):
                df[w] = df.get(w, 0) + 1
        target = set().union(*(S27.tokenize(c.search_text) for c in chunks if c.doc_id == expected))
        if not any(w in target and df.get(w, 99) <= 3 for w in S27.tokenize(q)):
            problems.append(f"TODO 4 {q!r} has no rare word that appears in {expected} - an exact-term question "
                            "contains a code, name or number from the answer")
    gate = getattr(mod, "GATE", None)
    if not (isinstance(gate, tuple) and len(gate) == 2 and isinstance(gate[0], (int, float))):
        problems.append("TODO 4 GATE must be (threshold number, reason)")
    elif not -15 <= gate[0] <= 15:
        problems.append(f"TODO 4 GATE {gate[0]} is outside the range reranker scores live in (about -12 to +12)")
    elif len(str(gate[1]).split()) < 8:
        problems.append("TODO 4 GATE: give a reason of at least 8 words")

    if "fuse=rrf_fuse" not in path.read_text(encoding="utf-8").split("class YourRetriever", 1)[-1]:
        problems.append("PART 1 was changed - YourRetriever must use your rrf_fuse (run setup with --fresh to compare)")
    results = path.with_name("results.md")
    if not results.exists():
        problems.append("results.md not found next to hybrid.py - run your file once (it writes results.md)")
    elif "| rerank |" not in results.read_text(encoding="utf-8"):
        problems.append("results.md has no rerank row - run your file again after finishing the TODOs")
    return problems

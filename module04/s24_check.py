"""Session 24 checker - imports YOUR <work repo>/s24/search.py and tests the four TODOs. Offline: no model needed
for TODOs 1-4; the last check only looks for the results.md your run wrote."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDENT_PATH = Path("s24") / "search.py"
ARTICLES = {p.stem for p in (HERE / "help_centre").glob("*.md")}


def load_module(path: Path):
    sys.path.insert(0, str(HERE))
    spec = importlib.util.spec_from_file_location(f"s24_student_{abs(hash(path))}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_s24_work(path: Path) -> list[str]:
    """Returns a list of problems. Empty list = everything passes."""
    problems: list[str] = []
    if not path.exists():
        return [f"{path} not found - run:  uv run python module04/s24_setup.py"]
    mod = load_module(path)

    # TODO 1 - cosine
    try:
        c = mod.cosine
        cases = [([1, 0], [1, 0], 1.0), ([1, 0], [0, 1], 0.0), ([1, 0], [-1, 0], -1.0), ([3, 4], [6, 8], 1.0),
                 ([1, 1], [1, 0], 2 ** -0.5), ([0, 0], [1, 2], 0.0)]
        for a, b, want in cases:
            got = c(np.array(a, float), np.array(b, float))
            if not isinstance(got, float) or abs(got - want) > 1e-6:
                problems.append(f"TODO 1 cosine({a}, {b}) returned {got!r}, expected {want:.4f}")
                break
    except NotImplementedError:
        problems.append("TODO 1 cosine() is not written yet")
    except Exception as e:
        problems.append(f"TODO 1 cosine() crashed: {type(e).__name__}: {e}")

    # TODO 2 - top_k
    try:
        m = np.array([[0, 1], [1, 0], [1, 1], [-1, 0]], float)
        got = mod.top_k(np.array([1, 0], float), m, 2)
        if list(map(int, got)) != [1, 2]:
            problems.append(f"TODO 2 top_k(...) returned {got!r}, expected [1, 2] (best first)")
        got = mod.top_k(np.array([0, 1], float), m[:2], 5)
        if list(map(int, got)) != [0, 1]:
            problems.append(f"TODO 2 top_k with k bigger than the matrix returned {got!r}, expected [0, 1]")
    except NotImplementedError:
        problems.append("TODO 2 top_k() is not written yet")
    except Exception as e:
        problems.append(f"TODO 2 top_k() crashed: {type(e).__name__}: {e}")

    # TODO 3 - split_sections
    try:
        sample = "---\nid: x\n---\n# Title\nintro line\n## A\none\ntwo\n## B\n\n## C\n  three  \n"
        got = mod.split_sections(sample)
        want = [("A", "one two"), ("C", "three")]
        if [tuple(x) for x in got] != want:
            problems.append(f"TODO 3 split_sections(...) returned {got!r}, expected {want!r}")
        real = sum(len(mod.split_sections(p.read_text(encoding="utf-8"))) for p in (HERE / "help_centre").glob("*.md"))
        if real != 53:
            problems.append(f"TODO 3 split_sections found {real} sections in the help centre, expected 53")
    except NotImplementedError:
        problems.append("TODO 3 split_sections() is not written yet")
    except Exception as e:
        problems.append(f"TODO 3 split_sections() crashed: {type(e).__name__}: {e}")

    # TODO 4 - three questions of your own
    my = getattr(mod, "MY_CASES", [])
    if len(my) < 3:
        problems.append(f"TODO 4 MY_CASES has {len(my)} questions, needs 3")
    else:
        from s24_queries import CASES
        course_q = {q.lower() for q, _ in CASES}
        for q, doc in my:
            if doc not in ARTICLES:
                problems.append(f"TODO 4 article {doc!r} doesn't exist - use a file name from module04/help_centre/")
            if q.lower() in course_q:
                problems.append(f"TODO 4 {q!r} is one of the course questions - write your own")

    # The run itself
    results = path.with_name("results.md")
    if not results.exists():
        problems.append("results.md not found next to search.py - run your file once (it writes results.md)")
    elif "hit@3" not in results.read_text(encoding="utf-8"):
        problems.append("results.md doesn't contain a hit@3 line - run your finished file again")
    return problems

"""Session 25 checker - imports YOUR <work repo>/s25/store.py and tests the four TODOs. Offline: no model needed."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDENT_PATH = Path("s25") / "store.py"
CATEGORIES = {"orders", "payments", "returns", "account", "products"}


def load_module(path: Path):
    sys.path.insert(0, str(HERE))
    spec = importlib.util.spec_from_file_location(f"s25_student_{abs(hash(path))}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_s25_work(path: Path) -> list[str]:
    """Returns a list of problems. Empty list = everything passes."""
    if not path.exists():
        return [f"{path} not found - run:  uv run python module04/s25_setup.py"]
    import s24_utils as S24
    mod = load_module(path)
    problems: list[str] = []

    # TODO 1
    try:
        chunk = S24.Chunk("refunds", "Refunds", "Refund timeline", "text")
        got = mod.make_metadata(chunk, {"category": "payments", "updated": "2026-03-02"})
        want = {"doc_id": "refunds", "category": "payments", "updated": 20260302}
        if got != want:
            problems.append(f"TODO 1 make_metadata(...) returned {got!r}, expected {want!r}")
        elif not isinstance(got["updated"], int):
            problems.append("TODO 1 'updated' must be an int like 20260302, not a string")
    except NotImplementedError:
        problems.append("TODO 1 make_metadata() is not written yet")
    except Exception as e:
        problems.append(f"TODO 1 make_metadata() crashed: {type(e).__name__}: {e}")

    # TODO 2
    try:
        cases = [((None, None), None),
                 (("payments", None), {"category": "payments"}),
                 ((None, "2026-06-01"), {"updated": {"$gte": 20260601}}),
                 (("returns", "2025-12-31"), {"$and": [{"category": "returns"}, {"updated": {"$gte": 20251231}}]})]
        for args, want in cases:
            got = mod.build_where(*args)
            if got != want:
                problems.append(f"TODO 2 build_where{args} returned {got!r}, expected {want!r}")
                break
    except NotImplementedError:
        problems.append("TODO 2 build_where() is not written yet")
    except Exception as e:
        problems.append(f"TODO 2 build_where() crashed: {type(e).__name__}: {e}")

    # TODO 3
    try:
        cases = [(([[1, 2, 3, 4]], [[1, 2, 9, 8]], 4), 0.5),
                 (([[1, 2], [3, 4]], [[2, 1], [5, 6]], 2), 0.5),
                 (([[1, 2, 3]], [[1, 2, 3]], 3), 1.0),
                 (([], [], 10), 0.0)]
        for args, want in cases:
            got = mod.recall_at_k(*args)
            if not isinstance(got, float) or abs(got - want) > 1e-9:
                problems.append(f"TODO 3 recall_at_k{args} returned {got!r}, expected {want}")
                break
    except NotImplementedError:
        problems.append("TODO 3 recall_at_k() is not written yet")
    except Exception as e:
        problems.append(f"TODO 3 recall_at_k() crashed: {type(e).__name__}: {e}")

    # TODO 4
    mine = getattr(mod, "MY_FILTERED", [])
    if len(mine) < 2:
        problems.append(f"TODO 4 MY_FILTERED has {len(mine)} questions, needs 2")
    else:
        if not any(c and s for _, c, s in mine):
            problems.append("TODO 4 at least one of your questions must use BOTH a category and a since-date")
        for q, c, s in mine:
            if c is not None and c not in CATEGORIES:
                problems.append(f"TODO 4 category {c!r} doesn't exist - use one of {sorted(CATEGORIES)}")
            if s is not None:
                try:
                    from datetime import date
                    date.fromisoformat(s)
                except ValueError:
                    problems.append(f"TODO 4 since-date {s!r} isn't YYYY-MM-DD")

    results = path.with_name("results.md")
    if not results.exists():
        problems.append("results.md not found next to store.py - run your file once (it writes results.md)")
    elif "recall@10" not in results.read_text(encoding="utf-8"):
        problems.append("results.md has no recall@10 table - run your finished file again")
    elif "| NO |" in results.read_text(encoding="utf-8"):
        problems.append("results.md shows a filtered search returning rows that DON'T match the filter - check TODO 1/2")
    return problems

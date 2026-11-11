"""Session 24 checkpoint. Run with:  uv run pytest tests/test_s24.py -rs

Offline. The course-side tests use a stand-in embedder, so they need no model. THE CHECKPOINT imports YOUR
<work repo>/s24/search.py and tests your four TODOs. It needs WORK_REPO set (in .env or the shell).

Optional live check of the real model (downloads bge-small once):   $env:S24_LIVE = "1"
"""
import os
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "module04"))
import s24_utils as U  # noqa: E402
from s24_check import STUDENT_PATH, check_s24_work  # noqa: E402
from s24_queries import CASES, OUT_OF_SCOPE, PASS_MARK  # noqa: E402

STARTER = ROOT / "module04" / "s24_homework.py"

KEY = ROOT / "S24" / "s24_answer_key.py"      # instructor only: gitignored, students don't have it


def load_filled() -> dict:
    if not KEY.exists():
        pytest.skip("instructor answer key not present (that's expected on a student laptop)")
    ns: dict = {}
    exec(KEY.read_text(encoding="utf-8"), ns)
    return ns["FILLED"]


def fill(src: str) -> str:
    for old, new in load_filled().items():
        assert old in src, f"starter changed - update FILLED: {old[:40]!r}"
        src = src.replace(old, new)
    return src.replace("import sys\n", "import re\nimport sys\n", 1)


class FakeEmbedder(U.Embedder):
    """Bag-of-words stand-in: not semantic, but deterministic and offline - enough to test the plumbing."""

    def __init__(self):
        super().__init__("bge-small")
        self.name = "fake"
        self.vocab: dict[str, int] = {}

    def embed(self, texts, kind="passage"):
        rows = []
        for t in texts:
            v = np.zeros(512)
            for w in U.words(t):
                v[self.vocab.setdefault(w, len(self.vocab) % 512)] += 1
            rows.append(v)
        return U.normalise(np.array(rows))


# ------------------------------------------------------------------------------------------ the course code itself
def test_help_centre_has_14_articles_and_53_sections():
    chunks = U.load_chunks()
    assert len({c.doc_id for c in chunks}) == 14
    assert len(chunks) == 53
    assert all(c.text and c.heading for c in chunks)
    assert {c.doc_id for c in chunks} >= {d for _, d in CASES}


def test_split_sections_handles_front_matter_and_windows_line_endings():
    raw = "---\r\nid: demo\r\ntitle: Demo\r\n---\r\n# Demo\r\n## One\r\na\r\nb\r\n## Empty\r\n\r\n## Two\r\nc\r\n"
    chunks = U.split_sections(raw, "fallback")
    assert [(c.doc_id, c.title, c.heading, c.text) for c in chunks] == [("demo", "Demo", "One", "a b"),
                                                                         ("demo", "Demo", "Two", "c")]
    assert chunks[0].source == "Demo > One"


def test_cosine_basics():
    assert U.cosine([1, 0], [1, 0]) == pytest.approx(1)
    assert U.cosine([1, 0], [0, 1]) == pytest.approx(0)
    assert U.cosine([1, 0], [-1, 0]) == pytest.approx(-1)
    assert U.cosine([3, 4], [6, 8]) == pytest.approx(1)        # length doesn't matter, direction does
    assert U.cosine([0, 0], [1, 1]) == 0.0


def test_keyword_search_misses_paraphrases():
    chunks = U.load_chunks()
    assert U.keyword_search("the parcel arrived smashed", chunks) == []        # not one shared word
    r = U.evaluate(lambda q, k: U.keyword_search(q, chunks, k), CASES)
    assert r["hits"] < PASS_MARK, "keyword search should NOT reach the pass mark - that's the lesson"


def test_index_and_evaluate_with_a_stand_in_embedder(tmp_path, monkeypatch):
    monkeypatch.setattr(U, "CACHE_DIR", tmp_path)
    index = U.Index(FakeEmbedder())
    assert index.vectors.shape == (53, 512)
    top = index.search("warranty period for headphones", 3)
    assert top[0][1].doc_id == "warranty" and top[0][0] >= top[1][0] >= top[2][0]
    r = U.evaluate(index.search, [("warranty period for headphones", "warranty"), ("zzz", "coupons")])
    assert (r["hits"], r["n"]) == (1, 2) and r["mrr"] == pytest.approx(0.5)
    assert (tmp_path / "fake.json").exists()                                     # cached for the next run


def test_queries_are_well_formed():
    assert len(CASES) == 10 and PASS_MARK == 8 and len(OUT_OF_SCOPE) >= 2
    assert len({q for q, _ in CASES}) == 10


# --------------------------------------------------------------------------------------------- the homework file
def test_starter_is_unfinished(tmp_path):
    (tmp_path / "s24").mkdir()
    shutil.copy(STARTER, tmp_path / STUDENT_PATH)
    problems = check_s24_work(tmp_path / STUDENT_PATH)
    assert any("TODO 1" in p for p in problems) and any("TODO 4" in p for p in problems)


def test_a_finished_file_passes(tmp_path):
    (tmp_path / "s24").mkdir()
    (tmp_path / STUDENT_PATH).write_text(fill(STARTER.read_text(encoding="utf-8")), encoding="utf-8")
    problems = check_s24_work(tmp_path / STUDENT_PATH)
    assert problems == ["results.md not found next to search.py - run your file once (it writes results.md)"]
    (tmp_path / "s24" / "results.md").write_text("Course questions: hit@3 9/10", encoding="utf-8")
    assert check_s24_work(tmp_path / STUDENT_PATH) == []


def test_checker_catches_common_mistakes(tmp_path):
    (tmp_path / "s24").mkdir()
    src = fill(STARTER.read_text(encoding="utf-8"))
    src = src.replace("key=lambda i: -scores[i]", "key=lambda i: scores[i]")            # worst first
    src = src.replace('"warranty"),\n    ("can I', '"warrantee"),\n    ("can I')          # an article that doesn't exist
    (tmp_path / STUDENT_PATH).write_text(src, encoding="utf-8")
    (tmp_path / "s24" / "results.md").write_text("hit@3", encoding="utf-8")
    problems = " | ".join(check_s24_work(tmp_path / STUDENT_PATH))
    assert "TODO 2" in problems and "warrantee" in problems


# --------------------------------------------------------------------------------------------------- checkpoint
def test_checkpoint_your_s24_search_passes():
    work = os.getenv("WORK_REPO", "").strip().strip('"')
    if not work:
        pytest.skip("WORK_REPO is not set - add WORK_REPO=<your work repo> to .env, then run again")
    path = Path(work).expanduser() / STUDENT_PATH
    if not path.exists():
        pytest.skip(f"{path} not found - run:  uv run python module04/s24_setup.py")
    problems = check_s24_work(path)
    assert not problems, "\n  - " + "\n  - ".join(problems)


@pytest.mark.skipif(os.getenv("S24_LIVE") != "1", reason="live model check: set S24_LIVE=1 (downloads bge-small once)")
def test_live_bge_small_reaches_the_pass_mark():
    index = U.Index(U.Embedder("bge-small"))
    assert index.vectors.shape == (53, 384)
    r = U.evaluate(index.search, CASES)
    assert r["hits"] >= PASS_MARK, [row for row in r["rows"] if not row["rank"]]
    assert re.match(r"BAAI/bge-small", index.embedder.model_id)

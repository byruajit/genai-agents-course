"""Session 27 checkpoint. Run with:  uv run pytest tests/test_s27.py -rs

Offline. The course-side tests use a stand-in embedder and a stand-in reranker (no downloads). THE CHECKPOINT imports
YOUR <work repo>/s27/hybrid.py and tests your four TODOs. It needs WORK_REPO set (in .env or the shell).
"""
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "module04"))
import s24_utils as S24  # noqa: E402
import s27_queries as Q  # noqa: E402
import s27_utils as S27  # noqa: E402
from s27_check import STUDENT_PATH, check_s27_work  # noqa: E402

STARTER = ROOT / "module04" / "s27_homework.py"
KEY = ROOT / "S27" / "s27_answer_key.py"      # instructor only: gitignored, students don't have it


def load_filled() -> dict:
    if not KEY.exists():
        pytest.skip("instructor answer key not present (that's expected on a student laptop)")
    ns: dict = {}
    exec(KEY.read_text(encoding="utf-8"), ns)
    return ns["FILLED"]


def fill(src: str) -> str:
    for old, new in load_filled().items():
        assert old in src, f"starter changed - update the answer key: {old[:40]!r}"
        src = src.replace(old, new)
    return src


class FakeEmbedder(S24.Embedder):
    def __init__(self):
        super().__init__("bge-small")
        self.name = "fake27"

    def embed(self, texts, kind="passage"):
        rows = []
        for t in texts:
            v = np.full(384, 1e-3)
            for w in S24.words(t):
                v[hash(w) % 384] += 1
            rows.append(v)
        return S24.normalise(np.array(rows))


class FakeReranker(S27.Reranker):
    def __init__(self):
        super().__init__()

    def score(self, question, passages):
        q = set(S27.tokenize(question))
        return [len(q & set(S27.tokenize(p))) * 2.0 - 1.0 for p in passages]


@pytest.fixture(scope="module")
def retrievers(tmp_path_factory):
    S27.CACHE_DIR = tmp_path_factory.mktemp("s27cache")
    return {c: S27.Retriever(c, embedder=FakeEmbedder(), reranker=FakeReranker()) for c in S27.CORPORA}


# ------------------------------------------------------------------------------------------ the course code itself
def test_corpora():
    assert len(S27.load_corpus("help")) == 53
    products = S27.load_corpus("products")
    assert len(products) == 30 and products[0].doc_id.startswith("SKU-") and products[0].doc_id in products[0].text


def test_tokenize_keeps_codes_and_drops_stop_words():
    toks = S27.tokenize("What is the price of SKU-FW-002 shoes?")
    assert "sku-fw-002" in toks and "shoe" in toks and "the" not in toks and "price" in toks
    assert "no-cost" not in S27.tokenize("no-cost EMI")          # only codes with a digit stay whole


def test_bm25_finds_an_exact_code_and_explains_it(retrievers):
    r = retrievers["products"]
    assert r.keyword("SKU-EL-004", 1)[0].chunk.doc_id == "SKU-EL-004"
    rows = r.bm25.explain("SKU-EL-004", r.keys.index(r.keyword("SKU-EL-004", 1)[0].key))
    assert any(w == "sku-el-004" and part > 0 for w, _, _, part in rows)


def test_rrf_and_weighted():
    got = S27.rrf([["a", "b"], ["b", "c"]])
    assert got[0][0] == "b" and got[0][1] == pytest.approx(1 / 62 + 1 / 61)
    assert dict(S27.weighted({"a": 10, "b": 0}, {"a": 0.2, "b": 0.9}, 0.5)) == pytest.approx({"a": 0.5, "b": 0.5})
    assert dict(S27.weighted({"x": 3, "y": 3}, {}, 0.0)) == pytest.approx({"x": 1.0, "y": 1.0})


def test_every_method_runs_and_evaluate_counts(retrievers):
    for m in (*S27.METHODS, "weighted"):
        res = S27.evaluate(retrievers, Q.CASES, m)
        assert res["all"]["n"] == len(Q.CASES) == res["exact"]["n"] + res["meaning"]["n"]
        assert 0 <= res["all"]["mrr"] <= 1


def test_rerank_reorders_the_hybrid_candidates(retrievers):
    r = retrievers["help"]
    hits = r.rerank("HDFC no-cost EMI", k=3)
    assert hits[0].chunk.doc_id == "payments"
    assert [h.score for h in hits] == sorted([h.score for h in hits], reverse=True)


def test_qdrant_native_hybrid(retrievers):
    from qdrant_client import QdrantClient
    client = QdrantClient(":memory:")
    S27.qdrant_hybrid_load(client, retrievers["products"])
    top = S27.qdrant_hybrid_search(client, retrievers["products"], "SKU-EL-004", k=3)
    assert len(top) == 3 and top[0][1]["doc_id"] == "SKU-EL-004"


def test_cases_point_at_real_documents():
    ids = {c: {ch.doc_id for ch in S27.load_corpus(c)} for c in S27.CORPORA}
    for q, corpus, expected, kind in Q.CASES:
        assert expected in ids[corpus] and kind in ("exact", "meaning"), q


# --------------------------------------------------------------------------------------------- the homework file
def test_starter_is_unfinished(tmp_path):
    (tmp_path / "s27").mkdir()
    shutil.copy(STARTER, tmp_path / STUDENT_PATH)
    problems = check_s27_work(tmp_path / STUDENT_PATH)
    assert any("TODO 1" in p for p in problems) and any("TODO 4" in p for p in problems)


def test_a_finished_file_passes(tmp_path):
    (tmp_path / "s27").mkdir()
    (tmp_path / STUDENT_PATH).write_text(fill(STARTER.read_text(encoding="utf-8")), encoding="utf-8")
    assert check_s27_work(tmp_path / STUDENT_PATH) == [
        "results.md not found next to hybrid.py - run your file once (it writes results.md)"]
    (tmp_path / "s27" / "results.md").write_text("| rerank | 20/25 |", encoding="utf-8")
    assert check_s27_work(tmp_path / STUDENT_PATH) == []


def test_checker_catches_common_mistakes(tmp_path):
    (tmp_path / "s27").mkdir()
    src = fill(STARTER.read_text(encoding="utf-8"))
    src = src.replace("1.0 / (k + rank)", "1.0 / rank")                                     # forgot k
    src = src.replace("return ranked[:k]", "return ranked[-k:]")                             # lowest instead of highest
    src = src.replace('("1.5L kettle", "products", "SKU-HK-003")', '("1.5L kettle", "products", "SKU-HK-999")')
    (tmp_path / STUDENT_PATH).write_text(src, encoding="utf-8")
    (tmp_path / "s27" / "results.md").write_text("| rerank |", encoding="utf-8")
    problems = " | ".join(check_s27_work(tmp_path / STUDENT_PATH))
    assert "TODO 1" in problems and "TODO 3" in problems and "SKU-HK-999" in problems


# --------------------------------------------------------------------------------------------------- checkpoint
def test_checkpoint_your_s27_hybrid_passes():
    work = os.getenv("WORK_REPO", "").strip().strip('"')
    if not work:
        pytest.skip("WORK_REPO is not set - add WORK_REPO=<your work repo> to .env, then run again")
    path = Path(work).expanduser() / STUDENT_PATH
    if not path.exists():
        pytest.skip(f"{path} not found - run:  uv run python module04/s27_setup.py")
    problems = check_s27_work(path)
    assert not problems, "\n  - " + "\n  - ".join(problems)

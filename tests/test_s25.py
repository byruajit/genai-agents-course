"""Session 25 checkpoint. Run with:  uv run pytest tests/test_s25.py -rs

Offline. The course-side tests use a stand-in embedder and an in-memory ChromaDB, so they need no model. THE CHECKPOINT
imports YOUR <work repo>/s25/store.py and tests your four TODOs. It needs WORK_REPO set (in .env or the shell).
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
import s25_utils as S25  # noqa: E402
from s25_check import STUDENT_PATH, check_s25_work  # noqa: E402

STARTER = ROOT / "module04" / "s25_homework.py"
KEY = ROOT / "S25" / "s25_answer_key.py"      # instructor only: gitignored, students don't have it


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
    """Bag-of-words stand-in: deterministic and offline - enough to test the plumbing."""

    def __init__(self):
        super().__init__("bge-small")
        self.name = "fake25"

    def embed(self, texts, kind="passage"):
        rows = []
        for t in texts:
            v = np.full(384, 1e-3)
            for w in S24.words(t):
                v[hash(w) % 384] += 1
            rows.append(v)
        return S24.normalise(np.array(rows))


@pytest.fixture
def col(tmp_path, monkeypatch):
    monkeypatch.setattr(S24, "CACHE_DIR", tmp_path)
    emb = FakeEmbedder()
    return S25.build_collection(S25.open_db(None), emb), emb


# ------------------------------------------------------------------------------------------ the course code itself
def test_every_article_has_category_and_date():
    docs = {c.doc_id for c in S24.load_chunks()}
    assert set(S25.META) == docs
    assert {m["category"] for m in S25.META.values()} == {"orders", "payments", "returns", "account", "products"}
    assert all(S25.date_int(m["updated"]) > 20250000 for m in S25.META.values())


def test_where_filter_and_dates():
    assert S25.where_filter() is None
    assert S25.where_filter("payments") == {"category": "payments"}
    assert S25.where_filter(since="2026-06-01") == {"updated": {"$gte": 20260601}}
    assert S25.where_filter("returns", "2026-01-01") == {"$and": [{"category": "returns"}, {"updated": {"$gte": 20260101}}]}


def test_collection_holds_53_rows_with_metadata(col):
    c, _ = col
    assert c.count() == 53
    row = c.get(limit=1, include=["metadatas"])
    assert set(row["metadatas"][0]) == {"doc_id", "title", "heading", "category", "updated"}


def test_filtered_search_only_returns_matching_rows(col):
    c, emb = col
    hits = S25.search(c, emb, "refund", 5, S25.where_filter("payments", "2026-06-01"))
    assert hits and all(h["meta"]["category"] == "payments" and h["meta"]["updated"] >= 20260601 for h in hits)
    assert S25.search(c, emb, "refund", 3, {"category": "nonexistent"}) == []


def test_upsert_changes_one_row(col):
    c, emb = col
    before = c.count()
    row = c.get(where={"doc_id": "payments"}, limit=1, include=["metadatas", "documents"])
    c.upsert(ids=row["ids"], documents=["changed"], metadatas=row["metadatas"], embeddings=[emb.embed(["changed"])[0].tolist()])
    assert c.count() == before and c.get(ids=row["ids"])["documents"] == ["changed"]


def test_recall_experiment_shows_the_trade_off():
    x, q = S25.clustered_vectors(3000, n_queries=20)
    exact = S25.exact_top_k(x, q, 10)
    assert S25.recall_at_k(exact, exact) == 1.0
    client = S25.open_db(None)
    fast = S25.recall_at_k(exact, S25.hnsw_run(client, x, q, "fast")["ids"])
    accurate = S25.recall_at_k(exact, S25.hnsw_run(client, x, q, "accurate")["ids"])
    assert accurate >= fast and accurate >= 0.95


# --------------------------------------------------------------------------------------------- the homework file
def test_starter_is_unfinished(tmp_path):
    (tmp_path / "s25").mkdir()
    shutil.copy(STARTER, tmp_path / STUDENT_PATH)
    problems = check_s25_work(tmp_path / STUDENT_PATH)
    assert any("TODO 1" in p for p in problems) and any("TODO 4" in p for p in problems)


def test_a_finished_file_passes(tmp_path):
    (tmp_path / "s25").mkdir()
    (tmp_path / STUDENT_PATH).write_text(fill(STARTER.read_text(encoding="utf-8")), encoding="utf-8")
    problems = check_s25_work(tmp_path / STUDENT_PATH)
    assert problems == ["results.md not found next to store.py - run your file once (it writes results.md)"]
    (tmp_path / "s25" / "results.md").write_text("| fast | recall@10 | yes |", encoding="utf-8")
    assert check_s25_work(tmp_path / STUDENT_PATH) == []


def test_checker_catches_common_mistakes(tmp_path):
    (tmp_path / "s25").mkdir()
    src = fill(STARTER.read_text(encoding="utf-8"))
    src = src.replace("d.year * 10000 + d.month * 100 + d.day", "info['updated']")          # date left as a string
    src = src.replace("{'$and': parts}", "{'$or': parts}")                                 # wrong operator
    (tmp_path / STUDENT_PATH).write_text(src, encoding="utf-8")
    (tmp_path / "s25" / "results.md").write_text("recall@10", encoding="utf-8")
    problems = " | ".join(check_s25_work(tmp_path / STUDENT_PATH))
    assert "TODO 1" in problems and "TODO 2" in problems


# --------------------------------------------------------------------------------------------------- checkpoint
def test_checkpoint_your_s25_store_passes():
    work = os.getenv("WORK_REPO", "").strip().strip('"')
    if not work:
        pytest.skip("WORK_REPO is not set - add WORK_REPO=<your work repo> to .env, then run again")
    path = Path(work).expanduser() / STUDENT_PATH
    if not path.exists():
        pytest.skip(f"{path} not found - run:  uv run python module04/s25_setup.py")
    problems = check_s25_work(path)
    assert not problems, "\n  - " + "\n  - ".join(problems)

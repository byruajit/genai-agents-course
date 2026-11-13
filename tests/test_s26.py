"""Session 26 checkpoint. Run with:  uv run pytest tests/test_s26.py -rs

Offline. The course-side tests use an in-memory Qdrant and a stand-in embedder. pgvector tests run only when a
PostgreSQL with pgvector answers at PG_DSN (the Docker file in module04/), otherwise they skip. THE CHECKPOINT imports
YOUR <work repo>/s26/migrate.py and tests your four TODOs. It needs WORK_REPO set (in .env or the shell).
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
import s26_utils as S26  # noqa: E402
from qdrant_client import models  # noqa: E402
from s26_check import STUDENT_PATH, check_s26_work  # noqa: E402

STARTER = ROOT / "module04" / "s26_homework.py"
KEY = ROOT / "S26" / "s26_answer_key.py"      # instructor only: gitignored, students don't have it


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
        self.name = "fake26"

    def embed(self, texts, kind="passage"):
        rows = []
        for t in texts:
            v = np.full(384, 1e-3)
            for w in S24.words(t):
                v[hash(w) % 384] += 1
            rows.append(v)
        return S24.normalise(np.array(rows))


def fake_rows(n=12):
    rng = np.random.default_rng(26)
    vecs = S24.normalise(rng.standard_normal((n, 384)))
    cats = ["payments", "returns", "orders"]
    return {"ids": [f"doc{i}#{i}" for i in range(n)], "embeddings": vecs.tolist(),
            "metadatas": [{"doc_id": f"doc{i}", "title": f"T{i}", "heading": f"H{i}", "category": cats[i % 3],
                           "updated": 20260101 + i} for i in range(n)],
            "documents": [f"text {i}" for i in range(n)]}


# ------------------------------------------------------------------------------------------ the course code itself
def test_point_ids_are_stable_uuids():
    assert S26.point_id("refunds#31") == S26.point_id("refunds#31") != S26.point_id("refunds#32")
    assert len(S26.point_id("x")) == 36


def test_migration_to_qdrant_keeps_results_identical():
    rows = fake_rows()
    client, where = S26.connect_qdrant("memory")
    assert S26.migrate_to_qdrant(client, rows) == len(rows["ids"])
    vecs = np.array(rows["embeddings"])
    for i in range(3):
        exact = [rows["ids"][j] for j in np.argsort(-(vecs @ vecs[i]))[:3]]
        got = [p["chroma_id"] for _, p in S26.search_qdrant(client, vecs[i], 3)]
        assert S26.overlap_at_k(exact, got, 3) == 1.0


def test_category_filter_in_qdrant():
    rows = fake_rows()
    client, _ = S26.connect_qdrant("memory")
    S26.migrate_to_qdrant(client, rows)
    hits = S26.search_qdrant(client, rows["embeddings"][0], 5, query_filter=S26.category_filter("returns"))
    assert hits and all(p["category"] == "returns" for _, p in hits)


def test_tenant_notes_and_filter():
    assert {n["customer_id"] for n in S26.NOTES} == {"CUST-1001", "CUST-1002"} and len(S26.NOTES) == 6
    client, _ = S26.connect_qdrant("memory")
    emb = FakeEmbedder()
    S26.migrate_notes(client, emb)
    q = emb.embed(["refund"], kind="query")[0]
    f = models.Filter(must=[models.FieldCondition(key="customer_id", match=models.MatchValue(value="CUST-1002"))])
    assert {p["customer_id"] for _, p in S26.search_qdrant(client, q, 6, "customer_notes", f)} == {"CUST-1002"}
    assert {p["customer_id"] for _, p in S26.search_qdrant(client, q, 6, "customer_notes")} == {"CUST-1001", "CUST-1002"}


def test_overlap():
    assert S26.overlap_at_k(["a", "b", "c"], ["c", "b", "x"], 3) == pytest.approx(2 / 3)


def test_compose_file_avoids_port_5432():
    text = (ROOT / "module04" / "s26_docker-compose.yml").read_text()
    assert '"5433:5432"' in text and '"6333:6333"' in text and "qdrant/qdrant:v1.15.1" in text


def pg_or_skip():
    try:
        return S26.connect_pg()
    except Exception:
        pytest.skip("no PostgreSQL+pgvector at PG_DSN - start module04/s26_docker-compose.yml to run this test")


def test_pgvector_migration_and_search_match_exact():
    conn = pg_or_skip()
    rows = fake_rows()
    assert S26.migrate_to_pg(conn, rows) == len(rows["ids"])
    vecs = np.array(rows["embeddings"])
    exact = [rows["ids"][j] for j in np.argsort(-(vecs @ vecs[0]))[:3]]
    got = [p["chroma_id"] for _, p in S26.search_pg(conn, vecs[0], 3, ef_search=100)]
    assert S26.overlap_at_k(exact, got, 3) == 1.0
    assert all(p["category"] == "payments" for _, p in S26.search_pg(conn, vecs[0], 4, category="payments"))


# --------------------------------------------------------------------------------------------- the homework file
def test_starter_is_unfinished(tmp_path):
    (tmp_path / "s26").mkdir()
    shutil.copy(STARTER, tmp_path / STUDENT_PATH)
    problems = check_s26_work(tmp_path / STUDENT_PATH)
    assert any("TODO 1" in p for p in problems) and any("TODO 4" in p for p in problems)


def test_a_finished_file_passes(tmp_path):
    (tmp_path / "s26").mkdir()
    (tmp_path / STUDENT_PATH).write_text(fill(STARTER.read_text(encoding="utf-8")), encoding="utf-8")
    assert check_s26_work(tmp_path / STUDENT_PATH) == [
        "results.md not found next to migrate.py - run your file once (it writes results.md)"]
    (tmp_path / "s26" / "results.md").write_text("-> SAFE", encoding="utf-8")
    assert check_s26_work(tmp_path / STUDENT_PATH) == []


def test_checker_catches_common_mistakes(tmp_path):
    (tmp_path / "s26").mkdir()
    src = fill(STARTER.read_text(encoding="utf-8"))
    src = src.replace("match=models.MatchValue(value=customer_id))])",
                      "match=models.MatchExcept(**{'except': [customer_id]}))])")          # inverted filter = leak
    src = src.replace('"hospital_onprem": ("pgvector",', '"hospital_onprem": ("pinecone",')
    (tmp_path / STUDENT_PATH).write_text(src, encoding="utf-8")
    (tmp_path / "s26" / "results.md").write_text("SAFE", encoding="utf-8")
    problems = " | ".join(check_s26_work(tmp_path / STUDENT_PATH))
    assert "TODO 3" in problems and "Pinecone" in problems


# --------------------------------------------------------------------------------------------------- checkpoint
def test_checkpoint_your_s26_migration_passes():
    work = os.getenv("WORK_REPO", "").strip().strip('"')
    if not work:
        pytest.skip("WORK_REPO is not set - add WORK_REPO=<your work repo> to .env, then run again")
    path = Path(work).expanduser() / STUDENT_PATH
    if not path.exists():
        pytest.skip(f"{path} not found - run:  uv run python module04/s26_setup.py")
    problems = check_s26_work(path)
    assert not problems, "\n  - " + "\n  - ".join(problems)

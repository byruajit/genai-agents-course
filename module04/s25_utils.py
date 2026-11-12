"""Session 25 helpers - a real vector database (ChromaDB) for the Northwind help centre, and an ANN experiment.

    open_db() / build_collection()   the 53 help-centre sections + vectors + metadata, saved to disk (module04/.s25_chroma)
    search()                         semantic search INSIDE the database, with optional metadata filters
    clustered_vectors() + exact_top_k() + hnsw_run()
                                     the speed-vs-accuracy experiment: 20,000 vectors, brute force vs three HNSW settings

ChromaDB runs inside your Python process and keeps its files on disk: no server, no Docker, no account.
We give it OUR vectors (bge-small from Session 24), so it never downloads a model of its own.
"""
from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

import numpy as np

import s24_utils as S24

HERE = Path(__file__).resolve().parent
DB_DIR = HERE / ".s25_chroma"
META = json.loads((HERE / "help_centre_meta.json").read_text(encoding="utf-8"))
COLLECTION = "help_centre"

# Three HNSW settings for the experiment. ef_search = how many candidates to look at per query; max_neighbors (M) =
# links per node; ef_construction = how hard to work while building. Bigger = more accurate, slower, more memory.
HNSW_PRESETS = {
    "fast": {"ef_search": 10, "ef_construction": 40, "max_neighbors": 8},
    "default": {"ef_search": 100, "ef_construction": 100, "max_neighbors": 16},
    "accurate": {"ef_search": 300, "ef_construction": 200, "max_neighbors": 32},
}


def date_int(iso: str) -> int:
    """'2026-03-02' -> 20260302. Vector databases filter numbers easily; dates as integers keep it simple."""
    d = date.fromisoformat(iso)
    return d.year * 10000 + d.month * 100 + d.day


def metadata_for(chunk: S24.Chunk) -> dict:
    """What we store next to each vector - the labels we can filter on."""
    m = META[chunk.doc_id]
    return {"doc_id": chunk.doc_id, "title": chunk.title, "heading": chunk.heading,
            "category": m["category"], "updated": date_int(m["updated"])}


def where_filter(category: str | None = None, since: str | None = None) -> dict | None:
    """Chroma's filter language: {"category": "payments"}, {"updated": {"$gte": 20260101}}, both inside {"$and": [...]}."""
    parts = []
    if category:
        parts.append({"category": category})
    if since:
        parts.append({"updated": {"$gte": date_int(since)}})
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else {"$and": parts}


# ------------------------------------------------------------------------------------------------- the database
def open_db(path: Path | None = DB_DIR):
    """A persistent client (files on disk). path=None gives an in-memory one (used by tests)."""
    import chromadb
    from chromadb.config import Settings
    settings = Settings(anonymized_telemetry=False)
    if path is None:
        return chromadb.EphemeralClient(settings)
    return chromadb.PersistentClient(path=str(path), settings=settings)


def build_collection(client, embedder: S24.Embedder, chunks: list[S24.Chunk] | None = None,
                     make_metadata=metadata_for, name: str = COLLECTION):
    """Create (or re-create) the collection and load every section: id + vector + metadata + text."""
    chunks = chunks or S24.load_chunks()
    vectors = S24.Index(embedder, chunks).vectors                 # cached from Session 24 if you ran it
    try:
        client.delete_collection(name)
    except Exception:
        pass
    col = client.create_collection(name, configuration={"hnsw": {"space": "cosine"}})
    col.add(ids=[f"{c.doc_id}#{i}" for i, c in enumerate(chunks)],
            embeddings=vectors.tolist(),
            metadatas=[make_metadata(c) for c in chunks],
            documents=[c.text for c in chunks])
    return col


def get_collection(client, name: str = COLLECTION):
    try:
        return client.get_collection(name)
    except Exception as e:
        raise RuntimeError("The collection doesn't exist yet. Run:  uv run python module04/s25_demo.py load") from e


def search(col, embedder: S24.Embedder, question: str, k: int = 3, where: dict | None = None) -> list[dict]:
    """Embed the question (query mode), let the database find the nearest k, optionally filtered."""
    q = embedder.embed([question], kind="query")[0]
    r = col.query(query_embeddings=[q.tolist()], n_results=k, where=where,
                  include=["metadatas", "documents", "distances"])
    out = []
    for i, d, m, t in zip(r["ids"][0], r["distances"][0], r["metadatas"][0], r["documents"][0]):
        out.append({"id": i, "score": 1 - d, "meta": m, "text": t})       # Chroma returns cosine DISTANCE = 1 - cosine
    return out


# ------------------------------------------------------------------------------------- the ANN (speed vs accuracy) lab
def clustered_vectors(n: int, dims: int = 384, topics: int = 200, n_queries: int = 50, seed: int = 25):
    """Fake but realistic-ish embeddings: n vectors around `topics` centres (real text clusters by subject)."""
    rng = np.random.default_rng(seed)
    centres = rng.standard_normal((topics, dims))
    x = centres[rng.integers(0, topics, n)] + 0.6 * rng.standard_normal((n, dims))
    q = centres[rng.integers(0, topics, n_queries)] + 0.6 * rng.standard_normal((n_queries, dims))
    return S24.normalise(x).astype(np.float32), S24.normalise(q).astype(np.float32)


def exact_top_k(vectors: np.ndarray, queries: np.ndarray, k: int = 10) -> list[list[int]]:
    """Brute force: compare every query with EVERY vector. Always right, cost grows with the data."""
    scores = queries @ vectors.T
    return np.argsort(-scores, axis=1)[:, :k].tolist()


def recall_at_k(exact: list[list[int]], approx: list[list[int]], k: int = 10) -> float:
    """Average share of the true top-k that the approximate search also found. 1.0 = nothing missed."""
    if not exact:
        return 0.0
    return float(np.mean([len(set(e[:k]) & set(a[:k])) / k for e, a in zip(exact, approx)]))


def hnsw_run(client, vectors: np.ndarray, queries: np.ndarray, preset: str, k: int = 10) -> dict:
    """Load the vectors into a collection with one HNSW preset, query, time both."""
    name = f"ann-{preset}"
    try:
        client.delete_collection(name)
    except Exception:
        pass
    col = client.create_collection(name, configuration={"hnsw": dict(space="cosine", **HNSW_PRESETS[preset])})
    t0 = time.perf_counter()
    for i in range(0, len(vectors), 5000):
        col.add(ids=[str(j) for j in range(i, min(i + 5000, len(vectors)))], embeddings=vectors[i:i + 5000])
    build_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    r = col.query(query_embeddings=queries, n_results=k, include=[])
    ms = (time.perf_counter() - t0) * 1000 / len(queries)
    client.delete_collection(name)
    return {"preset": preset, "ids": [[int(x) for x in row] for row in r["ids"]], "build_s": build_s, "ms_per_query": ms}

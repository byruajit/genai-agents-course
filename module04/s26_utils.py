"""Session 26 helpers - moving the S25 collection to production vector databases: Qdrant and pgvector.

    chroma_rows()                      read every row (id, vector, metadata, text) back out of the S25 ChromaDB collection
    connect_qdrant() / migrate_to_qdrant() / search_qdrant()
                                       Qdrant: a server in Docker, Qdrant Cloud, or the same API in-process (no Docker)
    connect_pg() / migrate_to_pg() / search_pg()
                                       pgvector: vectors inside PostgreSQL - plain SQL
    load_notes() / migrate_notes()     six private customer notes (Asha, Ravi) for the multi-tenancy demo

Connection settings come from .env or the shell (defaults match module04/s26_docker-compose.yml):
    QDRANT_URL=http://localhost:6333     PG_DSN=postgresql://course:course@localhost:5433/vectors
    QDRANT_CLOUD_URL=...  QDRANT_CLOUD_API_KEY=...      (optional: your free Qdrant Cloud cluster)
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import numpy as np

import s24_utils as S24
import s25_utils as S25

HERE = Path(__file__).resolve().parent
LOCAL_QDRANT = HERE / ".s26_qdrant"                     # in-process Qdrant files, used when no server is running
NOTES = json.loads((HERE / "customer_notes.json").read_text(encoding="utf-8"))
DIMS = 384
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
PG_DSN = os.getenv("PG_DSN", "postgresql://course:course@localhost:5433/vectors")


# ------------------------------------------------------------------------------------------- source: the S25 rows
def chroma_rows(embedder: S24.Embedder | None = None) -> dict:
    """All rows of the S25 collection: {"ids", "embeddings", "metadatas", "documents"}. Builds it if missing."""
    client = S25.open_db()
    try:
        col = client.get_collection(S25.COLLECTION)
    except Exception:
        col = S25.build_collection(client, embedder or S24.Embedder())
    r = col.get(include=["embeddings", "metadatas", "documents"])
    order = sorted(range(len(r["ids"])), key=lambda i: r["ids"][i])      # stable order, easier to compare
    return {"ids": [r["ids"][i] for i in order], "embeddings": [list(map(float, r["embeddings"][i])) for i in order],
            "metadatas": [r["metadatas"][i] for i in order], "documents": [r["documents"][i] for i in order]}


def point_id(text_id: str) -> str:
    """Qdrant ids must be a number or a UUID. 'refunds#31' -> the same UUID every time (uuid5)."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, text_id))


def overlap_at_k(a: list, b: list, k: int = 3) -> float:
    """Share of the top k that two result lists have in common (order ignored). 1.0 = same results."""
    return len(set(a[:k]) & set(b[:k])) / k if k else 0.0


# ------------------------------------------------------------------------------------------------------- Qdrant
def connect_qdrant(mode: str = "auto"):
    """mode: 'server' (Docker), 'local' (in-process files, no Docker), 'cloud' (Qdrant Cloud), 'memory' (tests),
    'auto' = server if it answers, else local. Returns (client, where) - `where` says which one you got."""
    from qdrant_client import QdrantClient
    if mode == "memory":
        return QdrantClient(":memory:"), "in-memory"
    if mode == "cloud":
        url, key = os.getenv("QDRANT_CLOUD_URL", ""), os.getenv("QDRANT_CLOUD_API_KEY", "")
        if not url or not key:
            raise RuntimeError("Set QDRANT_CLOUD_URL and QDRANT_CLOUD_API_KEY in the course .env (your free cluster's "
                               "URL and API key). Never commit them.")
        return QdrantClient(url=url, api_key=key, timeout=30), f"Qdrant Cloud ({url.split('//')[-1].split('/')[0]})"
    if mode in ("server", "auto"):
        client = QdrantClient(url=QDRANT_URL, timeout=5)
        try:
            client.get_collections()
            return client, f"Qdrant server at {QDRANT_URL}"
        except Exception as e:
            if mode == "server":
                raise RuntimeError(f"No Qdrant server at {QDRANT_URL}. Start it:  "
                                   "docker compose -f module04/s26_docker-compose.yml up -d") from e
    return QdrantClient(path=str(LOCAL_QDRANT)), "local Qdrant (in-process, no Docker)"


def migrate_to_qdrant(client, rows: dict, name: str = "help_centre", to_points=None) -> int:
    """Create the collection (384 numbers, cosine) and upload every row as a point. Returns the point count."""
    from qdrant_client import models
    if client.collection_exists(name):
        client.delete_collection(name)
    client.create_collection(name, vectors_config=models.VectorParams(size=DIMS, distance=models.Distance.COSINE))
    if to_points is None:
        points = [models.PointStruct(id=point_id(i), vector=v, payload={**m, "text": d, "chroma_id": i})
                  for i, v, m, d in zip(rows["ids"], rows["embeddings"], rows["metadatas"], rows["documents"])]
    else:
        points = to_points(rows)
    for start in range(0, len(points), 256):
        client.upsert(name, points=points[start:start + 256], wait=True)
    return client.count(name, exact=True).count


def search_qdrant(client, vector, k: int = 3, name: str = "help_centre", query_filter=None, hnsw_ef: int | None = None):
    from qdrant_client import models
    params = models.SearchParams(hnsw_ef=hnsw_ef) if hnsw_ef else None
    res = client.query_points(name, query=list(map(float, vector)), limit=k, query_filter=query_filter,
                              search_params=params, with_payload=True)
    return [(p.score, p.payload) for p in res.points]


def category_filter(category: str):
    from qdrant_client import models
    return models.Filter(must=[models.FieldCondition(key="category", match=models.MatchValue(value=category))])


# ----------------------------------------------------------------------------------------------------- pgvector
def connect_pg(dsn: str = PG_DSN):
    import psycopg
    from pgvector.psycopg import register_vector
    try:
        conn = psycopg.connect(dsn, autocommit=True, connect_timeout=5)
    except Exception as e:
        raise RuntimeError(f"Can't reach PostgreSQL ({dsn.split('@')[-1]}). Start it:  "
                           "docker compose -f module04/s26_docker-compose.yml up -d   (then wait ~10 s)") from e
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    return conn


PG_SCHEMA = f"""
DROP TABLE IF EXISTS help_centre;
CREATE TABLE help_centre (
    id        text PRIMARY KEY,          -- 'refunds#31'
    doc_id    text,
    title     text,
    heading   text,
    category  text,
    updated   integer,                   -- 20260618
    body      text,
    embedding vector({DIMS})              -- the 384 numbers
);
"""
PG_INDEX = "CREATE INDEX help_centre_hnsw ON help_centre USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"
PG_SEARCH = """SELECT id, title, heading, category, updated, 1 - (embedding <=> %(q)s) AS score
FROM help_centre {where}
ORDER BY embedding <=> %(q)s
LIMIT %(k)s;"""


def migrate_to_pg(conn, rows: dict) -> int:
    for stmt in PG_SCHEMA.split(";"):
        if stmt.strip():
            conn.execute(stmt)
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO help_centre (id, doc_id, title, heading, category, updated, body, embedding) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            [(i, m["doc_id"], m.get("title"), m.get("heading"), m["category"], m["updated"], d, np.array(v, dtype=np.float32))
             for i, v, m, d in zip(rows["ids"], rows["embeddings"], rows["metadatas"], rows["documents"])])
    conn.execute(PG_INDEX)
    return conn.execute("SELECT count(*) FROM help_centre").fetchone()[0]


def search_pg(conn, vector, k: int = 3, category: str | None = None, ef_search: int | None = None):
    if ef_search:
        conn.execute(f"SET hnsw.ef_search = {int(ef_search)}")
    where = "WHERE category = %(cat)s" if category else ""
    rows = conn.execute(PG_SEARCH.format(where=where),
                        {"q": np.array(vector, dtype=np.float32), "k": k, "cat": category}).fetchall()
    return [(float(r[5]), {"chroma_id": r[0], "title": r[1], "heading": r[2], "category": r[3], "updated": r[4]}) for r in rows]


# ------------------------------------------------------------------------------------------------- multi-tenancy
def load_notes() -> list[dict]:
    return NOTES


def migrate_notes(client, embedder: S24.Embedder, name: str = "customer_notes") -> int:
    from qdrant_client import models
    if client.collection_exists(name):
        client.delete_collection(name)
    client.create_collection(name, vectors_config=models.VectorParams(size=DIMS, distance=models.Distance.COSINE))
    vecs = embedder.embed([n["text"] for n in NOTES])
    client.upsert(name, wait=True, points=[models.PointStruct(id=point_id(n["id"]), vector=v.tolist(), payload=n)
                                           for n, v in zip(NOTES, vecs)])
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")                      # in-process mode warns that payload indexes do nothing
        try:
            client.create_payload_index(name, "customer_id", models.PayloadSchemaType.KEYWORD)
        except Exception:
            pass
    return len(NOTES)

"""Session 26 homework - migrate the S25 collection to Qdrant, prove the results match, keep tenants apart, choose a store.

Setup copies this file to <your work repo>/s26/migrate.py. Run it FROM THE COURSE REPO FOLDER:

    docker compose -f module04/s26_docker-compose.yml up -d     # optional: Qdrant server (else it runs in-process)
    uv run python "<your work repo>\\s26\\migrate.py"
    uv run pytest tests/test_s26.py -rs                          # the checker

Four TODOs. Read module04/s26_vector_stores.ipynb first (its Part B also has the pgvector steps).
PART 1 is given. PART 2 is yours. Using ChatGPT is allowed - never paste your .env or any key.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "module04"))        # run from the course repo folder, so these imports work
from dotenv import find_dotenv, load_dotenv  # noqa: E402
from qdrant_client import models  # noqa: E402

load_dotenv(find_dotenv(usecwd=True))
import s24_utils as S24  # noqa: E402
import s26_utils as S26  # noqa: E402

STORES = ["chroma", "qdrant", "pgvector", "pinecone", "weaviate"]


# ======================================================================================= PART 2 - YOUR CODE
def to_points(rows: dict) -> list:
    """TODO 1 - the migration itself: ChromaDB rows -> Qdrant points.

    rows = {"ids": [...], "embeddings": [...], "metadatas": [...], "documents": [...]}  (same position = same row)
    Return one models.PointStruct per row:
        id      = S26.point_id(<the chroma id>)       Qdrant ids must be a number or UUID; this makes a stable UUID
        vector  = the embedding (a list of floats)
        payload = the metadata dict, PLUS "text": <the document> and "chroma_id": <the chroma id>
    Check: to_points({"ids": ["a#1"], "embeddings": [[0.1, 0.2]], "metadatas": [{"category": "x"}], "documents": ["hi"]})[0].payload
           == {"category": "x", "text": "hi", "chroma_id": "a#1"}
    """
    raise NotImplementedError("TODO 1")


def overlap_at_k(a: list, b: list, k: int = 3) -> float:
    """TODO 2 - did the two databases return the same top k? (order doesn't matter)

    Return (number of ids in BOTH a[:k] and b[:k]) / k, as a float. k = 0 -> 0.0
    Check: overlap_at_k(["x", "y", "z"], ["z", "x", "q"], 3) == 2/3
    """
    raise NotImplementedError("TODO 2")


def tenant_filter(customer_id: str):
    """TODO 3 - the filter that keeps one customer's notes private.

    Return a models.Filter whose `must` list holds ONE models.FieldCondition: key "customer_id", match = models.MatchValue(value=customer_id)
    (In a real app the customer_id comes from the login token - never from what the user typed.)
    """
    raise NotImplementedError("TODO 3")


# TODO 4 - choose a vector store for each situation: one of "chroma", "qdrant", "pgvector", "pinecone", "weaviate",
# and a one-sentence reason (at least 8 words) that names the deciding factor. There's more than one defensible answer.
STORE_CHOICES: dict[str, tuple[str, str]] = {
    # A hospital: patient notes must stay inside its own data centre; the IT team already runs PostgreSQL.
    "hospital_onprem": ("", ""),
    # A 2-person startup, no ops engineer, US customers, wants to pay only as it grows.
    "startup_no_ops": ("", ""),
    # 50 million product vectors, heavy filtering by brand and price, a team happy to run its own servers.
    "ecommerce_scale": ("", ""),
}


# ========================================================================================= PART 1 - GIVEN
QUESTIONS = ["how long do refunds take", "my parcel arrived broken", "can I pay cash on delivery",
             "change my delivery address", "is there a warranty on headphones"]


def main() -> None:
    emb = S24.Embedder("bge-small")
    rows = S26.chroma_rows(emb)
    client, where = S26.connect_qdrant("auto")
    n = S26.migrate_to_qdrant(client, rows, to_points=to_points)
    print(f"migrated {n} points with YOUR to_points() -> {where}\n")
    report = ["# Session 26 - my migration results", "", f"Target: {where}", "",
              "## Same results? (YOUR overlap_at_k, top 3)", "", "| question | overlap |", "|---|---|"]

    from s25_utils import get_collection, open_db, search
    chroma = get_collection(open_db())
    for q in QUESTIONS:
        before = [h["id"] for h in search(chroma, emb, q, 3)]
        qv = emb.embed([q], kind="query")[0]
        after = [p["chroma_id"] for _, p in S26.search_qdrant(client, qv, 3)]
        ov = overlap_at_k(before, after, 3)
        print(f"  {ov:.2f}  {q}")
        report.append(f"| {q} | {ov:.2f} |")

    S26.migrate_notes(client, emb)
    qv = emb.embed(["what did the customer ask about their refund"], kind="query")[0]
    leaked = [p["customer_id"] for _, p in S26.search_qdrant(client, qv, 3, "customer_notes", tenant_filter("CUST-1001"))]
    safe = all(c == "CUST-1001" for c in leaked)
    print(f"\ntenant filter for Asha returned customers {leaked} -> {'SAFE' if safe else 'LEAK'}")
    report += ["", "## Multi-tenancy (YOUR tenant_filter)", "", f"Asha's search returned: {leaked} -> {'SAFE' if safe else 'LEAK'}",
               "", "## My store choices", ""]
    report += [f"- **{k}**: {v[0]} - {v[1]}" for k, v in STORE_CHOICES.items()]

    out = Path(__file__).with_name("results.md")
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\nwrote {out}  - commit it with this file")


if __name__ == "__main__":
    main()

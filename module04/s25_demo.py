"""Session 25 - vector databases, live. Run from the COURSE repo folder.

    uv run python module04/s25_demo.py load                               # 53 sections -> a ChromaDB collection on disk
    uv run python module04/s25_demo.py peek                               # what ONE row in a vector database holds
    uv run python module04/s25_demo.py search "how do refunds work"       # search inside the database
    uv run python module04/s25_demo.py search "how do refunds work" --category payments --since 2026-06-01
    uv run python module04/s25_demo.py update                             # edit one section (upsert) and search again
    uv run python module04/s25_demo.py scale                              # brute force gets slower as data grows
    uv run python module04/s25_demo.py recall                             # 20,000 vectors: exact vs three HNSW settings

Needs Session 24's model (bge-small, downloaded once). load/search reuse its cached vectors.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s24_utils as S24  # noqa: E402
from s25_utils import (COLLECTION, DB_DIR, HNSW_PRESETS, build_collection, clustered_vectors, exact_top_k,  # noqa: E402
                       get_collection, hnsw_run, open_db, recall_at_k, search, where_filter)


def cmd_load(args) -> None:
    t0 = time.perf_counter()
    col = build_collection(open_db(), S24.Embedder())
    print(f"collection '{COLLECTION}': {col.count()} rows, saved in {DB_DIR}   ({time.perf_counter() - t0:.1f} s)")
    print("each row = id + 384-number vector + metadata (doc, category, updated date) + the section text")


def cmd_peek(args) -> None:
    col = get_collection(open_db())
    r = col.get(limit=1, include=["embeddings", "metadatas", "documents"])
    print("ONE ROW of the vector database\n")
    print(f"  id        : {r['ids'][0]}")
    print(f"  vector    : [{', '.join(f'{x:+.3f}' for x in r['embeddings'][0][:6])}, ...]  ({len(r['embeddings'][0])} numbers)")
    print(f"  metadata  : {r['metadatas'][0]}")
    print(f"  document  : {r['documents'][0][:90]}...")
    print(f"\ncategories : {sorted({m['category'] for m in col.get(include=['metadatas'])['metadatas']})}")


def cmd_search(args) -> None:
    col = get_collection(open_db())
    where = where_filter(args.category, args.since)
    print(f'"{args.text}"' + (f"   filter: {where}" if where else "   (no filter)") + "\n")
    hits = search(col, S24.Embedder(), args.text, args.k, where)
    if not hits:
        print("   no rows match that filter")
    for h in hits:
        m = h["meta"]
        print(f"   {h['score']:.3f}  {m['title']} > {m['heading']:34}  [{m['category']}, updated {m['updated']}]")


def cmd_update(args) -> None:
    client, emb = open_db(), S24.Embedder()
    col = get_collection(client)
    q = "can I pay in instalments with my credit card"
    print(f'before: "{q}"')
    for h in search(col, emb, q, 2):
        print(f"   {h['score']:.3f}  {h['meta']['heading']}")
    row = col.get(where={"doc_id": "payments"}, limit=1, include=["metadatas", "documents"])
    new_text = row["documents"][0] + " NEW: no-cost EMI in 3, 6 or 9 monthly instalments on all major credit cards."
    col.upsert(ids=row["ids"], documents=[new_text], metadatas=row["metadatas"],
               embeddings=[emb.embed([new_text])[0].tolist()])
    print(f"\nupsert: re-embedded ONE row ({row['ids'][0]}) - no full re-index needed\n")
    print(f'after: "{q}"')
    for h in search(col, emb, q, 2):
        print(f"   {h['score']:.3f}  {h['meta']['heading']}")
    print("\n(run 'load' to put the original text back)")


def cmd_scale(args) -> None:
    print("brute force: compare ONE question with every vector (384 numbers each)\n")
    print(f"{'vectors':>10}{'ms per question':>18}{'memory (MB)':>14}")
    for n in (10_000, 50_000, 200_000):
        x, q = clustered_vectors(n, n_queries=20)
        t0 = time.perf_counter()
        for row in q:
            _ = x @ row
        ms = (time.perf_counter() - t0) * 1000 / len(q)
        print(f"{n:>10,}{ms:>18.2f}{x.nbytes / 1e6:>14.0f}")
    print("\n10x the data = 10x the time, per question, per user. 50 million products? That's why we need an index.")


def cmd_recall(args) -> None:
    n = args.n
    print(f"{n:,} vectors, 50 questions, true top-10 found by brute force, then three HNSW settings...\n")
    x, q = clustered_vectors(n)
    t0 = time.perf_counter()
    exact = exact_top_k(x, q, 10)
    exact_ms = (time.perf_counter() - t0) * 1000 / len(q)
    client = open_db(None)
    print(f"{'setting':10}{'ef_search':>10}{'M':>5}{'recall@10':>11}{'ms/query':>10}{'build s':>9}")
    print(f"{'exact':10}{'-':>10}{'-':>5}{1.0:>11.2f}{exact_ms:>10.2f}{'-':>9}")
    for preset in HNSW_PRESETS:
        r = hnsw_run(client, x, q, preset)
        p = HNSW_PRESETS[preset]
        print(f"{preset:10}{p['ef_search']:>10}{p['max_neighbors']:>5}{recall_at_k(exact, r['ids']):>11.2f}"
              f"{r['ms_per_query']:>10.2f}{r['build_s']:>9.1f}")
    print("\nrecall@10 = share of the TRUE top 10 that the index found. 'Approximate' means you choose this trade-off.")
    print("At this size brute force is still fast; at millions of vectors it isn't - and the index is what scales.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Session 25 - vector databases, live")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("load").set_defaults(fn=cmd_load)
    sub.add_parser("peek").set_defaults(fn=cmd_peek)
    p = sub.add_parser("search"); p.add_argument("text"); p.add_argument("--k", type=int, default=3)
    p.add_argument("--category", choices=["orders", "payments", "returns", "account", "products"])
    p.add_argument("--since", help="only sections updated on/after this date, e.g. 2026-06-01"); p.set_defaults(fn=cmd_search)
    sub.add_parser("update").set_defaults(fn=cmd_update)
    sub.add_parser("scale").set_defaults(fn=cmd_scale)
    p = sub.add_parser("recall"); p.add_argument("--n", type=int, default=20_000); p.set_defaults(fn=cmd_recall)
    args = ap.parse_args()
    try:
        args.fn(args)
    except RuntimeError as e:
        sys.exit(f"\n{e}")


if __name__ == "__main__":
    main()

"""Session 26 - production vector stores, live. Run from the COURSE repo folder.

    docker compose -f module04/s26_docker-compose.yml up -d      # start Qdrant + PostgreSQL/pgvector (pull them at home)
    uv run python module04/s26_demo.py status                     # what's running?
    uv run python module04/s26_demo.py migrate                    # S25 ChromaDB -> Qdrant AND -> pgvector
    uv run python module04/s26_demo.py compare "how long do refunds take"   # same question, three databases
    uv run python module04/s26_demo.py sql                        # the pgvector SQL, printed
    uv run python module04/s26_demo.py tenants                    # one customer must never see another's notes
    uv run python module04/s26_demo.py tune                       # payload index, hnsw_ef per query, quantisation
    uv run python module04/s26_demo.py cloud                      # optional: the same migration to YOUR Qdrant Cloud cluster

No Docker? Everything except pgvector still works: Qdrant falls back to an in-process copy (same API, files on disk).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import find_dotenv, load_dotenv  # noqa: E402

load_dotenv(find_dotenv(usecwd=True))
import s24_utils as S24  # noqa: E402
import s25_utils as S25  # noqa: E402
import s26_utils as S26  # noqa: E402


def cmd_status(args) -> None:
    client, where = S26.connect_qdrant("auto")
    names = [c.name for c in client.get_collections().collections]
    print(f"Qdrant   : {where}   collections: {names or 'none yet'}")
    try:
        conn = S26.connect_pg()
        v = conn.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'").fetchone()[0]
        tables = [r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")]
        print(f"pgvector : PostgreSQL at {S26.PG_DSN.split('@')[-1]}, extension vector {v}, tables: {tables or 'none yet'}")
    except RuntimeError as e:
        print(f"pgvector : not reachable - {e}")
    print(f"ChromaDB : {S25.DB_DIR} (Session 25)")


def cmd_migrate(args) -> None:
    rows = S26.chroma_rows()
    print(f"read {len(rows['ids'])} rows out of ChromaDB (id, 384 numbers, metadata, text)\n")
    client, where = S26.connect_qdrant(args.qdrant)
    n = S26.migrate_to_qdrant(client, rows)
    print(f"Qdrant   : {n} points written -> {where}")
    print("           each point = UUID id (from 'refunds#31') + vector + payload {doc_id, category, updated, text, ...}")
    try:
        conn = S26.connect_pg()
        print(f"pgvector : {S26.migrate_to_pg(conn, rows)} rows written -> table help_centre, HNSW index built")
    except RuntimeError as e:
        print(f"pgvector : skipped - {e}")
    print("\nMigration = read rows, write rows. The vectors are NOT re-computed: same model, same numbers.")


def cmd_compare(args) -> None:
    emb = S24.Embedder()
    q = emb.embed([args.text], kind="query")[0]
    print(f'"{args.text}"\n')
    results = {}
    hits = S25.search(S25.get_collection(S25.open_db()), emb, args.text, args.k)
    results["ChromaDB"] = [(h["score"], h["id"], f"{h['meta']['title']} > {h['meta']['heading']}") for h in hits]
    client, _ = S26.connect_qdrant(args.qdrant)
    results["Qdrant"] = [(s, p["chroma_id"], f"{p['title']} > {p['heading']}") for s, p in S26.search_qdrant(client, q, args.k)]
    try:
        results["pgvector"] = [(s, p["chroma_id"], f"{p['title']} > {p['heading']}")
                               for s, p in S26.search_pg(S26.connect_pg(), q, args.k)]
    except RuntimeError as e:
        print(f"(pgvector skipped - {e})\n")
    for name, rows in results.items():
        print(name)
        for s, _, label in rows:
            print(f"   {s:.3f}  {label}")
    base = [i for _, i, _ in results["ChromaDB"]]
    print("\noverlap with ChromaDB's top", args.k, ":",
          "   ".join(f"{n} {S26.overlap_at_k(base, [i for _, i, _ in r], args.k):.2f}" for n, r in results.items() if n != "ChromaDB"))


def cmd_sql(args) -> None:
    print("-- pgvector is just PostgreSQL with a new column type and three distance operators\n")
    print("CREATE EXTENSION IF NOT EXISTS vector;")
    print(S26.PG_SCHEMA.strip())
    print(S26.PG_INDEX)
    print("\n-- search (<=> cosine distance, <-> euclidean, <#> negative inner product):")
    print(S26.PG_SEARCH.format(where="WHERE category = 'payments'").replace("%(q)s", "'[0.02, -0.06, ...]'").replace("%(k)s", "3"))
    print("\n-- tune at query time, no rebuild:           SET hnsw.ef_search = 100;")
    print("-- rebuild after big changes (like any index): REINDEX INDEX help_centre_hnsw;")


def cmd_tenants(args) -> None:
    from qdrant_client import models
    emb = S24.Embedder()
    client, where = S26.connect_qdrant(args.qdrant)
    S26.migrate_notes(client, emb)
    print(f"{len(S26.NOTES)} private customer notes loaded into 'customer_notes' ({where})\n")
    question = "what did the customer ask about their refund"
    q = emb.embed([question], kind="query")[0]
    print(f'Asha (CUST-1001) asks: "{question}"\n')
    print("WITHOUT a tenant filter:")
    for s, p in S26.search_qdrant(client, q, 3, "customer_notes"):
        flag = "   <-- RAVI'S DATA LEAKED" if p["customer_id"] != "CUST-1001" else ""
        print(f"   {s:.3f}  [{p['customer_id']}] {p['text'][:78]}{flag}")
    tenant = models.Filter(must=[models.FieldCondition(key="customer_id", match=models.MatchValue(value="CUST-1001"))])
    print("\nWITH filter customer_id = CUST-1001 (taken from the login token, never from the chat):")
    for s, p in S26.search_qdrant(client, q, 3, "customer_notes", query_filter=tenant):
        print(f"   {s:.3f}  [{p['customer_id']}] {p['text'][:78]}")
    print("\nThe filter runs INSIDE the database. Filtering after the search, in app code, is how leaks happen.")


def cmd_tune(args) -> None:
    from qdrant_client import models
    emb = S24.Embedder()
    client, where = S26.connect_qdrant(args.qdrant)
    if not client.collection_exists("help_centre"):
        S26.migrate_to_qdrant(client, S26.chroma_rows())
    q = emb.embed(["how long do refunds take"], kind="query")[0]
    print(f"Qdrant: {where}\n")
    print("1. Payload index on 'category' (like a SQL index on a WHERE column):")
    local = "in-process" in where
    if local:
        print("   needs the Qdrant SERVER (Docker or Cloud) - in-process mode accepts it but does nothing")
    else:
        client.create_payload_index("help_centre", "category", models.PayloadSchemaType.KEYWORD)
        info = client.get_collection("help_centre")
        print(f"   indexed fields: {list((info.payload_schema or {}).keys())}")
    print("\n2. hnsw_ef per query - more candidates, no rebuild:")
    for ef in (8, 64, 256):
        top = S26.search_qdrant(client, q, 3, hnsw_ef=ef)
        print(f"   hnsw_ef={ef:<4} top: {top[0][1]['heading']}")
    print("\n3. Scalar quantisation - store each number in 1 byte instead of 4:")
    if local:
        print("   needs the Qdrant SERVER (Docker or Cloud) - shown as numbers only below")
    else:
        client.update_collection("help_centre", quantization_config=models.ScalarQuantization(
            scalar=models.ScalarQuantizationConfig(type=models.ScalarType.INT8, always_ram=True)))
        print("   enabled on 'help_centre' (int8): vectors take ~4x less memory; results are re-scored with the originals.")
    n = 10_000_000
    print(f"\n   {n:,} vectors x {S26.DIMS} numbers: float32 {n * S26.DIMS * 4 / 1e9:.1f} GB  ->  int8 {n * S26.DIMS / 1e9:.1f} GB"
          f"  ->  binary {n * S26.DIMS / 8 / 1e9:.2f} GB")


def cmd_cloud(args) -> None:
    rows = S26.chroma_rows()
    client, where = S26.connect_qdrant("cloud")
    n = S26.migrate_to_qdrant(client, rows)
    q = S24.Embedder().embed(["how long do refunds take"], kind="query")[0]
    print(f"{n} points written to {where}")
    for s, p in S26.search_qdrant(client, q, 3):
        print(f"   {s:.3f}  {p['title']} > {p['heading']}")
    print("\nSame code as local - only the URL and API key changed. Free clusters suspend after a week unused.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Session 26 - production vector stores, live")
    ap.add_argument("--qdrant", default="auto", choices=["auto", "server", "local"],
                    help="auto = Docker server if running, else in-process")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("migrate").set_defaults(fn=cmd_migrate)
    p = sub.add_parser("compare"); p.add_argument("text"); p.add_argument("--k", type=int, default=3); p.set_defaults(fn=cmd_compare)
    sub.add_parser("sql").set_defaults(fn=cmd_sql)
    sub.add_parser("tenants").set_defaults(fn=cmd_tenants)
    sub.add_parser("tune").set_defaults(fn=cmd_tune)
    sub.add_parser("cloud").set_defaults(fn=cmd_cloud)
    args = ap.parse_args()
    try:
        args.fn(args)
    except RuntimeError as e:
        sys.exit(f"\n{e}")


if __name__ == "__main__":
    main()

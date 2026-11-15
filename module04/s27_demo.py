"""Session 27 - hybrid search and reranking, live. Run from the COURSE repo folder.

    uv run python module04/s27_demo.py download                          # PRE-WORK at home: the reranker model (~80 MB)
    uv run python module04/s27_demo.py keyword "SKU-EL-004" --in products  # BM25 only
    uv run python module04/s27_demo.py dense   "SKU-EL-004" --in products  # vectors only - watch them miss the code
    uv run python module04/s27_demo.py hybrid  "SKU-EL-004" --in products  # both, fused with RRF
    uv run python module04/s27_demo.py rerank  "SKU-EL-004" --in products  # hybrid top 20 -> cross-encoder -> top 3
    uv run python module04/s27_demo.py all     "the parcel arrived smashed"  # the four methods side by side
    uv run python module04/s27_demo.py explain "HDFC no-cost EMI"          # where a BM25 score comes from, word by word
    uv run python module04/s27_demo.py fuse    "PowerCell" --in products   # the RRF arithmetic, row by row
    uv run python module04/s27_demo.py compare                             # all 22 test questions x 4 methods (+ weighted)
    uv run python module04/s27_demo.py gate                                # in-scope vs out-of-scope reranker scores
    uv run python module04/s27_demo.py qdrant "SKU-EL-004" --in products   # the same hybrid search INSIDE Qdrant

--in help (default) = the help centre; --in products = the 30-product catalog.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import find_dotenv, load_dotenv  # noqa: E402

load_dotenv(find_dotenv(usecwd=True))
import s27_queries as Q  # noqa: E402
import s27_utils as S27  # noqa: E402


def show(title: str, hits) -> None:
    print(title)
    if not hits:
        print("   (nothing - no shared words)")
    for h in hits:
        print(f"   {h.score:8.3f}  {h.chunk.source}   [{h.chunk.doc_id}]")


def cmd_one(args) -> None:
    r = S27.Retriever(args.corpus)
    t0 = time.perf_counter()
    hits = r.search(args.cmd, args.text, args.k)
    ms = (time.perf_counter() - t0) * 1000
    show(f'{args.cmd.upper()}  "{args.text}"   ({args.corpus}, {ms:.0f} ms)', hits)


def cmd_all(args) -> None:
    r = S27.Retriever(args.corpus)
    print(f'"{args.text}"   ({args.corpus})\n')
    for m in S27.METHODS:
        t0 = time.perf_counter()
        hits = r.search(m, args.text, args.k)
        show(f"{m:<8} ({(time.perf_counter() - t0) * 1000:.0f} ms)", hits)
        print()


def cmd_explain(args) -> None:
    r = S27.Retriever(args.corpus)
    print(f'question words: {S27.tokenize(args.text)}\n')
    for h in r.keyword(args.text, args.k):
        i = r.keys.index(h.key)
        print(f"{h.score:6.2f}  {h.chunk.source}")
        for w, idf, tf, part in r.bm25.explain(args.text, i):
            if tf:
                print(f"         {w:<14} idf {idf:5.2f}  x{tf} in this section  -> +{part:.2f}")
    print("\nidf = how RARE the word is across all sections (rare = worth more). Repeats help, but less each time;")
    print("long sections are scaled down so they don't win just for having more words.")


def cmd_fuse(args) -> None:
    r = S27.Retriever(args.corpus)
    kw, dn = r.keyword_ranking(args.text, args.n), r.dense_ranking(args.text, args.n)
    print(f'"{args.text}"   RRF: score = 1/(60 + keyword rank) + 1/(60 + vector rank)\n')
    print(f"{'row':<26}{'keyword':>9}{'vector':>8}{'RRF score':>12}")
    for key, s in S27.rrf([kw, dn])[:8]:
        a = kw.index(key) + 1 if key in kw else "-"
        b = dn.index(key) + 1 if key in dn else "-"
        print(f"{key:<26}{a!s:>9}{b!s:>8}{s:>12.4f}")
    print("\nA row near the top of BOTH lists beats a row that is first in only one. Scores never get added - only ranks.")


def cmd_compare(args) -> None:
    rs = {c: S27.Retriever(c) for c in S27.CORPORA}
    print(f"{len(Q.CASES)} questions ({sum(c[3] == 'exact' for c in Q.CASES)} exact, "
          f"{sum(c[3] == 'meaning' for c in Q.CASES)} meaning), top 3\n")
    print(f"{'method':<10}{'hit@3':>8}{'MRR':>7}{'exact':>8}{'meaning':>9}{'ms/q':>8}")
    results = {}
    for m in (*S27.METHODS, "weighted"):
        res = S27.evaluate(rs, Q.CASES, m)
        results[m] = res
        a, e, n = res["all"], res["exact"], res["meaning"]
        print(f"{m:<10}{a['hits']:>5}/{a['n']:<2}{a['mrr']:>7.2f}{e['hits']:>5}/{e['n']:<2}{n['hits']:>6}/{n['n']:<2}"
              f"{res['ms']:>8.0f}")
    if args.misses:
        for m, res in results.items():
            for row in res["rows"]:
                if row["rank"] is None:
                    print(f"  MISS {m:<8} {row['question']!r:<48} wanted {row['expected']}, got {row['found']}")
    print("\nExpected story: keyword wins 'exact', vectors win 'meaning', hybrid is good at both, rerank lifts MRR.")
    print("weighted = score fusion with alpha 0.5 (min-max normalised). Add --misses to see every miss.")


def cmd_gate(args) -> None:
    r = S27.Retriever("help")
    print(f"reranker top score per question; the gate keeps a passage only if score >= {S27.RERANK_MIN}\n")
    rows = [(q, "in scope") for q, c, *_ in Q.CASES if c == "help"][:5] + [(q, "OUT of scope") for q, _ in Q.OUT_OF_SCOPE]
    for q, label in rows:
        top = r.rerank(q, k=1)[0]
        verdict = "keep" if top.score >= S27.RERANK_MIN else "-> 'I don't know'"
        print(f"  {top.score:7.2f}  {label:<13} {q!r:<48} {verdict}")
    print("\nWithout a gate the LLM is handed the 'best' passage even for used cars - and answers from it.")


def cmd_qdrant(args) -> None:
    import s26_utils as S26
    r = S27.Retriever(args.corpus)
    client, where = S26.connect_qdrant(args.qdrant)
    name = S27.qdrant_hybrid_load(client, r)
    print(f"collection '{name}' -> {where}: each point has a dense vector (384 numbers) AND a sparse 'bm25' vector")
    print("(one slot per word it contains; Qdrant applies IDF itself)\n")
    for score, p in S27.qdrant_hybrid_search(client, r, args.text, args.k):
        print(f"   {score:.3f}  {p['source']}   [{p['doc_id']}]")
    print("\nOne query_points call: two prefetches (sparse + dense) and FusionQuery(RRF). Qdrant uses its own RRF constant,")
    print("so the scores differ from ours - the order is what matters. Weaviate does the same with hybrid(alpha=...).")


def cmd_download(args) -> None:
    import s24_utils as S24
    print("embedding model (S24) ...", end=" ", flush=True)
    S24.Embedder().embed(["warm up"])
    print("ok\nreranker model (~80 MB) ...", end=" ", flush=True)
    print("ok" if S27.Reranker().score("warm up", ["a passage"]) else "?")
    print("Both cached - S27 now runs offline.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Session 27 - hybrid search and reranking, live")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in (*S27.METHODS, "all", "explain", "fuse", "qdrant"):
        p = sub.add_parser(name)
        p.add_argument("text")
        p.add_argument("--in", dest="corpus", default="help", choices=S27.CORPORA)
        p.add_argument("--k", type=int, default=3)
        p.add_argument("--n", type=int, default=20, help="candidates per list (fuse)")
        p.add_argument("--qdrant", default="auto", choices=["auto", "server", "local"])
        fn = {"all": cmd_all, "explain": cmd_explain, "fuse": cmd_fuse, "qdrant": cmd_qdrant}.get(name, cmd_one)
        p.set_defaults(fn=fn)
    p = sub.add_parser("compare")
    p.add_argument("--misses", action="store_true")
    p.set_defaults(fn=cmd_compare)
    sub.add_parser("gate").set_defaults(fn=cmd_gate)
    sub.add_parser("download").set_defaults(fn=cmd_download)
    args = ap.parse_args()
    try:
        args.fn(args)
    except RuntimeError as e:
        sys.exit(f"\n{e}")


if __name__ == "__main__":
    main()

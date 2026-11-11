"""Session 24 - embeddings, live. Run from the COURSE repo folder; every command prints one thing to talk about.

    uv run python module04/s24_demo.py embed "return a damaged item"            # text -> 384 numbers
    uv run python module04/s24_demo.py similar "damaged item" "broken product" "gift card"   # cosine table
    uv run python module04/s24_demo.py keyword "my earbuds stopped working"     # the OLD way: shared words
    uv run python module04/s24_demo.py search "my earbuds stopped working"      # meaning search, top 3
    uv run python module04/s24_demo.py compare                                  # keyword vs two embedding models
    uv run python module04/s24_demo.py check                                    # the 10 test questions, pass mark 8

Options:  --model bge-small | minilm | nomic      (nomic needs Ollama running and `ollama pull nomic-embed-text`)
          --ollama                                  (compare: also include nomic)
The first run downloads the model once (~67 MB for bge-small). After that it works offline.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from s24_queries import CASES, OUT_OF_SCOPE, PASS_MARK  # noqa: E402
from s24_utils import DEFAULT_MODEL, MODELS, Embedder, Index, cosine, evaluate, keyword_search, load_chunks  # noqa: E402


def line(char: str = "-", n: int = 92) -> None:
    print(char * n)


def show_results(title: str, results) -> None:
    print(f"\n{title}")
    if not results:
        print("   (nothing - not one word in common)")
    for i, (score, c) in enumerate(results, 1):
        print(f"   {i}. {score:6.3f}   {c.source}")
        print(f"              {c.text[:80]}...")


def cmd_embed(args) -> None:
    emb = Embedder(args.model)
    t0 = time.perf_counter()
    vec = emb.embed([args.text])[0]
    ms = (time.perf_counter() - t0) * 1000
    print(f'text      : "{args.text}"')
    print(f"model     : {emb.model_id}   (runs on: {emb.runtime})")
    print(f"dimensions: {len(vec)}  numbers")
    print(f"first 8   : [{', '.join(f'{x:+.3f}' for x in vec[:8])}, ...]")
    print(f"length    : {float((vec ** 2).sum()) ** 0.5:.3f}   (scaled to 1, so cosine = a simple dot product)")
    print(f"time      : {ms:.0f} ms")
    print("\nNo single number means 'damaged' or 'refund'. Meaning lives in the PATTERN across all of them.")


def cmd_similar(args) -> None:
    texts = args.texts
    if len(texts) < 2:
        sys.exit('give at least two texts, e.g.  similar "damaged item" "broken product" "gift card"')
    emb = Embedder(args.model)
    vecs = emb.embed(texts)
    width = max(len(t) for t in texts) + 2
    print(f"cosine similarity, model {emb.model_id}   (1.00 = same meaning direction)\n")
    print(" " * width + "".join(f"{i + 1:>8}" for i in range(len(texts))))
    for i, t in enumerate(texts):
        print(f"{i + 1}. {t:<{width - 3}}" + "".join(f"{cosine(vecs[i], vecs[j]):8.2f}" for j in range(len(texts))))
    pairs = sorted(((cosine(vecs[i], vecs[j]), i, j) for i in range(len(texts)) for j in range(i + 1, len(texts))),
                   reverse=True)
    s, i, j = pairs[0]
    print(f'\nclosest pair : "{texts[i]}"  <->  "{texts[j]}"   ({s:.2f})')
    s, i, j = pairs[-1]
    print(f'furthest pair: "{texts[i]}"  <->  "{texts[j]}"   ({s:.2f})')


def cmd_keyword(args) -> None:
    show_results(f'KEYWORD search: "{args.text}"  (score = shared words)', keyword_search(args.text, load_chunks()))


def cmd_search(args) -> None:
    index = Index(Embedder(args.model))
    if index.seconds:
        print(f"(embedded {len(index.chunks)} help-centre sections in {index.seconds:.1f} s - cached for next time)")
    show_results(f'KEYWORD search: "{args.text}"', keyword_search(args.text, index.chunks))
    show_results(f'MEANING search ({index.embedder.model_id}): "{args.text}"', index.search(args.text, args.k))


def cmd_compare(args) -> None:
    chunks = load_chunks()
    rows = [("keyword (shared words)", "-", evaluate(lambda q, k: keyword_search(q, chunks, k), CASES), None)]
    names = ["bge-small", "minilm"] + (["nomic"] if args.ollama else [])
    for name in names:
        try:
            index = Index(Embedder(name), chunks)
        except RuntimeError as e:
            print(f"skipping {name}: {e}")
            continue
        t0 = time.perf_counter()
        result = evaluate(index.search, CASES)
        per_query = (time.perf_counter() - t0) * 1000 / len(CASES)
        rows.append((index.embedder.model_id, str(index.embedder.dims), result, per_query))
    print(f"\n{len(CASES)} customer questions, is the right article in the top 3?\n")
    print(f"{'method':42}{'dims':>6}{'hit@3':>8}{'MRR':>7}{'ms/query':>10}")
    line()
    for name, dims, r, ms in rows:
        print(f"{name:42}{dims:>6}{r['hits']:>5}/{r['n']:<2}{r['mrr']:>7.2f}{(f'{ms:.0f}' if ms else '-'):>10}")
    print("\nMISSES per method:")
    for name, _, r, _ in rows:
        missed = [row["question"] for row in r["rows"] if not row["rank"]]
        print(f"  {name}: {', '.join(missed) if missed else 'none'}")


def cmd_check(args) -> None:
    index = Index(Embedder(args.model))
    r = evaluate(index.search, CASES)
    print(f"model {index.embedder.model_id}\n")
    for row in r["rows"]:
        mark = f"#{row['rank']}" if row["rank"] else "MISS"
        print(f"  {mark:>4}  {row['question']:48} expected {row['expected']:18} got {row['found']}")
    print("\nout of scope (nothing should match well - note the LOW top score):")
    for q in OUT_OF_SCOPE:
        score, c = index.search(q, 1)[0]
        print(f"        {q:48} best {score:.2f}  {c.source}")
    print(f"\nhit@3 {r['hits']}/{r['n']}   MRR {r['mrr']:.2f}   pass mark {PASS_MARK}/{r['n']}")
    print("PASS" if r["hits"] >= PASS_MARK else "BELOW THE PASS MARK - see module04/s24_common_errors.md")
    sys.exit(0 if r["hits"] >= PASS_MARK else 1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Session 24 - embeddings, live")
    ap.add_argument("--model", default=DEFAULT_MODEL, choices=list(MODELS))
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("embed"); p.add_argument("text"); p.set_defaults(fn=cmd_embed)
    p = sub.add_parser("similar"); p.add_argument("texts", nargs="+"); p.set_defaults(fn=cmd_similar)
    p = sub.add_parser("keyword"); p.add_argument("text"); p.set_defaults(fn=cmd_keyword)
    p = sub.add_parser("search"); p.add_argument("text"); p.add_argument("--k", type=int, default=3); p.set_defaults(fn=cmd_search)
    p = sub.add_parser("compare"); p.add_argument("--ollama", action="store_true"); p.set_defaults(fn=cmd_compare)
    p = sub.add_parser("check"); p.set_defaults(fn=cmd_check)
    args = ap.parse_args()
    try:
        args.fn(args)
    except RuntimeError as e:
        sys.exit(f"\n{e}")


if __name__ == "__main__":
    main()

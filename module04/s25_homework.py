"""Session 25 homework - YOUR vector database: metadata, filters, and measuring an approximate index.

Setup copies this file to <your work repo>/s25/store.py. Run it FROM THE COURSE REPO FOLDER:

    uv run python "<your work repo>\\s25\\store.py"
    uv run pytest tests/test_s25.py -rs                  # the checker

Four TODOs. Read module04/s25_vector_db.ipynb first: it explains every idea used here.
PART 1 is given (the database, the model, the experiment). PART 2 is yours.
Using ChatGPT is allowed - never paste your .env or any key, and be ready to explain every line you wrote.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "module04"))        # run from the course repo folder, so these imports work
import s24_utils as S24  # noqa: E402
import s25_utils as S25  # noqa: E402

CATEGORIES = ["orders", "payments", "returns", "account", "products"]


# ======================================================================================= PART 2 - YOUR CODE
def make_metadata(chunk: S24.Chunk, info: dict) -> dict:
    """TODO 1 - the labels stored next to one section's vector.

    `info` is this article's entry from module04/help_centre_meta.json, e.g. {"category": "payments", "updated": "2026-09-30"}.
    Return exactly three keys:
        "doc_id"   -> chunk.doc_id
        "category" -> info["category"]
        "updated"  -> the date as an INTEGER YYYYMMDD: "2026-09-30" -> 20260930   (numbers are easy to filter with >=)
    Check: make_metadata(chunk, {"category": "returns", "updated": "2026-03-02"})["updated"] == 20260302
    """
    raise NotImplementedError("TODO 1")


def build_where(category: str | None = None, since: str | None = None) -> dict | None:
    """TODO 2 - turn two optional filters into ChromaDB's filter language.

    nothing given            -> None
    only category            -> {"category": category}
    only since ("YYYY-MM-DD")-> {"updated": {"$gte": <since as YYYYMMDD int>}}
    both                     -> {"$and": [ <the category part>, <the since part> ]}   (category first)
    Check: build_where("payments", "2026-06-01") ==
           {"$and": [{"category": "payments"}, {"updated": {"$gte": 20260601}}]}
    """
    raise NotImplementedError("TODO 2")


def recall_at_k(exact: list[list[int]], approx: list[list[int]], k: int = 10) -> float:
    """TODO 3 - how much did the approximate index miss?

    exact[i]  = the TRUE top-k ids for question i (from brute force)
    approx[i] = the top-k ids the index returned for question i
    For each question: (how many of exact[i][:k] are also in approx[i][:k]) / k. Return the AVERAGE over all questions,
    as a float between 0 and 1. Empty input -> 0.0
    Check: recall_at_k([[1, 2, 3, 4]], [[1, 2, 9, 8]], k=4) == 0.5
    """
    raise NotImplementedError("TODO 3")


# TODO 4 - two filtered questions of YOUR OWN: (question, category or None, since-date "YYYY-MM-DD" or None).
# At least one of them must use BOTH filters. Categories: orders, payments, returns, account, products.
MY_FILTERED: list[tuple[str, str | None, str | None]] = [
    # ("my question", "payments", "2026-01-01"),
]


# ========================================================================================= PART 1 - GIVEN
def main() -> None:
    client = S25.open_db(None)                                   # in memory - nothing written to your disk
    emb = S24.Embedder("bge-small")
    col = S25.build_collection(client, emb, make_metadata=lambda c: make_metadata(c, S25.META[c.doc_id]))
    print(f"collection built with YOUR make_metadata(): {col.count()} rows\n")
    report = ["# Session 25 - my vector database results", "", "## Filtered search (YOUR build_where)", "",
              "| question | filter | top results | all match the filter? |", "|---|---|---|---|"]

    course = [("how long do refunds take", "payments", None), ("change my delivery address", None, "2026-01-01"),
              ("my parcel arrived broken", "returns", "2026-06-01")]
    for question, category, since in course + MY_FILTERED:
        where = build_where(category, since)
        hits = S25.search(col, emb, question, 3, where)
        ok = all((not category or h["meta"]["category"] == category) and
                 (not since or h["meta"]["updated"] >= S25.date_int(since)) for h in hits)
        names = ", ".join(f"{h['meta']['doc_id']} ({h['meta']['updated']})" for h in hits) or "no rows match"
        print(f"  {'ok  ' if ok else 'FAIL'} {question[:40]:40} {where}\n        -> {names}")
        report.append(f"| {question} | `{where}` | {names} | {'yes' if ok else 'NO'} |")

    print("\nANN experiment: 20,000 vectors (about 20 seconds), exact top-10 vs three HNSW settings (YOUR recall_at_k)")
    x, q = S25.clustered_vectors(20_000)
    exact = S25.exact_top_k(x, q, 10)
    report += ["", "## Speed vs accuracy (YOUR recall_at_k)", "", "| setting | recall@10 | ms/query |", "|---|---|---|"]
    ann = S25.open_db(None)
    for preset in S25.HNSW_PRESETS:
        r = S25.hnsw_run(ann, x, q, preset)
        rec = recall_at_k(exact, r["ids"], 10)
        print(f"  {preset:9} recall@10 {rec:.2f}   {r['ms_per_query']:.2f} ms/query")
        report.append(f"| {preset} | {rec:.2f} | {r['ms_per_query']:.2f} |")

    out = Path(__file__).with_name("results.md")
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\nwrote {out}  - commit it with this file")


if __name__ == "__main__":
    main()

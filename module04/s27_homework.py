"""Session 27 homework - build hybrid search and a reranking step yourself, then measure all of it.

Setup copies this file to <your work repo>/s27/hybrid.py. Run it FROM THE COURSE REPO FOLDER:

    uv run python "<your work repo>\\s27\\hybrid.py"
    uv run pytest tests/test_s27.py -rs                          # the checker

Four TODOs. Read module04/s27_hybrid_rerank.ipynb first. PART 1 is given. PART 2 is yours.
Using ChatGPT is allowed - never paste your .env or any key.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "module04"))        # run from the course repo folder, so these imports work
from dotenv import find_dotenv, load_dotenv  # noqa: E402

load_dotenv(find_dotenv(usecwd=True))
import s27_queries as Q  # noqa: E402
import s27_utils as S27  # noqa: E402


# ======================================================================================= PART 2 - YOUR CODE
def rrf_fuse(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """TODO 1 - Reciprocal Rank Fusion.

    rankings = several lists of ids, best first, e.g. [["a", "b", "c"], ["c", "a", "d"]]  (keyword list, vector list)
    Every list gives each id it contains 1 / (k + rank), rank starting at 1. Add an id's shares from all lists.
    An id missing from a list gets nothing from that list.
    Return [(id, score), ...] sorted by score, highest first.
    Check: rrf_fuse([["a", "b"], ["b"]], k=60)[0] == ("b", 1/62 + 1/61)
    """
    raise NotImplementedError("TODO 1")


def weighted_fuse(keyword: dict[str, float], dense: dict[str, float], alpha: float = 0.5) -> list[tuple[str, float]]:
    """TODO 2 - score fusion (the other way to merge, used by Weaviate's hybrid(alpha=...)).

    1. Min-max normalise each dict to 0..1:  (score - lowest) / (highest - lowest).  If all scores in a dict are equal,
       every id in it gets 1.0.  An empty dict stays empty.
    2. For every id in either dict:  alpha * dense_norm + (1 - alpha) * keyword_norm   (a missing id counts as 0).
    Return [(id, fused score), ...] highest first.
    Check: dict(weighted_fuse({"a": 10, "b": 0}, {"a": 0.2, "b": 0.9}, 0.5)) == {"a": 0.5, "b": 0.5}
    """
    raise NotImplementedError("TODO 2")


def rerank_top(question: str, candidates: list, score_fn, k: int = 3) -> list[tuple[float, object]]:
    """TODO 3 - the second stage of two-stage retrieval.

    candidates = hybrid's top 20, each one has .chunk.search_text (the passage text)
    score_fn(question, [text, text, ...]) -> [score, score, ...]   - the cross-encoder. Call it ONCE with all the texts
    (one batch is much faster than 20 single calls).
    Return the k best as [(score, candidate), ...], highest score first.
    """
    raise NotImplementedError("TODO 3")


# TODO 4 - (a) three EXACT-term questions of your own: a code, a name, a number or a brand word a customer would type.
# Each: (question, corpus, expected doc_id). corpus "products" -> doc_id is a SKU (see module04/products.json);
# corpus "help" -> doc_id is an article name (see module04/help_centre/). Not one of the questions in s27_queries.py.
MY_EXACT_CASES: list[tuple[str, str, str]] = [
    # ("...", "products", "SKU-..."),
]

# (b) the relevance gate: the lowest reranker score you still trust. Run `s27_demo.py gate`, look at the in-scope and
# out-of-scope scores, pick a number, and say why in one sentence (at least 8 words).
GATE: tuple[float, str] = (0.0, "")


# ========================================================================================= PART 1 - GIVEN
class YourRetriever:
    """The course Retriever, with YOUR fusion and YOUR reranking step plugged in."""

    def __init__(self, r: S27.Retriever):
        self.r = r

    def search(self, method: str, question: str, k: int = 3):
        r = self.r
        if method == "hybrid":
            return r.hybrid(question, k, fuse=rrf_fuse)
        if method == "weighted":
            return r.weighted(question, k, alpha=0.5, fuse=weighted_fuse)
        if method == "rerank":
            if r.reranker is None:
                r.reranker = S27.Reranker()
            cands = r.hybrid(question, k=20, fuse=rrf_fuse)
            return [S27.Hit(s, c.chunk, c.key) for s, c in rerank_top(question, cands, r.reranker.score, k)]
        return r.search(method, question, k)


def main() -> None:
    rs = {c: YourRetriever(S27.Retriever(c)) for c in S27.CORPORA}
    cases = Q.CASES + [(q, c, e, "exact") for q, c, e in MY_EXACT_CASES]
    report = ["# Session 27 - my hybrid search results", "",
              (f"{len(cases)} questions ({sum(c[3] == 'exact' for c in cases)} exact incl. my {len(MY_EXACT_CASES)}, "
               f"{sum(c[3] == 'meaning' for c in cases)} meaning), top 3"), "",
              "| method | hit@3 | MRR | exact | meaning |", "|---|---|---|---|---|"]
    print(report[2] + "\n")
    for m in ("keyword", "dense", "hybrid", "weighted", "rerank"):
        res = S27.evaluate(rs, cases, m)
        a, e, n = res["all"], res["exact"], res["meaning"]
        line = f"| {m} | {a['hits']}/{a['n']} | {a['mrr']:.2f} | {e['hits']}/{e['n']} | {n['hits']}/{n['n']} |"
        print(line)
        report.append(line)

    threshold, reason = GATE
    r = rs["help"]
    inside = [q for q, c, *_ in Q.CASES if c == "help"]
    kept = sum(r.search("rerank", q, 1)[0].score >= threshold for q in inside)
    blocked = sum(r.search("rerank", q, 1)[0].score < threshold for q, _ in Q.OUT_OF_SCOPE)
    gate = (f"Gate {threshold}: kept {kept}/{len(inside)} in-scope questions, said 'I don't know' to "
            f"{blocked}/{len(Q.OUT_OF_SCOPE)} out-of-scope ones. Why this number: {reason}")
    print("\n" + gate)
    report += ["", "## My relevance gate", "", gate, "", "## My exact-term questions", ""]
    report += [f"- `{q}` ({c}) -> {e}" for q, c, e in MY_EXACT_CASES]

    out = Path(__file__).with_name("results.md")
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\nwrote {out}  - commit it with this file")


if __name__ == "__main__":
    main()

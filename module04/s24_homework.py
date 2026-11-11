"""Session 24 homework - YOUR semantic search over the Northwind help centre.

Setup copies this file to <your work repo>/s24/search.py. Run it FROM THE COURSE REPO FOLDER:

    uv run python "<your work repo>\\s24\\search.py"
    uv run pytest tests/test_s24.py -rs                  # the checker

Four TODOs. Each one is a few lines. Read module04/s24_embeddings.ipynb first: it explains every idea used here.
PART 1 is given (loading the model, running the test). PART 2 is yours.
Using ChatGPT is allowed - but never paste your .env or any key, and be ready to explain every line you wrote.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path.cwd() / "module04"))        # run from the course repo folder, so these imports work
from s24_queries import CASES, PASS_MARK  # noqa: E402
from s24_utils import KB_DIR, Embedder  # noqa: E402


# ======================================================================================= PART 2 - YOUR CODE
def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """TODO 1 - how alike two vectors point.

    cos(angle) = (a . b) / (|a| * |b|)       a . b  is  np.dot(a, b)      |a|  is  np.linalg.norm(a)
    Return a plain float. If either vector is all zeros, return 0.0 (don't divide by zero).
    Check: cosine([1, 0], [1, 0]) == 1.0,  cosine([1, 0], [0, 1]) == 0.0,  cosine([1, 0], [-1, 0]) == -1.0
    """
    raise NotImplementedError("TODO 1")


def top_k(query: np.ndarray, matrix: np.ndarray, k: int = 3) -> list[int]:
    """TODO 2 - the row numbers of the k rows of `matrix` most similar to `query`, BEST FIRST.

    Use your cosine() on every row (a loop is fine), then sort. Return a list of ints, length k
    (or fewer if the matrix has fewer rows).
    Check: top_k(np.array([1, 0]), np.array([[0, 1], [1, 0], [1, 1]]), 2) == [1, 2]
    """
    raise NotImplementedError("TODO 2")


def split_sections(markdown: str) -> list[tuple[str, str]]:
    """TODO 3 - one help-centre article -> a list of (heading, text), one per '## ' section.

    - Ignore everything before the first line that starts with '## ' (the front matter and the '# Title').
    - heading = the rest of the '## ' line, stripped.     text = the lines under it, joined with single spaces.
    - Skip a section whose text is empty.
    Check: split_sections("# T\\n## A\\none\\ntwo\\n## B\\n\\n## C\\nthree") == [("A", "one two"), ("C", "three")]
    """
    raise NotImplementedError("TODO 3")


# TODO 4 - three questions of YOUR OWN, written the way a customer would type them, each with the article that
# answers it. Article names are the file names in module04/help_centre/ without .md (e.g. "warranty", "returns").
# Try to use DIFFERENT words from the article - that's what meaning search is for.
MY_CASES: list[tuple[str, str]] = [
    # ("my question", "article-name"),
]


# ========================================================================================= PART 1 - GIVEN
def load_sections() -> tuple[list[str], list[str], list[str]]:
    """All articles -> (texts to embed, article names, 'Article > Section' labels), using YOUR split_sections."""
    texts, docs, labels = [], [], []
    for path in sorted(KB_DIR.glob("*.md")):
        for heading, text in split_sections(path.read_text(encoding="utf-8")):
            texts.append(f"{heading}. {text}")
            docs.append(path.stem)
            labels.append(f"{path.stem} > {heading}")
    return texts, docs, labels


def main() -> None:
    texts, docs, labels = load_sections()
    print(f"{len(texts)} sections loaded with YOUR split_sections()")
    emb = Embedder("bge-small")
    matrix = emb.embed(texts)                                     # offline half: every section, once
    print(f"embedded them with {emb.model_id}: {matrix.shape[0]} rows x {matrix.shape[1]} numbers\n")

    report = ["# Session 24 - my semantic search results", "", f"Model: {emb.model_id}", "",
              "| # | question | expected | top 3 (YOUR top_k) | hit |", "|---|---|---|---|---|"]
    hits = mine = 0
    for i, (question, expected) in enumerate(CASES + MY_CASES, 1):
        q = emb.embed([question], kind="query")[0]                 # online half: the question
        found = [docs[j] for j in top_k(q, matrix, 3)]
        ok = expected in found
        if i <= len(CASES):
            hits += ok
        else:
            mine += ok
        print(f"  {'ok  ' if ok else 'MISS'} {question[:50]:50} -> {found}")
        report.append(f"| {i} | {question} | {expected} | {', '.join(found)} | {'yes' if ok else 'no'} |")

    summary = f"Course questions: hit@3 {hits}/{len(CASES)} (pass mark {PASS_MARK}).  My questions: {mine}/{len(MY_CASES)}."
    print("\n" + summary)
    report += ["", summary, ""]
    out = Path(__file__).with_name("results.md")
    out.write_text("\n".join(report), encoding="utf-8")
    print(f"wrote {out}  - commit it with this file")


if __name__ == "__main__":
    main()

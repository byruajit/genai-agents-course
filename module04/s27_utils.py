"""Session 27 helpers - hybrid search (BM25 keywords + vectors) and reranking, over the Northwind help centre AND catalog.

Read it top to bottom - every piece is small:

    load_corpus("help")       the 53 help-centre sections (S24)          load_corpus("products")  the 30-product catalog
    tokenize()                text -> search words (lower case, no stop words, simple plurals, keeps codes like sku-fw-001)
    BM25                      keyword search with a score: rare words count more, repeats help less each time, long
                              documents don't win just for being long.  .explain() shows each word's contribution
    DenseIndex                meaning search (S24's bge-small vectors, cached per corpus)
    rrf()                     Reciprocal Rank Fusion: merge RANKINGS, not scores.   score = sum(1 / (60 + rank))
    weighted()                the other way: min-max each list's scores to 0..1, then alpha*dense + (1-alpha)*keyword
    Reranker                  a cross-encoder that reads question + passage TOGETHER and scores the pair (slow, accurate)
    Retriever                 one corpus, all methods: keyword / dense / hybrid / weighted / rerank
    evaluate()                hit@3 and MRR for any method, split into "exact" and "meaning" questions
    qdrant_hybrid_*           the same hybrid search done INSIDE Qdrant: a sparse BM25 vector + a dense vector, fused by RRF

ShopAssist Pro uses exactly this pattern (app/rag/index.py): BM25 + Qdrant vectors, RRF, and a relevance gate.
"""
from __future__ import annotations

import json
import re
import time
import zlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import s24_utils as S24

HERE = Path(__file__).resolve().parent
PRODUCTS_FILE = HERE / "products.json"
CACHE_DIR = HERE / ".s27_cache"
CORPORA = ("help", "products")

RRF_K = 60                          # the constant from the original RRF paper; 60 works well almost everywhere
RERANK_MODELS = {
    "minilm": "Xenova/ms-marco-MiniLM-L-6-v2",         # ~80 MB, CPU, trained on Bing search questions -> passages
    "minilm-12": "Xenova/ms-marco-MiniLM-L-12-v2",     # a bit better, twice as slow
}
DEFAULT_RERANKER = "minilm"
RERANK_MIN = 0.0                    # MiniLM scores are raw logits: above 0 ~ "relevant", far below 0 ~ "unrelated"


# ------------------------------------------------------------------------------------------------- the documents
def product_chunk(p: dict) -> S24.Chunk:
    """A product becomes one Chunk: doc_id = its SKU, so search results are scored exactly like help articles."""
    sizes = f" Sizes: {', '.join(p['sizes'])}." if p["sizes"] else ""
    text = (f"{p['sku']}. {p['description']}{sizes} Colours: {', '.join(p['colors'])}. Price Rs {p['price']}. "
            f"Rating {p['rating']}.")
    return S24.Chunk(p["sku"], p["name"], p["category"].replace("_", " "), text)


def load_corpus(name: str = "help") -> list[S24.Chunk]:
    if name == "help":
        return S24.load_chunks()
    if name == "products":
        return [product_chunk(p) for p in json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))["products"]]
    raise ValueError(f"unknown corpus {name!r}; choose one of {CORPORA}")


def keys_for(chunks: list[S24.Chunk]) -> list[str]:
    """A unique id per chunk ('refunds#31', 'SKU-EL-004#0'). Fusion works on ids, so both lists talk about the same rows."""
    return [f"{c.doc_id}#{i}" for i, c in enumerate(chunks)]


# ----------------------------------------------------------------------------------------------- keyword: BM25
STOP = S24.STOP | set("i'm im any have has got get please want need much many there some".split())
CODE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)+")          # sku-fw-001, ord-10231: keep the whole code as ONE token too
WORD = re.compile(r"[a-z0-9]+")


def stem(w: str) -> str:
    """A deliberately tiny stemmer: shoes -> shoe, batteries -> battery. Real systems use Snowball/Porter."""
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def tokenize(text: str) -> list[str]:
    low = text.lower()
    codes = [c for c in CODE.findall(low) if any(ch.isdigit() for ch in c)]      # codes only, not "no-cost"
    return [stem(w) for w in WORD.findall(low) if w not in STOP] + codes


class BM25:
    """Okapi BM25 via rank_bm25. k1 = how fast repeats stop helping (1.5); b = how much long documents are penalised (0.75)."""

    def __init__(self, texts: list[str], k1: float = 1.5, b: float = 0.75):
        from rank_bm25 import BM25Okapi
        self.docs = [tokenize(t) for t in texts]
        self.bm25 = BM25Okapi(self.docs, k1=k1, b=b)

    def scores(self, question: str) -> np.ndarray:
        return np.asarray(self.bm25.get_scores(tokenize(question)), dtype=np.float64)

    def explain(self, question: str, i: int) -> list[tuple[str, float, int, float]]:
        """(word, idf, times in this doc, contribution) for every question word - where a BM25 score comes from."""
        m, rows = self.bm25, []
        dl = m.doc_len[i]
        for w in dict.fromkeys(tokenize(question)):
            tf = m.doc_freqs[i].get(w, 0)
            idf = m.idf.get(w, 0.0)
            part = idf * tf * (m.k1 + 1) / (tf + m.k1 * (1 - m.b + m.b * dl / m.avgdl)) if tf else 0.0
            rows.append((w, float(idf), tf, float(part)))
        return rows


# ------------------------------------------------------------------------------------------- meaning: vectors
class DenseIndex:
    """S24's semantic search, with the vectors cached per corpus and model in module04/.s27_cache/."""

    def __init__(self, embedder: S24.Embedder, chunks: list[S24.Chunk], corpus: str):
        self.embedder, self.chunks = embedder, chunks
        texts = [c.search_text for c in chunks]
        cache = CACHE_DIR / f"{corpus}-{embedder.name}.json"
        if cache.exists() and json.loads(cache.read_text(encoding="utf-8")).get("texts") == texts:
            self.vectors = np.array(json.loads(cache.read_text(encoding="utf-8"))["vectors"], dtype=np.float32)
        else:
            self.vectors = embedder.embed(texts)
            CACHE_DIR.mkdir(exist_ok=True)
            cache.write_text(json.dumps({"texts": texts, "vectors": self.vectors.tolist()}), encoding="utf-8")

    def scores(self, question: str) -> np.ndarray:
        return self.vectors @ self.embedder.embed([question], kind="query")[0]


# --------------------------------------------------------------------------------------------------- fusion
def ranking(keys: list[str], scores: np.ndarray, n: int, positive_only: bool = False) -> list[str]:
    """The top n ids by score. For BM25 a 0 means 'no shared word at all' - such rows are not in the keyword list."""
    order = [int(i) for i in np.argsort(-scores, kind="stable")[:n]]
    return [keys[i] for i in order if not positive_only or scores[i] > 0]


def rrf(rankings: list[list[str]], k: int = RRF_K) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion. Each list gives a row 1/(k + rank), ranks start at 1; a row missing from a list gets
    nothing from it. Ranks, not scores - BM25 (0..20+) and cosine (0..1) live on different scales."""
    total: dict[str, float] = {}
    for ranked in rankings:
        for r, key in enumerate(ranked, start=1):
            total[key] = total.get(key, 0.0) + 1.0 / (k + r)
    return sorted(total.items(), key=lambda kv: -kv[1])


def minmax(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    lo, hi = min(scores.values()), max(scores.values())
    return {k: (1.0 if hi == lo else (v - lo) / (hi - lo)) for k, v in scores.items()}


def weighted(keyword: dict[str, float], dense: dict[str, float], alpha: float = 0.5) -> list[tuple[str, float]]:
    """Score fusion, Weaviate-style: alpha = 1 -> pure vectors, alpha = 0 -> pure keywords."""
    kw, dn = minmax(keyword), minmax(dense)
    keys = list(dict.fromkeys([*dn, *kw]))
    fused = {key: alpha * dn.get(key, 0.0) + (1 - alpha) * kw.get(key, 0.0) for key in keys}
    return sorted(fused.items(), key=lambda kv: -kv[1])


# ------------------------------------------------------------------------------------------------- reranking
class Reranker:
    """A cross-encoder: question and passage go into the model TOGETHER, it outputs one relevance score.

    A bi-encoder (our embedder) encodes them apart, so documents can be embedded once, in advance - fast, but it never
    'sees' the question next to the passage. A cross-encoder must run once per (question, passage) pair at question
    time - too slow for 1 million documents, perfect for the top 20.
    """

    def __init__(self, name: str = DEFAULT_RERANKER):
        if name not in RERANK_MODELS:
            raise ValueError(f"unknown reranker {name!r}; choose one of {', '.join(RERANK_MODELS)}")
        self.name, self.model_id, self._model = name, RERANK_MODELS[name], None

    def _load(self):
        if self._model is None:
            try:
                from fastembed.rerank.cross_encoder import TextCrossEncoder
            except ImportError as e:
                raise RuntimeError(f"fastembed could not be imported ({type(e).__name__}: {e}) - see S24's common "
                                   "errors (uv sync, or the Visual C++ Redistributable on Windows)") from e
            try:
                self._model = TextCrossEncoder(self.model_id)   # first time: downloads ~80 MB
            except Exception as e:
                raise RuntimeError(f"Could not download {self.model_id}. You need internet the FIRST time (home Wi-Fi "
                                   "or a hotspot); after that it runs offline. Pre-work: s27_demo.py download") from e
        return self._model

    def score(self, question: str, passages: list[str]) -> list[float]:
        return [float(s) for s in self._load().rerank(question, passages)]


# -------------------------------------------------------------------------------------------------- retriever
@dataclass
class Hit:
    score: float
    chunk: S24.Chunk
    key: str


class Retriever:
    """One corpus, every method. Each method returns [Hit, ...] best first."""

    def __init__(self, corpus: str = "help", embedder: S24.Embedder | None = None, reranker: Reranker | None = None,
                 chunks: list[S24.Chunk] | None = None):
        self.corpus = corpus
        self.chunks = chunks if chunks is not None else load_corpus(corpus)
        self.keys = keys_for(self.chunks)
        self.by_key = dict(zip(self.keys, self.chunks))
        self.bm25 = BM25([c.search_text for c in self.chunks])
        self.dense_index = DenseIndex(embedder or S24.Embedder(), self.chunks, corpus)
        self.reranker = reranker

    def _hits(self, pairs) -> list[Hit]:
        return [Hit(float(s), self.by_key[k], k) for k, s in pairs]

    def keyword_ranking(self, question: str, n: int = 20) -> list[str]:
        return ranking(self.keys, self.bm25.scores(question), n, positive_only=True)

    def dense_ranking(self, question: str, n: int = 20) -> list[str]:
        return ranking(self.keys, self.dense_index.scores(question), n)

    def keyword(self, question: str, k: int = 3) -> list[Hit]:
        s = self.bm25.scores(question)
        return self._hits((key, s[self.keys.index(key)]) for key in self.keyword_ranking(question, k))

    def dense(self, question: str, k: int = 3) -> list[Hit]:
        s = self.dense_index.scores(question)
        return self._hits((key, s[self.keys.index(key)]) for key in self.dense_ranking(question, k))

    def hybrid(self, question: str, k: int = 3, n: int = 20, fuse=rrf) -> list[Hit]:
        """Both searches take their top n; RRF merges the two rankings; keep the top k."""
        return self._hits(fuse([self.keyword_ranking(question, n), self.dense_ranking(question, n)])[:k])

    def weighted(self, question: str, k: int = 3, alpha: float = 0.5, fuse=weighted) -> list[Hit]:
        kw, dn = self.bm25.scores(question), self.dense_index.scores(question)
        return self._hits(fuse(dict(zip(self.keys, map(float, kw))), dict(zip(self.keys, map(float, dn))), alpha)[:k])

    def rerank(self, question: str, k: int = 3, n: int = 20) -> list[Hit]:
        """Stage 1: hybrid top n (cheap, wide).  Stage 2: the cross-encoder re-reads those n, keep its top k."""
        if self.reranker is None:
            self.reranker = Reranker()
        cands = self.hybrid(question, k=n, n=n)
        scores = self.reranker.score(question, [h.chunk.search_text for h in cands])
        order = sorted(range(len(cands)), key=lambda i: -scores[i])[:k]
        return [Hit(scores[i], cands[i].chunk, cands[i].key) for i in order]

    def search(self, method: str, question: str, k: int = 3) -> list[Hit]:
        return getattr(self, method)(question, k=k)


METHODS = ("keyword", "dense", "hybrid", "rerank")


# ------------------------------------------------------------------------------------------------- measuring
def evaluate(retrievers: dict[str, Retriever], cases, method: str, k: int = 3) -> dict:
    """cases = [(question, corpus, expected doc_id, kind), ...]  kind = "exact" (codes, names, numbers) or "meaning"."""
    rows, t0 = [], time.perf_counter()
    for question, corpus, expected, kind in cases:
        found = [h.chunk.doc_id for h in retrievers[corpus].search(method, question, k)]
        rank = found.index(expected) + 1 if expected in found else None
        rows.append({"question": question, "corpus": corpus, "expected": expected, "kind": kind, "found": found,
                     "rank": rank})
    ms = (time.perf_counter() - t0) * 1000 / max(len(cases), 1)

    def part(rs):
        n = len(rs) or 1
        return {"hits": sum(r["rank"] is not None for r in rs), "n": len(rs),
                "mrr": sum(1 / r["rank"] for r in rs if r["rank"]) / n}

    return {"method": method, "all": part(rows), "exact": part([r for r in rows if r["kind"] == "exact"]),
            "meaning": part([r for r in rows if r["kind"] == "meaning"]), "ms": ms, "rows": rows}


# ------------------------------------------------------------------------------------ hybrid INSIDE Qdrant
def sparse_bm25(tokens: list[str], avgdl: float, k1: float = 1.5, b: float = 0.75) -> tuple[list[int], list[float]]:
    """A document as a SPARSE vector: one slot per word (slot = a stable hash of the word), value = BM25's term-frequency
    part. Qdrant multiplies by IDF itself (modifier=IDF), so query vectors just put 1.0 on each question word."""
    tf, dl = Counter(tokens), len(tokens)
    idx = {zlib.crc32(w.encode()) & 0x7FFFFFFF: w for w in tf}
    return list(idx), [t * (k1 + 1) / (t + k1 * (1 - b + b * dl / avgdl)) for t in (tf[w] for w in idx.values())]


def sparse_query(question: str) -> tuple[list[int], list[float]]:
    slots = sorted({zlib.crc32(w.encode()) & 0x7FFFFFFF for w in tokenize(question)})
    return slots, [1.0] * len(slots)


def qdrant_hybrid_load(client, r: Retriever, name: str | None = None) -> str:
    from qdrant_client import models
    name = name or f"s27_{r.corpus}"
    if client.collection_exists(name):
        client.delete_collection(name)
    client.create_collection(
        name, vectors_config={"dense": models.VectorParams(size=r.dense_index.vectors.shape[1],
                                                           distance=models.Distance.COSINE)},
        sparse_vectors_config={"bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)})
    docs = [tokenize(c.search_text) for c in r.chunks]
    avgdl = sum(map(len, docs)) / len(docs)
    points = []
    for i, (c, toks) in enumerate(zip(r.chunks, docs)):
        ind, val = sparse_bm25(toks, avgdl)
        points.append(models.PointStruct(
            id=i, vector={"dense": r.dense_index.vectors[i].tolist(), "bm25": models.SparseVector(indices=ind, values=val)},
            payload={"key": r.keys[i], "doc_id": c.doc_id, "source": c.source}))
    client.upsert(name, points=points, wait=True)
    return name


def qdrant_hybrid_search(client, r: Retriever, question: str, k: int = 3, n: int = 20, name: str | None = None):
    """One call: Qdrant runs the sparse search and the dense search (prefetch), then fuses them with RRF itself."""
    from qdrant_client import models
    ind, val = sparse_query(question)
    qv = r.dense_index.embedder.embed([question], kind="query")[0].tolist()
    res = client.query_points(
        name or f"s27_{r.corpus}",
        prefetch=[models.Prefetch(query=models.SparseVector(indices=ind, values=val), using="bm25", limit=n),
                  models.Prefetch(query=qv, using="dense", limit=n)],
        query=models.FusionQuery(fusion=models.Fusion.RRF), limit=k, with_payload=True)
    return [(p.score, p.payload) for p in res.points]

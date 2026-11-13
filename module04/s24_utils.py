"""Session 24 helpers - embeddings and semantic search over the Northwind help centre.

Everything a live demo or the homework needs, in one small file you can read top to bottom:

    load_chunks()        the 14 help-centre articles, one chunk per "## " section (53 chunks)
    keyword_search()     the OLD way: count shared words. Shows why keyword search misses paraphrases
    Embedder             turns text into vectors. Default: BAAI/bge-small-en-v1.5 on your CPU via fastembed
                         (no API key, no cost; downloads ~67 MB once). Also: all-MiniLM-L6-v2, or Ollama nomic-embed-text
    cosine()             how alike two vectors point: 1.0 = same direction, 0 = unrelated
    semantic_search()    embed every chunk once, embed the question, rank by cosine
    evaluate()           hit@3 and MRR over a list of (question, expected article) pairs

The store data is fictional (Northwind Store, the same one as Mini-Project 1 and ShopAssist Pro).
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
KB_DIR = HERE / "help_centre"
CACHE_DIR = HERE / ".s24_cache"            # vectors of the 53 chunks, per model - so a second run is instant

MODELS = {
    # short name : (where it runs, the model id, dimensions)
    "bge-small": ("fastembed", "BAAI/bge-small-en-v1.5", 384),
    "minilm": ("fastembed", "sentence-transformers/all-MiniLM-L6-v2", 384),
    "nomic": ("ollama", "nomic-embed-text", 768),
}
DEFAULT_MODEL = "bge-small"
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)


# ---------------------------------------------------------------------------------------------------- the documents
@dataclass(frozen=True)
class Chunk:
    doc_id: str        # "warranty"            - the article
    title: str         # "Warranty"
    heading: str       # "Warranty periods"    - the section
    text: str          # the section body

    @property
    def source(self) -> str:
        """What a citation would say: Article > Section."""
        return f"{self.title} > {self.heading}"

    @property
    def search_text(self) -> str:
        """What gets embedded. The title and heading carry a lot of meaning in short sections."""
        return f"{self.title}. {self.heading}. {self.text}"


def split_sections(raw: str, doc_id: str) -> list[Chunk]:
    """One markdown article -> one Chunk per '## ' section. Front matter (--- id/title ---) gives the title."""
    meta: dict[str, str] = {}
    m = FRONTMATTER.match(raw.replace("\r\n", "\n"))
    body = raw.replace("\r\n", "\n")
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip()
        body = body[m.end():]
    title = meta.get("title", doc_id)
    chunks = []
    for section in re.split(r"^## ", body, flags=re.M)[1:]:
        heading, _, text = section.partition("\n")
        text = " ".join(text.split())
        if text:
            chunks.append(Chunk(meta.get("id", doc_id), title, heading.strip(), text))
    return chunks


def load_chunks(kb_dir: Path = KB_DIR) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(kb_dir.glob("*.md")):
        chunks += split_sections(path.read_text(encoding="utf-8"), path.stem)
    return chunks


# ---------------------------------------------------------------------------------------------- keyword search (old)
WORD = re.compile(r"[a-z0-9]+")
STOP = set("a an and are as at be but by can do does for from how i if in is it its me my of on or our so that the "
           "this to was we what when where which who will with you your".split())


def words(text: str) -> set[str]:
    return {w for w in WORD.findall(text.lower()) if w not in STOP}


def keyword_search(question: str, chunks: list[Chunk], k: int = 3) -> list[tuple[float, Chunk]]:
    """Score = how many of the question's words appear in the chunk. No meaning, just spelling."""
    q = words(question)
    scored = [(float(len(q & words(c.search_text))), c) for c in chunks]
    scored.sort(key=lambda sc: -sc[0])
    return [sc for sc in scored[:k] if sc[0] > 0]


# ---------------------------------------------------------------------------------------------------- embeddings
class Embedder:
    """Text in, vectors out. Same model for documents AND questions - always."""

    def __init__(self, name: str = DEFAULT_MODEL):
        if name not in MODELS:
            raise ValueError(f"unknown model {name!r}; choose one of {', '.join(MODELS)}")
        self.name = name
        self.runtime, self.model_id, self.dims = MODELS[name]
        self._model = None

    def _load(self):
        if self._model is None and self.runtime == "fastembed":
            try:
                from fastembed import TextEmbedding
            except ImportError as e:                             # missing package OR a dependency that won't load
                raise RuntimeError(f"fastembed could not be imported ({type(e).__name__}: {e}).\n"
                                   "  - 'No module named fastembed': run  uv sync  from the course repo folder\n"
                                   "  - 'DLL load failed' (onnxruntime, Windows): install the Microsoft Visual C++ "
                                   "Redistributable (x64) from https://aka.ms/vs/17/release/vc_redist.x64.exe, "
                                   "restart the terminal, try again") from e
            try:
                self._model = TextEmbedding(self.model_id)       # first time: downloads the model (~67-90 MB)
            except Exception as e:                               # no internet, proxy, firewall
                raise RuntimeError(
                    f"Could not download {self.model_id}. You need internet the FIRST time (home Wi-Fi or a hotspot "
                    "works; some office networks block it). After that it runs offline.") from e
        return self._model

    def embed(self, texts: list[str], kind: str = "passage") -> np.ndarray:
        """One row per text, each scaled to length 1 (so cosine = dot product).

        kind="passage" for documents, kind="query" for questions. Retrieval models are trained with a small hint that
        says which is which (bge adds an instruction to queries; nomic wants "search_query: "). Same model either way.
        """
        if self.runtime == "fastembed":
            model = self._load()
            gen = model.query_embed(texts) if kind == "query" else model.passage_embed(texts)
            vecs = np.array(list(gen), dtype=np.float32)
        else:
            prefix = "search_query: " if kind == "query" else "search_document: "
            vecs = self._ollama([prefix + t for t in texts])
        return normalise(vecs)

    def _ollama(self, texts: list[str]) -> np.ndarray:
        import httpx
        try:
            r = httpx.post("http://localhost:11434/api/embed", json={"model": self.model_id, "input": texts}, timeout=120)
            r.raise_for_status()
        except Exception as e:
            raise RuntimeError("Ollama isn't reachable. Start Ollama, then run:  ollama pull nomic-embed-text") from e
        return np.array(r.json()["embeddings"], dtype=np.float32)


def normalise(vecs: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vecs, axis=-1, keepdims=True)
    return vecs / np.where(norms == 0, 1, norms)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """cos(angle) = (a . b) / (|a| |b|).  1 = same direction, 0 = unrelated, -1 = opposite."""
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(a @ b / denom) if denom else 0.0


# --------------------------------------------------------------------------------------------- semantic search
class Index:
    """The 'offline' half: every chunk embedded once and kept in memory (S25 moves this into a vector database)."""

    def __init__(self, embedder: Embedder, chunks: list[Chunk] | None = None):
        self.embedder = embedder
        self.chunks = chunks or load_chunks()
        self.vectors, self.seconds = self._vectors()

    def _vectors(self) -> tuple[np.ndarray, float]:
        texts = [c.search_text for c in self.chunks]
        cache = CACHE_DIR / f"{self.embedder.name}.json"
        if cache.exists():
            data = json.loads(cache.read_text(encoding="utf-8"))
            if data.get("texts") == texts:
                return np.array(data["vectors"], dtype=np.float32), 0.0
        t0 = time.perf_counter()
        vecs = self.embedder.embed(texts)
        took = time.perf_counter() - t0
        CACHE_DIR.mkdir(exist_ok=True)
        cache.write_text(json.dumps({"model": self.embedder.model_id, "texts": texts, "vectors": vecs.tolist()}),
                         encoding="utf-8")
        return vecs, took

    def search(self, question: str, k: int = 3) -> list[tuple[float, Chunk]]:
        """The 'online' half: embed the question, compare with every chunk, return the top k."""
        q = self.embedder.embed([question], kind="query")[0]
        scores = self.vectors @ q                                # rows are length 1, so dot product = cosine
        order = np.argsort(-scores)[:k]
        return [(float(scores[i]), self.chunks[i]) for i in order]


def semantic_search(question: str, model: str = DEFAULT_MODEL, k: int = 3) -> list[tuple[float, Chunk]]:
    return Index(Embedder(model)).search(question, k)


# ------------------------------------------------------------------------------------------------- measuring it
def evaluate(search, cases: list[tuple[str, str]], k: int = 3) -> dict:
    """search(question, k) -> [(score, Chunk), ...].  hit@k: right article in the top k.  MRR: 1/rank of the first hit."""
    rows, hits, rr = [], 0, []
    for question, expected in cases:
        found = [c.doc_id for _, c in search(question, k)]
        rank = found.index(expected) + 1 if expected in found else None
        hits += rank is not None
        rr.append(1 / rank if rank else 0.0)
        rows.append({"question": question, "expected": expected, "found": found, "rank": rank})
    n = len(cases) or 1
    return {"hits": hits, "n": len(cases), "hit_at_k": hits / n, "mrr": sum(rr) / n, "rows": rows}

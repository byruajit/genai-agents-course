"""Session 9b helpers — tokens, cost, embeddings. Imported by the notebook and the test."""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import tiktoken
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ---------------------------------------------------------------- tokenizer
# gpt-oss models use the o200k_harmony encoding; tiktoken ships it. For other
# models (e.g. llama3.2 on Ollama) this is an estimate — the model's own usage
# field is the truth after you send.
ENCODING = "o200k_harmony"


def count_tokens(text: str, encoding: str = ENCODING) -> int:
    enc = tiktoken.get_encoding(encoding)
    return len(enc.encode(text))


def show_tokens(text: str, encoding: str = ENCODING) -> list[str]:
    """The text split into the pieces the model sees."""
    enc = tiktoken.get_encoding(encoding)
    return [enc.decode([t]) for t in enc.encode(text)]


# ---------------------------------------------------------------- cost
# Indicative price cards, USD per 1M tokens (edit these — prices change).
PRICE_CARDS = {
    "groq gpt-oss-20b": {"input": 0.10, "output": 0.50},
    "frontier small":   {"input": 0.15, "output": 0.60},
    "frontier large":   {"input": 2.50, "output": 10.00},
}
USD_TO_INR = 84.0


def cost_inr(prompt_tokens: int, completion_tokens: int, card: str, calls: int = 1) -> float:
    p = PRICE_CARDS[card]
    usd = (prompt_tokens * p["input"] + completion_tokens * p["output"]) / 1_000_000
    return round(usd * USD_TO_INR * calls, 4)


# ---------------------------------------------------------------- clients
def chat_client() -> OpenAI:
    """The provider in .env (Groq by default)."""
    return OpenAI(base_url=os.getenv("BASE_URL"), api_key=os.getenv("API_KEY"))


def ollama_client() -> OpenAI:
    """Local Ollama — a provider is just a base URL."""
    return OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")


def usage_for(client: OpenAI, model: str, text: str) -> tuple[int, int]:
    """Send text; return (prompt_tokens, completion_tokens) as the model counted them."""
    r = client.chat.completions.create(model=model, max_tokens=16, messages=[{"role": "user", "content": text}])
    return r.usage.prompt_tokens, r.usage.completion_tokens


# ---------------------------------------------------------------- embeddings
WORDS = ["loan", "EMI", "interest", "credit score", "bank", "hospital", "doctor", "prescription", "cricket", "monsoon"]
CACHE = Path(__file__).with_name("embeddings_10words.json")


def embed_via_ollama(words: list[str], model: str = "nomic-embed-text") -> np.ndarray:
    r = ollama_client().embeddings.create(model=model, input=words)
    return np.array([d.embedding for d in r.data], dtype=float)


def pca_2d(x: np.ndarray) -> np.ndarray:
    """Project N×D vectors to N×2 with plain NumPy (centre, SVD, keep two directions)."""
    xc = x - x.mean(axis=0)
    _, _, vt = np.linalg.svd(xc, full_matrices=False)
    return xc @ vt[:2].T


def load_points(words: list[str] = WORDS) -> tuple[np.ndarray, str]:
    """2-D points for the words: Ollama first, cached JSON second. Returns (points, source)."""
    try:
        vecs = embed_via_ollama(words)
        return pca_2d(vecs), "ollama:nomic-embed-text"
    except Exception:
        if CACHE.exists():
            data = json.loads(CACHE.read_text())
            vecs = np.array([data[w] for w in words], dtype=float)
            return pca_2d(vecs), "cache:embeddings_10words.json"
        raise RuntimeError(
            "No embedding source. Either run `ollama pull nomic-embed-text` and start Ollama, "
            "or ask the instructor for module01/embeddings_10words.json."
        )


def write_cache(words: list[str] = WORDS) -> Path:
    """Instructor: run once with Ollama up to create the fallback file."""
    vecs = embed_via_ollama(words)
    CACHE.write_text(json.dumps({w: v.tolist() for w, v in zip(words, vecs)}))
    return CACHE

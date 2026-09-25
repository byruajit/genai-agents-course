"""Instructor only. With Ollama running and nomic-embed-text pulled:  uv run python module01/make_embeddings_cache.py"""
from tokens_utils import write_cache  # noqa: E402

if __name__ == "__main__":
    print("wrote", write_cache())

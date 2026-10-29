"""Session 20, instructor pre-class run: score the golden set four ways on one model and print the tables.

    uv run python module03/s20_golden_run.py                         # whatever .env says
    uv run python module03/s20_golden_run.py --ollama llama3.2:3b    # local Ollama model, ignores .env

Answers are cached in ~/.genai_course/s20_cache.json (re-running is free and gives the same numbers).
A JSON copy of every answer is written next to the cache, for the deck's model-comparison slide."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "module02"))
sys.path.insert(0, str(HERE))

from dotenv import load_dotenv  # noqa: E402
from openai import OpenAI  # noqa: E402
from reasoning_utils import DiskCache  # noqa: E402
from tool_utils import S20_CACHE, compare_fixes, fixes_table, question_grid  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ollama", metavar="MODEL", help="use a local Ollama model, e.g. llama3.2:3b")
    a = p.parse_args()
    load_dotenv(override=True)
    if a.ollama:
        base_url, api_key, model = "http://localhost:11434/v1", "ollama", a.ollama
    else:
        base_url, api_key, model = os.environ["BASE_URL"], os.environ["API_KEY"], os.environ["MODEL"]
    client = OpenAI(base_url=base_url, api_key=api_key)
    print(f"model: {model}   endpoint: {base_url}")
    print("running 10 golden questions x 4 ways (first run can take a few minutes on a laptop)...\n")
    results = compare_fixes(client, model, cache=DiskCache(S20_CACHE))
    print(fixes_table(results))
    print()
    print(question_grid(results))
    out = S20_CACHE.parent / f"s20_golden_{model.replace('/', '_').replace(':', '_')}.json"
    out.write_text(json.dumps({"model": model, "results": results}, indent=1, default=str), encoding="utf-8")
    print(f"\nfull answers saved to {out}")


if __name__ == "__main__":
    main()

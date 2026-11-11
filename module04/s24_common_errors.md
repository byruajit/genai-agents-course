# Session 24 - common errors and fixes

| You see | Why | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'fastembed'` | You didn't sync after `git pull` | `uv sync` in the course repo folder |
| `Could not download BAAI/bge-small-en-v1.5` | First run needs internet; some office/college networks block model downloads | Use home Wi-Fi or a phone hotspot once. After that it runs offline |
| Very slow first command (20-60 s) | Downloading the model, then embedding 53 sections | Normal, once. The vectors are cached in `module04/.s24_cache/` |
| `ModuleNotFoundError: No module named 's24_utils'` when running `search.py` | You ran it from inside your work repo | Run it **from the course repo folder**: `uv run python "<your work repo>\s24\search.py"` |
| `WORK_REPO is not set` (setup or checker) | No `WORK_REPO=` line in the course `.env` | Add `WORK_REPO=<your work repo path>` to the course repo's `.env` (same as S23) |
| `TODO 1 cosine(...) returned ... expected 1.0000` | Forgot to divide by both lengths, or returned a numpy value | `float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))`, and handle a zero length |
| `TODO 2 top_k(...) returned [2, 1]` | Sorted worst first | Sort by score **descending**: `sorted(..., key=lambda i: -scores[i])` |
| `TODO 3 ... found 54 sections` (or 52) | Kept an empty section, or didn't skip text before the first `##` | Skip sections whose text is empty; ignore everything before the first `## ` line |
| `TODO 4 article 'warrantee' doesn't exist` | Typo in the article name | Use a file name from `module04/help_centre/` without `.md` |
| `results.md not found` | You haven't run your finished file yet | `uv run python "<your work repo>\s24\search.py"` |
| Meaning search scores below the pass mark | Usually a bug in `top_k` (wrong order) or `split_sections` (merged sections) | Run the `Check:` line from each TODO's docstring in the notebook |
| `nomic`: `Ollama isn't reachable` | Optional model, needs Ollama | Start Ollama and `ollama pull nomic-embed-text`, or skip it |
| `source code string cannot contain null bytes` | Damaged `.venv` (often OneDrive) | `uv sync --reinstall`; keep repos out of OneDrive |

Using ChatGPT? Paste the TODO's docstring, never your `.env`, and make sure you can explain the answer line by line.

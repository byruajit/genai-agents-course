# Session 27 - common errors and fixes

| You see | Why | Fix |
|---|---|---|
| `No module named 'rank_bm25'` | Didn't sync after `git pull` | `uv sync` in the course repo folder |
| `Could not download Xenova/ms-marco-MiniLM-L-6-v2` | First run of the reranker needs internet (~80 MB) | Home Wi-Fi or a hotspot: `uv run python module04/s27_demo.py download` - after that it runs offline |
| `fastembed is not installed` or `fastembed could not be imported` | Old copy of the code, or onnxruntime can't load its DLL on Windows | `git pull` then `uv sync`; `DLL load failed`: install the Microsoft Visual C++ Redistributable x64 (https://aka.ms/vs/17/release/vc_redist.x64.exe), reopen the terminal |
| `No module named 's27_utils'` | Ran `hybrid.py` from your work repo | Run it from the COURSE repo folder: `uv run python "<work repo>\s27\hybrid.py"` |
| `keyword` prints "(nothing - no shared words)" | BM25 only scores documents that share a word with the question | That's the point of the demo - meaning questions need vectors |
| The first `compare` takes a minute | Both corpora are embedded once, then cached in `module04/.s27_cache/` | Wait once; delete that folder to rebuild |
| `qdrant` is slow or says local | The S26 Qdrant server isn't running | `docker compose -f module04/s26_docker-compose.yml up -d`, or use `--qdrant local` |
| `Storage folder ... is already accessed by another instance` | Notebook and a terminal both opened in-process Qdrant | Close one, or start the Docker server |
| Checker: `TODO 1 ... expected ids a, c, b, d` | Added scores instead of `1/(k + rank)`, or ranks started at 0 | `enumerate(ranked, start=1)` and `1.0 / (k + rank)` |
| Checker: `TODO 2 when all scores in a dict are equal` | Division by zero in min-max | If highest == lowest, every id gets 1.0 |
| Checker: `TODO 3 call score_fn ONCE` | Called the reranker in a loop, one passage at a time | Build the list of texts first, one call |
| Checker: `TODO 4 ... has no rare word` | Your question is a meaning question, not an exact one | Use a code, name or number that appears in the answer (a SKU, `1.5L`, `Visa`) |
| Checker: `TODO 4 ... is not a doc_id` | Typo in the SKU or article name | SKUs are in `module04/products.json`; article names are the file names in `module04/help_centre/` |

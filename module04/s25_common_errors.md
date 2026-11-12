# Session 25 - common errors and fixes

| You see | Why | Fix |
|---|---|---|
| `No module named 'chromadb'` | You didn't sync after `git pull` | `uv sync` in the course repo folder |
| `The collection doesn't exist yet` | You ran `search` before `load` | `uv run python module04/s25_demo.py load` |
| `Could not download BAAI/bge-small-en-v1.5` | First time the model is used on this laptop | Home Wi-Fi or a hotspot once (see S24) |
| `No module named 's24_utils'` / `'s25_utils'` running `store.py` | Ran from your work repo | Run from the **course repo folder**: `uv run python "<your work repo>\s25\store.py"` |
| `TODO 1 ... 'updated' must be an int` | Returned `"2026-03-02"` | Convert: `"2026-03-02"` → `20260302` (`int(s.replace("-", ""))` or via `date.fromisoformat`) |
| `TODO 2 build_where(...)` wrong | Used `$or`, put `since` first, or returned `{}` instead of `None` | Category part first, `{"$and": [...]}` only when both, `None` when neither |
| `TODO 3 recall_at_k ... expected 0.5` | Divided by the wrong count, or returned an int | Per question: overlap / k; then the average; return a float |
| `results.md shows ... DON'T match the filter` | Metadata keys or date format don't match what the filter compares | `make_metadata` must use exactly `doc_id`, `category`, `updated` (int) |
| `InvalidArgumentError: Expected a name containing 3-512 characters` | Chroma collection names need 3+ characters | Use a longer name |
| The recall run takes a minute | Building three HNSW indexes over 20,000 vectors | Normal; close other heavy apps |
| Filtered search returns fewer than 3 rows | Only that many rows match the filter (e.g. Size guide has 2 sections) | Correct behaviour - filters are rules |
| `.s25_chroma` folder appeared | That's the database on disk | Leave it; it's gitignored. Delete it to start fresh |

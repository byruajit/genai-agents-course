# Session 26 - common errors and fixes

| You see | Why | Fix |
|---|---|---|
| `No module named 'qdrant_client'` / `'psycopg'` | Didn't sync after `git pull` | `uv sync` |
| `error during connect` / `Cannot connect to the Docker daemon` | Docker Desktop isn't running | Start it, wait for "Engine running" |
| `pull access denied` or very slow pull in class | Images weren't pulled at home | `docker compose -f module04/s26_docker-compose.yml pull` on good Wi-Fi; meanwhile use in-process Qdrant (`--qdrant local`) |
| `Bind for 0.0.0.0:6333 failed: port is already allocated` | ShopAssist Pro (or another Qdrant) is running | `docker compose down` in that project's folder, then start S26's |
| `Bind for 0.0.0.0:5433 failed` | Something already uses 5433 | Change `"5433:5432"` to `"5434:5432"` in the compose file and set `PG_DSN=postgresql://course:course@localhost:5434/vectors` in `.env` |
| `Can't reach PostgreSQL` right after `up -d` | Postgres takes ~10 s to start | `docker compose -f module04/s26_docker-compose.yml ps` until it says `healthy` |
| `password authentication failed for user "course"` | An old volume from a different password | `docker compose -f module04/s26_docker-compose.yml down -v` (deletes the lab data), then `up -d` |
| `Storage folder ... is already accessed by another instance of Qdrant client` | Two programs opened the in-process Qdrant at once (e.g. the notebook and `migrate.py`) | Restart the notebook kernel, or start the Docker server so both use it |
| `Payload indexes have no effect in the local Qdrant` | In-process mode | Fine - indexes and quantisation need the server (Docker or Cloud) |
| Qdrant rejects the point: `... is not a valid point ID` | Used the Chroma id directly | `id=S26.point_id(chroma_id)` - Qdrant ids are numbers or UUIDs |
| `expected 384 dimensions, not ...` (pgvector) | Vector size doesn't match the column | Use the bge-small vectors (384) from S24/S25 |
| `Set QDRANT_CLOUD_URL and QDRANT_CLOUD_API_KEY` | Optional cloud step without settings | Add both to the course `.env` - never commit them |
| `TODO 3 tenant_filter('CUST-1001') let these customers through` | Filter on the wrong key, or `MatchExcept` | `FieldCondition(key="customer_id", match=MatchValue(value=customer_id))` |
| `TODO 4 ... Pinecone is a managed cloud service` | Hospital data must stay on premises | Choose a self-hostable store and say why |

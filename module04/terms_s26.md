# Session 26 terms - production vector stores

| Term | What it is | Say it as | Comes back at |
|---|---|---|---|
| **Client-server** | Your code (client) talks to a database running as its own process (server) over a network port - many apps can share it. | "A restaurant kitchen, not your own stove." | Module 12 (cloud deployment) |
| **Qdrant** | Open-source database built only for vectors (written in Rust). Self-host in Docker, run in-process, or use Qdrant Cloud. ShopAssist Pro uses it. | "A dedicated vector engine." | S27, ShopAssist Pro |
| **Point / payload** | Qdrant's words for a row and its metadata. | "Row and labels." | S27 |
| **pgvector** | A PostgreSQL extension: a `vector(384)` column type, distance operators and HNSW/IVF indexes - vectors next to your normal tables, queried in SQL. | "Postgres learns vectors." | S31 (Text-to-SQL), capstone |
| **Extension** | An add-on installed into PostgreSQL with `CREATE EXTENSION`. | "A plug-in for the database." | - |
| **`<=>`, `<->`, `<#>`** | pgvector operators: cosine distance, Euclidean distance, negative inner product. `ORDER BY embedding <=> query LIMIT 3`. | "Distance in SQL." | - |
| **Pinecone** | A fully managed vector database service: no servers to run; you pay for usage. | "Vector DB as a service." | S58-S60 (cloud) |
| **Weaviate** | Open-source vector database with built-in modules (hybrid search, vectorisers); self-host or cloud. | "Batteries included." | S27 (hybrid) |
| **Managed vs self-hosted** | Someone else runs and upgrades the servers vs your team does. Trade: convenience and speed vs control, cost at scale and data location. | "Rent vs own." | Module 12 |
| **Migration** | Move data between stores: read id + vector + payload, write them, verify. No re-embedding if the model is unchanged. | "Moving house, not rebuilding it." | S29 |
| **overlap@k** | Share of the top k that two systems agree on - the proof a migration kept the results. | "Same answers after the move?" | S27, S32 |
| **UUID** | A 128-bit unique id. Qdrant ids must be numbers or UUIDs, so `refunds#31` becomes a stable uuid5 and the original id goes in the payload. | "A unique serial number." | - |
| **Multi-tenancy** | Many customers' data in one system, each seeing only their own: a filter on an indexed tenant field, a collection per tenant, or a database per tenant. | "One building, many locked flats." | S47 (MCP security), S55-S56 |
| **Tenant id from auth** | The filter value comes from the verified login token, never from the user's message. | "The key card, not what you say at the door." | ShopAssist Pro Gap 1 |
| **Payload index** | Qdrant's index on a payload field so filters are fast - like a SQL index on a WHERE column. | "An index for the labels." | S27 |
| **Quantisation** | Store each number in fewer bits: int8 (4x smaller), binary (32x). Results are usually re-scored with the original vectors. | "Compressing the map." | S58-S60 (cost) |
| **Snapshot / replica / shard** | Backup copy / a copy serving reads / a slice of the data on another machine. | "Backup / mirror / split." | Module 12 |
| **Free tier limits** | Qdrant Cloud free: 1 GB RAM, suspended after a week unused, deleted after 4 weeks. Pinecone Starter: ~2 GB, one US region. Weaviate Cloud: a free cluster for learning. | "Free, with conditions." | - |

## One sentence per idea
- A production vector database is a server many apps share; ChromaDB is a library inside one program.
- pgvector puts vectors inside PostgreSQL, so search is SQL; Qdrant is purpose-built; Pinecone runs everything for you.
- Migration = read rows, write rows, prove the top-k results match (overlap@k), then switch.
- Multi-tenancy is a filter inside the query whose value comes from the login - never filter afterwards in app code.

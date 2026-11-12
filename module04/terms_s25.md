# Session 25 terms - vector databases

| Term | What it is | Say it as | Comes back at |
|---|---|---|---|
| **Vector database** | A database built to store vectors with their metadata and find the nearest ones fast. Today: ChromaDB (a library, files on disk). | "A library with a catalogue." | S26 (Qdrant, pgvector, Pinecone, Weaviate), all of RAG |
| **Collection** | One named set of rows inside the database - like a table. Ours: `help_centre`. | "One shelf." | S26 |
| **Row / record / point** | One stored item: id + vector + metadata + the original text. (Qdrant calls it a *point* and metadata a *payload*.) | "A library card." | S26 |
| **Metadata / payload** | Labels stored next to the vector: category, date, customer, language, access level. | "Genre and year on the card." | S26 (multi-tenancy), S30 (routing) |
| **Filter (`where`)** | Search only rows whose metadata matches. `{"category": "payments"}`, `{"updated": {"$gte": 20260601}}`, combined with `$and`. | "Only cookery books after 2020." | S26, S31, ShopAssist Pro Gap 1 |
| **Persistence** | The data stays on disk after the program stops. | "It's still there tomorrow." | S26 |
| **CRUD / upsert** | Create, read, update, delete. Upsert = update if the id exists, insert if not. Change one article, re-embed one row. | "Replace one card." | S29 (ingestion pipelines) |
| **Brute force / exact / flat search** | Compare the question with every vector. Always right; time and memory grow linearly with the data. | "Reading every book." | Today's baseline |
| **Index** | A data structure that lets search skip most vectors. | "The catalogue." | S26 |
| **ANN (approximate nearest neighbour)** | Search through an index: much faster, may miss a few true neighbours. | "Ask the librarian." | S26-S27 |
| **HNSW** | Hierarchical Navigable Small World - a layered graph: sparse "highway" layers on top, dense "local road" layers below; search zooms down. The default in Chroma, Qdrant, pgvector, Weaviate. | "Expressway → main road → lane." | S26 |
| **IVF** | Inverted File index: cluster vectors into neighbourhoods, search only the nearest few (`nprobe`). Cheaper in memory; often paired with quantisation. | "Search only the nearest districts." | S26 |
| **ef_search** | HNSW: how many candidates to examine per query. Higher = more accurate, slower. | "How many shops you check." | S26 tuning |
| **M / max_neighbors** | HNSW: links per node. Higher = more accurate, more memory, slower build. | "Roads per junction." | S26 |
| **ef_construction** | HNSW: how hard to work while building the graph. Higher = better graph, slower build. | "How carefully the roads are laid." | S26 |
| **recall@k** | Share of the TRUE top k (from brute force) that the index returned. 1.0 = missed nothing. | "Did the librarian miss any?" | S26, S27, S32 |
| **Cosine distance** | 1 - cosine similarity. What Chroma returns; smaller = closer. | "Distance, not similarity." | S26 |
| **Quantisation** | Storing vectors with fewer bits (e.g. 8-bit or 1-bit) to save memory, at a small accuracy cost. | "Compressing the map." | S26 |

## One sentence per idea
- A vector database stores vectors with metadata on disk and finds the nearest ones without checking every vector.
- "Approximate" means you trade a little recall for a lot of speed - and you measure that trade with recall@k.
- Filters are rules, not hints: use them for relevance (category, date) and for security (whose data).
- Update one document by re-embedding and upserting one row; changing the embedding MODEL means re-indexing everything.

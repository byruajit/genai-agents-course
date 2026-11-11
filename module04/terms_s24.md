# Session 24 terms - embeddings: searching by meaning

Read this before the notebook. Each term: what it is, how to say it out loud, and where it comes back.

| Term | What it is | Say it as | Comes back at |
|---|---|---|---|
| **Embedding** | A list of numbers (a vector) that represents the *meaning* of a piece of text. Texts that mean similar things get similar lists. | "GPS coordinates for meaning." | S25-S27, all of Module 5 (RAG), agent memory (S38) |
| **Embedding model** | A model that turns text into an embedding. It doesn't chat or write - it only maps text to numbers. Today: `BAAI/bge-small-en-v1.5`, run on your CPU with `fastembed`. | "A translator into number language." | S25-S27, RAG |
| **Vector** | An ordered list of numbers, e.g. 384 of them. Can be drawn as an arrow from the origin. | "An arrow in a space with many directions." | S25 (vector databases) |
| **Dimensions** | How many numbers are in each vector: 384 for bge-small and MiniLM, 768 for nomic-embed-text, 1536-3072 for large hosted models. More dimensions = finer meaning, more storage, slower search. | "How detailed the map is." | S25 (storage and index size), S26 (choosing a store) |
| **Dense vector** | A vector where every number is used (no zeros). Captures meaning. What embedding models produce. | "A fingerprint." | S27 (hybrid search) |
| **Sparse vector** | Mostly zeros, with one slot per word in the vocabulary. Captures exact words, not meaning. Keyword search and BM25 work this way. | "A word checklist." | S27 (BM25 + dense = hybrid) |
| **Cosine similarity** | How much two vectors point in the same direction: `(a . b) / (|a| x |b|)`. 1 = same direction, 0 = unrelated, -1 = opposite. Length doesn't matter. | "The angle between two arrows." | S25 (distance metrics), S27, RAG thresholds |
| **Normalising** | Scaling a vector to length 1. Then cosine is just the dot product - cheaper to compute. | "Making every arrow the same length." | S25 |
| **Chunk** | The piece of a document that gets embedded and returned. Today: one `##` section of a help-centre article (53 chunks from 14 articles). | "One FAQ answer." | S28-S29 (chunking strategies) |
| **Semantic search** | Embed the question, compare it with every chunk's embedding, return the most similar. Finds paraphrases that share no words. | "Search by meaning." | S25-S28 |
| **Keyword search** | Find chunks that contain the question's words. Fast and exact, but blind to synonyms ("smashed" vs "damaged"). | "Ctrl+F with a score." | S27 (BM25) |
| **Top-k** | The k best results. We use k = 3. | "The first page of results." | S25, RAG |
| **Offline / online** | Offline: embed all documents once and store the vectors. Online: embed each question and compare. Only the online half runs per question. | "Indexing vs searching." | S25 (the vector database IS the offline half) |
| **Query vs passage** | Retrieval models embed questions and documents slightly differently (bge adds an instruction to queries; nomic uses `search_query:` / `search_document:`). Same model, two modes. | "Asking vs answering." | S26-S27 |
| **hit@k** | Share of test questions with the right document in the top k. Today: hit@3 on 10 questions, pass mark 8. | "Was it on the first page?" | S26-S27, S32 (RAG evaluation) |
| **MRR (mean reciprocal rank)** | Average of 1/rank of the first correct result: 1.0 if always first, 0.5 if usually second, 0 if never found. | "How high up was it?" | S27, S32 |
| **Golden set** | A fixed list of questions with known right answers, run after every change (MP1 had one too). | "The exam with an answer key." | S32, Module 10 |
| **MTEB** | The Massive Text Embedding Benchmark - a public leaderboard of embedding models. A starting point, not a decision: always test on your own questions. | "The model league table." | S26 |
| **Relevance threshold** | A minimum similarity score below which a result is thrown away, because search always returns *something*. | "No answer is better than a wrong answer." | S28-S31 (RAG), ShopAssist Pro's `RAG_MIN_DENSE` |

## One sentence per term, if you only have thirty seconds
- An embedding turns text into a list of numbers so that similar meanings land close together.
- Cosine similarity measures the angle between two vectors: same direction = same meaning.
- Embed the documents once (offline), embed each question (online), and return the closest chunks.
- Documents and questions must go through the **same** model - change the model, re-embed everything.
- Search always returns the nearest thing, even when nothing is relevant - that's why we measure it and add a threshold.

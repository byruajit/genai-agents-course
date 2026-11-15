# Session 27 terms - hybrid search and reranking

| Term | What it is | Say it as | Comes back at |
|---|---|---|---|
| **Hybrid search** | Run keyword search AND vector search for the same question, then merge the two result lists. Catches exact words and paraphrases. | "Two detectives, one report." | S28 (Gate 1), all of Module 5, ShopAssist Pro |
| **Exact-term question** | A question whose key word is a code, name or number: `SKU-EL-004`, `WELCOME10`, `HDFC`, `26cm`. Vectors often miss these. | "Words that have spelling, not meaning." | S29-S32 (RAG eval sets) |
| **BM25** | The standard keyword-scoring formula (Elasticsearch, OpenSearch, Lucene). Adds a share per question word: rare words count more, repeats help less each time, long documents are scaled down. | "Ctrl+F with a score." | S28, S29, ShopAssist Pro (`rank_bm25`) |
| **Tokenisation** | Turning text into the words search compares: lower case, drop stop words, trim plurals, keep codes whole. Decides what can ever match. | "Cutting text into search pieces." | S29 (chunking), S33 |
| **Stop words** | Very common words (the, is, my) removed before keyword search because they say nothing. | "Filler words." | S29 |
| **Stemming** | Cutting words to a base form so `shoes` matches `shoe`. Real systems use Porter/Snowball; we use a tiny version. | "Same root, same word." | S29 |
| **IDF (inverse document frequency)** | How rare a word is across all documents. Appears in 1 of 53 sections -> high; in all of them -> near zero. | "Rare is informative." | S28 |
| **k1, b** | BM25's two knobs: k1 = how fast repeats stop helping (1.5); b = how much long documents are penalised (0.75). | "Saturation and length." | Interviews |
| **Sparse vector** | One slot per word, almost all zeros. BM25 is a sparse vector; Qdrant can store one next to the dense vector. | "A word checklist." | S28, Qdrant hybrid |
| **Fusion** | Merging several ranked lists into one. | "Combining two shortlists." | S28, S31 |
| **RRF (Reciprocal Rank Fusion)** | Each list gives a row `1/(60 + rank)`; add them up. Uses ranks, not scores, so BM25 (0-20+) and cosine (0-1) can be combined. Default in Qdrant, Elasticsearch, OpenSearch, Azure AI Search. | "Points for placing in each race." | S28, ShopAssist Pro |
| **Weighted (score) fusion, alpha** | Min-max each list's scores to 0..1, then `alpha x vector + (1 - alpha) x keyword`. alpha 1 = vectors only. Weaviate's `hybrid(alpha=...)`. | "A volume slider between the two." | S28 |
| **Min-max normalisation** | `(score - lowest) / (highest - lowest)`: squeezes scores into 0..1. Sensitive to one outlier. | "Rescale to a 0-1 ruler." | S32 (eval scores) |
| **Bi-encoder** | Embeds question and document separately (our embedder). Documents can be embedded in advance: fast, but never sees the pair together. | "Two strangers described separately." | S28, S38 (memory) |
| **Cross-encoder / reranker** | Reads question + passage together and outputs one relevance score. Accurate, slow: runs once per pair at question time. Today: `ms-marco-MiniLM-L-6-v2` (~80 MB). | "An interviewer reading both CVs side by side." | S28, S31, S32 |
| **Two-stage retrieval** | Stage 1 cheap and wide (hybrid, top 20); stage 2 slow and precise (rerank, top 3). | "Shortlist, then interview." | All of Module 5 |
| **Logit** | A reranker's raw score: above 0 ~ relevant, far below 0 ~ unrelated. Not a probability. | "A raw confidence number." | S32 (judges) |
| **Relevance gate** | A threshold below which retrieval returns nothing, so the LLM can say "I don't know" instead of answering from a wrong passage. | "No passage beats a wrong passage." | S30 (grounding), S32, ShopAssist Pro |
| **hit@3, MRR (recap)** | Right document in the top 3; average of 1/rank of the first right one. Rerankers mostly raise MRR. | "On the first page? How high?" | S32 |
| **Prefetch (Qdrant)** | Sub-queries run inside one `query_points` call (sparse + dense), whose results are then fused on the server. | "Two searches, one round trip." | Capstone |

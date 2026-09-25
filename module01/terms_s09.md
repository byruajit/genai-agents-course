# Terms from Session 9b — what they are, and where they come back

| Term | What it is | Say it as | Comes back at |
|---|---|---|---|
| Provider | Where the model runs: a cloud service (Groq) or your own machine (Ollama). Identified by `BASE_URL`. | A place. | S10, S12, Module 12 |
| Model | The trained weights that answer. Identified by `MODEL`. | A brain. | Every session |
| Token | The unit the model reads — a piece of text from a fixed dictionary; ~¾ of an English word. | Not a word, a dictionary entry. | Every cost line; S19; S34; S38 |
| Tokenizer | The dictionary that cuts text into tokens. Belongs to the model. | Different model, different cuts. | S19, S38 |
| Encoding (`o200k_harmony`) | The name of one tokenizer dictionary; `tiktoken` ships it. | The dictionary's name. | S19, S38 |
| `usage` | The field returned after every call: `prompt_tokens`, `completion_tokens`, `total_tokens`. | The truth after you send. | Every lab; S53; S54 |
| Context window | The maximum tokens a model can see at once; everything must fit. | A budget. | S19; S30; S34; S38 |
| Embedding | A vector of numbers standing for a text's meaning. | Meaning as coordinates. | Module 4; Module 5; S39 |
| Vector | A list of numbers treated as a point or direction; "close" = pointing the same way. | A point on a map. | S24; Modules 4–5 |
| Embedding model | A model whose output is a vector, not text. Never answers. | Text in, numbers out. | S24; Module 5 |
| PCA | Squashing many dimensions to two so humans can look. Pictures only. | For the picture, not the search. | S24 |
| Next-token prediction | How answers are produced: score every possible next token, pick one, repeat. | One token at a time. | S11; S15 |
| Attention | How the model weighs which earlier tokens matter for the next one. | Looking back over the context. | Intuition only |
| Temperature | How much randomness in each pick; 0 = the most likely token every time. | The randomness dial. | S11; S34 |
| Reasoning model | A model that spends hidden tokens thinking before the visible answer. | Thinks first; costs more. | S15; S37 |
| Pre-training | Learning to predict the next token from a huge corpus → a base model. | Reading the internet. | S10; S12 |
| Fine-tuning (instruction tuning) | Further training on instruction/answer pairs → a chat model. | Learning to follow instructions. | S54 |
| Preference tuning (RLHF) | Nudging toward human-preferred answers. | Learning manners. | S15; S57 |
| Base model vs chat model | Pre-trained only vs fine-tuned to follow instructions. You call chat models. | Raw vs trained to talk. | S10; S12 |
| Hugging Face | The public hub where open-weight models, datasets and tokenizers are published. Ollama and Groq run models from it. | Where open models come from. | S12; S24 |
| Open-weight vs frontier | Downloadable weights (Llama, Qwen, gpt-oss) vs vendor-API-only (GPT, Claude, Gemini). | Can you run it yourself? | S10; S12; S57 |

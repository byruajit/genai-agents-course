# Session 22 terms - LiteLLM: one call format, many models, fallbacks and cost

Read this before the notebook. Each term: what it is, how to say it out loud, and where it comes back.

| Term | What it is | Say it as | Comes back at |
|---|---|---|---|
| **Provider** | A company or server that runs models behind an API: Groq, OpenAI, Anthropic, Google, your own Ollama. Each has its own SDK, key and quirks. | "The kitchen that cooks the answer." | Every session; Module 13 (cloud) |
| **LiteLLM** | An open-source library that gives **one call format** (`completion(...)`) for 100+ providers, plus routing, fallbacks and cost tracking. | "A universal power adapter." | MP1, Module 6, Module 13 |
| **Model string** | `provider/model`, e.g. `groq/openai/gpt-oss-20b`, `ollama_chat/llama3.2:3b`. Changing the string changes the provider; the code stays the same. | "The address of the model." | MP1, Module 13 |
| **`completion()`** | LiteLLM's one function to call any chat model. Returns an OpenAI-shaped response: `choices[0].message.content`, `usage`. | "Same question, any kitchen." | MP1 |
| **Router** | A LiteLLM object that knows several deployments by **model group names** you choose (`bankassist`, `bankassist-backup`) and decides which one to call. | "The switchboard." | MP1, Module 13 |
| **Model group** | A name your app asks for instead of a provider, e.g. `bankassist`. Lets you swap the real model without changing app code. | "Ask for the role, not the person." | MP1 |
| **Fallback** | If the primary fails (error, timeout, rate limit), the Router tries the backup group. The customer still gets an answer. | "The spare tyre." | MP1, Module 6, Module 13 |
| **Retry** | Trying the **same** model again after a brief wait (`num_retries`), before falling back. Good for short blips, bad for a dead model. | "Knock again before going next door." | Module 6 |
| **Timeout** | The longest you wait for a provider (`timeout=30`). A hung call is treated as a failure, so the fallback can start. | "The kitchen gets 30 seconds." | S23, MP1 |
| **Rate limit (429)** | The provider refusing because you sent too many requests or tokens. Free tiers hit this often. | "Too many orders at once." | S23, MP1 |
| **Token cost** | `prompt_tokens × input price + completion_tokens × output price`. LiteLLM ships a price list; local models cost $0 per token (you pay for the hardware). | "The bill for one answer." | MP1, Module 10 |
| **LLM gateway / LiteLLM proxy** | LiteLLM run as a **server**: one OpenAI-compatible URL for the whole company, with per-team keys, budgets, logging and fallbacks in one place. | "One front door to every model." | Hard-rung demo today; Module 13 |
| **Vendor lock-in** | Being stuck with one provider because your code depends on its SDK. A one-call-format layer reduces it. | "Not marrying the first kitchen." | Module 13 |

## One sentence per term, if you only have thirty seconds
- LiteLLM gives one `completion()` call for many providers; the model string picks the provider.
- A Router asks for a group name and falls back to a backup group when the primary fails.
- Retries knock again; fallbacks go next door; a timeout decides when to stop waiting.
- Cost = tokens × price; log it per request, with the model that **really** answered.
- A gateway (proxy) puts all of this in one place for the whole company.

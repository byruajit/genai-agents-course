# S22 version card — paste this into ChatGPT (or any AI assistant) BEFORE you ask for help

LiteLLM changes fast, and ChatGPT often mixes old and new LiteLLM code, or invents Router settings. Copy the
box below as your first message, then ask your question underneath it.

```text
I am a student working in Python 3.12 with these exact versions:
  litellm==1.80.0, openai 1.x, python-dotenv. (Also langchain==1.4.7 / langchain-openai==1.1.9 from last session.)

Use ONLY these imports and APIs:
  from litellm import completion, Router, cost_per_token
  response = completion(model="groq/openai/gpt-oss-20b", messages=[...], api_key=..., temperature=0, max_tokens=1500)
  response.choices[0].message.content ; response.usage.prompt_tokens / completion_tokens / total_tokens
  router = Router(model_list=[{"model_name": "bankassist", "litellm_params": {...}},
                              {"model_name": "bankassist-backup", "litellm_params": {...}}],
                  fallbacks=[{"bankassist": ["bankassist-backup"]}], num_retries=1, timeout=30)
  response = router.completion(model="bankassist", messages=[...])
  cost_in, cost_out = cost_per_token(model="groq/openai/gpt-oss-20b", prompt_tokens=..., completion_tokens=...)
Model strings are "provider/model": groq/..., ollama_chat/...

Do NOT use: litellm.acompletion or async code, the LiteLLM proxy server, callbacks, Langfuse,
litellm.set_verbose, budget managers, or environment variables I have not set. Do not change params(),
messages_for(), answered_by() or fallbacks_used() - they are given.

Explain what each line does. Do not rewrite my whole file - show only the lines I need to change.

My question:
```

## Three rules for today
1. **Never paste your `.env` file or your API key** into any chat.
2. **Ask it to explain or fix *your* code**, not to write the whole file. You explain your code at the exit check.
3. **If its answer uses something on the "do not use" list, it ignored the card.** Paste the card again.

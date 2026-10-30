# Session 21 terms - LangChain, your first build

Read this before the notebook. Each term: what it is, how to say it out loud, and where it comes back.

| Term | What it is | Say it as | Comes back at |
|---|---|---|---|
| **Framework** | A library that writes the repeated parts of your code for you. LangChain writes S20's schema, parsing and id-matching; you still decide what the app does. | "An automatic gearbox: same engine, fewer things to do by hand." | Every session from here |
| **LangChain** | A family of packages: `langchain-core` (messages, prompts, tools, the pipe), `langchain-openai` (talks to any OpenAI-compatible API - Groq and Ollama included), `langchain` (higher-level pieces such as prebuilt agents). | "Core is the toolbox; the integration packages are the plugs." | S22, Module 5 (retrievers), Module 6 |
| **Chat model (`ChatOpenAI`)** | One object that replaces `OpenAI(...)` + `chat.completions.create(...)`. `.invoke(...)` returns an `AIMessage`. | "The model, as a Python object." | All later sessions |
| **Message classes** | `SystemMessage`, `HumanMessage`, `AIMessage`, `ToolMessage` - S19's list of dicts, with types. The list is still resent every call, so cost still grows. | "S19's list, wearing name badges." | S22, S23, Module 6 |
| **Prompt template** | A prompt with blanks, e.g. `{question}`, filled at run time. | "A form letter." | Module 5 (RAG prompts) |
| **LCEL / the pipe `\|`** | LangChain Expression Language: `prompt \| llm \| parser` - the output of the left becomes the input of the right. | "An assembly line." | Module 5 (RAG chains), S23 (streaming) |
| **Output parser** | Turns the model's message into what you want - `StrOutputParser` gives plain text. | "Unwrapping the parcel." | Module 5 |
| **`@tool` decorator** | Turns a normal Python function into a tool. Type hints become the schema's types; the docstring becomes its description. `parse_docstring=True` puts each argument's description in the schema. | "The docstring is now your prompt." | S22, Module 6, Module 8 (MCP) |
| **`bind_tools`** | Attaches tools to the model once, instead of passing `tools=` on every call. | "Handing the clerk the calculator." | Module 6 |
| **`tool_calls` (LangChain)** | A list of dicts on the `AIMessage`: `name`, `args` (already a dict - no `json.loads`), `id`. | "The request, already unpacked." | Module 6 |
| **Version pinning** | Fixing exact package versions (`langchain==1.4.7`) so code written today still runs next month. LangChain changes its APIs often. | "Freeze the recipe." | S22, Module 13 (deployment) |
| **Version card** | A short block you paste into ChatGPT first, listing the exact versions and allowed APIs, so it doesn't write outdated code. | "Telling the helper which edition of the textbook you have." | Every build session |

## One sentence per term, if you only have thirty seconds
- A framework writes the repeated parts; you still own the decisions and the loop.
- The pipe `|` connects prompt, model and parser into a chain.
- With `@tool`, the docstring is your prompt and the type hints are your schema.
- `tool_calls` arrive as dicts with ids, and `tool.invoke(call)` returns the matching `ToolMessage`.
- Pin versions, and give ChatGPT the version card.

# Session 20 terms - function calling

Read this before the notebook. Each term: what it is, how to say it out loud, and where it comes back.

| Term | What it is | Say it as | Comes back at |
|---|---|---|---|
| **Function calling / tool use** | The model replies with a structured request (a function name and JSON arguments) instead of prose. Your code decides whether to run it, runs it, and sends the result back. The model never executes anything itself. | "The banker asks; the clerk runs the calculator." | S21-22 (LangChain `@tool`, `bind_tools`), Module 6 (agents), Module 8 (MCP) |
| **Tool schema** | One function described in JSON Schema: `name`, `description`, typed `parameters`, `required`. The description is a prompt: it's the only thing the model reads to decide *when* to call. Types and `required` are requests, not rules. | "The tool's job description." | Module 8 (MCP standardises it) |
| **Round trip** | Send messages + tools → model returns `tool_calls` → your code runs them → append the assistant message (with `tool_calls`) and one `tool` message per call → call the model again → it answers. Two model calls for one answer. | "Ask, run, hand back, answer." | S21, S23, Module 6 |
| **`tool_calls` / `tool_call_id`** | `tool_calls` is the list of requests in the model's reply, each with an `id`, `name`, and an `arguments` **string**. Your `tool` message must carry `tool_call_id` equal to that `id`. | "A ticket number: the answer carries the same number as the request." | S21, Module 6 |
| **`tool_choice`** | How much freedom the model has: `auto` (it decides), `none`, `required`, or one named function. | "Who decides whether the calculator comes out." | S21, Module 6 |
| **Over-calling** | Calling a tool the question didn't need. Small models are known for it. Recorded on llama3.2:3b: an EMI tool call for "what are your branch timings?". | "Reaching for the calculator to answer 'what time do you open?'" | Module 6 evals |
| **Argument hallucination** | Invented or mistyped arguments: zeros because nothing fits, `"0"` strings where numbers belong, a fraction (0.085) where a percent (8.5) belongs, values the customer never gave. | "A form filled in by someone guessing." | Module 6, Module 12 |
| **Argument validation** | Checking types, ranges and required fields in code *before* the function runs, and sending any error back to the model as the tool result so it can recover. | "Check the form before you process it." | Module 6, Module 12 (tool permissions) |
| **Bounded loop (max_steps)** | The round trip repeated until the model answers in prose or a step cap (3 today) is hit. A loop with no cap is an agent. | "A loop with a safety brake." | Module 6 (the ReAct loop) |
| **Router** | A cheap first call that decides the path - here TOOL or NO_TOOL - before the main call. A model with no tools attached cannot over-call. Its own failure: a wrong route. | "Triage at the entrance." | Module 6 multi-agent |
| **FOIR** | Fixed Obligations to Income Ratio: all EMIs ÷ monthly income. Northwind's simplified rule is ≤ 50%; real lenders use 40-60% depending on income and product. | "How much of your pay already goes to EMIs." | BFS showcase agents |

## One sentence per term, if you only have thirty seconds
- The model asks; your code acts.
- The description decides *when*; the schema only *requests* the types.
- Every tool request and result joins the messages list, with matching ids.
- Small models over-call and invent arguments, so validate in code and cap the loop.
- A router stops over-calling but can itself be wrong, so score it too.

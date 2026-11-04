# S23 version card — paste this into ChatGPT (or any AI assistant) BEFORE you ask for help

Without it, ChatGPT tends to write Flask code, old `@app.on_event` startup hooks, `async` code mixed with blocking
calls, or a different streaming library (`sse-starlette`) that isn't installed. Copy the box, paste it first, then
ask your question underneath.

```text
I am a student working in Python 3.12 with these exact versions:
  fastapi==0.162.0, uvicorn==0.54.0, pydantic 2.x, langchain-core 1.7.x, langchain-openai==1.1.9, httpx.

My app is ONE file. Use ONLY these APIs:
  from fastapi import FastAPI
  from fastapi.responses import StreamingResponse
  from pydantic import BaseModel, Field
  app = FastAPI()
  @app.get("/health") / @app.post("/chat") / @app.delete("/sessions/{session_id}")  on plain `def` functions
  class ChatRequest(BaseModel): session_id: str; message: str = Field(min_length=1, max_length=2000)
  StreamingResponse(generator(), media_type="text/event-stream")   # I format each SSE event myself:
      f"event: {name}\ndata: {json.dumps(data)}\n\n"
  uvicorn.run(app, host="127.0.0.1", port=8000)
  Memory is a dict: SESSIONS[session_id] -> list of LangChain messages (HumanMessage, AIMessage).

Do NOT use: Flask, async def endpoints, sse-starlette, EventSourceResponse, WebSockets, @app.on_event,
databases, Redis, or LangChain memory classes (ConversationBufferMemory, RunnableWithMessageHistory).
Do not change the GIVEN part of my file (make_llm, the tools, stream_turn, run_turn).

Explain what each line does. Do not rewrite my whole file - show only the lines I need to change.

My question:
```

## Three rules for today
1. **Never paste your `.env` file or your API key** into any chat.
2. **Ask it to explain or fix *your* code**, not to write the whole file. You explain your endpoints at the exit check.
3. **If its answer uses something on the "do not use" list, it ignored the card.** Paste the card again.

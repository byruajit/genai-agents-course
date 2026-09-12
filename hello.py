"""Session 2 — your first LLM call. Run with:  uv run python hello.py"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url=os.getenv("BASE_URL"), api_key=os.getenv("API_KEY"))
MODEL = os.getenv("MODEL")

stream = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": "You are a concise assistant for a retail bank."},
        {"role": "user", "content": "Say hello and tell me one thing AI agents can do."},
    ],
    stream=True,
    stream_options={"include_usage": True},
)
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
    if chunk.usage:
        u = chunk.usage
        print(f"\n\nprompt={u.prompt_tokens} completion={u.completion_tokens} total={u.total_tokens}")
        break
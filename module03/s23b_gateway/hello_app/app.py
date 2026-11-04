"""A 30-line web app that talks to the LiteLLM PROXY, not to Groq. It knows one URL and one key - nothing else."""
import os

from fastapi import FastAPI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

PROXY_URL = os.getenv("PROXY_URL", "http://localhost:4000")      # in Docker Compose: http://litellm:4000
PROXY_KEY = os.getenv("LITELLM_MASTER_KEY", "sk-class-1234")

llm = ChatOpenAI(model="shopassist", base_url=PROXY_URL, api_key=PROXY_KEY, temperature=0, max_tokens=800)
app = FastAPI(title="hello-gateway")


class Ask(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok", "proxy": PROXY_URL}


@app.post("/ask")
def ask(body: Ask):
    reply = llm.invoke([("system", "You are ShopAssist, a helpful online-store assistant. Answer in 2 sentences."),
                        ("human", body.question)])
    return {"answer": reply.content, "asked_for": "shopassist", "proxy": PROXY_URL}

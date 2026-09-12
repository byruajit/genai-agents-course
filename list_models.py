"""Which models can my key use?  Run:  uv run python list_models.py"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url=os.getenv("BASE_URL"), api_key=os.getenv("API_KEY"))
for m in sorted(x.id for x in client.models.list()):
    print(m)

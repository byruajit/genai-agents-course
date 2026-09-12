"""Session 2 checkpoint. Run with:  uv run pytest tests/test_setup.py"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def test_python_version():
    assert sys.version_info[:2] == (3, 12), "Run commands with `uv run`, never plain `python`."


def test_env_present():
    for key in ("BASE_URL", "API_KEY", "MODEL"):
        assert os.getenv(key), f"{key} missing — did you copy .env.example to .env?"
    assert "paste_your" not in os.getenv("API_KEY"), "API_KEY is still the placeholder."
    assert not os.getenv("API_KEY").startswith(("'", '"')), "No quotes around the key in .env."


def test_model_answers():
    from openai import OpenAI

    client = OpenAI(base_url=os.getenv("BASE_URL"), api_key=os.getenv("API_KEY"))
    r = client.chat.completions.create(
        model=os.getenv("MODEL"),
        max_tokens=64,
        messages=[{"role": "user", "content": "Reply with OK"}],
    )
    assert r.choices[0].message.content

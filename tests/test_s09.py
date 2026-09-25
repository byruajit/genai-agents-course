"""Session 9b checkpoint. Run with:  uv run pytest tests/test_s09.py"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "module01"))
from tokens_utils import (CACHE, PRICE_CARDS, WORDS, chat_client, cost_inr, count_tokens,  # noqa: E402
                          load_points, show_tokens)

ENGLISH = "Can I get a personal loan of 8 lakh rupees for five years?"


def test_count_tokens_is_sensible():
    n = count_tokens(ENGLISH)
    assert 10 <= n <= 25, f"unexpected token count {n}"
    assert "".join(show_tokens(ENGLISH)) == ENGLISH  # pieces reassemble to the text


def test_cost_function():
    # 1,000 tokens in and 1,000 out on the first card, 1 call
    card = next(iter(PRICE_CARDS))
    p = PRICE_CARDS[card]
    expected = round((1000 * p["input"] + 1000 * p["output"]) / 1_000_000 * 84.0, 4)
    assert cost_inr(1000, 1000, card) == expected
    assert cost_inr(1000, 1000, card, calls=1000) == round(expected * 1000, 4)


@pytest.mark.skipif(not os.getenv("API_KEY") or "paste_your" in os.getenv("API_KEY", ""), reason="no API key in .env")
def test_estimate_matches_model_usage():
    """The provider wraps your message in a chat template (~70 tokens for gpt-oss on Groq).
    Measure the wrapper with a tiny message, subtract it, and the estimate should match."""
    client = chat_client(); model = os.getenv("MODEL")
    def usage(text):
        r = client.chat.completions.create(model=model, max_tokens=8, messages=[{"role": "user", "content": text}])
        return r.usage.prompt_tokens
    overhead = usage("hi") - count_tokens("hi")
    estimate = count_tokens(ENGLISH)
    actual = usage(ENGLISH) - overhead
    assert overhead > 0, "expected a chat-template wrapper"
    assert abs(actual - estimate) <= max(3, int(0.10 * estimate)), f"estimate {estimate} vs usage-minus-template {actual} (template {overhead})"


def test_embeddings_give_ten_points():
    try:
        pts, source = load_points()
    except RuntimeError as e:
        pytest.skip(str(e))
    assert pts.shape == (len(WORDS), 2), source

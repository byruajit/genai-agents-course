"""Session 23b checkpoint. Run with:  uv run pytest tests/test_s23b.py -rs

Offline checks read the gateway files and run everywhere. The live check runs only while YOUR gateway is up on
http://localhost:4000 (lab step 2) - otherwise it is skipped with a reason (a skip is not a pass).
"""
import os
from pathlib import Path

import httpx
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "module03" / "s23b_gateway"
GATEWAY = os.getenv("GATEWAY_URL", "http://localhost:4000")
KEY = os.getenv("LITELLM_MASTER_KEY", "sk-class-1234")


def cfg():
    return yaml.safe_load((G / "config.yaml").read_text(encoding="utf-8"))


def compose():
    return yaml.safe_load((G / "docker-compose.yml").read_text(encoding="utf-8"))


def test_config_has_two_model_groups_with_a_fallback():
    c = cfg()
    groups = {m["model_name"]: m["litellm_params"]["model"] for m in c["model_list"]}
    assert set(groups) == {"shopassist", "shopassist-backup"}
    assert all("/" in m for m in groups.values()), "every model needs a provider prefix, e.g. groq/..."
    assert {"shopassist": ["shopassist-backup"]} in c["router_settings"]["fallbacks"]


def test_no_secret_is_written_in_the_config():
    c = cfg()
    for m in c["model_list"]:
        assert str(m["litellm_params"]["api_key"]).startswith("os.environ/"), "keys must come from the environment"
    assert str(c["general_settings"]["master_key"]).startswith("os.environ/")


def test_compose_runs_gateway_and_app_and_the_app_calls_the_service_name():
    s = compose()["services"]
    assert {"litellm", "app"} <= set(s)
    assert s["app"]["environment"]["PROXY_URL"] == "http://litellm:4000", "inside Compose, use the SERVICE NAME"
    assert "4000:4000" in s["litellm"]["ports"] and "8000:8000" in s["app"]["ports"]


def test_images_are_pinned_and_never_copy_a_dotenv():
    proxy = (G / "proxy" / "Dockerfile").read_text(encoding="utf-8")
    app = (G / "hello_app" / "Dockerfile").read_text(encoding="utf-8")
    assert "litellm[proxy]==1.80.0" in proxy
    for d in (proxy, app):
        assert ".env" not in "\n".join(l for l in d.splitlines() if l.strip().upper().startswith("COPY"))
    assert "0.0.0.0" in app, "the app must listen on 0.0.0.0 to be reachable from outside its container"
    for ign in (G / ".dockerignore", G / "hello_app" / ".dockerignore"):
        assert ".env" in ign.read_text(encoding="utf-8")


def test_client_and_app_compile():
    for p in (ROOT / "module03" / "s23b_client.py", G / "hello_app" / "app.py"):
        compile(p.read_text(encoding="utf-8"), str(p), "exec")


def _gateway_up():
    try:
        return httpx.get(f"{GATEWAY}/health/liveliness", timeout=3).status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not _gateway_up(), reason=f"gateway not running at {GATEWAY} - start it (lab step 2), then re-run")
def test_live_gateway_needs_the_key_and_lists_the_model_groups():
    assert httpx.get(f"{GATEWAY}/v1/models", timeout=10).status_code == 401
    r = httpx.get(f"{GATEWAY}/v1/models", headers={"Authorization": f"Bearer {KEY}"}, timeout=10)
    assert r.status_code == 200
    assert {"shopassist", "shopassist-backup"} <= {m["id"] for m in r.json()["data"]}

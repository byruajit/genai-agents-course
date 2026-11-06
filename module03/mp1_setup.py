"""Mini-Project 1 (ShopAssist) - copy the starter into YOUR OWN repository. Run ONCE, from the course repo:

    # 1. on GitHub: create an EMPTY repo called shopassist-mp1, then clone it, e.g. into Documents
    # 2. add ONE line to the course repo's .env (the checkpoint reads it too):
    #        MP1_REPO=C:\\Users\\you\\Documents\\shopassist-mp1
    uv run python module03/mp1_setup.py

What it does:
  - copies module03/mp1_starter into your repo (a file that already exists is never overwritten, except GitHub's
    one-line starter README.md), so it is safe to re-run;
  - writes YOUR repo's .env (git-ignored): your Groq API_KEY copied from the course repo's .env, and a NEW random
    LITELLM_MASTER_KEY - the key your app sends to the gateway.

Then:  cd <your shopassist-mp1 folder> ; git status   (.env must NOT be listed) ; git add . ; git commit -m "MP1: starter" ; git push
"""
import os
import secrets
import shutil
import sys
from pathlib import Path

from dotenv import dotenv_values, find_dotenv, load_dotenv

ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "module03" / "mp1_starter"
SKIP = {"__pycache__", ".venv"}


def make_env(course_env: Path) -> tuple[str, list]:
    """The .env for the student's repo, and any warnings."""
    course = dotenv_values(course_env) if course_env.exists() else {}
    warnings = []
    api_key = course.get("API_KEY") or ""
    base = (course.get("BASE_URL") or "").lower()
    if not api_key or api_key == "ollama" or ("groq" not in base and not api_key.startswith("gsk_")):
        warnings.append("The gateway calls Groq, but your course .env doesn't look like a Groq setup. Open .env in "
                        "your MP1 repo and paste your Groq key after API_KEY= (it starts with gsk_).")
        api_key = api_key if api_key.startswith("gsk_") else "paste_your_groq_key_here"
    lines = [
        f"API_KEY={api_key}",
        f"LITELLM_MASTER_KEY=sk-mp1-{secrets.token_hex(16)}",
        "GATEWAY_URL=http://localhost:4000",
        "MODEL=shopassist",
        "MEMORY=",
        "KEEP_TURNS=",
    ]
    return "\n".join(lines) + "\n", warnings


def main() -> None:
    load_dotenv(find_dotenv(usecwd=True))          # MP1_REPO=... in the course .env works too (shell value wins)
    target = Path(sys.argv[1] if len(sys.argv) > 1 else (os.getenv("MP1_REPO") or "").strip().strip('"'))
    if not str(target) or str(target) == "." or not target.is_dir():
        sys.exit("MP1_REPO is not set (or that folder doesn't exist). Add this line to the course repo's .env:\n"
                 "  MP1_REPO=C:\\Users\\you\\Documents\\shopassist-mp1     (the folder you cloned shopassist-mp1 into)")
    if not (target / ".git").exists():
        sys.exit(f"{target} is not a git repository - create shopassist-mp1 on GitHub and git clone it there first")
    if target.resolve() in (ROOT.resolve(), *ROOT.resolve().parents) or ROOT.resolve() in target.resolve().parents:
        sys.exit("MP1_REPO points at (or inside) the course repository - it must be your own shopassist-mp1 repo")

    copied, kept = [], []
    for src in sorted(STARTER.rglob("*")):
        rel = src.relative_to(STARTER)
        if src.is_dir() or SKIP & set(rel.parts):
            continue
        dst = target / rel
        github_readme = (rel == Path("README.md") and dst.exists()
                         and len(dst.read_text(encoding="utf-8").splitlines()) <= 3)
        if dst.exists() and not github_readme:
            kept.append(str(rel))
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(str(rel))

    warnings = []
    env = target / ".env"
    if not env.exists():
        text, warnings = make_env(ROOT / ".env")
        env.write_text(text, encoding="utf-8")
        copied.append(".env  (your Groq API_KEY + a new random LITELLM_MASTER_KEY - git-ignored, never commit it)")

    print(f"Copied {len(copied)} files into {target}:")
    for c in copied:
        print("  +", c)
    if kept:
        print(f"Kept {len(kept)} existing files (not overwritten):", ", ".join(kept))
    for w in warnings:
        print("\nWARNING:", w)
    print("\nNext:  cd", target, " ;  uv sync  ;  git status  (.env must NOT be listed)  ;  git add .  ;  "
          'git commit -m "MP1: starter"  ;  git push')


if __name__ == "__main__":
    main()

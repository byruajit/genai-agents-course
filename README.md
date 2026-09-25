# GenAI · Agentic AI · AI Agents — course repo

Instructor: **Ajit Byru** · `ajitbyru@gmail.com` · github.com/byruajit

This repository is the single source of truth for the course: every command shown in class is here, character for character. If a slide and this README disagree, the README wins.

**Rule for the whole course: every Python command starts with `uv run`.** Never plain `python`, never `conda`. Have Anaconda? Keep it — it is never used and never touched. See `(base)` in your prompt? Ignore it.

> **Starting at Session 9?** Session 1's Git section is covered by the Git & GitHub webinar — watch it before Session 14. Do only step 8 of Session 1 (clone this repo), then all of Session 2's setup.

---

## Session 1 — Git & GitHub

Two repos live side by side in `Documents`: **genai-course-work** (yours — you push) and **genai-agents-course** (this one — you pull).

| # | Step | Command |
|---|---|---|
| 1 | Install Git and VS Code, then **close and reopen the terminal** (already have them? verify only) | `winget install --id Git.Git -e` · `winget install --id Microsoft.VisualStudioCode -e` · `git --version` · `code --version` |
| 2 | Identity — real name, professional email | `git config --global user.name "Your Name"` · `git config --global user.email "you@example.com"` · `git config --global init.defaultBranch main` · `git config --global core.autocrlf true` (Windows) |
| 3 | Create **your** repo in the browser | github.com → New → `genai-course-work` → Public → tick "Add a README file" → Create |
| 4 | Clone it | `cd ~\Documents` · `git clone https://github.com/<your-username>/genai-course-work.git` · `cd genai-course-work` · `code .` |
| 5 | First commit (edit README.md) | `git status` · `git add README.md` · `git commit -m "Add intro to README"` · `git push` |
| 6 | Second commit (create `notes/session01.md`) | `git add .` · `git commit -m "Session 1 notes"` · `git push` · `git log --oneline` |
| 7 | Branch, change, merge | `git switch -c experiment` · edit · `git add . && git commit -m "Experiment"` · `git switch main` · `git merge experiment` · `git push` · `git branch -d experiment` |
| 8 | Clone this course repo alongside | `cd ~\Documents` · `git clone https://github.com/byruajit/genai-agents-course.git` · `cd genai-agents-course` · `type .gitignore` · `git pull` |
| 9 | **Checkpoint** | Your GitHub page shows ≥ 2 commits and the merge; `git config --global --list` shows your name and email |

Start every session with `git pull` in this repo.

**Secrets:** `.env` is in `.gitignore`, so `git add` ignores it. If a key ever reaches a commit it is public within minutes — revoke it in the Groq console and create a new one.

---

## Session 2 — set up your machine (Windows, PowerShell)

Already have VS Code, Git or Python? Keep them. Skip the matching install line and run the version check only. Everyone runs steps 1, 2 and 5–8.

| # | Step | Command |
|---|---|---|
| 1 | Install uv, then **close and reopen the terminal** (have uv? `uv self update`) | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` then `uv self version` |
| 1b | Only if step 1 still says "not recognized" after reopening | `[Environment]::SetEnvironmentVariable('Path', $env:Path + ';' + $HOME + '\.local\bin', 'User')` → reopen |
| 2 | Python 3.12 via uv (do this even if you have Python; it never touches yours) | `uv python install 3.12` then `uv python list` |
| 3 | Git and VS Code, then reopen the terminal (already installed? verify only) | `winget install --id Git.Git -e` · `winget install --id Microsoft.VisualStudioCode -e` · `git --version` · `code --version` |
| 4 | Clone and open — never in `C:\WINDOWS\system32` | `cd ~\Documents` · `git clone https://github.com/byruajit/genai-agents-course.git` · `cd genai-agents-course` · `code .` |
| 5 | Install pinned packages (VS Code terminal, Ctrl+`) | `uv sync` |
| 6 | Private config — paste **your own** Groq key as `API_KEY` (free: console.groq.com → API Keys → Create); do not touch `MODEL`; no quotes; no trailing space | `copy .env.example .env` (Mac/Linux: `cp .env.example .env`) |
| 7 | First LLM call — read the token count | `uv run python hello.py` |
| 8 | **Checkpoint** | `uv run pytest tests/test_setup.py` → `3 passed` |
| 9 | Background / homework | ollama.com → install → `ollama pull llama3.2:3b` |

### Mac / Linux differences
Step 1: `curl -LsSf https://astral.sh/uv/install.sh | sh` · Step 3: `xcode-select --install` (Mac) or `sudo apt install git` (Ubuntu); VS Code from code.visualstudio.com, then Command Palette → "Shell Command: Install code command in PATH" · Step 6: `cp` not `copy`. Everything else is identical.

### Switching to Ollama (rate limits, or private data)
In `.env`, comment the three Groq lines and uncomment the three Ollama lines. No code changes.

---

## Troubleshooting — the three errors that cover almost everything

**`uv` is not recognized** — you did not reopen the terminal. Close every terminal (including VS Code's) and open again. Still failing → step 1b.

**401 invalid API key** — open `.env` (not `.env.example`). No quotes around the key, no trailing space, not the placeholder. If in doubt, create a new key in the Groq console and paste it again.

**Ollama: model not found / connection refused** — not found → `ollama pull llama3.2:3b`. Connection refused → Ollama is not running: check the tray icon, or run `ollama serve` in a second terminal.

**Model not found (404)** — the pinned model was retired. Run `uv run python list_models.py`, pick a current model, and tell the instructor; do not change `MODEL` on your own.

Also seen: a warning that `UV_NATIVE_TLS` is deprecated — harmless, ignore. `uv version` (no dashes) errors outside a project — use `uv self version`.

---

## Keys
You create your own free Groq key at console.groq.com. It lives in `.env` and nowhere else. If it ever appears in chat, code or a screenshot, revoke it in the console immediately and create a new one.

## Links
- Community channel: _(added by instructor)_
- Submission form: _(added by instructor)_
- Baseline quiz: _(added by instructor)_
- Fix videos: _(coming)_

## Session 9b — tokens, cost, context, embeddings

```powershell
git pull
uv sync                                  # adds jupyter, tiktoken, numpy, matplotlib
ollama pull nomic-embed-text             # 270 MB, for the embeddings section (optional: a cached copy is used if Ollama is absent)
uv run jupyter lab module01/s09_tokens.ipynb
uv run pytest tests/test_s09.py          # checkpoint
```
Pre-read: `module01/reading_tokens.md` (10 minutes). First run of `tiktoken` downloads its encoding file once (needs internet).

## Layout
```
module01/                   Session 9b notebook, helpers, pre-read
hello.py                    Session 2 first call
list_models.py              which models your key can use
tests/test_setup.py         Session 2 checkpoint
tests/test_s09.py           Session 9b checkpoint
cheatsheet/python-for-agents.md
.env.example                copy to .env
pyproject.toml              pinned dependencies (uv sync)
```
Modules are added as the course progresses (`module01/ … module14/`).

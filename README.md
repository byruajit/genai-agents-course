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

Start every session with `git pull` in this repo. If it refuses because you saved a notebook, see [UPDATING.md](UPDATING.md) (or run `uv run python tools/update_course.py`).

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

## Session 9a — your environment and your first LLM call, explained

```powershell
git pull
uv sync
uv run jupyter lab module01/s09a_first_call.ipynb
uv run pytest tests/test_s09a.py         # offline check of the notebook
```
A guided notebook for Session 2's setup and `hello.py`: the two repositories, `uv`, `.env`, and the first call rebuilt cell by cell (whole reply, then streamed, then the token count). Runs without a key: model cells say "skipped".

**All notebooks from Session 9a to 16 now have long explanations** (Part A: why, the words you need, how the session is built; six steps per section; Part C: summary, interview questions, troubleshooting). If `git pull` complains that your local changes would be overwritten, follow [UPDATING.md](UPDATING.md).

## Session 9b — tokens, cost, context, embeddings

```powershell
git pull
uv sync                                  # adds jupyter, tiktoken, numpy, matplotlib
ollama pull nomic-embed-text             # 270 MB, for the embeddings section (optional: a cached copy is used if Ollama is absent)
uv run jupyter lab module01/s09_tokens.ipynb
uv run pytest tests/test_s09.py          # checkpoint
```
Pre-read: `module01/reading_tokens.md` (10 minutes). First run of `tiktoken` downloads its encoding file once (needs internet).

## Session 10 — the model landscape

```powershell
git pull
uv sync
uv run jupyter lab module01/s10_model_matrix.ipynb
uv run pytest tests/test_s10.py          # checkpoint (works offline)
```
Pre-read: `module01/reading_landscape.md` (10 minutes). Terms: `module01/terms_s10.md`. Catalog numbers are **indicative** — verifying two of them is part of the lab. To submit: run the last notebook cell, then upload `module01/s10_matrix_output.md` through the submission form (personal repositories start at Session 14).

## Showcase A2 — Insurance (workflow)

```powershell
uv run python showcase/a2_insurance/insurance_claim.py --all
uv run pytest showcase/a2_insurance/test_a2_insurance.py
```
Free-text claim -> the model extracts a structured form -> code routes by severity -> a template answers.
First showcase in the course's 4x4 matrix (row A: workflow, column: Insurance). See showcase/a2_insurance/README.md.

## Session 11 — multi-provider calls

```powershell
git pull
uv sync
uv run jupyter lab module01/s11_providers.ipynb
uv run pytest tests/test_s11.py          # checkpoint (offline-safe)
```
Pre-read: `module01/reading_providers.md`. You will need a free Gemini key today (aistudio.google.com) in
addition to your existing Groq key — see `.env.example`. Terms: `module01/terms_s11.md`.

## Session 12 — local and open models

```powershell
git pull
uv sync
ollama pull qwen2.5:7b          # a second local model, for comparison (do this at home)
uv run jupyter lab module01/s12_local_models.ipynb
uv run pytest tests/test_s12.py          # checkpoint (offline-safe)
```
Pre-read: `module01/reading_local_models.md`. Terms: `module01/terms_s12.md`.

## Session 13 — images in, structured data out

```powershell
git pull
uv sync                                  # no new packages (Pillow already comes with matplotlib)
uv run jupyter lab module01/s13_vision_structured.ipynb
uv run pytest tests/test_s13.py          # checkpoint (offline-safe)
```
Pre-read: `module01/reading_structured.md`. Terms: `module01/terms_s13.md`. The sample documents are **synthetic**
(`module01/sample_docs/`) — fictional people, fake numbers, a SAMPLE watermark.

## Showcase A3 — Healthcare (workflow)

```powershell
uv run python showcase/a3_healthcare/appointment_flow.py --all
uv run pytest showcase/a3_healthcare/test_a3_healthcare.py
```
Safety rule -> intent router -> slot filling -> booking -> confirmation. The model reads; the code decides.
See `showcase/a3_healthcare/README.md`.

## Session 14 — prompt anatomy (Module 2 begins) and your own work repository

```powershell
git pull
uv sync                                  # no new packages
uv run jupyter lab module02/s14_prompt_anatomy.ipynb
uv run pytest tests/test_s14.py          # checkpoint (offline-safe)
```
Pre-read: `module02/reading_prompt_anatomy.md`. **Before class:** read `module02/work_repo_steps.md` and have your GitHub username ready.
Terms: `module02/terms_s14.md`. Your submission is a pushed `prompts/library.md` in **your own** `genai-course-work` repository, not this one.

## Session 15 — reasoning prompts: when thinking helps, and what it costs

```powershell
git pull
uv sync                                  # no new packages
uv run jupyter lab module02/s15_reasoning.ipynb
uv run pytest tests/test_s15.py          # checkpoint (offline-safe)
```
Pre-read: `module02/reading_reasoning.md` (10 minutes). Terms: `module02/terms_s15.md`. A loan-eligibility checker for ten applicants, asked four ways
(plain, step by step, step back, vote), with tokens, seconds and cost per 1,000 questions. **Budget:** about 40,000-80,000 tokens of a free key's
200,000-a-day limit; answers are remembered on disk (`~/.genai_course/`), so re-running a cell is free. Your submission is `experiments/s15_accuracy_table.md`
and version-2 entries in `prompts/library.md`, both pushed to **your own** `genai-course-work` repository.

## Session 16 — structured prompting: tags, templates, and a system prompt in a file

```powershell
git pull
uv sync                                  # no new packages (Jinja2 already comes with Jupyter)
uv run jupyter lab module02/s16_structured.ipynb
$env:WORK_REPO = "$HOME\Documents\genai-course-work"
uv run pytest tests/test_s16.py -rs      # checkpoint: your classifier needs 16/20 on the held-out set
```
Pre-read: `module02/reading_structured.md` (10 minutes). Terms: `module02/terms_s16.md`. The customer-support classifier (card, loan, account, other): customer text inside
`<ticket>` tags, a Jinja template with variables, and the system prompt as a file loaded at runtime. **Budget:** about 40,000-70,000 tokens of a free key's
200,000-a-day limit; answers are remembered on disk (`~/.genai_course/`), so re-running an unchanged cell is free. Your submission is `prompts/support_classifier/system.md`,
`prompts/support_classifier/user.j2` and `experiments/s16_heldout.md`, pushed to **your own** `genai-course-work` repository. The checkpoint test is skipped without a key
(read the reason with `-rs`: a skip is not a pass) and fails on purpose with a key but no `WORK_REPO`.

## Session 17 — prompt evaluation: a golden set, a rubric, and a judge

```powershell
git pull
uv sync                                  # no new packages
uv run jupyter lab module02/s17_evaluation.ipynb
$env:WORK_REPO = "$HOME\Documents\genai-course-work"
uv run pytest tests/test_s17.py -rs      # checkpoint: a complete evaluation report, both prompts, 20 tickets, + a 5-ticket spot-check
```
No pre-read notebook: Part A of `s17_evaluation.ipynb` is self-contained. Scores your Session 14 baseline against your Session 16 structured prompt
on the SAME twenty held-out tickets (reused, not new data), using a second model call as an LLM judge against a four-criterion rubric (correct label,
cites the right house rule, follows the reply format, invents no policy). Guards against the judge's own biases (position, verbosity, self-preference)
with a shuffled answer order and a five-ticket human spot-check. **Budget:** about 60,000-90,000 tokens of a free key's 200,000-a-day limit — roughly
double Session 16's, since every ticket is answered AND judged, for both prompts. Your submission is `experiments/s17_eval.md`, pushed to **your own**
`genai-course-work` repository; your Session 16 `prompts/support_classifier/` files are read, not changed. The checkpoint test is skipped without a key
(read the reason with `-rs`: a skip is not a pass).

## Session 18 — defensive prompting: attacking your own classifier, on purpose

```powershell
git pull
uv sync                                  # no new packages
uv run jupyter lab module02/s18_defensive_prompting.ipynb
$env:WORK_REPO = "$HOME\Documents\genai-course-work"
uv run pytest tests/test_s18.py -rs      # checkpoint: a complete defense report, 16 attacks x 2 prompts, + clean accuracy held
```
Pre-read: none, Part A of `s18_defensive_prompting.ipynb` is self-contained. Terms: `module02/terms_s18.md`. Attacks Session 16's classifier on purpose
with 16 adversarial tickets across four families (override, authority, exfiltrate, smuggle), then hardens the system prompt with an instruction
hierarchy and a scratchpad/final reply split, and re-measures. Session 16's own held-out set checks the defense did not break ordinary accuracy.
**Budget:** about 50,000-80,000 tokens of a free key's 200,000-a-day limit (16 attack tickets + 20 clean tickets, each prompt). Your submission is
`experiments/s18_defense.md`, pushed to **your own** `genai-course-work` repository; your Session 16 files are read, not changed. The checkpoint test
is skipped without a key (read the reason with `-rs`: a skip is not a pass).

## Session 19 — chat state & memory windows: a conversation that actually remembers

```powershell
git pull
uv sync                                  # no new packages
uv run jupyter lab module03/s19_chat_memory.ipynb
$env:WORK_REPO = "$HOME\Documents\genai-course-work"
uv run pytest tests/test_s19.py -rs      # checkpoint: all three memory strategies scored, naive recalls, both fixes cost less
```
Pre-read: Part A of `s19_chat_memory.ipynb` is self-contained. Terms: `module03/terms_s19.md`. Starts Module 3 (LLM Applications) with a new,
standalone running example — BankAssist, a bank product-FAQ assistant — built around one fact every session depends on: an API call is stateless,
and "the assistant remembers" is your own code resending the conversation's `messages` list on every call. Builds a real 17-turn scripted conversation
with a fact planted at turn 2 and asked for back at turn 17, measures the naive (resend-everything) cost growth, then fixes it two ways — a sliding
window (flat cost, silent forgetting) and summarization (recovers recall, one extra call, a new risk of a wrong summary) — and compares all three
honestly rather than assuming either fix "just works." **Budget:** about 20,000-35,000 tokens of a free key's 200,000-a-day limit (three 17-turn
conversations, plus summarization's own extra calls). Your submission is `experiments/s19_chat_memory.md`, pushed to **your own** `genai-course-work`
repository. The checkpoint test is skipped without a key (read the reason with `-rs`: a skip is not a pass).

## Session 20 — function calling: giving BankAssist hands

```powershell
git pull
uv sync                                  # no new packages
ollama pull llama3.2:3b                  # only if your .env points at Ollama (BASE_URL=http://localhost:11434/v1)
uv run jupyter lab module03/s20_function_calling.ipynb
$env:WORK_REPO = "$HOME\Documents\genai-course-work"
uv run pytest tests/test_s20.py -rs      # checkpoint: golden set scored four ways, model named
```
Pre-read: Part A of `s20_function_calling.ipynb` is self-contained. Terms: `module03/terms_s20.md`. BankAssist from Session 19
gets three tools (`calculate_emi`, `get_rate`, `check_eligibility`) using the raw OpenAI-compatible API, no framework. The round trip is
built by hand, then in a loop capped at three steps. Students watch a model call the wrong tool with invented arguments, then fix it three
ways: prompt guidance, argument validation fed back to the model, and a router that decides "needs a tool?" first. A 10-question golden set
is scored four ways (right tool, valid arguments, correct answer). Runs unchanged on Groq `openai/gpt-oss-20b` or local Ollama
`llama3.2:3b`. **Budget:** on Groq about 30,000-50,000 tokens of the 200,000-a-day limit; on Ollama, free. Answers are cached in
`~/.genai_course/s20_cache.json`. Your submission is `experiments/s20_tools.md`, pushed to **your own** `genai-course-work` repository.
Instructor pre-class run on any model: `uv run python module03/s20_golden_run.py` (or `--ollama llama3.2:3b`).

## Session 21 — LangChain: your first build

```powershell
git pull
uv sync                                  # NEW: langchain==1.4.7 and langchain-openai==1.1.9 (pinned)
$env:WORK_REPO = "$HOME\Documents\genai-course-work"
uv run jupyter lab module03/s21_langchain_build.ipynb      # Section 1 copies the starter into your work repo
uv run python $env:WORK_REPO\s21\bankassist_lc.py        # run YOUR file, from the course repo folder
uv run pytest tests/test_s21.py -rs      # checkpoint: tests the functions YOU wrote (offline, no tokens)
```
Pre-read: Part A of `s21_langchain_build.ipynb`. Terms: `module03/terms_s21.md`. **This is the first session where you write the code.**
You build BankAssist again with LangChain in your own file, `s21/bankassist_lc.py` in **your own** `genai-course-work` repository,
starting from `module03/s21_starter.py`: five TODOs (model, chain, `@tool`, your capped tool loop, and a stretch second tool), with a
check after each. Using ChatGPT is allowed: paste `module03/s21_version_card.md` first, **never paste your `.env` or API key**, and be
ready to explain your code. Stuck? `module03/s21_common_errors.md`. Runs on Groq `openai/gpt-oss-20b` or Ollama `llama3.2:3b`.
**Budget:** a few thousand tokens; the checkpoint itself makes no model calls. Submission: commit and push `s21/bankassist_lc.py`.

## Layout
```
module01/                   Sessions 9a-13 notebooks, helpers, pre-reads
hello.py                    Session 2 first call
list_models.py              which models your key can use
tests/test_setup.py         Session 2 checkpoint
tests/test_s09a.py          Session 9a notebook check (offline)
tests/test_s09.py           Session 9b checkpoint
tests/test_s10.py           Session 10 checkpoint
showcase/a2_insurance/      Showcase A2 (Insurance workflow) + its own tests
showcase/a3_healthcare/     Showcase A3 (Healthcare workflow) + its own tests
tests/test_s11.py           Session 11 checkpoint
tests/test_s12.py           Session 12 checkpoint
tests/test_s13.py           Session 13 checkpoint
tests/test_s14.py           Session 14 checkpoint
tests/test_s15.py           Session 15 checkpoint
tests/test_s16.py           Session 16 checkpoint
tests/test_s17.py           Session 17 checkpoint
tests/test_s18.py           Session 18 checkpoint
tests/test_s19.py           Session 19 checkpoint
tests/test_s20.py           Session 20 checkpoint
tests/test_s21.py           Session 21 checkpoint (tests your own s21/bankassist_lc.py)
module02/                   Module 2 (prompt engineering): S14-S18 notebooks, helpers, work-repo steps
module03/                   Module 3 (LLM applications): S19-S23 notebooks, helpers, work-repo steps
cheatsheet/python-for-agents.md
tools/update_course.py      safe update: back up your edited notebooks, then git pull
UPDATING.md                 how to update when git pull refuses
.env.example                copy to .env
pyproject.toml              pinned dependencies (uv sync)
```
Modules are added as the course progresses (`module01/ … module14/`).

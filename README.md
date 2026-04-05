# decision-logs-with-llm
## about
- いろいろなLLMと会話していると、誰と何を話したのか忘れてしまうので、議事録を残していくことにしました。
- 議事録をプロンプトとして「この話の続きなんだけど…」とやると、あたらしいスレッドを立てたり、他のLLMと議論の続きができるので重宝しています。

---

## Weekly Blog Automation

A GitHub Actions workflow (`weekly-blog.yml`) runs every Friday at 09:00 UTC and
generates an engaging blog-style post from recent entries in `logs/`.
Generated posts are saved under `blog/YYYY-MM-DD.md` and opened as a PR for review.

### How it works

1. The script (`scripts/generate_weekly_blog.py`) scans `logs/` for directories or
   files whose names contain a `yyyymmdd` date token (e.g. `20260310-grant-agent`).
2. Files whose date falls within the past 7 days are collected. Both plain-text files
   and **PDF files** (`.pdf`) are supported — text is extracted from PDFs automatically
   using [pypdf](https://pypdf.readthedocs.io/).
3. If no dated files are found the script falls back to a `git diff` against the
   last processed commit (recorded in `.blog_state.json`).
4. The previous blog post in `blog/` is read as context so the new post can
   describe what changed since last time.
5. A prompt is sent to the configured LLM backend, and the response is written to
   `blog/YYYY-MM-DD.md`.

### Environment variables / workflow inputs

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | LLM backend: `openai`, `anthropic`, or `ollama` |
| `BLOG_DAYS` | `7` | Days to look back |
| `BLOG_DATE` | today UTC | Override output date (`YYYY-MM-DD`) |
| `OPENAI_API_KEY` | — | Required for `openai` mode (store as GitHub Secret) |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Override OpenAI-compatible endpoint |
| `OPENAI_MODEL` | `gpt-5.4-mini` | Model for OpenAI mode |
| `ANTHROPIC_API_KEY` | — | Required for `anthropic` mode (store as GitHub Secret) |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Model for Anthropic mode |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `gpt-oss:20b` | Model for Ollama mode |

### Running locally with Anthropic

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export LLM_PROVIDER=anthropic

python scripts/generate_weekly_blog.py
```

### Running locally with OpenAI

```bash
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-5.4-mini

python scripts/generate_weekly_blog.py
```

You can also point the script at any OpenAI-compatible API (e.g. Azure OpenAI,
Together AI, Groq) by setting `OPENAI_BASE_URL`.

### Running locally with Ollama

```bash
# 1. Start Ollama (if not already running)
ollama serve &

# 2. Pull the model once
ollama pull gpt-oss:20b

# 3. Run the generator
LLM_PROVIDER=ollama python scripts/generate_weekly_blog.py
```

The new post is written to `blog/YYYY-MM-DD.md`.

### Manual workflow dispatch

Go to **Actions → Weekly Blog Generator → Run workflow** in the GitHub UI.
You can override `llm_provider`, `blog_days`, and `blog_date` inputs before running.

### Scheduling

The workflow is scheduled via cron (`0 9 * * 5` – every Friday 09:00 UTC).
To change the schedule, edit `.github/workflows/weekly-blog.yml`.

### Running tests

```bash
pip install -r requirements.txt pytest
pytest scripts/tests/
```

## Weekly Documentation Goal Automation

A GitHub Actions workflow (`.github/workflows/weekly-doc-goal-issue.yml`) runs every
Friday at 09:00 UTC and analyzes the repository documentation as a whole.

It builds an inventory from `README.md`, `prompts/`, `blog/`, and `logs/` (including
**PDF files** in `logs/`), asks an LLM to identify the most original and challenging
next goal, and then opens a GitHub issue draft as a regular issue.

### Environment variables / workflow inputs

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | LLM backend: `openai` or `anthropic` |
| `ISSUE_DATE` | today UTC | Override issue date (`YYYY-MM-DD`) |
| `OPENAI_API_KEY` | — | Required for `openai` mode |
| `OPENAI_MODEL` | `gpt-5.4-mini` | Model for OpenAI mode |
| `ANTHROPIC_API_KEY` | — | Required for `anthropic` mode |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Model for Anthropic mode |

### Manual workflow dispatch

Go to **Actions → Weekly Documentation Goal Issue → Run workflow** in the GitHub UI.
You can override `llm_provider` and `issue_date` before running.

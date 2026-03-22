# decision-logs-with-llm
## about
- いろいろなLLMと会話していると、誰と何を話したのか忘れてしまうので、議事録を残していくことにしました。
- 議事録をプロンプトとして「この話の続きなんだけど…」とやると、あたらしいスレッドを立てたり、他のLLMと議論の続きができるので重宝しています。

## prompt

```
意思決定のプロセスを記録しておくために、このチャットの会話の議事録を作って、マークダウン形式でmdファイルに書き出して。
最終成果物は別のmdファイルで書き出して。
```

---

## Weekly Blog Automation

A GitHub Actions workflow (`weekly-blog.yml`) runs every Monday at 09:00 UTC and
generates an engaging blog-style post from recent entries in `logs/`.
Generated posts are saved under `blog/YYYY-MM-DD.md` and opened as a PR for review.

### How it works

1. The script (`scripts/generate_weekly_blog.py`) scans `logs/` for directories or
   files whose names contain a `yyyymmdd` date token (e.g. `20260310-grant-agent`).
2. Files whose date falls within the past 7 days are collected.
3. If no dated files are found the script falls back to a `git diff` against the
   last processed commit (recorded in `.blog_state.json`).
4. The previous blog post in `blog/` is read as context so the new post can
   describe what changed since last time.
5. A prompt is sent to the configured LLM backend, and the response is written to
   `blog/YYYY-MM-DD.md`.

### Environment variables / workflow inputs

| Variable | Default | Description |
|---|---|---|
| `BLOG_MODE` | `openai` | LLM backend: `openai` or `ollama` |
| `BLOG_DAYS` | `7` | Days to look back |
| `BLOG_DATE` | today UTC | Override output date (`YYYY-MM-DD`) |
| `OPENAI_API_KEY` | — | Required for `openai` mode (store as GitHub Secret) |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Override OpenAI-compatible endpoint |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model for OpenAI mode |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `llama3` | Model for Ollama mode |

### Running locally with Ollama

```bash
# 1. Start Ollama (if not already running)
ollama serve &

# 2. Pull the model once
ollama pull llama3

# 3. Run the generator
BLOG_MODE=ollama python scripts/generate_weekly_blog.py
```

The new post is written to `blog/YYYY-MM-DD.md`.

### Running locally with an external API

```bash
export OPENAI_API_KEY=sk-...          # your key
export OPENAI_MODEL=gpt-4o-mini       # or any compatible model

python scripts/generate_weekly_blog.py
```

You can also point the script at any OpenAI-compatible API (e.g. Azure OpenAI,
Together AI, Groq) by setting `OPENAI_BASE_URL`.

### Manual workflow dispatch

Go to **Actions → Weekly Blog Generator → Run workflow** in the GitHub UI.
You can override `blog_mode`, `blog_days`, and `blog_date` inputs before running.

### Scheduling

The workflow is scheduled via cron (`0 9 * * 1` – every Monday 09:00 UTC).
To change the schedule, edit `.github/workflows/weekly-blog.yml`.

### Running tests

```bash
pip install pytest
pytest scripts/tests/
```

## Weekly Documentation Goal Automation

A GitHub Actions workflow (`.github/workflows/weekly-doc-goal-issue.yml`) runs every
week and analyzes the repository documentation as a whole.

It builds an inventory from `README.md`, `prompts/`, `blog/`, and `logs/`, asks an
LLM to identify the most original and challenging next goal, and then opens a
GitHub issue draft as a regular issue.

### Manual workflow dispatch

Go to **Actions → Weekly Documentation Goal Issue → Run workflow** in the GitHub UI.
You can override the backend, model, and `issue_date` before running.

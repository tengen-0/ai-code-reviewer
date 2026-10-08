# AI-Powered Code Reviewer

A production-oriented FastAPI service that turns a pull-request diff into structured, CI-friendly findings. It combines **deterministic security guardrails** with an optional **OpenAI-compatible LLM provider**.

## Why this project is credible

- Deterministic checks run without credentials and are easy to test.
- Findings include rule ID, severity, file, line, message, and remediation.
- Provider selection is explicit (`heuristic` by default, `openai` when configured).
- The service fails closed with a clear `502` if an external provider is unavailable.
- GitHub Actions runs tests and Ruff on every push and pull request.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://localhost:8000/docs` for interactive API documentation.

## Review a diff

```bash
curl -X POST http://localhost:8000/review \
  -H 'Content-Type: application/json' \
  -d '{
    "repo_url": "https://github.com/example/repo",
    "pr_number": 42,
    "author": "octocat",
    "diff": "+++ b/app.py\n+result = eval(user_input)\n"
  }'
```

The default heuristic provider detects hard-coded credentials, dynamic code execution, shell command risks, and SQL string interpolation. Findings use a stable JSON schema that can be converted to GitHub Checks or review comments.

## Optional LLM analysis

Copy `.env.example` to `.env` and set:

```dotenv
REVIEW_PROVIDER=openai
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
# Optional for an OpenAI-compatible gateway:
# OPENAI_API_BASE=https://api.openai.com/v1
```

The LLM supplements the review; keep deterministic checks in a separate CI job for high-confidence gating.

## Test and lint

```bash
pytest -q
ruff check main.py test_main.py
```

## Project layout

- `main.py` — API models, provider abstraction, heuristic engine, and routes.
- `test_main.py` — endpoint and detection regression tests.
- `.github/workflows/ci.yml` — reproducible test/lint workflow.

## License

MIT

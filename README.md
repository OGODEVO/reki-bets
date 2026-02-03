# Reki Bets

Reki Bets is a two-agent system for sports betting analysis and supporting research. The repo contains:

- **Agent 1 (Betting Analyst):** A FastAPI service that uses sports data tools (NFL/NBA) and a Streamlit UI to deliver betting analysis.
- **Agent 2 (Research Agent):** A FastAPI service that uses Brave Search plus Grok for web research and summarization, with a scheduler to trigger daily runs.

## Repository layout

```
.
├── agent1/                 # Betting analyst API + Streamlit UI
├── agent2/                 # Research agent API + scheduler
└── spot.txt                # Project status and current priorities
```

## Prerequisites

- Python 3.12+ for `agent1` (per `agent1/pyproject.toml`).
- Python 3.9+ for `agent2` (per `agent2/pyproject.toml`).
- API keys for the external services listed below.

## Environment variables

Create `.env` files in each agent directory (or export these variables in your shell). The services will error at startup if required values are missing.

### Agent 1

Required:

- `GEMINI_API_KEY`
- `BRAVE_API_KEY`
- `SPORTRADAR_API_KEY`
- `SERPAPI_API_KEY`

Optional:

- `TIMEZONE` (defaults to `UTC`)
- `XAI_API_KEY` (used if calling Grok in the agent)
- `XAI_BASE_URL` (used if calling Grok in the agent)

### Agent 2

Required:

- `BRAVE_API_KEY`
- `XAI_API_KEY`
- `XAI_BASE_URL`

## Running Agent 1 (Betting Analyst)

From `agent1/`, install dependencies and start the FastAPI service:

```bash
cd agent1
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r <(python - <<'PY'
import tomllib
from pathlib import Path
pyproject = tomllib.loads(Path('pyproject.toml').read_text())
print("\n".join(pyproject["project"]["dependencies"]))
PY
)

python api.py
```

In a separate terminal, run the Streamlit UI:

```bash
cd agent1
source .venv/bin/activate
streamlit run ui.py
```

The API serves OpenAI-compatible streaming responses at `http://127.0.0.1:8005/v1/chat/completions`, which the Streamlit UI consumes.

## Running Agent 2 (Research Agent)

From `agent2/`, install dependencies with Poetry and start the FastAPI service:

```bash
cd agent2
poetry install
poetry run uvicorn researcher:app --host 0.0.0.0 --port 8007
```

To trigger the scheduled daily research job:

```bash
cd agent2
poetry run python scheduler.py
```

## Project status

See `spot.txt` for current priorities, including odds tooling fixes for Agent 1 and stabilization work for Agent 2’s scraping/summarization pipeline.

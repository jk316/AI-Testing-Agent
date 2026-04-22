# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-Test-Agent is a "Network Test Compiler" that converts natural language test intent into executable hping3 bash scripts via a multi-agent pipeline: Planner → Compiler → Verifier.

## Development Commands

```bash
# Install dependencies (uv)
uv sync

# Run the application
uv run python main.py
# Access at http://localhost:5000

# Run with explicit env file
uv run python -c "from dotenv import load_dotenv; load_dotenv('.env'); from main import app; app.run()"
```

## Architecture

### Multi-Agent Pipeline
```
User Input → Planner → DSL → Compiler → hping3 Script → Verifier → Output
```

**Agents** (in `backend/agents/`):
- `planner.py` - Converts NL to structured DSL (JSON)
- `compiler.py` - Converts DSL to hping3 bash script
- `verifier.py` - Validates generated command matches intent

**LLM Integration** (`orchestrator.py`):
- `MinimaxChatModel` - Custom wrapper for Minimax API using Anthropic-compatible format
- Supports both Minimax native format (`choices[0].message.content`) and Anthropic format (`content[0].text`)
- Endpoint: configured via `ANTHROPIC_BASE_URL` env var

**Web Layer** (`backend/app.py`):
- Flask app serving `frontend/index.html`
- Single API endpoint: `POST /api/execute`

### Environment Configuration
Required in `.env`:
```
ANTHROPIC_API_KEY=your_key
ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic
MINIMAX_MODEL=MiniMax-Text-01
```

## Key Implementation Notes

- LLM responses may use single-quoted JSON - `_extract_json()` handles this with `ast.literal_eval`
- Script output uses `\n` escapes - frontend uses `<pre>` to preserve formatting
- Verifier field names may be lowercase or uppercase - frontend handles both
- Target extraction has fallback if LLM fails to parse it from input

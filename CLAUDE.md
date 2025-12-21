# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sae is an A2A (Agent-to-Agent) protocol-native legal services agent that enables AI agents to request contract clause review and risk analysis. Built with FastAPI, LangGraph, and GPT-4o.

## Commands

```bash
# Install dependencies
uv sync

# Run development server
uv run uvicorn sae.main:app --reload

# Run tests
uv run pytest tests/

# Run single test file
uv run pytest tests/test_file.py

# Run tests with coverage
uv run pytest tests/ --cov=src/sae

# Linting
uv run ruff check src/ tests/

# Type checking
uv run mypy src/
```

## Architecture

### Core Flow
1. **API Layer** (`src/sae/api/`) - Receives A2A JSON-RPC requests at `/a2a`
2. **Task Manager** (`src/sae/services/task_manager.py`) - Manages task lifecycle with state machine
3. **LangGraph Workflow** (`src/sae/agents/contract_review.py`) - Orchestrates the analysis pipeline
4. **Processing Nodes** (`src/sae/agents/nodes/`) - Individual LLM-powered analysis steps

### LangGraph Workflow
The contract review workflow in `agents/contract_review.py` chains three nodes:
- `extract_clauses.py` - Identifies and categorizes contract clauses (15 types)
- `analyze_risks.py` - Assesses risks with confidence scores (LOW/MEDIUM/HIGH/CRITICAL)
- `generate_recommendations.py` - Produces prioritized actionable suggestions

Each node uses GPT-4o with structured JSON prompts and includes fallback parsing for malformed responses.

### A2A Protocol Implementation
- Agent Card discovery: `GET /.well-known/agent.json`
- JSON-RPC 2.0 endpoint: `POST /a2a` (methods: `tasks/send`, `tasks/get`, `tasks/cancel`)
- SSE streaming: `GET /a2a/stream/{task_id}`

### Key Models
- `src/sae/models/a2a.py` - A2A protocol types (Task, Message, AgentCard, TaskState)
- `src/sae/models/clauses.py` - Contract analysis types (ClauseType, RiskLevel, Recommendation)

## Code Style

- **Line length**: 100 characters (enforced by Ruff)
- **Type hints**: Strict MyPy enabled - all functions need type annotations
- **Async**: Use `async`/`await` throughout - the codebase is async-first
- **Logging**: Use structlog for all logging (JSON output)
- **Config**: Access settings via `get_settings()` from `config.py` (cached singleton)

## Environment Variables

Required:
- `OPENAI_API_KEY` - OpenAI API key for GPT-4o

Optional:
- `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` - For future RAG integration
- `API_KEY` - API key for authentication (if set, X-API-Key header required)
- `CORS_ORIGINS` - Comma-separated list of allowed origins (default: *)
- `RATE_LIMIT_ENABLED` - Enable rate limiting (default: true)
- `RATE_LIMIT_PER_MINUTE` - Max requests per minute per IP (default: 30)
- `LOG_LEVEL` - Logging level (default: INFO)
- `ENVIRONMENT` - development/staging/production

## Testing Guidelines

Tests must be kept up to date during the development of new features and run regularly.

### Running Tests

Always run tests before committing changes:

```bash
# Run all tests
uv run pytest tests/

# Run with coverage (required: 80% minimum)
uv run pytest tests/ --cov=src/sae

# Run specific test file
uv run pytest tests/unit/api/test_jsonrpc.py -v

# Run tests matching pattern
uv run pytest tests/ -k "test_parse"
```

### Test Structure

- `tests/unit/` - Unit tests (mock external dependencies)
- `tests/integration/` - Integration tests (test real workflows)
- `tests/fixtures/` - Shared test data and mock responses

### Writing Tests

1. **Mock LLM calls** - Never make real OpenAI API calls in tests
2. **Use fixtures** - See `tests/conftest.py` for available fixtures
3. **Test error cases** - Include tests for failure scenarios
4. **Type hints** - All test functions should have return type `-> None`

### Before Committing

1. Run `uv run pytest tests/` - All tests must pass
2. Run `uv run ruff check src/ tests/` - No linting errors
3. Run `uv run mypy src/` - No type errors
4. Add tests for new features

### Test Coverage

Coverage is configured in `pyproject.toml`:
- Minimum: 80%
- Excludes: `__init__.py`, `py.typed`
- Report shows missing lines

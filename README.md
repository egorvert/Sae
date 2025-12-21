# Sae

**A2A-Native Legal Agent for Contract Review**

An autonomous legal services agent built on Google's A2A protocol, enabling AI agents to request contract clause review and risk analysis.

## Features

- **A2A Protocol Native**: Full implementation of Google's Agent-to-Agent protocol
- **Contract Clause Review**: Extract and analyze contract clauses
- **Risk Analysis**: Identify legal risks with confidence scores
- **Recommendations**: Actionable suggestions for contract improvements
- **Streaming Support**: Real-time updates via Server-Sent Events

## Quick Start

### Prerequisites

- Python 3.12+
- [UV](https://github.com/astral-sh/uv) package manager
- OpenAI API key
- Pinecone API key (optional, for RAG)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/sae-law-agent.git
cd sae-law-agent

# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
```

### Running

```bash
# Start the server
uv run uvicorn sae.main:app --reload

# Server runs at http://localhost:8000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/.well-known/agent.json` | GET | A2A Agent Card |
| `/a2a` | POST | A2A JSON-RPC endpoint |
| `/a2a/stream/{task_id}` | GET | SSE streaming for task updates |
| `/health` | GET | Health check |
| `/docs` | GET | OpenAPI documentation |

## Usage

### A2A Protocol

Sae implements the A2A protocol for agent-to-agent communication.

**1. Discover Agent Capabilities**

```bash
curl http://localhost:8000/.well-known/agent.json
```

**2. Submit a Contract for Review**

```bash
curl -X POST http://localhost:8000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/send",
    "id": "req-001",
    "params": {
      "id": "task-001",
      "message": {
        "role": "user",
        "parts": [{
          "type": "text",
          "text": "Please review this NDA:\n\nCONFIDENTIALITY AGREEMENT\n\n1. Definition of Confidential Information..."
        }]
      }
    }
  }'
```

**3. Check Task Status**

```bash
curl -X POST http://localhost:8000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/get",
    "id": "req-002",
    "params": {
      "id": "task-001"
    }
  }'
```

**4. Stream Updates (SSE)**

```bash
curl -N http://localhost:8000/a2a/stream/task-001
```

## Project Structure

```
sae-law-agent/
├── src/sae/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── api/
│   │   ├── agent_card.py    # A2A Agent Card endpoint
│   │   ├── jsonrpc.py       # JSON-RPC handler
│   │   └── streaming.py     # SSE streaming
│   ├── agents/
│   │   ├── contract_review.py  # LangGraph workflow
│   │   ├── state.py         # Agent state definitions
│   │   └── nodes/           # Processing nodes
│   ├── models/
│   │   ├── a2a.py           # A2A protocol models
│   │   └── clauses.py       # Contract analysis models
│   └── services/
│       └── task_manager.py  # Task lifecycle management
├── tests/
├── Dockerfile
└── pyproject.toml
```

## Docker

```bash
# Build
docker build -t sae-legal-agent .

# Run
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e PINECONE_API_KEY=... \
  sae-legal-agent
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT-4o |
| `PINECONE_API_KEY` | No | Pinecone API key for RAG |
| `PINECONE_INDEX_NAME` | No | Pinecone index name |
| `LOG_LEVEL` | No | Logging level (default: INFO) |
| `ENVIRONMENT` | No | development/staging/production |

## License

Apache 2.0

## Status

**MVP Phase**: Core contract review functionality implemented.
- [x] A2A Protocol (Agent Card, JSON-RPC, SSE)
- [x] LangGraph contract review workflow
- [x] Clause extraction
- [x] Risk analysis
- [x] Recommendations
- [ ] RAG integration (Pinecone)
- [ ] Payment integration (x402)
- [ ] Production deployment

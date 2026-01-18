# 🔬 Self-Correcting Research Assistant

A multi-agent research assistant powered by **LangGraph** that automatically plans, researches, and synthesizes answers to complex queries. Features self-correction through an internal review loop and human-in-the-loop approval.

## ✨ Features

- **🧠 Intelligent Planning** — Breaks down complex queries into actionable research steps
- **🔍 Automated Research** — Uses Tavily API for web search and information gathering
- **🔄 Self-Correction Loop** — Internal reviewer critiques results and triggers refinements
- **👤 Human-in-the-Loop** — Pause for human approval before final synthesis
- **💾 Session Persistence** — SQLite-based checkpointing for resumable sessions
- **⏱️ Time-Travel Debugging** — View and restore previous checkpoints
- **🌐 REST API** — FastAPI-powered API for programmatic access

## 📦 Architecture

```
┌─────────┐    ┌────────────┐    ┌──────────┐    ┌────────┐
│ Planner │───▶│ Researcher │───▶│ Reviewer │───▶│ Writer │
└─────────┘    └────────────┘    └──────────┘    └────────┘
                     ▲                 │
                     │   (if score<0.8)│
                     └─────────────────┘
```

### Agent Nodes

| Node | Description |
|------|-------------|
| **Planner** | Decomposes user query into structured research steps |
| **Researcher** | Executes search queries via Tavily API |
| **Reviewer** | Critiques gathered research and decides if refinement is needed |
| **Writer** | Synthesizes final response from approved research |

## 🚀 Installation

### Prerequisites

- Python 3.11+
- [OpenAI API Key](https://platform.openai.com/api-keys)
- [Tavily API Key](https://tavily.com/)

### Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd MultiAgent
   ```

2. **Create and activate virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -e .
   ```

   For development with testing tools:

   ```bash
   pip install -e ".[dev]"
   ```

4. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your API keys:

   ```env
   OPENAI_API_KEY=your-openai-api-key
   TAVILY_API_KEY=your-tavily-api-key
   
   # Optional
   OPENAI_MODEL=gpt-4o-mini
   CHECKPOINT_DB_PATH=research_checkpoints.db
   ```

## 🎮 Usage

### Interactive Mode

Start the assistant in interactive mode:

```bash
python main.py
```

You'll be prompted to enter your research query.

### Command Line

Run with a specific query:

```bash
python main.py --query "What are the latest advancements in quantum computing?"
```

### CLI Options

| Option | Description |
|--------|-------------|
| `-q, --query` | Research query to investigate |
| `-t, --thread` | Thread ID for session persistence |
| `--no-hitl` | Disable human-in-the-loop breakpoint |
| `--checkpoints THREAD_ID` | List checkpoints for a thread |
| `--resume THREAD_ID` | Resume a previous session |

### Examples

```bash
# Run with custom thread ID
python main.py -q "Explain transformer architecture" -t my-session

# Run without human review (automatic mode)
python main.py -q "Compare React vs Vue" --no-hitl

# View checkpoints for a session
python main.py --checkpoints my-session

# Resume a previous session
python main.py --resume my-session
```

### Human-in-the-Loop Flow

When HITL is enabled (default), the assistant pauses before final synthesis:

```
🛑 HUMAN-IN-THE-LOOP BREAKPOINT

📚 GATHERED RESEARCH:
   Step 1: [query]
   Findings: ...

🔍 REVIEWER CRITIQUE:
   Score: 0.85/1.00
   Feedback: ...

Options:
  [a] Approve and continue to final synthesis
  [f] Provide feedback and continue
  [r] Reject and abort
```

---

## 🌐 REST API

The project also provides a FastAPI-powered REST API for programmatic access.

### Starting the API Server

```bash
uvicorn app.main:app --reload
```

API documentation is available at:
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/research` | Start a new research session |
| `GET` | `/research/{thread_id}` | Get session status and results |
| `POST` | `/research/{thread_id}/approve` | Approve HITL breakpoint |
| `GET` | `/research/{thread_id}/checkpoints` | List checkpoints for debugging |
| `GET` | `/health` | Health check |

### Example: Start Research via API

```bash
# Start a new research session
curl -X POST "http://127.0.0.1:8000/research" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest advancements in quantum computing?"}'

# Check session status
curl "http://127.0.0.1:8000/research/abc12345"

# Approve and continue
curl -X POST "http://127.0.0.1:8000/research/abc12345/approve" \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

---

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_graph.py
```

## 📁 Project Structure

```
MultiAgent/
├── main.py                      # CLI entry point
├── pyproject.toml               # Project configuration
├── .env.example                 # Environment template
├── app/                         # FastAPI REST API
│   ├── main.py                  # FastAPI app entry point
│   ├── api/
│   │   └── routes/
│   │       └── research.py      # Research API routes
│   ├── schemas/
│   │   └── research.py          # Pydantic request/response models
│   ├── services/
│   │   └── research.py          # Service layer wrapping LangGraph
│   └── core/
│       └── config.py            # App configuration
├── src/
│   └── research_assistant/
│       ├── __init__.py
│       ├── graph.py             # LangGraph workflow definition
│       ├── state.py             # State schemas & types
│       ├── persistence.py       # SQLite checkpointing
│       └── nodes/
│           ├── __init__.py
│           ├── planner.py       # Query planning agent
│           ├── researcher.py    # Web research agent
│           ├── reviewer.py      # Quality review agent
│           └── writer.py        # Response synthesis agent
└── tests/
    ├── test_graph.py
    ├── test_nodes.py
    └── test_state.py
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key |
| `TAVILY_API_KEY` | ✅ | — | Tavily search API key |
| `OPENAI_MODEL` | ❌ | `gpt-4o-mini` | OpenAI model to use |
| `CHECKPOINT_DB_PATH` | ❌ | `research_checkpoints.db` | SQLite database path |

### Self-Correction Settings

- **Max Revisions**: 3 (prevents infinite loops)
- **Quality Threshold**: 0.8 score required to proceed without refinement

## 📄 License

MIT License

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

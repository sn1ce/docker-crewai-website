# CrewAI Control Panel

A lightweight web UI for managing and launching [CrewAI](https://github.com/crewAIInc/crewAI) crews across multiple Ollama instances on your local network.

![Stack](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Stack](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![Stack](https://img.shields.io/badge/Ollama-000000?style=flat&logoColor=white)

## Features

- **Live machine monitoring** — Auto-pings all Ollama instances on page load and every 60 seconds
- **Crew execution with real-time streaming** — Launch a crew and watch logs via Server-Sent Events (SSE)
- **Agent & task editors** — Create/edit agents and tasks, export as YAML
- **Pipeline configuration** — Choose sequential or hierarchical execution, set max iterations and memory
- **Multi-machine support** — Distribute agents across different Ollama hosts

## Machines

| Name | IP | GPU | Models |
|------|-----|-----|--------|
| Gaming Rig | `10.0.0.88:11434` | RTX 5090 32GB | qwen3-coder-30b |
| NAS (UGreen) | `10.0.0.4:11434` | RTX 4070 12GB | qwen3-8b-ctx32k, qwen3-coder-30b |
| MacBook M4 Max | `10.0.1.162:11434` | M4 Max 36GB unified | llama3.2:3b |

## Prerequisites

- Docker & Docker Compose
- A CrewAI project at `/home/test/crewai/website_builder` (with venv + dependencies installed via `uv sync`)
- Ollama running on the machines listed above

## Quick Start

```bash
cd /home/test/docker/crewai
docker compose up -d --build
```

The UI is available at **http://localhost:4200**.

## Project Structure

```
docker/crewai/
├── compose.yaml      # Docker Compose config (ports, volumes, env)
├── Dockerfile         # Python 3.12-slim + FastAPI/Uvicorn
├── main.py            # FastAPI backend (API endpoints)
├── static/
│   └── index.html     # Single-page frontend (vanilla HTML/CSS/JS)
└── README.md
```

## Architecture

```
┌──────────────┐       ┌──────────────────────┐
│  Browser UI  │◄─────►│  FastAPI (port 4200)  │
│  (index.html)│  SSE  │  main.py in Docker    │
└──────────────┘       └──────────┬───────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ Gaming   │ │ NAS      │ │ MacBook  │
              │ :11434   │ │ :11434   │ │ :11434   │
              └──────────┘ └──────────┘ └──────────┘
                 Ollama       Ollama       Ollama
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/ping/{machine}` | Check if an Ollama instance is reachable (`gaming`, `nas`, `mac`) |
| `GET` | `/api/agents` | Get agents YAML config |
| `POST` | `/api/agents` | Save agents YAML config |
| `GET` | `/api/tasks` | Get tasks YAML config |
| `POST` | `/api/tasks` | Save tasks YAML config |
| `GET` | `/api/topic` | Read current topic from `main.py` |
| `POST` | `/api/run` | Set the topic and prepare crew for execution |
| `GET` | `/api/logs` | SSE stream — launches the crew and streams stdout |
| `POST` | `/api/stop` | Terminate a running crew process |
| `GET` | `/api/output` | List files in the output directory |

## Configuration

Environment variables (set in `compose.yaml`):

| Variable | Default | Description |
|----------|---------|-------------|
| `CREWAI_DIR` | `/crewai/website_builder` | Path to the CrewAI project inside the container |
| `OUTPUT_DIR` | `/crewai/output` | Where crew output files are written |

Volume mounts map the host CrewAI project and output directory into the container:

```yaml
volumes:
  - /home/test/crewai/website_builder:/crewai/website_builder
  - /home/test/crewai/output:/crewai/output
```

## How It Works

1. The frontend sends the task prompt via `POST /api/run` to set the topic
2. It then opens an `EventSource` on `GET /api/logs`
3. The backend spawns a Python subprocess that imports and runs the crew directly (bypassing `crewai run` / `uv` to avoid venv conflicts)
4. Stdout is streamed back to the browser line-by-line via SSE
5. The crew distributes work across your Ollama machines as configured in `crew.py`

## Adding Machines

To add a new Ollama instance, update the `ping_machine` endpoint in `main.py`:

```python
endpoints = {
    "gaming": "http://10.0.0.88:11434",
    "nas": "http://10.0.0.4:11434",
    "mac": "http://10.0.1.162:11434",
    "new_machine": "http://10.0.0.XX:11434",  # add here
}
```

Then add corresponding UI cards in `static/index.html`.

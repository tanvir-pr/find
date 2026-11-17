# Dokan Assistant (Backend)

POS + AI agent backend for stationery / general stores (Phitron final project).

## Step 1 status

Scaffold ready: FastAPI app, config, module folders, Docker Compose skeleton.

## Quick start (local)

```bash
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload
```

- Health: http://localhost:8000/health  
- Swagger: http://localhost:8000/docs  

## Docker (DB + API)

```bash
cd backend
cp .env.example .env
docker compose up --build
```

Postgres (pgvector) starts as `db`. Embedding service is under profile `full` (step 9).

## Layout

```
app/
  core/           # config, security, errors
  db/             # engine, session, Base
  modules/        # auth, products, stock, sales, shifts, ...
  integrations/   # llm, embedding, notify
  mcp/            # MCP server (step 10)
  main.py
scripts/          # seed, ingest (later steps)
knowledge/        # RAG documents (step 9)
```

## Next

Step 2 — SQLAlchemy models + Alembic migrations for all tables.

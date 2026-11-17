# Dokan Assistant (Backend)

POS + AI agent backend for stationery / general stores (Phitron final project).

## Status

- Step 1: Scaffold done
- Step 2: Full schema + Alembic migration done (25 tables + pgvector)

## Quick start (local)

```bash
cd backend
cp .env.example .env
uv sync
docker compose up -d db
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

- Health: http://localhost:8000/health  
- Swagger: http://localhost:8000/docs  
- Postgres host port: **55432** (avoids local 5432/5433 conflicts)

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
  models/         # all SQLAlchemy tables
  modules/        # auth, products, stock, sales, shifts, ...
  integrations/   # llm, embedding, notify
  mcp/            # MCP server (step 10)
  main.py
alembic/          # migrations
scripts/          # seed, ingest (later steps)
knowledge/        # RAG documents (step 9)
```

## Next

Step 3 — JWT auth & roles.

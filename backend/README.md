# Dokan Assistant (Backend)

POS + AI agent backend for stationery / general stores (Phitron final project).

## Status

- Step 1: Scaffold done
- Step 2: Full schema + Alembic migration done (25 tables + pgvector)
- Step 3: JWT auth + roles + seed users done
- Step 4: Products, suppliers, purchases, stock movements done
- Step 5: Sales, payments, returns, receipt logs done

## Quick start (local)

```bash
cd backend
cp .env.example .env
uv sync
docker compose up -d db
uv run alembic upgrade head
uv run python scripts/seed_users.py
uv run uvicorn app.main:app --reload
```

- Health: http://localhost:8000/health  
- Swagger: http://localhost:8000/docs  
- Postgres host port: **55432** (avoids local 5432/5433 conflicts)

### Seed logins

| Email | Password | Role |
| --- | --- | --- |
| `admin@dokan.example` | `Admin123!` | admin |
| `staff@dokan.example` | `Staff123!` | staff |

Auth API: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`

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

### Catalog / stock API (Step 4)

- `POST/GET/PATCH/DELETE /api/v1/products` (+ variants)
- `POST/GET /api/v1/suppliers`
- `POST/GET /api/v1/purchases` (invoice → batches → stock_movements)
- `GET /api/v1/stock/variants/{id}`
- `POST /api/v1/stock/adjustments`

### Sales API (Step 5)

- `POST/GET /api/v1/sales`, `GET /api/v1/sales/by-bill/{bill_no}`
- `POST /api/v1/sales/by-bill/{bill_no}/receipt` (copy)
- `POST /api/v1/returns`
- `POST/GET /api/v1/customers`

## Next

Step 6 — Shifts, cash closing, reports.

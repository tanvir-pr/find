# Dokan Assistant (Backend)

POS + AI agent backend for stationery / general stores (Phitron final project).

## Status

- Step 1: Scaffold done
- Step 2: Full schema + Alembic migration done (25 tables + pgvector)
- Step 3: JWT auth + roles + seed users done
- Step 4: Products, suppliers, purchases, stock movements done
- Step 5: Sales, payments, returns, receipt logs done
- Step 6: Shifts, cash closing, stock counts, reports, due reminders done
- Step 7: Rich demo seed + Swagger E2E verify done
- Step 8: LLM chat + 7 read-only tools done
- Step 9: Knowledge docs + RAG `search_policy` done
- Step 10: MCP HTTP + stdio (3 tools, catalog resource, daily prompt) done

## Quick start (local)

```bash
cd backend
cp .env.example .env
uv sync
docker compose up -d db
uv run alembic upgrade head
uv run python scripts/seed_users.py
uv run python scripts/seed_demo.py
uv run uvicorn app.main:app --reload
```

- Health: http://localhost:8000/health  
- Swagger: http://localhost:8000/docs  
- Postgres host port: **55432** (avoids local 5432/5433 conflicts)

### Seed logins

| Email | Password | Role |
| --- | --- | --- |
| `admin@dokan.example` | `Admin123!` | admin |
| `manager@dokan.example` | `Manager123!` | manager |
| `staff@dokan.example` | `Staff123!` | staff |

Demo catalog barcodes start with `SEED-` (bags, pens, glue/ink expiry, seasonal bottles/caps).

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

### Ops / reports (Step 6)

- `/api/v1/shifts` — open, summary, close + cash closing
- `/api/v1/stock/counts` — stock count + optional adjustments
- `/api/v1/reports/sales-summary|low-stock|expiring`
- `/api/v1/suppliers/{id}/payments`
- `/api/v1/customers/{id}/history|collections`, `?area=`, due-reminders/run

### Demo seed (Step 7)

```bash
uv run python scripts/seed_demo.py   # idempotent
uv run python scripts/test_step7.py  # API + OpenAPI smoke
```

Covers seasonal sales (A7), near-expiry batches (B4/B5), low stock (B6), credit customers/dues (D2/D7).

### Chat / tools (Step 8)

`POST /api/v1/chat` — admin + manager. Set `LLM_*` in `.env` for a real model; empty → mock keyword router.

Tools: `check_stock`, `low_stock_list`, `expiring_items`, `sales_summary`, `reorder_suggestion`, `seasonal_top_products`, `customer_due`, `search_policy`.

```bash
uv run python scripts/test_step8.py
```

### RAG (Step 9)

Knowledge markdown in `knowledge/`. Embeddings: Gemini `gemini-embedding-001` (768-d), or mock if no key.

```bash
uv run python scripts/ingest_knowledge.py
uv run python scripts/test_step9.py
```

### MCP (Step 10)

HTTP (API key required): `POST /mcp/` with `Authorization: Bearer <MCP_API_KEY>` or `X-API-Key`.

Tools: `check_stock`, `sales_summary`, `low_stock_list`  
Resource: `dokan://catalog`  
Prompt: `daily_sales_report`

stdio (Claude Desktop):
```bash
uv run python scripts/run_mcp_stdio.py
uv run python scripts/test_step10.py
```

## Next

Step 11 — Next.js portal.

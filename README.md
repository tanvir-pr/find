# Dokan Assistant

POS + AI agent for stationery / general stores (Phitron final project).

## What the agent does / who it is for

**Who:** shop owners, managers, and cashiers at stationery or general stores.

**Problem:** paper ledgers, missed stock, unclear profit, and no owner visibility when staff run the counter.

**What the agent does:**
- Answers shop questions in chat using **live DB tools** (stock, sales, dues, reorder, expiry).
- Answers **shop policy** questions with **RAG** over markdown knowledge in Postgres/pgvector.
- Exposes the same capabilities over **MCP** for external AI clients.
- Powers a Next.js portal: POS, products, customers/loyalty, shifts, dashboard, and shop alerts.

## Links (Section 2)

| Item | URL |
| --- | --- |
| Git repo | https://github.com/tanvir-pr/find |
| Google Drive video | *(paste your Drive demo link here)* |
| Live Swagger | https://dokan-assistant-api.vercel.app/docs |

Also live:
- Frontend: https://dokan-assistant.vercel.app
- API health: https://dokan-assistant-api.vercel.app/health

## Setup

### 1. Clone

```bash
git clone https://github.com/tanvir-pr/find.git
cd find
```

### 2. Backend `.env`

```bash
cd backend
cp .env.example .env
```

Edit at least:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:55432/dokan_assistant
JWT_SECRET_KEY=change-me-to-a-long-random-string

# Optional — real LLM/embeddings (empty → mock)
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
EMBEDDING_PROVIDER=gemini
EMBEDDING_API_KEY=
MCP_API_KEY=change-me-mcp-key
```

### 3. Docker (Postgres + pgvector)

```bash
# from backend/
docker compose up -d db
```

Host port: **55432** → container `5432`.

Full stack (DB + API):

```bash
docker compose up --build
```

### 4. Install, migrate, seed, ingest

```bash
# from backend/
uv sync
uv run alembic upgrade head
uv run python scripts/seed_users.py
uv run python scripts/seed_demo.py
uv run python scripts/ingest_knowledge.py
uv run uvicorn app.main:app --reload --port 8000
```

### 5. Frontend

```bash
cd ../frontend
cp .env.local.example .env.local
# NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
npm install
npm run dev
```

Portal: http://localhost:3000  
Swagger: http://localhost:8000/docs

### Seed logins

| Email | Password | Role |
| --- | --- | --- |
| `admin@dokan.example` | `Admin123!` | admin |
| `manager@dokan.example` | `Manager123!` | manager |
| `staff@dokan.example` | `Staff123!` | staff |

## Example API requests

Base URL local: `http://127.0.0.1:8000`  
Base URL live: `https://dokan-assistant-api.vercel.app`

### Login

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"admin@dokan.example\",\"password\":\"Admin123!\"}"
```

Save `access_token` from the response as `TOKEN`.

### CRUD — list products (Read)

```bash
curl "http://127.0.0.1:8000/api/v1/products?limit=10" \
  -H "Authorization: Bearer TOKEN"
```

### CRUD — create product (Create)

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/products" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Demo Pen\",
    \"category\": \"Stationery\",
    \"variants\": [
      {\"sku\": \"PEN-DEMO-1\", \"barcode\": \"SEED-PEN-DEMO\", \"unit\": \"pcs\", \"sale_price\": 15}
    ]
  }"
```

### CRUD — update product (Update)

```bash
curl -X PATCH "http://127.0.0.1:8000/api/v1/products/PRODUCT_UUID" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"Demo Pen Pro\"}"
```

### Chat (tools + RAG)

```bash
# Tool example — low stock
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"What products are low on stock?\"}"

# RAG example — policy docs
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"What is our return policy?\"}"
```

Admin/manager roles can use chat. Tools include `check_stock`, `low_stock_list`, `sales_summary`, `search_policy`, and more.

## Project layout

```
backend/     FastAPI, Alembic, knowledge/, MCP
frontend/    Next.js portal
```

# Dokan Assistant — Portal (Next.js)

Admin/manager portal for the Phitron POS + AI backend.

## Pages

| Route | Purpose |
| --- | --- |
| `/login` | JWT login (admin/manager only) |
| `/dashboard` | Today/month sales, profit, payment mix, low stock, expiry |
| `/products` | Name/barcode search, dual prices, stock |
| `/pos` | Quick sale with qty +/- |
| `/sales` | Recent bills + receipt reprint/print |
| `/customers` | Area filter, dues, offer opt-in toggle |
| `/stock` | Stock count + optional adjustments |
| `/chat` | Multi-turn AI assistant (tools + RAG) |

## Run

```bash
# Backend (example port 8001 if 8000 is busy)
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001

# Frontend
cd frontend
cp .env.local.example .env.local
# set NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001
npm install
npm run dev
```

Open http://localhost:3000  
Demo: `admin@dokan.example` / `Admin123!`

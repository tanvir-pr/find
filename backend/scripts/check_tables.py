import psycopg

from app.core.config import settings

url = settings.SYNC_DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1)
with psycopg.connect(url) as conn:
    tables = conn.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1"
    ).fetchall()
    vector = conn.execute(
        "SELECT extname FROM pg_extension WHERE extname='vector'"
    ).fetchone()
    print("tables", len(tables))
    for (name,) in tables:
        print("-", name)
    print("vector_ext", bool(vector))

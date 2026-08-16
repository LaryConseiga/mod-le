"""Shared top-k semantic search over menu_items + restaurant_info.

Used by the CLI sanity-check script (ingestion/search.py) and by the
running agent (app/agent.py) — one query path, not duplicated.
"""
from __future__ import annotations

import os

import psycopg2
from pgvector.psycopg2 import register_vector

from ingestion.embeddings import embed

SEARCH_SQL = """
    select source, label, content, distance from (
        select 'menu' as source, name as label, content, embedding <=> %(vector)s::vector as distance
        from menu_items
        union all
        select 'info' as source, coalesce(label, type) as label, content, embedding <=> %(vector)s::vector as distance
        from restaurant_info
    ) matches
    order by distance asc
    limit %(k)s
"""


def search(query: str, k: int = 5, db_url: str | None = None, conn=None) -> list[dict]:
    """Pass `conn` to reuse an already-open, already-pooled connection (the
    running agent does this — see app/db.py). Without it, opens and closes
    its own connection, for standalone/CLI use (ingestion/search.py)."""
    vector = embed(query)

    if conn is not None:
        with conn.cursor() as cur:
            cur.execute(SEARCH_SQL, {"vector": vector, "k": k})
            rows = cur.fetchall()
        return [{"source": s, "label": l, "content": c, "distance": d} for s, l, c, d in rows]

    own_conn = psycopg2.connect(db_url or os.environ["SUPABASE_DB_URL"])
    register_vector(own_conn)
    try:
        with own_conn.cursor() as cur:
            cur.execute(SEARCH_SQL, {"vector": vector, "k": k})
            rows = cur.fetchall()
    finally:
        own_conn.close()

    return [{"source": s, "label": l, "content": c, "distance": d} for s, l, c, d in rows]

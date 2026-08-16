"""Conversation state (Supabase — same database as the RAG catalog).

Pooled: a fresh TLS-encrypted connection through the Supabase pooler costs
hundreds of ms, and one incoming message used to open 6-8 of them (one per
call below). All db.* calls for a single message now share one connection,
checked out once in app.agent.handle_incoming_message and passed through.
"""
from __future__ import annotations

import os
from contextlib import contextmanager

from pgvector.psycopg2 import register_vector
from psycopg2.extras import Json
from psycopg2.pool import ThreadedConnectionPool

_pool: ThreadedConnectionPool | None = None


class _VectorAwarePool(ThreadedConnectionPool):
    def _connect(self, key=None):
        conn = super()._connect(key)
        register_vector(conn)
        return conn


def _get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = _VectorAwarePool(1, 5, os.environ["SUPABASE_DB_URL"])
    return _pool


@contextmanager
def get_connection():
    """One connection for the whole request: `with db.get_connection() as conn: ...`.
    Commits once at the end, rolls back the lot on any exception."""
    p = _get_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


def get_or_create_conversation(conn, phone_number: str) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            "select current_step, cart, human_takeover, last_order from conversations where phone_number = %s",
            (phone_number,),
        )
        row = cur.fetchone()
        is_new = row is None
        if row is None:
            cur.execute(
                """
                insert into conversations (phone_number) values (%s)
                returning current_step, cart, human_takeover, last_order
                """,
                (phone_number,),
            )
            row = cur.fetchone()
    return {
        "current_step": row[0],
        "cart": row[1] or [],
        "human_takeover": row[2],
        "last_order": row[3],
        "is_new": is_new,
    }


def save_message(conn, phone_number: str, role: str, content: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "insert into messages (phone_number, role, content) values (%s, %s, %s)",
            (phone_number, role, content),
        )
        cur.execute(
            "update conversations set last_message_at = now() where phone_number = %s",
            (phone_number,),
        )


def get_recent_messages(conn, phone_number: str, limit: int = 10) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select role, content from messages
            where phone_number = %s
            order by created_at desc
            limit %s
            """,
            (phone_number, limit),
        )
        rows = cur.fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def update_cart(conn, phone_number: str, cart: list[dict]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "update conversations set cart = %s where phone_number = %s",
            (Json(cart), phone_number),
        )


def update_last_order(conn, phone_number: str, last_order: dict | None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "update conversations set last_order = %s where phone_number = %s",
            (Json(last_order) if last_order is not None else None, phone_number),
        )


def set_human_takeover(conn, phone_number: str, value: bool) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "update conversations set human_takeover = %s where phone_number = %s",
            (value, phone_number),
        )


def get_menu_items(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("select id, name, category, price_text from menu_items order by category, name")
        rows = cur.fetchall()
    return [{"id": i, "name": n, "category": c, "price_text": p} for i, n, c, p in rows]


def insert_order_outbox(
    conn,
    order_id: str,
    phone_number: str,
    payload: dict,
    idempotency_key: str,
    status: str,
    partner_order_id: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into orders_outbox (id, phone_number, payload, status, idempotency_key, partner_order_id)
            values (%s, %s, %s, %s, %s, %s)
            """,
            (order_id, phone_number, Json(payload), status, idempotency_key, partner_order_id),
        )


def update_order_outbox_payload(conn, order_id: str, payload: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "update orders_outbox set payload = %s, updated_at = now() where id = %s",
            (Json(payload), order_id),
        )

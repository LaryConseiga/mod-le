"""Parse knowledge_base/issouf_fast_food.md, embed it, and upsert into Supabase.

Usage:
    python -m ingestion.ingest
"""
from __future__ import annotations

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector

from ingestion.embeddings import embed_batch
from ingestion.parser import parse_knowledge_base

KB_PATH = Path(__file__).resolve().parent.parent / "knowledge_base" / "issouf_fast_food.md"

UPSERT_MENU_ITEM = """
    insert into menu_items (id, name, category, composition, price_text, content, embedding, updated_at)
    values (%s, %s, %s, %s, %s, %s, %s, now())
    on conflict (id) do update set
        name = excluded.name,
        category = excluded.category,
        composition = excluded.composition,
        price_text = excluded.price_text,
        content = excluded.content,
        embedding = excluded.embedding,
        updated_at = now()
"""

UPSERT_INFO_FACT = """
    insert into restaurant_info (id, type, label, content, embedding, updated_at)
    values (%s, %s, %s, %s, %s, now())
    on conflict (id) do update set
        type = excluded.type,
        label = excluded.label,
        content = excluded.content,
        embedding = excluded.embedding,
        updated_at = now()
"""


def main() -> None:
    load_dotenv()
    db_url = os.environ["SUPABASE_DB_URL"]

    md_text = KB_PATH.read_text(encoding="utf-8")
    menu_items, info_facts = parse_knowledge_base(md_text)
    print(f"{len(menu_items)} plats et {len(info_facts)} informations trouvés dans {KB_PATH.name}")

    if not menu_items or not info_facts:
        raise SystemExit(
            "Parsing suspect (liste vide) — abandon avant de synchroniser, "
            "pour ne pas vider la table par erreur. Vérifie le fichier .md."
        )

    menu_vectors = embed_batch([item.content for item in menu_items])
    info_vectors = embed_batch([fact.content for fact in info_facts])

    menu_ids = [item.id for item in menu_items]
    info_ids = [fact.id for fact in info_facts]

    conn = psycopg2.connect(db_url)
    register_vector(conn)
    try:
        with conn, conn.cursor() as cur:
            for item, vector in zip(menu_items, menu_vectors):
                cur.execute(
                    UPSERT_MENU_ITEM,
                    (item.id, item.name, item.category, item.composition, item.price_text, item.content, vector),
                )
            for fact, vector in zip(info_facts, info_vectors):
                cur.execute(UPSERT_INFO_FACT, (fact.id, fact.type, fact.label, fact.content, vector))

            # Le fichier .md est la seule source de vérité : tout id disparu du
            # fichier doit disparaître de la base (sinon un plat retiré/renommé
            # reste répondable par le RAG indéfiniment).
            cur.execute("delete from menu_items where not (id = any(%s))", (menu_ids,))
            deleted_menu = cur.rowcount
            cur.execute("delete from restaurant_info where not (id = any(%s))", (info_ids,))
            deleted_info = cur.rowcount
    finally:
        conn.close()

    print(f"{deleted_menu} plat(s) et {deleted_info} info(s) obsolètes supprimés.")
    print("Ingestion terminée : menu_items et restaurant_info sont à jour dans Supabase.")


if __name__ == "__main__":
    main()

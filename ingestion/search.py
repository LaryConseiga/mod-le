"""Sanity-check the ingestion by running a real top-k similarity search.

Usage:
    python -m ingestion.search "vous êtes ouverts jusqu'à quelle heure ?"
"""
from __future__ import annotations

import sys

from dotenv import load_dotenv

from ingestion.retrieval import search


def main(query: str, k: int = 5) -> None:
    load_dotenv()
    rows = search(query, k=k)

    if not rows:
        print("Aucun résultat — as-tu lancé `python -m ingestion.ingest` ?")
        return

    print(f'Question : "{query}"\n')
    for row in rows:
        print(f"[{row['source']}] {row['label']}  (distance={row['distance']:.4f})\n  {row['content']}\n")


if __name__ == "__main__":
    main(" ".join(sys.argv[1:]) or "Vous êtes ouverts jusqu'à quelle heure ?")

"""Local embedding model — Groq has no embeddings endpoint, so we run one
ourselves. all-MiniLM-L6-v2 outputs 384-dim vectors, matching vector(384)
in db/schema.sql, and is small enough to run on CPU in well under a second
per batch at this catalog's scale.
"""
from __future__ import annotations

from functools import lru_cache

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    # CPU only: at this catalog's scale (tens of texts) it's plenty fast,
    # and it sidesteps host CUDA/driver mismatches entirely.
    return SentenceTransformer(MODEL_NAME, device="cpu")


def embed_batch(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = _model().encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def embed(text: str) -> list[float]:
    return embed_batch([text])[0]

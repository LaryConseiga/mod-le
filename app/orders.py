"""Push a confirmed order to the partner's ordering app.

Stub: the exact contract (auth, field names) is still "à confirmer avec le
partenaire" per Feuille A-08 of the architecture doc. Until PARTNER_API_URL
is set, orders simply stay queued as "pending" in orders_outbox — nothing
is lost, they just wait for a retry job once the real endpoint exists.
"""
from __future__ import annotations

import os

import requests


def push_to_partner(payload: dict) -> tuple[str, str | None]:
    """Returns (status, partner_order_id)."""
    partner_url = os.environ.get("PARTNER_API_URL")
    if not partner_url:
        return "pending", None

    try:
        response = requests.post(
            partner_url,
            json=payload,
            headers={"Authorization": f"Bearer {os.environ.get('PARTNER_API_KEY', '')}"},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        return "sent", data.get("order_id")
    except requests.RequestException:
        return "failed", None

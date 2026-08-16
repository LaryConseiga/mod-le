"""Meta WhatsApp Cloud API: inbound webhook parsing/verification, outbound send,
and voice-note media download (Meta serves media in two hops: resolve the
media id to a temporary URL, then fetch that URL — both calls need the
access token)."""
from __future__ import annotations

import hashlib
import hmac
import os

import requests

GRAPH_API_VERSION = "v21.0"


def verify_signature(payload_body: bytes, signature_header: str | None, app_secret: str) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), payload_body, hashlib.sha256).hexdigest()
    received = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, received)


def parse_incoming(payload: dict) -> dict | None:
    """Returns one of:
    - {phone_number, type: "text", text, message_id}
    - {phone_number, type: "audio", media_id, message_id}   (voice note)
    or None for anything else (status callbacks, unsupported message types, malformed payloads)."""
    try:
        value = payload["entry"][0]["changes"][0]["value"]
        messages = value.get("messages")
        if not messages:
            return None
        message = messages[0]
        msg_type = message.get("type")

        if msg_type == "text":
            return {
                "phone_number": message["from"],
                "type": "text",
                "text": message["text"]["body"],
                "message_id": message["id"],
            }
        if msg_type == "audio":
            return {
                "phone_number": message["from"],
                "type": "audio",
                "media_id": message["audio"]["id"],
                "message_id": message["id"],
            }
        return None
    except (KeyError, IndexError, TypeError):
        return None


def get_media_url(media_id: str) -> tuple[str, str]:
    """Returns (temporary_download_url, mime_type)."""
    access_token = os.environ["META_ACCESS_TOKEN"]
    response = requests.get(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{media_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return data["url"], data.get("mime_type", "audio/ogg")


def download_media(url: str) -> bytes:
    access_token = os.environ["META_ACCESS_TOKEN"]
    response = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=30)
    response.raise_for_status()
    return response.content


def mark_as_read_with_typing(message_id: str) -> requests.Response:
    """Coche bleue + bulle "en train d'écrire..." pendant le traitement (RAG/Groq
    prend quelques secondes). L'indicateur disparaît dès qu'on répond, ou après
    25s max côté Meta."""
    phone_number_id = os.environ["META_PHONE_NUMBER_ID"]
    access_token = os.environ["META_ACCESS_TOKEN"]
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages"
    return requests.post(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
            "typing_indicator": {"type": "text"},
        },
        timeout=10,
    )


def send_text_message(to: str, body: str) -> requests.Response:
    phone_number_id = os.environ["META_PHONE_NUMBER_ID"]
    access_token = os.environ["META_ACCESS_TOKEN"]
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages"
    return requests.post(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        },
        timeout=10,
    )

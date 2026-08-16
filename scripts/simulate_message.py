"""Simule un webhook Meta entrant contre le serveur Flask local — pas besoin
d'un vrai numéro WhatsApp pour tester l'orchestration (RAG + Groq + Supabase).

Usage :
    python scripts/simulate_message.py "+22670000001" "vous êtes ouverts jusqu'à quelle heure ?"
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys

import requests
from dotenv import load_dotenv


def build_payload(phone_number: str, text: str) -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": phone_number,
                                    "id": "wamid.simulated",
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


def main() -> None:
    if len(sys.argv) < 3:
        print('Usage: python scripts/simulate_message.py "+22670000001" "message"')
        sys.exit(1)

    load_dotenv()
    phone_number, text = sys.argv[1], " ".join(sys.argv[2:])
    body = json.dumps(build_payload(phone_number, text)).encode()

    headers = {"Content-Type": "application/json"}
    app_secret = os.environ.get("META_APP_SECRET")
    if app_secret:
        signature = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-Hub-Signature-256"] = f"sha256={signature}"

    response = requests.post("http://localhost:8080/webhook", data=body, headers=headers, timeout=30)
    print(response.status_code, response.text)


if __name__ == "__main__":
    main()

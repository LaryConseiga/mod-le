from __future__ import annotations

import os

from flask import Flask, jsonify, request

from app import db
from app.agent import handle_incoming_message
from app.transcription import transcribe
from app.whatsapp import (
    download_media,
    get_media_url,
    mark_as_read_with_typing,
    parse_incoming,
    send_text_message,
    verify_signature,
)


def _has_meta_credentials() -> bool:
    return bool(os.environ.get("META_ACCESS_TOKEN") and os.environ.get("META_PHONE_NUMBER_ID"))


def _warmup() -> None:
    """Pay the ~10s embedding-model load and the first pooled DB connection
    at boot, not on some customer's first message (see [latence] logs)."""
    from ingestion.embeddings import embed

    embed("préchauffage")
    with db.get_connection():
        pass


def create_app() -> Flask:
    app = Flask(__name__)
    _warmup()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/webhook")
    def verify():
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge", "")
        if mode == "subscribe" and token == os.environ.get("META_VERIFY_TOKEN"):
            return challenge, 200
        return "Forbidden", 403

    @app.post("/webhook")
    def incoming():
        app_secret = os.environ.get("META_APP_SECRET")
        if app_secret:
            signature = request.headers.get("X-Hub-Signature-256")
            if not verify_signature(request.get_data(), signature, app_secret):
                return "Invalid signature", 403

        payload = request.get_json(silent=True) or {}
        parsed = parse_incoming(payload)
        if not parsed:
            return jsonify({"status": "ignored"}), 200

        # Coche bleue + "en train d'écrire..." tout de suite : le traitement
        # (RAG + Groq, éventuellement transcription audio) prend quelques secondes.
        if _has_meta_credentials():
            try:
                mark_as_read_with_typing(parsed["message_id"])
            except Exception:
                app.logger.exception("Échec du marquage lu/typing pour %s", parsed["phone_number"])

        if parsed["type"] == "text":
            text = parsed["text"]
        else:  # "audio" — note vocale
            try:
                url, mime_type = get_media_url(parsed["media_id"])
                audio_bytes = download_media(url)
                text = transcribe(audio_bytes, mime_type)
            except Exception:
                app.logger.exception("Échec de transcription audio pour %s", parsed["phone_number"])
                text = ""
            if not text:
                if _has_meta_credentials():
                    try:
                        send_text_message(
                            parsed["phone_number"],
                            "Désolé, je n'ai pas réussi à comprendre votre note vocale — pouvez-vous réessayer ou écrire votre message ?",
                        )
                    except Exception:
                        app.logger.exception("Échec de l'envoi WhatsApp vers %s", parsed["phone_number"])
                return jsonify({"status": "ok"}), 200
            app.logger.info("Note vocale transcrite pour %s : %s", parsed["phone_number"], text)

        reply = handle_incoming_message(parsed["phone_number"], text)
        if reply:
            app.logger.info("Réponse générée pour %s : %s", parsed["phone_number"], reply)
            if _has_meta_credentials():
                try:
                    send_text_message(parsed["phone_number"], reply)
                except Exception:
                    app.logger.exception("Échec de l'envoi WhatsApp vers %s", parsed["phone_number"])
            else:
                app.logger.warning("META_ACCESS_TOKEN/META_PHONE_NUMBER_ID absents — réponse non envoyée (mode dev)")

        return jsonify({"status": "ok"}), 200

    return app

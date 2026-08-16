"""Speech-to-text for WhatsApp voice notes — Groq also hosts Whisper, so no
separate transcription provider is needed."""
from __future__ import annotations

import os
from functools import lru_cache

_EXTENSION_BY_MIME = {
    "audio/ogg": "ogg",
    "audio/opus": "opus",
    "audio/mpeg": "mp3",
    "audio/mp4": "mp4",
    "audio/amr": "amr",
    "audio/wav": "wav",
    "audio/webm": "webm",
}


@lru_cache(maxsize=1)
def _client():
    from groq import Groq

    return Groq(api_key=os.environ["GROQ_API_KEY"])


def extension_for(mime_type: str) -> str:
    return _EXTENSION_BY_MIME.get(mime_type.split(";")[0].strip(), "ogg")


def transcribe(audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    model = os.environ.get("GROQ_TRANSCRIBE_MODEL", "whisper-large-v3-turbo")
    filename = f"voice.{extension_for(mime_type)}"
    result = _client().audio.transcriptions.create(
        file=(filename, audio_bytes),
        model=model,
        language="fr",
    )
    return (result.text or "").strip()

"""Thin wrapper around the Groq chat completions API (function-calling enabled)."""
from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def _client():
    from groq import Groq

    return Groq(api_key=os.environ["GROQ_API_KEY"])


def chat(messages: list[dict], tools: list[dict] | None = None):
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    return _client().chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto" if tools else None,
        temperature=0.3,
    )

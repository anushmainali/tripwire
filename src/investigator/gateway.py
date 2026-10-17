"""Minimal Chalk Model Gateway client for the investigator (OpenAI-compatible router)."""

import json
import re
from functools import lru_cache

from openai import OpenAI

from src import config

FAST_MODEL = "anthropic/claude-haiku-5-5"
STRONG_MODEL = "anthropic/claude-sonnet-5-5"


@lru_cache(maxsize=1)
def client() -> OpenAI:
    cfg = config.chalk_router()
    return OpenAI(
        base_url=cfg.base_url, api_key=cfg.api_key, default_headers={"X-Chalk-Env-Id": cfg.env_id}, max_retries=1
    )


def chat_json(system: str, user: str, model: str = STRONG_MODEL, timeout: float = 25.0, max_tokens: int = 800) -> dict:
    """One chat completion that must return a JSON object. Raises on transport or parse failure."""
    resp = client().chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        timeout=timeout,
        max_tokens=max_tokens,
    )
    return parse_json(resp.choices[0].message.content or "")


def parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in model output")
    return json.loads(match.group(0))

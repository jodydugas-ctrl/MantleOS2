"""Foreign Food parsing and the minimal OpenRouter MIND transport."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_FOOD_BYTES = 8_192
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._~:/-]+$")


class NutritionError(RuntimeError):
    """Food could not be safely parsed, stored, or tested."""


@dataclass(frozen=True)
class OpenRouterFood:
    api_key: str
    model: str
    source_sha256: str
    key_fingerprint: str


def parse_openrouter_food(raw: bytes) -> OpenRouterFood:
    if not raw or len(raw) > MAX_FOOD_BYTES:
        raise NutritionError("Food must contain between 1 and 8192 bytes")
    source_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        lines = [line.strip() for line in raw.decode("utf-8-sig").splitlines() if line.strip()]
    except UnicodeDecodeError as exc:
        raise NutritionError("Food is not UTF-8 text") from exc
    if len(lines) != 2:
        raise NutritionError("OpenRouter Food must contain exactly a key line and a model line")
    api_key, model = lines
    if not api_key.startswith("sk-or-v1-") or len(api_key) < 32:
        raise NutritionError("The first Food line is not an OpenRouter key")
    if not MODEL_PATTERN.fullmatch(model):
        raise NutritionError("The second Food line is not a safe OpenRouter model identifier")
    return OpenRouterFood(
        api_key=api_key,
        model=model,
        source_sha256=source_sha256,
        key_fingerprint=hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16],
    )


def openrouter_completion(
    api_key: str,
    model: str,
    message: str,
    *,
    max_tokens: int = 256,
    timeout: float = 45.0,
) -> dict[str, Any]:
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "max_tokens": max(1, min(max_tokens, 2_048)),
            "temperature": 0,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OPENROUTER_CHAT_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "MantleOS/2",
            "X-OpenRouter-Title": "MantleOS",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise NutritionError(f"OpenRouter rejected the request with HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise NutritionError(f"OpenRouter could not be reached ({type(exc).__name__})") from None
    try:
        result = json.loads(raw.decode("utf-8"))
        choice = result["choices"][0]
        content = choice["message"]["content"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise NutritionError("OpenRouter returned an unreadable completion") from exc
    if not isinstance(content, str) or not content.strip():
        raise NutritionError("OpenRouter returned an empty completion")
    return {
        "content": content,
        "selected_model": str(result.get("model") or model),
        "response_id": str(result.get("id") or ""),
        "usage": result.get("usage") if isinstance(result.get("usage"), dict) else {},
    }


def verify_openrouter_food(food: OpenRouterFood) -> dict[str, Any]:
    result = openrouter_completion(
        food.api_key,
        food.model,
        "Credential verification only. Reply with the exact text MANTLE_BODY_OK.",
        # The free router may select a reasoning model. Leave enough room for
        # hidden reasoning plus the short visible verification response.
        max_tokens=256,
    )
    return {
        "ok": True,
        "requested_model": food.model,
        "selected_model": result["selected_model"],
        "response_id": result["response_id"],
        "response_chars": len(result["content"]),
        "usage": result["usage"],
    }

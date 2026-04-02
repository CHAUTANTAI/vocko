"""Minimal OpenRouter chat-completions client (httpx)."""

import json
import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_OR_HTTP_ERR = re.compile(r"OpenRouter HTTP (\d+):", re.IGNORECASE)


def http_status_for_openrouter_error(
    message: str, *, default_for_unknown: int = 400
) -> int:
    """
    Map error strings from chat_completion (and similar) to an HTTP status for API responses.
    429 from the provider is surfaced as 429 so clients can retry or show rate-limit messaging.

    default_for_unknown: use 400 for validation-style errors (e.g. tag suggest); use 503 when the
    endpoint only fails due to the AI pipeline (hints / explain).
    """
    if not (message or "").strip():
        return 503
    el = message.lower()
    m = _OR_HTTP_ERR.match(message.strip())
    if m:
        code = int(m.group(1))
        if code == 429:
            return 429
        if code >= 500:
            return 502
        return 503
    if "openrouter" in el:
        return 503
    if "timed out" in el:
        return 503
    return default_for_unknown

DEFAULT_BASE = "https://openrouter.ai/api/v1"
TIMEOUT = 25.0

# OpenRouter auto-routes to a free model; use with X-OpenRouter-Only-Free (see _openrouter_extra_headers).
MODEL_OPENROUTER_FREE = "openrouter/free"


def _openrouter_extra_headers(for_model: str) -> dict[str, str]:
    """
    OpenRouter: pair model openrouter/free with X-OpenRouter-Only-Free (always sent for that model id).
    OPENROUTER_ONLY_FREE=1 forces the header for any model id; =0 skips it except for openrouter/free.
    """
    m = (for_model or "").strip().lower()
    env = os.getenv("OPENROUTER_ONLY_FREE", "").strip().lower()
    if m == MODEL_OPENROUTER_FREE:
        return {"X-OpenRouter-Only-Free": "true"}
    if env in ("0", "false", "no"):
        return {}
    if env in ("1", "true", "yes"):
        return {"X-OpenRouter-Only-Free": "true"}
    return {}


def _openrouter_error_message(r: httpx.Response) -> str:
    try:
        j = r.json()
        if isinstance(j, dict):
            err = j.get("error")
            if isinstance(err, dict) and err.get("message"):
                return str(err["message"])[:800]
            if isinstance(err, str):
                return err[:800]
    except (json.JSONDecodeError, TypeError):
        pass
    text = (r.text or "").strip()
    return text[:800] if text else f"HTTP {r.status_code}"


def _message_text(msg: dict[str, Any]) -> str | None:
    """Normalize OpenAI-compatible message.content (str or multimodal parts)."""
    c = msg.get("content")
    if isinstance(c, str):
        s = c.strip()
        return s if s else None
    if isinstance(c, list):
        parts: list[str] = []
        for p in c:
            if isinstance(p, dict):
                if p.get("type") == "text" and isinstance(p.get("text"), str):
                    parts.append(p["text"])
                elif isinstance(p.get("content"), str):
                    parts.append(p["content"])
            elif isinstance(p, str):
                parts.append(p)
        s = "".join(parts).strip()
        return s if s else None
    return None


def chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str,
    temperature: float = 0.3,
    timeout: float | None = None,
) -> tuple[str | None, str | None]:
    """
    Returns (content, error). error is None on success.
    timeout: seconds for this request; None uses default TIMEOUT (25s).
    """
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        return None, "OPENROUTER_API_KEY is not set"
    model = (model or "").strip()
    if not model:
        return None, "Model id is empty (check OPENROUTER_MODEL_HINT / OPENROUTER_MODEL_GRADE)"
    base = os.getenv("OPENROUTER_BASE_URL", DEFAULT_BASE).rstrip("/")
    url = f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://localhost"),
        "X-Title": os.getenv("OPENROUTER_APP_TITLE", "VocKO"),
        **_openrouter_extra_headers(model),
    }
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    eff_timeout = float(timeout) if timeout is not None else TIMEOUT
    try:
        with httpx.Client(timeout=eff_timeout) as client:
            r = client.post(url, json=body, headers=headers)
            if r.status_code >= 400:
                msg = _openrouter_error_message(r)
                logger.warning("OpenRouter %s for model %s: %s", r.status_code, model, msg)
                return None, f"OpenRouter HTTP {r.status_code}: {msg}"
            try:
                data = r.json()
            except json.JSONDecodeError:
                logger.warning("OpenRouter returned non-JSON body for model %s", model)
                return None, "Invalid response from OpenRouter (not JSON)"
            choice = data.get("choices") or []
            if not choice:
                logger.warning("OpenRouter empty choices for model %s: %s", model, str(data)[:500])
                return None, "Model returned no choices (check model id and account credits)"
            msg_d = choice[0].get("message") or {}
            text = _message_text(msg_d) if isinstance(msg_d, dict) else None
            if not text:
                logger.warning("OpenRouter empty message content for model %s", model)
                return None, "Model returned empty content"
            return text, None
    except httpx.TimeoutException:
        logger.warning("OpenRouter timeout for model %s", model)
        return None, "OpenRouter request timed out"
    except httpx.HTTPError as e:
        logger.warning("OpenRouter HTTP error for model %s: %s", model, e)
        return None, f"OpenRouter network error: {e}"
    except (KeyError, TypeError, ValueError) as e:
        logger.warning("OpenRouter parse error for model %s: %s", model, e)
        return None, "Unexpected response shape from OpenRouter"

"""
Centralized Groq API client with open-keypool key rotation, bounded retries,
safe masked logging, and model-fallback compatibility.
"""

import logging
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from open_keypool import AllKeysExhaustedError, KeyPool, KeyState

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_RETRIES = 4
DEFAULT_COOLDOWN_SECONDS = 60
DEFAULT_RETRY_BACKOFF = 0.5

_INDEXED_KEY_RE = re.compile(r"^GROQ_API_KEY_(\d+)$")

_POOL_LOCK = threading.Lock()
_SHARED_POOL: Optional[KeyPool] = None
_SHARED_POOL_KEYS: Tuple[str, ...] = ()


class GroqClientError(RuntimeError):
    """Base error for centralized Groq client failures."""


class GroqConfigurationError(GroqClientError):
    """Raised when no Groq API keys are configured."""


class GroqAPIError(GroqClientError):
    """Raised on non-retryable or exhausted Groq API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def mask_api_key(key: Optional[str]) -> str:
    """Returns a safe masked representation of an API key for logging."""
    raw = (key or "").strip()
    if not raw:
        return "<empty>"
    if len(raw) <= 8:
        return "****"
    prefix = raw[:4] if raw.startswith("gsk_") else ""
    return f"{prefix}****{raw[-4:]}"


def _get_setting_or_env(name: str, default: str = "") -> str:
    val = os.getenv(name, "")
    if not val:
        try:
            from django.conf import settings

            val = getattr(settings, name, "") or ""
        except Exception:
            val = ""
    return str(val).strip() or default


def load_groq_api_keys() -> List[str]:
    """
    Loads Groq API keys from environment variables without hardcoding:
    1. Indexed keys: GROQ_API_KEY_1, GROQ_API_KEY_2, ... (sorted numerically)
    2. Comma-separated GROQ_API_KEYS (if provided)
    3. Single fallback GROQ_API_KEY (env or Django settings)
    """
    indexed: List[Tuple[int, str]] = []
    for name, value in os.environ.items():
        match = _INDEXED_KEY_RE.match(name)
        if match and value and value.strip():
            indexed.append((int(match.group(1)), value.strip()))
    indexed.sort(key=lambda item: item[0])

    ordered_keys: List[str] = [val for _, val in indexed]

    raw_multi = _get_setting_or_env("GROQ_API_KEYS", "")
    if raw_multi:
        for part in raw_multi.split(","):
            cleaned = part.strip()
            if cleaned and cleaned not in ordered_keys:
                ordered_keys.append(cleaned)

    single_key = os.getenv("GROQ_API_KEY", "").strip()
    if not single_key and not ordered_keys:
        single_key = _get_setting_or_env("GROQ_API_KEY", "")
    if single_key and single_key not in ordered_keys:
        ordered_keys.append(single_key)

    return ordered_keys


def get_primary_model(explicit_model: Optional[str] = None) -> str:
    """Returns the primary Groq model independent of API key selection."""
    if explicit_model and str(explicit_model).strip():
        return str(explicit_model).strip()
    return _get_setting_or_env("GROQ_MODEL", DEFAULT_GROQ_MODEL)


def get_fallback_models() -> List[str]:
    """Returns optional comma-separated fallback models from GROQ_FALLBACK_MODELS."""
    raw = _get_setting_or_env("GROQ_FALLBACK_MODELS", "")
    return [m.strip() for m in raw.split(",") if m.strip()]


def get_model_candidates(explicit_model: Optional[str] = None) -> List[str]:
    """Returns deduplicated ordered model candidates: [primary, ...fallbacks]."""
    primary = get_primary_model(explicit_model=explicit_model)
    fallbacks = get_fallback_models()
    ordered: List[str] = []
    for candidate in [primary] + fallbacks:
        if candidate and candidate not in ordered:
            ordered.append(candidate)
    return ordered


def _get_timeout(timeout: Optional[float] = None) -> float:
    if timeout is not None:
        return float(timeout)
    raw = _get_setting_or_env("GROQ_TIMEOUT", "")
    if raw:
        try:
            return max(1.0, float(raw))
        except ValueError:
            pass
    return DEFAULT_TIMEOUT_SECONDS


def _get_max_retries(max_retries: Optional[int] = None) -> int:
    if max_retries is not None:
        return max(1, int(max_retries))
    raw = _get_setting_or_env("GROQ_MAX_RETRIES", "")
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return DEFAULT_MAX_RETRIES


def _get_cooldown_seconds() -> int:
    raw = _get_setting_or_env("GROQ_KEY_COOLDOWN_SECONDS", "")
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return DEFAULT_COOLDOWN_SECONDS


def reset_groq_key_pool() -> None:
    """Resets the process-wide KeyPool (primarily for tests)."""
    global _SHARED_POOL, _SHARED_POOL_KEYS
    with _POOL_LOCK:
        _SHARED_POOL = None
        _SHARED_POOL_KEYS = ()


def get_groq_key_pool() -> KeyPool:
    """
    Returns the shared process-wide open-keypool `KeyPool` instance.
    Re-initializes if the configured environment key list has changed.
    """
    global _SHARED_POOL, _SHARED_POOL_KEYS
    keys = load_groq_api_keys()
    if not keys:
        raise GroqConfigurationError(
            "No Groq API keys configured. Set GROQ_API_KEY_1..N or GROQ_API_KEY."
        )

    keys_tuple = tuple(keys)
    with _POOL_LOCK:
        if _SHARED_POOL is None or _SHARED_POOL_KEYS != keys_tuple:
            _SHARED_POOL = KeyPool(
                keys=keys,
                max_retries=_get_max_retries(),
                cooldown_seconds=_get_cooldown_seconds(),
                strategy="round_robin",
                provider="groq",
            )
            _SHARED_POOL_KEYS = keys_tuple
            logger.info("Initialized Groq KeyPool with %s key(s).", len(keys))
        return _SHARED_POOL


def _extract_response_info(
    resp_or_exc: Any,
) -> Tuple[Optional[int], Dict[str, str], Any]:
    """
    Extracts `(status_code, headers, body)` from either a `requests.Response`
    or an exception object (e.g. Groq SDK `APIStatusError` with `.response` / `.status_code`).
    """
    if isinstance(resp_or_exc, Exception):
        resp = getattr(resp_or_exc, "response", None) or resp_or_exc
    else:
        resp = resp_or_exc
    status_code = getattr(resp, "status_code", None)
    if status_code is None and isinstance(resp_or_exc, Exception):
        status_code = getattr(resp_or_exc, "status_code", None)

    raw_headers = getattr(resp, "headers", None)
    headers: Dict[str, str] = dict(raw_headers) if raw_headers else {}

    body: Any = None
    if hasattr(resp, "json"):
        try:
            body = resp.json()
        except Exception:
            body = getattr(resp, "text", None)
    elif hasattr(resp, "text"):
        body = resp.text
    elif hasattr(resp_or_exc, "body"):
        body = getattr(resp_or_exc, "body", None)

    return status_code, headers, body


def _extract_chat_content(data: Any) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    choices = data.get("choices")
    if choices:
        ch = choices[0]
        message = ch.get("message") or ch
        if isinstance(message, dict):
            return message.get("content") or message.get("text")
        return str(message)
    if data.get("output"):
        try:
            return data["output"][0]["content"][0]["text"]
        except Exception:
            return None
    return None


def _execute_single_model_with_pool(
    pool: KeyPool,
    *,
    messages: List[Dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    timeout: float,
    max_attempts: int,
) -> str:
    url = f"{GROQ_BASE_URL}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
    }

    last_exc: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        key = pool.get_key()
        masked = mask_api_key(key)
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        try:
            logger.info(
                "Groq request attempt=%s/%s model=%s key=%s",
                attempt,
                max_attempts,
                model,
                masked,
            )
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.Timeout as exc:
            last_exc = exc
            logger.warning(
                "Groq timeout attempt=%s/%s model=%s key=%s",
                attempt,
                max_attempts,
                model,
                masked,
            )
            if attempt < max_attempts:
                time.sleep(min(DEFAULT_RETRY_BACKOFF * attempt, 2.0))
            continue
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "Groq network error (%s) attempt=%s/%s model=%s key=%s",
                type(exc).__name__,
                attempt,
                max_attempts,
                model,
                masked,
            )
            if attempt < max_attempts:
                time.sleep(min(DEFAULT_RETRY_BACKOFF * attempt, 2.0))
            continue
        except Exception as exc:
            # Handles SDK-style exceptions if requests.post or a wrapped transport raises one
            status_code, resp_headers, resp_body = _extract_response_info(exc)
            if status_code is not None:
                key_state = pool.handle_response(key, status_code, resp_headers, resp_body)
                logger.warning(
                    "Groq SDK/HTTP exception status=%s state=%s model=%s key=%s",
                    status_code,
                    key_state.value if hasattr(key_state, "value") else key_state,
                    model,
                    masked,
                )
                last_exc = GroqAPIError(
                    f"Groq API returned HTTP status {status_code}",
                    status_code=status_code,
                )
                if status_code in (400, 404, 422):
                    raise last_exc
                if status_code >= 500 and attempt < max_attempts:
                    time.sleep(min(DEFAULT_RETRY_BACKOFF * attempt, 2.0))
                continue
            raise

        status_code, resp_headers, resp_body = _extract_response_info(resp)
        body_len = len(getattr(resp, "text", "") or "")
        logger.info("Groq status=%s len=%s model=%s key=%s", status_code, body_len, model, masked)

        if status_code == 200:
            pool.handle_response(key, 200, resp_headers, resp_body)
            content = _extract_chat_content(resp_body)
            if not content:
                raise GroqAPIError("Empty content returned by Groq", status_code=200)
            return str(content)

        if status_code is None:
            raise GroqAPIError("Groq response missing HTTP status code")

        # Do not penalize healthy keys or retry across keys on malformed/missing-model errors
        if status_code in (400, 404, 422):
            raise GroqAPIError(
                f"Groq API returned HTTP status {status_code}",
                status_code=status_code,
            )

        key_state = pool.handle_response(key, status_code, resp_headers, resp_body)
        last_exc = GroqAPIError(
            f"Groq API returned HTTP status {status_code}",
            status_code=status_code,
        )

        # 401/403 -> key marked DISABLED by handle_response; rotate to next active key
        if key_state == KeyState.DISABLED:
            logger.warning(
                "Groq key disabled (status=%s) key=%s; rotating if another active key exists.",
                status_code,
                masked,
            )
            continue

        # 429 -> key placed in COOLDOWN by handle_response; immediately rotate to next key
        if key_state == KeyState.COOLDOWN:
            logger.warning(
                "Groq key rate-limited (status=%s) key=%s; rotating to next active key.",
                status_code,
                masked,
            )
            continue

        # 5xx transient server error -> bounded backoff & retry
        if status_code >= 500 and attempt < max_attempts:
            time.sleep(min(DEFAULT_RETRY_BACKOFF * attempt, 2.0))
            continue

    raise last_exc or GroqAPIError("Groq call failed after bounded retries")


def groq_chat_completion(
    prompt: str,
    *,
    model: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    system_prompt: str = "You are an interview question generator.",
    temperature: float = 0.15,
    max_tokens: int = 2200,
    top_p: float = 0.95,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> str:
    """
    Centralized synchronous Groq chat completion using open-keypool rotation,
    bounded retries (no nested SDK retries), and optional model fallback.
    """
    pool = get_groq_key_pool()
    effective_timeout = _get_timeout(timeout)
    effective_retries = _get_max_retries(max_retries)
    msg_list = messages or [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    model_candidates = get_model_candidates(explicit_model=model)
    last_exc: Optional[Exception] = None

    for candidate_model in model_candidates:
        try:
            return _execute_single_model_with_pool(
                pool,
                messages=msg_list,
                model=candidate_model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                timeout=effective_timeout,
                max_attempts=effective_retries,
            )
        except (AllKeysExhaustedError, GroqConfigurationError):
            # Key exhaustion or missing config applies across all models; do not loop models
            raise
        except GroqAPIError as exc:
            last_exc = exc
            logger.warning(
                "Groq model=%s failed (status=%s): %s",
                candidate_model,
                exc.status_code,
                exc,
            )
            continue
        except Exception as exc:
            last_exc = exc
            logger.warning("Groq model=%s failed: %s", candidate_model, exc)
            continue

    raise last_exc or GroqAPIError("All configured Groq models failed")


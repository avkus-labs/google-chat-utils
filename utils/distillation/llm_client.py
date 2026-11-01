"""Minimal OpenAI-compatible chat-completion client with retry and disk cache.

Transport: httpx (sync). No provider auto-detection: base_url and model
are always passed explicitly (task 001 decision).
"""

import hashlib
import json
import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 2  # up to 2 retries after the first attempt


class LLMFatalError(Exception):
    """Non-retryable failure (4xx auth/client errors, exhausted retries)."""


class ChunkFailedError(Exception):
    """Model response finished with finish_reason != 'stop'."""


def cache_key(chunk_text: str, prompt_template: str, model: str, base_url: str) -> str:
    """sha256 over chunk + prompt + model + base_url.

    base_url is part of the key on purpose: different gateways behind
    different URLs must not share cache entries.
    """
    h = hashlib.sha256()
    for part in (chunk_text, prompt_template, model, base_url):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


class DistillCache:
    """File cache: .distill_cache/<sha256>.json next to the output."""

    def __init__(self, cache_dir: str):
        self.dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        return os.path.join(self.dir, f"{key}.json")

    def get(self, key: str):
        p = self._path(key)
        if not os.path.isfile(p):
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                content = json.load(f).get("content")
            # Treat empty/whitespace-only cached content as a miss (poisoned cache protection)
            if content is None or not content.strip():
                return None
            return content
        except Exception:
            return None

    def put(self, key: str, content: str) -> None:
        # Never cache empty or whitespace-only content
        if not content or not content.strip():
            return
        with open(self._path(key), "w", encoding="utf-8") as f:
            json.dump({"content": content}, f, ensure_ascii=False)


def chat_completion(base_url: str, model: str, prompt: str,
                    api_key: str = "", timeout: float = 600.0,
                    stream: bool = True) -> str:
    """POST {base_url}/chat/completions and return the message content.

    - 429/5xx: up to 2 retries with exponential backoff.
    - other 4xx: stop immediately (LLMFatalError).
    - finish_reason != 'stop': chunk is failed (ChunkFailedError).
    - stream=True: uses SSE streaming (httpx.stream). The timeout parameter
      sets the read pause between incoming bytes/chunks (via httpx.Timeout(timeout, connect=30.0)),
      not the overall duration of the entire request.
    - stream=False: falls back to standard non-streaming httpx.post.
    """
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    for attempt in range(MAX_RETRIES + 1):
        if not stream:
            try:
                resp = httpx.post(url, json=payload, headers=headers, timeout=timeout)
            except httpx.HTTPError as e:
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                    continue
                raise LLMFatalError(f"Network error after retries: {e}")

            if resp.status_code in RETRYABLE_STATUS:
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                    continue
                raise LLMFatalError(f"HTTP {resp.status_code} after retries")
            if resp.status_code >= 400:
                raise LLMFatalError(f"HTTP {resp.status_code}: {resp.text[:200]}")

            data = resp.json()
            choice = data["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise ChunkFailedError(
                    f"finish_reason={choice.get('finish_reason')!r}")
            content = choice["message"]["content"]
            if not content or not content.strip():
                raise ChunkFailedError("empty response")
            return content

        # Streaming mode (stream=True)
        collected_content = []
        last_finish_reason = None
        try:
            with httpx.stream(
                "POST",
                url,
                json={**payload, "stream": True},
                headers=headers,
                timeout=httpx.Timeout(timeout, connect=30.0),
            ) as resp:
                if resp.status_code in RETRYABLE_STATUS:
                    retry_status = resp.status_code
                elif resp.status_code >= 400:
                    body = resp.read().decode("utf-8", errors="replace")
                    raise LLMFatalError(f"HTTP {resp.status_code}: {body[:200]}")
                else:
                    retry_status = None
                    for line in resp.iter_lines():
                        line = line.strip()
                        if not line or line.startswith(":"):
                            continue
                        if not line.startswith("data:"):
                            continue
                        data_str = line[len("data:"):].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            event = json.loads(data_str)
                        except Exception:
                            logger.debug("Unrecognized JSON in SSE keep-alive: %r", data_str)
                            continue

                        if isinstance(event, dict) and "error" in event:
                            raise httpx.HTTPError(f"Stream error event: {event['error']}")

                        if not isinstance(event, dict):
                            continue

                        choices = event.get("choices")
                        if not choices or not isinstance(choices, list) or len(choices) == 0:
                            continue

                        choice0 = choices[0]
                        if not isinstance(choice0, dict):
                            continue

                        fr = choice0.get("finish_reason")
                        if fr is not None:
                            last_finish_reason = fr

                        delta = choice0.get("delta")
                        if isinstance(delta, dict):
                            content_piece = delta.get("content")
                            if content_piece:
                                collected_content.append(content_piece)

            if retry_status is not None:
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                    continue
                raise LLMFatalError(f"HTTP {retry_status} after retries")

            if last_finish_reason is None:
                raise httpx.HTTPError("Stream closed without finish_reason")

        except httpx.HTTPError as e:
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue
            raise LLMFatalError(f"Network error after retries: {e}")

        if last_finish_reason != "stop":
            raise ChunkFailedError(f"finish_reason={last_finish_reason!r}")
        result = "".join(collected_content)
        if not result.strip():
            raise ChunkFailedError("empty response")
        return result

    raise LLMFatalError("unreachable")
"""Minimal OpenAI-compatible chat-completion client with retry and disk cache.

Transport: httpx (sync). No provider auto-detection: base_url and model
are always passed explicitly (task 001 decision).
"""

import hashlib
import json
import os
import time

import httpx

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
                return json.load(f).get("content")
        except Exception:
            return None

    def put(self, key: str, content: str) -> None:
        with open(self._path(key), "w", encoding="utf-8") as f:
            json.dump({"content": content}, f, ensure_ascii=False)


def chat_completion(base_url: str, model: str, prompt: str,
                    api_key: str = "", timeout: float = 600.0) -> str:
    """POST {base_url}/chat/completions and return the message content.

    - 429/5xx: up to 2 retries with exponential backoff.
    - other 4xx: stop immediately (LLMFatalError).
    - finish_reason != 'stop': chunk is failed (ChunkFailedError).
    """
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    for attempt in range(MAX_RETRIES + 1):
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
        return choice["message"]["content"]

    raise LLMFatalError("unreachable")
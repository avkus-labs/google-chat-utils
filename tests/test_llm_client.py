"""Tests for LLM client and cache (httpx mocked, no network)."""

from unittest.mock import patch, MagicMock
import pytest

from utils.distillation.llm_client import (
    chat_completion, cache_key, DistillCache, LLMFatalError, ChunkFailedError,
)


def _mock_response(status=200, json_data=None, text=""):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


def _ok_response(content="answer"):
    return _mock_response(200, {
        "choices": [{"finish_reason": "stop",
                     "message": {"content": content}}]
    })


class TestChatCompletion:
    @patch("utils.distillation.llm_client.httpx.post")
    def test_success(self, mock_post):
        mock_post.return_value = _ok_response("привет")
        out = chat_completion("http://x/v1", "m", "prompt", "key")
        assert out == "привет"
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["model"] == "m"
        assert kwargs["headers"]["Authorization"] == "Bearer key"

    @patch("utils.distillation.llm_client.httpx.post")
    def test_url_construction(self, mock_post):
        mock_post.return_value = _ok_response()
        chat_completion("http://x/v1/", "m", "p")
        assert mock_post.call_args[0][0] == "http://x/v1/chat/completions"

    @patch("utils.distillation.llm_client.time.sleep")
    @patch("utils.distillation.llm_client.httpx.post")
    def test_retry_on_429_then_success(self, mock_post, mock_sleep):
        mock_post.side_effect = [_mock_response(429), _ok_response("ok")]
        out = chat_completion("http://x", "m", "p")
        assert out == "ok"
        assert mock_post.call_count == 2

    @patch("utils.distillation.llm_client.time.sleep")
    @patch("utils.distillation.llm_client.httpx.post")
    def test_429_exhausted(self, mock_post, mock_sleep):
        mock_post.return_value = _mock_response(429)
        with pytest.raises(LLMFatalError):
            chat_completion("http://x", "m", "p")
        assert mock_post.call_count == 3  # 1 + 2 retries

    @patch("utils.distillation.llm_client.time.sleep")
    @patch("utils.distillation.llm_client.httpx.post")
    def test_401_stops_immediately(self, mock_post, mock_sleep):
        mock_post.return_value = _mock_response(401, text="bad key")
        with pytest.raises(LLMFatalError):
            chat_completion("http://x", "m", "p")
        assert mock_post.call_count == 1

    @patch("utils.distillation.llm_client.httpx.post")
    def test_finish_reason_length_fails_chunk(self, mock_post):
        mock_post.return_value = _mock_response(200, {
            "choices": [{"finish_reason": "length",
                         "message": {"content": "truncated"}}]
        })
        with pytest.raises(ChunkFailedError):
            chat_completion("http://x", "m", "p")


class TestCacheKey:
    def test_base_url_changes_key(self):
        k1 = cache_key("chunk", "prompt", "model", "http://a")
        k2 = cache_key("chunk", "prompt", "model", "http://b")
        assert k1 != k2

    def test_model_changes_key(self):
        k1 = cache_key("chunk", "prompt", "m1", "http://a")
        k2 = cache_key("chunk", "prompt", "m2", "http://a")
        assert k1 != k2

    def test_deterministic(self):
        assert cache_key("a", "b", "c", "d") == cache_key("a", "b", "c", "d")


class TestDistillCache:
    def test_roundtrip(self, tmp_path):
        cache = DistillCache(str(tmp_path / ".distill_cache"))
        assert cache.get("k1") is None
        cache.put("k1", "content here")
        assert cache.get("k1") == "content here"

    def test_corrupt_file_returns_none(self, tmp_path):
        cache = DistillCache(str(tmp_path / "c"))
        with open(tmp_path / "c" / "bad.json", "w") as f:
            f.write("{not json")
        assert cache.get("bad") is None
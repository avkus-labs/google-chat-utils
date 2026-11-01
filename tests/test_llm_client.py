"""Tests for LLM client and cache (httpx mocked, no network)."""

from unittest.mock import patch, MagicMock
import httpx
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


class MockStreamResponse:
    def __init__(self, status_code=200, lines=None, text=""):
        self.status_code = status_code
        self.lines = lines or []
        self._text = text

    def iter_lines(self):
        for line in self.lines:
            if isinstance(line, Exception):
                raise line
            yield line

    def read(self):
        return self._text.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class TestChatCompletion:
    @patch("utils.distillation.llm_client.httpx.post")
    def test_success(self, mock_post):
        mock_post.return_value = _ok_response("привет")
        out = chat_completion("http://x/v1", "m", "prompt", "key", stream=False)
        assert out == "привет"
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["model"] == "m"
        assert kwargs["headers"]["Authorization"] == "Bearer key"

    @patch("utils.distillation.llm_client.httpx.post")
    def test_url_construction(self, mock_post):
        mock_post.return_value = _ok_response()
        chat_completion("http://x/v1/", "m", "p", stream=False)
        assert mock_post.call_args[0][0] == "http://x/v1/chat/completions"

    @patch("utils.distillation.llm_client.time.sleep")
    @patch("utils.distillation.llm_client.httpx.post")
    def test_retry_on_429_then_success(self, mock_post, mock_sleep):
        mock_post.side_effect = [_mock_response(429), _ok_response("ok")]
        out = chat_completion("http://x", "m", "p", stream=False)
        assert out == "ok"
        assert mock_post.call_count == 2

    @patch("utils.distillation.llm_client.time.sleep")
    @patch("utils.distillation.llm_client.httpx.post")
    def test_429_exhausted(self, mock_post, mock_sleep):
        mock_post.return_value = _mock_response(429)
        with pytest.raises(LLMFatalError):
            chat_completion("http://x", "m", "p", stream=False)
        assert mock_post.call_count == 3  # 1 + 2 retries

    @patch("utils.distillation.llm_client.time.sleep")
    @patch("utils.distillation.llm_client.httpx.post")
    def test_401_stops_immediately(self, mock_post, mock_sleep):
        mock_post.return_value = _mock_response(401, text="bad key")
        with pytest.raises(LLMFatalError):
            chat_completion("http://x", "m", "p", stream=False)
        assert mock_post.call_count == 1

    @patch("utils.distillation.llm_client.httpx.post")
    def test_finish_reason_length_fails_chunk(self, mock_post):
        mock_post.return_value = _mock_response(200, {
            "choices": [{"finish_reason": "length",
                         "message": {"content": "truncated"}}]
        })
        with pytest.raises(ChunkFailedError):
            chat_completion("http://x", "m", "p", stream=False)


class TestChatCompletionStream:
    @patch("utils.distillation.llm_client.httpx.stream")
    def test_stream_success_assembly(self, mock_stream):
        lines = [
            ": keep-alive comment",
            "",
            "event: ping",
            "data: not-a-json",
            'data: {"choices": []}',
            'data: {"choices": [{"delta": {"reasoning_content": "thinking..."}, "finish_reason": null}]}',
            'data: {"choices": [{"delta": {"content": "Привет, "}, "finish_reason": null}]}',
            ": another comment",
            'data: {"choices": [{"delta": {"content": "мир!"}, "finish_reason": null}]}',
            'data: {"choices": [{"delta": {}, "finish_reason": "stop"}]}',
            "data: [DONE]",
        ]
        mock_stream.return_value = MockStreamResponse(200, lines=lines)
        out = chat_completion("http://x/v1", "m", "prompt", "key")
        assert out == "Привет, мир!"
        args, kwargs = mock_stream.call_args
        assert args[0] == "POST"
        assert args[1] == "http://x/v1/chat/completions"
        assert kwargs["json"]["stream"] is True
        assert kwargs["json"]["model"] == "m"
        assert kwargs["headers"]["Authorization"] == "Bearer key"
        assert kwargs["timeout"].connect == 30.0
        assert kwargs["timeout"].read == 600.0

    @patch("utils.distillation.llm_client.httpx.stream")
    def test_finish_reason_length_fails_chunk(self, mock_stream):
        lines = [
            'data: {"choices": [{"delta": {"content": "truncated"}, "finish_reason": "length"}]}',
            "data: [DONE]",
        ]
        mock_stream.return_value = MockStreamResponse(200, lines=lines)
        with pytest.raises(ChunkFailedError):
            chat_completion("http://x", "m", "p")

    @patch("utils.distillation.llm_client.time.sleep")
    @patch("utils.distillation.llm_client.httpx.stream")
    def test_retry_on_429_then_success(self, mock_stream, mock_sleep):
        ok_lines = [
            'data: {"choices": [{"delta": {"content": "ok"}, "finish_reason": "stop"}]}',
            "data: [DONE]",
        ]
        mock_stream.side_effect = [
            MockStreamResponse(429),
            MockStreamResponse(200, lines=ok_lines),
        ]
        out = chat_completion("http://x", "m", "p")
        assert out == "ok"
        assert mock_stream.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @patch("utils.distillation.llm_client.time.sleep")
    @patch("utils.distillation.llm_client.httpx.stream")
    def test_429_exhausted(self, mock_stream, mock_sleep):
        mock_stream.return_value = MockStreamResponse(429)
        with pytest.raises(LLMFatalError, match="HTTP 429 after retries"):
            chat_completion("http://x", "m", "p")
        assert mock_stream.call_count == 3  # 1 + 2 retries

    @patch("utils.distillation.llm_client.time.sleep")
    @patch("utils.distillation.llm_client.httpx.stream")
    def test_401_stops_immediately(self, mock_stream, mock_sleep):
        mock_stream.return_value = MockStreamResponse(401, text="bad api key")
        with pytest.raises(LLMFatalError, match="HTTP 401: bad api key"):
            chat_completion("http://x", "m", "p")
        assert mock_stream.call_count == 1
        mock_sleep.assert_not_called()

    @patch("utils.distillation.llm_client.time.sleep")
    @patch("utils.distillation.llm_client.httpx.stream")
    def test_stream_closed_without_finish_reason_retries_and_fails(self, mock_stream, mock_sleep):
        lines = [
            'data: {"choices": [{"delta": {"content": "cutoff"}, "finish_reason": null}]}',
        ]
        mock_stream.return_value = MockStreamResponse(200, lines=lines)
        with pytest.raises(LLMFatalError, match="Network error after retries"):
            chat_completion("http://x", "m", "p")
        assert mock_stream.call_count == 3

    @patch("utils.distillation.llm_client.time.sleep")
    @patch("utils.distillation.llm_client.httpx.stream")
    def test_error_event_retries_and_succeeds(self, mock_stream, mock_sleep):
        err_lines = [
            'data: {"choices": [{"delta": {"content": "partial"}}, "finish_reason": null]}',
            'data: {"error": {"message": "overloaded"}}',
        ]
        ok_lines = [
            'data: {"choices": [{"delta": {"content": "clean answer"}, "finish_reason": "stop"}]}',
            "data: [DONE]",
        ]
        mock_stream.side_effect = [
            MockStreamResponse(200, lines=err_lines),
            MockStreamResponse(200, lines=ok_lines),
        ]
        out = chat_completion("http://x", "m", "p")
        assert out == "clean answer"
        assert mock_stream.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @patch("utils.distillation.llm_client.time.sleep")
    @patch("utils.distillation.llm_client.httpx.stream")
    def test_mid_stream_network_error_retries_and_discards_partial(self, mock_stream, mock_sleep):
        bad_lines = [
            'data: {"choices": [{"delta": {"content": "partial discarded"}, "finish_reason": null}]}',
            httpx.ReadTimeout("connection dropped"),
        ]
        ok_lines = [
            'data: {"choices": [{"delta": {"content": "final good text"}, "finish_reason": "stop"}]}',
            "data: [DONE]",
        ]
        mock_stream.side_effect = [
            MockStreamResponse(200, lines=bad_lines),
            MockStreamResponse(200, lines=ok_lines),
        ]
        out = chat_completion("http://x", "m", "p")
        assert out == "final good text"
        assert mock_stream.call_count == 2

    @patch("utils.distillation.llm_client.httpx.stream")
    def test_empty_content_with_finish_reason_stop(self, mock_stream):
        """006.A: stream returns finish_reason=stop but no content => ChunkFailedError."""
        lines = [
            'data: {"choices": [{"delta": {}, "finish_reason": "stop"}]}',
            "data: [DONE]",
        ]
        mock_stream.return_value = MockStreamResponse(200, lines=lines)
        with pytest.raises(ChunkFailedError, match="empty response"):
            chat_completion("http://x", "m", "p")


class TestEmptyResponseIntegrity:
    """006.A: empty response = ChunkFailedError, not cached."""

    @patch("utils.distillation.llm_client.httpx.post")
    def test_empty_content_non_stream_raises(self, mock_post):
        """006.A: non-stream empty content → ChunkFailedError."""
        mock_post.return_value = _mock_response(200, {
            "choices": [{"finish_reason": "stop", "message": {"content": ""}}]
        })
        with pytest.raises(ChunkFailedError, match="empty response"):
            chat_completion("http://x", "m", "p", stream=False)

    @patch("utils.distillation.llm_client.httpx.post")
    def test_whitespace_only_non_stream_raises(self, mock_post):
        """006.A: non-stream whitespace-only content → ChunkFailedError."""
        mock_post.return_value = _mock_response(200, {
            "choices": [{"finish_reason": "stop", "message": {"content": "   \n"}}]
        })
        with pytest.raises(ChunkFailedError, match="empty response"):
            chat_completion("http://x", "m", "p", stream=False)

    @patch("utils.distillation.llm_client.httpx.stream")
    def test_whitespace_only_stream_raises(self, mock_stream):
        """006.A: stream whitespace-only content → ChunkFailedError."""
        lines = [
            'data: {"choices": [{"delta": {"content": "   "}, "finish_reason": null}]}',
            'data: {"choices": [{"delta": {}, "finish_reason": "stop"}]}',
            "data: [DONE]",
        ]
        mock_stream.return_value = MockStreamResponse(200, lines=lines)
        with pytest.raises(ChunkFailedError, match="empty response"):
            chat_completion("http://x", "m", "p")


class TestCacheIntegrity:
    """006.A: cache protects against poisoning with empty values."""

    def test_put_empty_string_not_stored(self, tmp_path):
        cache = DistillCache(str(tmp_path / ".cache"))
        cache.put("k", "")
        assert cache.get("k") is None

    def test_put_whitespace_not_stored(self, tmp_path):
        cache = DistillCache(str(tmp_path / ".cache"))
        cache.put("k", "   \n")
        assert cache.get("k") is None

    def test_get_empty_cached_value_is_miss(self, tmp_path):
        """006.A: pre-existing poisoned cache (empty string) is treated as miss."""
        import json as _json
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        (cache_dir / "poisoned.json").write_text(
            _json.dumps({"content": ""}), encoding="utf-8"
        )
        cache = DistillCache(str(cache_dir))
        assert cache.get("poisoned") is None

    def test_get_whitespace_cached_value_is_miss(self, tmp_path):
        import json as _json
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        (cache_dir / "ws.json").write_text(
            _json.dumps({"content": "  \n"}), encoding="utf-8"
        )
        cache = DistillCache(str(cache_dir))
        assert cache.get("ws") is None

    def test_valid_content_cached_and_retrieved(self, tmp_path):
        cache = DistillCache(str(tmp_path / ".cache"))
        cache.put("k", "valid content")
        assert cache.get("k") == "valid content"


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
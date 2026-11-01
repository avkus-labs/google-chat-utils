"""Tests for the shared distillation pipeline (no network)."""

import argparse
import os
from unittest.mock import patch

import pytest

from utils.cli_v3 import _add_distill_options, build_distill_config
from utils.distillation.pipeline import (
    DistillConfig, DistillError, _SIOnlySignal, distill_human_markdown,
    prepare, validate_turn_headers,
)


# Sufficiently long turn body to pass the 200-char content check
_LONG_BODY = "Это длинный текст ответа модели. " * 7  # ~231 chars

HUMAN_MD = f"""# Chat: test

### System Instruction
> secret instruction

### **User**
вопрос про ключи, вот ключ sk-{"a" * 30}
### **Model**
{_LONG_BODY}
```python
x = 1
```
### **User**
уточнение про настройку
### **Model**
финальный ответ с деталями
"""


SI_ONLY_MD = """# Chat: BDX

### System Instruction
> Ты эксперт по деобфускации кода Bitrix.
> Используй анализ AST и паттерны.
> Всегда отвечай по-русски.
"""


def write_human(tmp_path, content=HUMAN_MD, name="chat_human.md"):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def cfg(**kw):
    base = dict(llm_base_url="http://test", llm_model="test-model",
                dry_run=True, chunk_tokens=50000)
    base.update(kw)
    return DistillConfig(**base)


class TestValidation:
    def test_no_headers_raises_code_2(self, tmp_path):
        p = tmp_path / "plain.md"
        p.write_text("просто текст без заголовков ходов", encoding="utf-8")
        with pytest.raises(DistillError) as e:
            validate_turn_headers(str(p))
        assert e.value.exit_code == 2

    def test_headers_ok(self, tmp_path):
        assert validate_turn_headers(write_human(tmp_path)) is None

    def test_si_only_document_mode_raises_signal(self, tmp_path):
        """007: SI-only file in document mode raises _SIOnlySignal."""
        p = tmp_path / "si_human.md"
        p.write_text(SI_ONLY_MD, encoding="utf-8")
        c = cfg(si_only="document")
        with pytest.raises(_SIOnlySignal):
            validate_turn_headers(str(p), c)

    def test_si_only_skip_mode_raises_distill_error(self, tmp_path):
        """007: SI-only file in skip mode raises DistillError exit=2."""
        p = tmp_path / "si_human.md"
        p.write_text(SI_ONLY_MD, encoding="utf-8")
        c = cfg(si_only="skip")
        with pytest.raises(DistillError) as exc:
            validate_turn_headers(str(p), c)
        assert exc.value.exit_code == 2

    def test_file_with_si_and_turns_passes(self, tmp_path):
        """007: file with both SI and turns is NOT SI-only."""
        assert validate_turn_headers(write_human(tmp_path)) is None


class TestPrepare:
    def test_si_omitted_thoughts_dropped(self, tmp_path):
        prep = prepare(write_human(tmp_path), cfg())
        assert "secret instruction" not in prep.text
        assert "[system instruction omitted:" in prep.text

    def test_secrets_redacted(self, tmp_path):
        prep = prepare(write_human(tmp_path), cfg())
        assert "sk-" + "a" * 30 not in prep.text
        assert prep.redaction_counts.get("sk_key") == 1

    def test_turns_numbered(self, tmp_path):
        prep = prepare(write_human(tmp_path), cfg())
        assert prep.turn_count == 4
        assert "[#1]" in prep.text and "[#4]" in prep.text

    def test_no_user_replies_sets_flag(self, tmp_path):
        """006.D: file with only Model headers sets no_user_replies=True."""
        model_only = "# Chat\n\n### **Model**\n" + _LONG_BODY + "\n### **Model**\n" + _LONG_BODY
        prep = prepare(write_human(tmp_path, model_only), cfg())
        assert prep.no_user_replies is True
        assert "[примечание пайплайна:" in prep.text

    def test_with_user_replies_flag_false(self, tmp_path):
        """006.D: normal file with user turns has no_user_replies=False."""
        prep = prepare(write_human(tmp_path), cfg())
        assert prep.no_user_replies is False
        assert "[примечание пайплайна:" not in prep.text

    def test_short_content_raises(self, tmp_path):
        """006.D: very short turn content raises DistillError."""
        tiny = "# Chat\n\n### **User**\nok\n### **Model**\nyes\n"
        p = write_human(tmp_path, tiny)
        with pytest.raises(DistillError) as exc:
            prepare(p, cfg())
        assert "содержимого для дистилляции" in str(exc.value)

    def test_turn_count_unchanged_for_no_user_replies(self, tmp_path):
        """006.D: turn_count reflects real turns, pipeline note doesn't add turns."""
        model_only = "# Chat\n\n### **Model**\n" + _LONG_BODY + "\n"
        prep = prepare(write_human(tmp_path, model_only), cfg())
        assert prep.turn_count == 1  # only 1 Model turn


class TestDistill:
    def test_dry_run_no_llm_no_output(self, tmp_path):
        p = write_human(tmp_path)
        result = distill_human_markdown(p, cfg())
        assert result is None
        assert not os.path.exists(str(tmp_path / "chat_distilled.md"))

    def test_existing_distilled_stops(self, tmp_path):
        p = write_human(tmp_path)
        (tmp_path / "chat_distilled.md").write_text("existing", encoding="utf-8")
        with pytest.raises(DistillError):
            distill_human_markdown(p, cfg(dry_run=False))

    def test_real_run_with_mocked_llm(self, tmp_path):
        p = write_human(tmp_path)
        chunk_answer = "### Тема (ходы 1–4)\nтекст"
        synth_answer = ('{"title": "Тест", "summary": "ок", "keywords": ["k"], '
                        '"tags": ["t"], "decisions_made": [], "lessons_learned": [], '
                        '"topics_covered": [], "open_questions": []}')
        with patch("utils.distillation.pipeline.chat_completion",
                   side_effect=[chunk_answer, synth_answer]) as mock_llm:
            out = distill_human_markdown(p, cfg(dry_run=False))
        assert out and os.path.isfile(out)
        content = open(out, encoding="utf-8").read()
        assert content.startswith("---")
        assert "source_sha256:" in content
        assert "## Ключевая информация" in content
        assert mock_llm.call_count == 2

    def test_cache_prevents_second_llm_call(self, tmp_path):
        p = write_human(tmp_path)
        chunk_answer = "### Тема (ходы 1–4)"
        synth_answer = '{"title": "Т", "summary": "", "keywords": [], "tags": [], "decisions_made": [], "lessons_learned": [], "topics_covered": [], "open_questions": []}'
        calls = []

        def fake_llm(*a, **k):
            calls.append(1)
            return chunk_answer if len(calls) == 1 else synth_answer

        with patch("utils.distillation.pipeline.chat_completion", side_effect=fake_llm):
            distill_human_markdown(p, cfg(dry_run=False))
        first_call_count = len(calls)
        # second run: output exists -> must stop, not silently overwrite
        with pytest.raises(DistillError):
            distill_human_markdown(p, cfg(dry_run=False))
        assert len(calls) == first_call_count

    def test_max_chunks_limits_calls(self, tmp_path):
        # tiny chunks force many chunks; max_chunks=1 limits them
        p = write_human(tmp_path)
        with patch("utils.distillation.pipeline.chat_completion",
                   side_effect=["(ходы 1)", '{"title":"t","summary":"","keywords":[],"tags":[],"decisions_made":[],"lessons_learned":[],"topics_covered":[],"open_questions":[]}']) as mock_llm:
            distill_human_markdown(p, cfg(dry_run=False, chunk_tokens=50, max_chunks=1))
        assert mock_llm.call_count == 2  # 1 chunk + 1 synthesis

    def test_pipeline_passes_llm_stream_true_by_default(self, tmp_path):
        p = write_human(tmp_path)
        with patch("utils.distillation.pipeline.chat_completion",
                   side_effect=["chunk output (ходы 1–4)", '{"title":"t","summary":"","keywords":[],"tags":[],"decisions_made":[],"lessons_learned":[],"topics_covered":[],"open_questions":[]}'
                                 ]) as mock_llm:
            distill_human_markdown(p, cfg(dry_run=False))
        assert mock_llm.call_count == 2
        for call in mock_llm.call_args_list:
            assert call.kwargs.get("stream") is True

    def test_pipeline_passes_llm_stream_false_when_configured(self, tmp_path):
        p = write_human(tmp_path)
        with patch("utils.distillation.pipeline.chat_completion",
                   side_effect=["chunk output (ходы 1–4)", '{"title":"t","summary":"","keywords":[],"tags":[],"decisions_made":[],"lessons_learned":[],"topics_covered":[],"open_questions":[]}'
                                 ]) as mock_llm:
            distill_human_markdown(p, cfg(dry_run=False, llm_stream=False))
        assert mock_llm.call_count == 2
        for call in mock_llm.call_args_list:
            assert call.kwargs.get("stream") is False


class TestDistillStrict:
    """006.B: --distill_strict tests."""

    def test_strict_aborts_on_missed_turns(self, tmp_path):
        """strict=True + missed turns => DistillError, no file."""
        p = write_human(tmp_path)
        chunk_answer = "### Тема (ходы 1–2)\nтекст"  # only covers 2 of 4 turns
        synth_answer = '{"title":"t","summary":"","keywords":[],"tags":[],"decisions_made":[],"lessons_learned":[],"topics_covered":[],"open_questions":[]}'
        with patch("utils.distillation.pipeline.chat_completion",
                   side_effect=[chunk_answer, synth_answer]):
            with pytest.raises(DistillError) as exc:
                distill_human_markdown(p, cfg(dry_run=False, strict=True))
        assert exc.value.exit_code == 2
        assert not os.path.exists(str(tmp_path / "chat_distilled.md"))

    def test_strict_allows_full_coverage(self, tmp_path):
        """strict=True + full coverage => file created."""
        p = write_human(tmp_path)
        chunk_answer = "### Тема (ходы 1–4)\nтекст"  # covers all 4 turns
        synth_answer = '{"title":"t","summary":"","keywords":[],"tags":[],"decisions_made":[],"lessons_learned":[],"topics_covered":[],"open_questions":[]}'
        with patch("utils.distillation.pipeline.chat_completion",
                   side_effect=[chunk_answer, synth_answer]):
            out = distill_human_markdown(p, cfg(dry_run=False, strict=True))
        assert out and os.path.isfile(out)

    def test_strict_false_does_not_abort_on_missed_turns(self, tmp_path):
        """strict=False (default) => file created even with missed turns."""
        p = write_human(tmp_path)
        chunk_answer = "### Тема (ходы 1–2)\nтекст"
        synth_answer = '{"title":"t","summary":"","keywords":[],"tags":[],"decisions_made":[],"lessons_learned":[],"topics_covered":[],"open_questions":[]}'
        with patch("utils.distillation.pipeline.chat_completion",
                   side_effect=[chunk_answer, synth_answer]):
            out = distill_human_markdown(p, cfg(dry_run=False, strict=False))
        assert out and os.path.isfile(out)


class TestDistillEmptyResponse:
    """006.A: empty response handling."""

    def test_empty_chunk_not_cached(self, tmp_path):
        """006.A: empty chunk response raises DistillError; nothing cached."""
        from utils.distillation.llm_client import ChunkFailedError
        p = write_human(tmp_path)
        calls = []

        def fake_llm(*a, **k):
            calls.append(1)
            raise ChunkFailedError("empty response")

        with patch("utils.distillation.pipeline.chat_completion", side_effect=fake_llm):
            with pytest.raises(DistillError):
                distill_human_markdown(p, cfg(dry_run=False))

        # cache dir shouldn't have anything useful
        cache_dir = str(tmp_path / ".distill_cache")
        if os.path.isdir(cache_dir):
            files = os.listdir(cache_dir)
            assert files == []  # nothing was cached

    def test_poisoned_cache_empty_string_is_miss(self, tmp_path):
        """006.A: cached empty string is treated as a miss."""
        from utils.distillation.llm_client import DistillCache
        cache = DistillCache(str(tmp_path / ".cache"))
        key = "testkey"
        # Manually poison the cache with an empty string
        import json
        cache_path = tmp_path / ".cache" / f"{key}.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({"content": ""}), encoding="utf-8")
        # get() should return None (miss)
        assert cache.get(key) is None

    def test_cache_put_skips_empty(self, tmp_path):
        """006.A: DistillCache.put() ignores empty content."""
        from utils.distillation.llm_client import DistillCache
        cache = DistillCache(str(tmp_path / ".cache"))
        cache.put("k", "")
        cache.put("k2", "   ")
        assert cache.get("k") is None
        assert cache.get("k2") is None

    def test_empty_synthesis_raises_distill_error(self, tmp_path):
        """006.A: empty synthesis response => DistillError."""
        p = write_human(tmp_path)
        chunk_answer = "### Тема (ходы 1–4)\nтекст"

        side_effects = [chunk_answer, ""]  # synthesis returns empty

        with patch("utils.distillation.pipeline.chat_completion",
                   side_effect=side_effects):
            with pytest.raises(DistillError) as exc:
                distill_human_markdown(p, cfg(dry_run=False))
        assert "пустой ответ" in str(exc.value).lower() or exc.value.exit_code in (1, 2)


class TestNoUserReplies:
    """006.D: chats without user replies."""

    def test_plan_line_shows_warning(self, tmp_path):
        """006.D: plan_line includes warning for no-user-replies files."""
        from utils.distillation.pipeline import plan_line
        model_only = "# Chat\n\n### **Model**\n" + _LONG_BODY + "\n"
        prep = prepare(write_human(tmp_path, model_only), cfg())
        line = plan_line(str(tmp_path / "chat_human.md"), prep)
        assert "нет реплик пользователя" in line

    def test_pipeline_note_in_text(self, tmp_path):
        """006.D: pipeline note prepended when no user replies."""
        model_only = "# Chat\n\n### **Model**\n" + _LONG_BODY + "\n"
        prep = prepare(write_human(tmp_path, model_only), cfg())
        assert "[примечание пайплайна:" in prep.text
        assert "подтверждений со стороны пользователя нет" in prep.text

    def test_dry_run_no_user_reply(self, tmp_path):
        """006.D: dry-run for no-user-replies still works."""
        model_only = "# Chat\n\n### **Model**\n" + _LONG_BODY + "\n"
        p = write_human(tmp_path, model_only)
        result = distill_human_markdown(p, cfg())
        assert result is None  # dry-run => None


class TestCliStreamFlag:
    def test_flags_parsing_in_all_commands(self):
        for cmd_name in ["parse", "distill", "fetch-drive"]:
            parser = argparse.ArgumentParser()
            _add_distill_options(parser)
            # Default without --llm_no_stream
            parsed_def = parser.parse_args([])
            assert parsed_def.llm_no_stream is False

            # With --llm_no_stream
            parsed_flag = parser.parse_args(["--llm_no_stream"])
            assert parsed_flag.llm_no_stream is True

    def test_build_distill_config_stream_mapping(self):
        parser = argparse.ArgumentParser()
        _add_distill_options(parser)

        # Default: llm_stream is True
        args_def = parser.parse_args([])
        cfg_def = build_distill_config(args_def)
        assert cfg_def.llm_stream is True

        # With --llm_no_stream: llm_stream is False
        args_no_stream = parser.parse_args(["--llm_no_stream"])
        cfg_no_stream = build_distill_config(args_no_stream)
        assert cfg_no_stream.llm_stream is False

    def test_distill_strict_flag(self):
        """006.B: --distill_strict flag parsed and mapped."""
        parser = argparse.ArgumentParser()
        _add_distill_options(parser)
        args = parser.parse_args(["--distill_strict"])
        c = build_distill_config(args)
        assert c.strict is True

    def test_distill_si_only_flag(self):
        """007: --distill_si_only flag parsed and mapped."""
        parser = argparse.ArgumentParser()
        _add_distill_options(parser)
        args_doc = parser.parse_args(["--distill_si_only", "document"])
        c_doc = build_distill_config(args_doc)
        assert c_doc.si_only == "document"

        args_skip = parser.parse_args(["--distill_si_only", "skip"])
        c_skip = build_distill_config(args_skip)
        assert c_skip.si_only == "skip"

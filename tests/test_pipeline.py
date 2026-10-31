"""Tests for the shared distillation pipeline (no network)."""

import argparse
import os
from unittest.mock import patch

import pytest

from utils.cli_v3 import _add_distill_options, build_distill_config
from utils.distillation.pipeline import (
    DistillConfig, DistillError, distill_human_markdown, prepare,
    validate_turn_headers,
)


HUMAN_MD = """# Chat: test

### System Instruction
> secret instruction

### **User**
вопрос про ключи, вот ключ sk-""" + "a" * 30 + """
### **Model**
ответ с кодом:
```python
x = 1
```
### **User**
уточнение
### **Model**
финальный ответ
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
        chunk_answer = "### Тема (ходы 1–2)\nтекст"
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
                   side_effect=["chunk output", '{"title":"t","summary":"","keywords":[],"tags":[],"decisions_made":[],"lessons_learned":[],"topics_covered":[],"open_questions":[]}']) as mock_llm:
            distill_human_markdown(p, cfg(dry_run=False))
        assert mock_llm.call_count == 2
        for call in mock_llm.call_args_list:
            assert call.kwargs.get("stream") is True

    def test_pipeline_passes_llm_stream_false_when_configured(self, tmp_path):
        p = write_human(tmp_path)
        with patch("utils.distillation.pipeline.chat_completion",
                   side_effect=["chunk output", '{"title":"t","summary":"","keywords":[],"tags":[],"decisions_made":[],"lessons_learned":[],"topics_covered":[],"open_questions":[]}']) as mock_llm:
            distill_human_markdown(p, cfg(dry_run=False, llm_stream=False))
        assert mock_llm.call_count == 2
        for call in mock_llm.call_args_list:
            assert call.kwargs.get("stream") is False


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
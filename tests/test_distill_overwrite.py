"""Tests for incremental distillation: skipping existing _distilled.md and --distill_overwrite flag."""

import argparse
import os
from unittest.mock import patch, MagicMock
import pytest

from utils.cli_v3 import run_distill_batch, _add_distill_options, handle_distill
from utils.distillation.pipeline import (
    DistillConfig,
    DistillError,
    distill_human_markdown,
)
from utils.distillation.llm_client import LLMFatalError
from utils.interactive import interactive_distill, interactive_parse


SAMPLE_HUMAN_MD = """# Chat: test

### System Instruction
> instruction

### **User**
Вопрос пользователя 1 с подробным описанием проблемы и контекста для проверки дистилляции.
### **Model**
Ответ модели 1 с техническими деталями, рекомендациями и примерами кода для решения задачи.
### **User**
Вопрос пользователя 2 с уточнениями по поводу предложенного решения и дополнительными требованиями.
### **Model**
Ответ модели 2 с финальным заключением и подтверждением работоспособности предложенного подхода.
"""


def create_human_file(tmp_path, name="test_human.md", content=SAMPLE_HUMAN_MD):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def make_args(tmp_path, overwrite=False, dry_run=False, assume_yes=True):
    return argparse.Namespace(
        llm_base_url="http://mock-llm:8000/v1",
        llm_model="mock-model",
        llm_api_key_env="DISTILL_API_KEY",
        distill_prompt_dir="prompts",
        chunk_tokens=30000,
        max_total_input_tokens=400000,
        distill_max_chunks=None,
        distill_thoughts="drop",
        distill_dry_run=dry_run,
        yes=assume_yes,
        distill_overwrite=overwrite,
    )


SYNTHESIS_MOCK_JSON = (
    '{"title": "Test Title", "summary": "Short summary", "keywords": ["kw1"], '
    '"tags": ["tag1"], "decisions_made": [], "lessons_learned": [], '
    '"topics_covered": [], "open_questions": []}'
)


class TestBatchSkipAndOverwrite:
    def test_batch_skip_existing_and_process_new(self, tmp_path):
        """[готовый, новый] -> LLM вызван только для нового; готовый не изменён."""
        h1 = create_human_file(tmp_path, "chat1_human.md")
        h2 = create_human_file(tmp_path, "chat2_human.md")

        # Existing distilled file for chat1
        d1 = tmp_path / "chat1_distilled.md"
        d1.write_text("ORIGINAL CHAT 1 CONTENT", encoding="utf-8")

        args = make_args(tmp_path, overwrite=False)

        with patch("utils.distillation.pipeline.chat_completion",
                   side_effect=["### Chunk summary", SYNTHESIS_MOCK_JSON]) as mock_llm:
            run_distill_batch([h1, h2], args, output_dir=str(tmp_path))

        # LLM must be called only for chat2 (1 chunk + 1 synthesis = 2 calls)
        assert mock_llm.call_count == 2

        # chat1 must remain untouched
        assert d1.read_text(encoding="utf-8") == "ORIGINAL CHAT 1 CONTENT"

        # chat2 distilled must be created
        d2 = tmp_path / "chat2_distilled.md"
        assert d2.exists()
        assert "Test Title" in d2.read_text(encoding="utf-8")

    def test_batch_order_new_ready_new(self, tmp_path):
        """[новый, готовый, новый] -> оба новых обработаны, готовый не тронут."""
        h1 = create_human_file(tmp_path, "chat1_human.md", content=SAMPLE_HUMAN_MD + "\nДополнение 1")
        h2 = create_human_file(tmp_path, "chat2_human.md")
        h3 = create_human_file(tmp_path, "chat3_human.md", content=SAMPLE_HUMAN_MD + "\nДополнение 3")

        d2 = tmp_path / "chat2_distilled.md"
        d2.write_text("ORIGINAL CHAT 2 CONTENT", encoding="utf-8")

        args = make_args(tmp_path, overwrite=False)

        # 2 calls per new file = 4 calls total
        with patch("utils.distillation.pipeline.chat_completion",
                   side_effect=["chunk 1", SYNTHESIS_MOCK_JSON, "chunk 3", SYNTHESIS_MOCK_JSON]) as mock_llm:
            run_distill_batch([h1, h2, h3], args, output_dir=str(tmp_path))

        assert mock_llm.call_count == 4
        assert d2.read_text(encoding="utf-8") == "ORIGINAL CHAT 2 CONTENT"
        assert (tmp_path / "chat1_distilled.md").exists()
        assert (tmp_path / "chat3_distilled.md").exists()

    def test_all_ready_no_llm_exit_0(self, tmp_path):
        """все готовые -> 0 вызовов LLM, выход 0, без запроса подтверждения."""
        h1 = create_human_file(tmp_path, "chat1_human.md")
        d1 = tmp_path / "chat1_distilled.md"
        d1.write_text("ALREADY DONE", encoding="utf-8")

        # assume_yes is False to verify input() is NOT called
        args = make_args(tmp_path, overwrite=False, assume_yes=False)

        with patch("utils.distillation.pipeline.chat_completion") as mock_llm, \
             patch("builtins.input", side_effect=AssertionError("input() should not be called!")):
            run_distill_batch([h1], args, output_dir=str(tmp_path))

        assert mock_llm.call_count == 0
        assert d1.read_text(encoding="utf-8") == "ALREADY DONE"

    def test_distill_overwrite_flag_regenerates(self, tmp_path):
        """с --distill_overwrite -> готовый регенерирован (вызовы LLM есть, содержимое заменено)."""
        h1 = create_human_file(tmp_path, "chat1_human.md")
        d1 = tmp_path / "chat1_distilled.md"
        d1.write_text("OLD PREVIOUS CONTENT", encoding="utf-8")

        args = make_args(tmp_path, overwrite=True)

        with patch("utils.distillation.pipeline.chat_completion",
                   side_effect=["New Chunk Content", SYNTHESIS_MOCK_JSON]) as mock_llm:
            run_distill_batch([h1], args, output_dir=str(tmp_path))

        assert mock_llm.call_count == 2
        content = d1.read_text(encoding="utf-8")
        assert "OLD PREVIOUS CONTENT" not in content
        assert "Test Title" in content

    def test_atomic_write_preserves_old_file_on_error(self, tmp_path):
        """сбой LLM при перезаписи -> старый файл цел (проверка атомарности)."""
        h1 = create_human_file(tmp_path, "chat1_human.md")
        d1 = tmp_path / "chat1_distilled.md"
        d1.write_text("CRUCIAL OLD CONTENT", encoding="utf-8")

        cfg = DistillConfig(
            llm_base_url="http://mock-llm",
            llm_model="mock-model",
            overwrite=True,
            output_dir=str(tmp_path),
            dry_run=False,
        )

        with patch("utils.distillation.pipeline.chat_completion",
                   side_effect=LLMFatalError("Connection failed")):
            with pytest.raises(DistillError):
                distill_human_markdown(h1, cfg)

        # File must remain untouched
        assert d1.read_text(encoding="utf-8") == "CRUCIAL OLD CONTENT"
        # .tmp must not exist
        assert not os.path.exists(str(d1) + ".tmp")


class TestCLIOptionsAndInteractive:
    def test_distill_options_parsing(self):
        """--distill_overwrite парсится в parse, distill, fetch-drive."""
        for cmd in ["parse", "distill", "fetch-drive"]:
            parser = argparse.ArgumentParser()
            _add_distill_options(parser)
            parsed = parser.parse_args(["--distill_overwrite"])
            assert parsed.distill_overwrite is True

            # default is False
            parsed_def = parser.parse_args([])
            assert parsed_def.distill_overwrite is False

    def test_interactive_distill_sets_overwrite(self):
        """Интерактивный режим distill запрашивает и устанавливает distill_overwrite."""
        mock_handler = MagicMock()
        handlers = {"distill": mock_handler}

        # Inputs: is_dir (n), input_file (Enter), llm_base_url, llm_model, llm_synthesis_model (Enter),
        # dry_run (n), distill_overwrite (y)
        with patch("builtins.input", side_effect=["n", "", "http://localhost:11434/v1", "test-model", "", "n", "y"]):
            interactive_distill(handlers)

        mock_handler.assert_called_once()
        args = mock_handler.call_args[0][0]
        assert getattr(args, "distill_overwrite", None) is True

    def test_interactive_parse_sets_overwrite(self):
        """Интерактивный режим parse запрашивает distill_overwrite если distill=True."""
        mock_handler = MagicMock()
        handlers = {"parse": mock_handler}

        # Inputs: is_dir (n), input_file (Enter), output_prefix (Enter), log_to_memory (n),
        # distill (y), distill_overwrite (y), llm_base_url, llm_model, llm_synthesis_model (Enter)
        with patch("builtins.input", side_effect=["n", "", "", "n", "y", "y", "http://localhost:11434/v1", "test-model", ""]):
            interactive_parse(handlers)

        mock_handler.assert_called_once()
        args = mock_handler.call_args[0][0]
        assert getattr(args, "distill_overwrite", None) is True


def test_handle_distill_recursive_input_dir(tmp_path):
    sub1 = tmp_path / "sub1"
    sub1.mkdir()
    h1 = sub1 / "chat1_human.md"
    h1.write_text(SAMPLE_HUMAN_MD, encoding="utf-8")

    sub2_deep = tmp_path / "sub2" / "deep"
    sub2_deep.mkdir(parents=True)
    h2 = sub2_deep / "chat2_human.md"
    h2.write_text(SAMPLE_HUMAN_MD, encoding="utf-8")

    cache_dir = tmp_path / ".distill_cache"
    cache_dir.mkdir()
    (cache_dir / "ignored_human.md").write_text(SAMPLE_HUMAN_MD, encoding="utf-8")

    args = argparse.Namespace(
        input_file=None,
        input_dir=str(tmp_path),
        output_dir=None,
        llm_base_url="http://test",
        llm_model="model",
        llm_synthesis_model="",
        llm_api_key_env="KEY",
        distill_prompt_dir="prompts",
        chunk_tokens=30000,
        max_total_input_tokens=400000,
        distill_max_chunks=None,
        distill_thoughts="drop",
        distill_overwrite=False,
        distill_dry_run=True,
        yes=True,
    )

    with patch("utils.cli_v3.run_distill_batch") as mock_batch:
        handle_distill(args)

    mock_batch.assert_called_once()
    found_files = mock_batch.call_args[0][0]
    assert len(found_files) == 2
    normalized_found = [os.path.normpath(f) for f in found_files]
    assert os.path.normpath(str(h1)) in normalized_found
    assert os.path.normpath(str(h2)) in normalized_found
    assert os.path.normpath(str(cache_dir / "ignored_human.md")) not in normalized_found

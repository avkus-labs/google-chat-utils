"""Tests for SI-only distillation mode (task 007)."""

import json
import os
from unittest.mock import patch

import pytest

from utils.distillation.pipeline import (
    DistillConfig, DistillError,
    distill_human_markdown, distill_si_document, is_si_only,
)


# SI-only file (System Instruction present, no User/Model turns)
SI_ONLY_MD = """# Chat: BDX Expert

### System Instruction
> Ты эксперт по деобфускации кода Bitrix (BDX).
> Используй анализ AST и паттерны деобфускации.
> Всегда отвечай по-русски с техническими примерами.
> Приоритет: безопасность и читаемость кода.
"""

# Normal file with both SI and turns
MIXED_MD = """# Chat: Normal

### System Instruction
> Системная инструкция

### **User**
вопрос
### **Model**
ответ достаточно длинный чтобы пройти проверку длины текста в пайплайне для дистилляции
""" + "Дополнительный текст. " * 10

SYNTH_ANSWER = json.dumps({
    "title": "BDX Expert",
    "summary": "Экспертная система для деобфускации Bitrix кода",
    "keywords": ["bitrix", "deobfuscation"],
    "tags": ["expert"],
    "decisions_made": [],
    "lessons_learned": [],
    "topics_covered": [],
    "open_questions": [],
})


def write_file(tmp_path, content, name="chat_human.md"):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def cfg(**kw):
    base = dict(llm_base_url="http://test", llm_model="test-model",
                dry_run=False, chunk_tokens=50000, si_only="document")
    base.update(kw)
    return DistillConfig(**base)


class TestIsSimOnly:
    def test_si_only_returns_true(self):
        assert is_si_only(SI_ONLY_MD) is True

    def test_mixed_returns_false(self):
        assert is_si_only(MIXED_MD) is False

    def test_no_si_returns_false(self):
        assert is_si_only("# Chat\n\n### **User**\nhello\n") is False

    def test_empty_returns_false(self):
        assert is_si_only("") is False


class TestDistillSIDocument:
    def test_si_document_creates_distilled(self, tmp_path):
        """007: SI-only file in document mode creates _distilled.md."""
        p = write_file(tmp_path, SI_ONLY_MD)
        with patch("utils.distillation.pipeline.chat_completion",
                   return_value=SYNTH_ANSWER) as mock_llm:
            out = distill_si_document(p, cfg())
        assert out and os.path.isfile(out)
        assert mock_llm.call_count == 1  # only synthesis, no chunk calls
        content = open(out, encoding="utf-8").read()
        # Frontmatter checks
        assert "chunks: 0" in content
        assert "source_kind: system_instruction" in content
        assert "trust_tier: ai-generated" in content
        # SI text verbatim (after redaction)
        assert "деобфускации кода Bitrix" in content
        # No turn_coverage in frontmatter
        assert "turn_coverage" not in content

    def test_si_document_dry_run(self, tmp_path):
        """007: dry_run=True skips LLM calls."""
        p = write_file(tmp_path, SI_ONLY_MD)
        with patch("utils.distillation.pipeline.chat_completion") as mock_llm:
            out = distill_si_document(p, cfg(dry_run=True))
        assert out is None
        assert mock_llm.call_count == 0

    def test_si_only_via_distill_human_markdown_document_mode(self, tmp_path):
        """007: distill_human_markdown routes SI-only file to distill_si_document."""
        p = write_file(tmp_path, SI_ONLY_MD)
        with patch("utils.distillation.pipeline.chat_completion",
                   return_value=SYNTH_ANSWER) as mock_llm:
            out = distill_human_markdown(p, cfg())
        assert out and os.path.isfile(out)
        assert mock_llm.call_count == 1

    def test_si_only_via_distill_human_markdown_skip_mode(self, tmp_path):
        """007: distill_human_markdown with skip mode raises DistillError exit=2."""
        p = write_file(tmp_path, SI_ONLY_MD)
        with patch("utils.distillation.pipeline.chat_completion"):
            with pytest.raises(DistillError) as exc:
                distill_human_markdown(p, cfg(si_only="skip"))
        assert exc.value.exit_code == 2
        assert not os.path.exists(str(tmp_path / "chat_distilled.md"))

    def test_mixed_file_uses_normal_path(self, tmp_path):
        """007: file with SI and turns uses normal distillation path."""
        p = write_file(tmp_path, MIXED_MD)
        chunk_answer = "### Тема (ходы 1–2)\nтекст"
        with patch("utils.distillation.pipeline.chat_completion",
                   side_effect=[chunk_answer, SYNTH_ANSWER]) as mock_llm:
            out = distill_human_markdown(p, cfg())
        assert out and os.path.isfile(out)
        content = open(out, encoding="utf-8").read()
        # Should NOT have source_kind: system_instruction
        assert "source_kind: system_instruction" not in content
        assert "chunks:" in content
        # Should have used chunk + synthesis calls
        assert mock_llm.call_count == 2

    def test_si_document_too_large(self, tmp_path):
        """007: SI text > chunk_tokens raises DistillError."""
        big_si = "# Chat\n\n### System Instruction\n> " + "x " * 200000
        p = write_file(tmp_path, big_si)
        with pytest.raises(DistillError) as exc:
            distill_si_document(p, cfg(chunk_tokens=100))
        assert "слишком большой" in str(exc.value).lower()

    def test_si_document_secret_redacted(self, tmp_path):
        """007: secrets in SI text are redacted in output."""
        si_with_secret = SI_ONLY_MD + "\n> API_KEY=sk-" + "z" * 30 + "\n"
        p = write_file(tmp_path, si_with_secret)
        with patch("utils.distillation.pipeline.chat_completion",
                   return_value=SYNTH_ANSWER):
            out = distill_si_document(p, cfg())
        content = open(out, encoding="utf-8").read()
        assert "sk-" + "z" * 30 not in content
        assert "[REDACTED]" in content

    def test_si_document_already_exists(self, tmp_path):
        """007: existing _distilled.md raises DistillError without overwrite."""
        p = write_file(tmp_path, SI_ONLY_MD)
        (tmp_path / "chat_distilled.md").write_text("existing", encoding="utf-8")
        with pytest.raises(DistillError):
            distill_si_document(p, cfg())

    def test_si_document_plan_line_contains_si_mode(self, tmp_path):
        """007: log output includes 'SI-документ' marker."""
        p = write_file(tmp_path, SI_ONLY_MD)
        logs = []

        def capture_log(msg):
            logs.append(msg)

        c = cfg(dry_run=True, log=capture_log)
        distill_si_document(p, c)
        assert any("SI-документ" in line for line in logs)

    def test_si_document_chunks_zero_in_frontmatter(self, tmp_path):
        """007: _distilled.md frontmatter has chunks: 0."""
        p = write_file(tmp_path, SI_ONLY_MD)
        with patch("utils.distillation.pipeline.chat_completion",
                   return_value=SYNTH_ANSWER):
            out = distill_si_document(p, cfg())
        content = open(out, encoding="utf-8").read()
        # Must have exactly 'chunks: 0'
        assert "\nchunks: 0\n" in content

    def test_si_document_no_resolution_failed_in_frontmatter(self, tmp_path):
        """007: SI document should not have resolution/failed_approaches fields."""
        p = write_file(tmp_path, SI_ONLY_MD)
        with patch("utils.distillation.pipeline.chat_completion",
                   return_value=SYNTH_ANSWER):
            out = distill_si_document(p, cfg())
        content = open(out, encoding="utf-8").read()
        # Extract frontmatter
        fm_end = content.find("---", 4)
        frontmatter = content[:fm_end]
        assert "resolution:" not in frontmatter
        assert "failed_approaches:" not in frontmatter


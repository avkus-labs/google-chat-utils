"""Tests for separate synthesis model (--llm_synthesis_model)."""

import argparse
from unittest.mock import patch, MagicMock


from utils.cli_v3 import _add_distill_options, build_distill_config, run_distill_batch
from utils.distillation.pipeline import (
    DistillConfig,
    distill_human_markdown,
    synthesis_model,
)
from utils.interactive import interactive_distill, interactive_parse


SAMPLE_HUMAN_MD = """# Chat: test

### System Instruction
> instruction

### **User**
Вопрос пользователя с подробным описанием проблемы и контекста для проверки дистилляции.
### **Model**
Ответ модели с техническими деталями, рекомендациями и примерами кода для решения задачи.
"""

SYNTH_JSON_OK = (
    '{"title": "Title", "summary": "Sum", "keywords": ["k"], '
    '"tags": ["t"], "decisions_made": [], "lessons_learned": [], '
    '"topics_covered": [], "open_questions": []}'
)


def create_human_file(tmp_path, name="chat_human.md", content=SAMPLE_HUMAN_MD):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_distill_config_synthesis_model_property():
    # Empty synthesis model falls back to llm_model
    cfg1 = DistillConfig(llm_model="model-A", llm_synthesis_model="")
    assert cfg1.synthesis_model == "model-A"
    assert synthesis_model(cfg1) == "model-A"

    # None or missing defaults to llm_model
    cfg2 = DistillConfig(llm_model="model-A")
    assert cfg2.synthesis_model == "model-A"
    assert synthesis_model(cfg2) == "model-A"

    # Explicit synthesis model
    cfg3 = DistillConfig(llm_model="model-A", llm_synthesis_model="model-B")
    assert cfg3.synthesis_model == "model-B"
    assert synthesis_model(cfg3) == "model-B"


def test_models_used_in_llm_calls_with_separate_synthesis_model(tmp_path):
    h = create_human_file(tmp_path)
    cfg = DistillConfig(
        llm_base_url="http://mock-llm:8000/v1",
        llm_model="chunk-model-A",
        llm_synthesis_model="synth-model-B",
        dry_run=False,
        output_dir=str(tmp_path),
    )

    call_records = []

    def fake_chat(base_url, model, prompt, api_key, timeout=120, *args, **kwargs):
        call_records.append({"model": model, "prompt": prompt})
        if "distilled_text" in prompt:
            return SYNTH_JSON_OK
        return "### Chunk summary (ходы 1–2)\nтекст"

    with patch("utils.distillation.pipeline.chat_completion", side_effect=fake_chat):
        out = distill_human_markdown(h, cfg)

    assert out is not None
    assert len(call_records) == 2
    # Chunk call uses chunk-model-A
    assert call_records[0]["model"] == "chunk-model-A"
    # Synthesis call uses synth-model-B
    assert call_records[1]["model"] == "synth-model-B"


def test_retry_invalid_json_uses_synthesis_model(tmp_path):
    h = create_human_file(tmp_path)
    cfg = DistillConfig(
        llm_base_url="http://mock-llm:8000/v1",
        llm_model="chunk-model-A",
        llm_synthesis_model="synth-model-B",
        dry_run=False,
        output_dir=str(tmp_path),
    )

    models_called = []

    def fake_chat(base_url, model, prompt, api_key, timeout=120, *args, **kwargs):
        models_called.append(model)
        if len(models_called) == 1:
            return "### Chunk summary (ходы 1–2)\nтекст"
        elif len(models_called) == 2:
            return "INVALID NON-JSON RESPONSE"
        else:
            return SYNTH_JSON_OK

    with patch("utils.distillation.pipeline.chat_completion", side_effect=fake_chat):
        out = distill_human_markdown(h, cfg)

    assert out is not None
    assert len(models_called) == 3
    assert models_called[0] == "chunk-model-A"
    assert models_called[1] == "synth-model-B"
    assert models_called[2] == "synth-model-B"


def test_without_synthesis_flag_all_calls_use_chunk_model(tmp_path):
    h = create_human_file(tmp_path)
    cfg = DistillConfig(
        llm_base_url="http://mock-llm:8000/v1",
        llm_model="single-model-A",
        dry_run=False,
        output_dir=str(tmp_path),
    )

    models_called = []

    def fake_chat(base_url, model, prompt, api_key, timeout=120, *args, **kwargs):
        models_called.append(model)
        if len(models_called) == 1:
            return "### Chunk summary (ходы 1–2)\nтекст"
        elif len(models_called) == 2:
            return "INVALID NON-JSON RESPONSE"
        else:
            return SYNTH_JSON_OK

    with patch("utils.distillation.pipeline.chat_completion", side_effect=fake_chat):
        out = distill_human_markdown(h, cfg)

    assert out is not None
    assert len(models_called) == 3
    assert all(m == "single-model-A" for m in models_called)


def test_cache_invalidation_isolated_to_synthesis(tmp_path):
    """Changing synthesis model does NOT invalidate chunk cache."""
    h = create_human_file(tmp_path)

    # First run: chunk-model-A + synth-model-B
    cfg1 = DistillConfig(
        llm_base_url="http://mock-llm:8000/v1",
        llm_model="chunk-model-A",
        llm_synthesis_model="synth-model-B",
        dry_run=False,
        output_dir=str(tmp_path),
        overwrite=True,
    )

    calls_run1 = []

    def fake_chat_1(base_url, model, prompt, api_key, timeout=120, *args, **kwargs):
        calls_run1.append((model, "synthesis" if "distilled_text" in prompt else "chunk"))
        if "distilled_text" in prompt:
            return SYNTH_JSON_OK
        return "### Chunk summary (ходы 1–2)\nтекст"

    with patch("utils.distillation.pipeline.chat_completion", side_effect=fake_chat_1):
        distill_human_markdown(h, cfg1)

    assert len(calls_run1) == 2
    assert calls_run1[0] == ("chunk-model-A", "chunk")
    assert calls_run1[1] == ("synth-model-B", "synthesis")

    # Second run: same chunk-model-A, different synth-model-C
    cfg2 = DistillConfig(
        llm_base_url="http://mock-llm:8000/v1",
        llm_model="chunk-model-A",
        llm_synthesis_model="synth-model-C",
        dry_run=False,
        output_dir=str(tmp_path),
        overwrite=True,
    )

    calls_run2 = []

    def fake_chat_2(base_url, model, prompt, api_key, timeout=120, *args, **kwargs):
        calls_run2.append((model, "synthesis" if "distilled_text" in prompt else "chunk"))
        if "distilled_text" in prompt:
            return SYNTH_JSON_OK
        return "### Chunk summary (ходы 1–2)\nтекст"

    with patch("utils.distillation.pipeline.chat_completion", side_effect=fake_chat_2):
        distill_human_markdown(h, cfg2)

    # Chunk should be served from cache! Only synthesis called.
    assert len(calls_run2) == 1
    assert calls_run2[0] == ("synth-model-C", "synthesis")


def test_frontmatter_synthesis_model_key(tmp_path):
    h = create_human_file(tmp_path)

    # Run with differing models: synthesis_model must be in frontmatter
    cfg_diff = DistillConfig(
        llm_base_url="http://mock-llm:8000/v1",
        llm_model="model-A",
        llm_synthesis_model="model-B",
        dry_run=False,
        output_dir=str(tmp_path),
        overwrite=True,
    )

    with patch("utils.distillation.pipeline.chat_completion",
               side_effect=["### Chunk (ходы 1–2)", SYNTH_JSON_OK]):
        out1 = distill_human_markdown(h, cfg_diff)

    content1 = open(out1, encoding="utf-8").read()
    assert 'synthesis_model: "model-B"' in content1
    assert '  by: "model-A"' in content1

    # Run with identical/empty synthesis model: synthesis_model must NOT be in frontmatter
    cfg_same = DistillConfig(
        llm_base_url="http://mock-llm:8000/v1",
        llm_model="model-A",
        llm_synthesis_model="",
        dry_run=False,
        output_dir=str(tmp_path),
        overwrite=True,
    )

    with patch("utils.distillation.pipeline.chat_completion",
               side_effect=["### Chunk (ходы 1–2)", SYNTH_JSON_OK]):
        out2 = distill_human_markdown(h, cfg_same)

    content2 = open(out2, encoding="utf-8").read()
    assert "synthesis_model:" not in content2
    assert '  by: "model-A"' in content2


def test_cli_flags_parsing():
    for cmd in ["parse", "distill", "fetch-drive"]:
        parser = argparse.ArgumentParser()
        _add_distill_options(parser)
        parsed = parser.parse_args(["--llm_synthesis_model", "synth-X"])
        assert parsed.llm_synthesis_model == "synth-X"

        parsed_def = parser.parse_args([])
        assert parsed_def.llm_synthesis_model == ""

    # build_distill_config test
    args = argparse.Namespace(
        llm_base_url="http://test",
        llm_model="mod-A",
        llm_synthesis_model="mod-B",
        llm_api_key_env="DISTILL_API_KEY",
        distill_prompt_dir="prompts",
        chunk_tokens=30000,
        max_total_input_tokens=400000,
        distill_max_chunks=None,
        distill_thoughts="drop",
        distill_dry_run=False,
        yes=True,
        distill_overwrite=False,
    )
    cfg = build_distill_config(args)
    assert cfg.llm_model == "mod-A"
    assert cfg.llm_synthesis_model == "mod-B"
    assert cfg.synthesis_model == "mod-B"

    # Compatibility when args lacks llm_synthesis_model
    del args.llm_synthesis_model
    cfg_compat = build_distill_config(args)
    assert cfg_compat.llm_synthesis_model == ""
    assert cfg_compat.synthesis_model == "mod-A"


def test_interactive_passes_synthesis_model():
    mock_handler = MagicMock()
    handlers = {"distill": mock_handler}

    # Inputs: is_dir (n), input_file (Enter), llm_base_url, llm_model, llm_synthesis_model,
    # dry_run (n), distill_overwrite (n)
    with patch("builtins.input", side_effect=["n", "", "http://test", "model-A", "model-B", "n", "n"]):
        interactive_distill(handlers)

    mock_handler.assert_called_once()
    args = mock_handler.call_args[0][0]
    assert args.llm_model == "model-A"
    assert args.llm_synthesis_model == "model-B"


def test_interactive_refuses_without_model(capsys):
    mock_handler = MagicMock()
    handlers = {"distill": mock_handler, "parse": mock_handler}

    # When DISTILLER_MODEL is unset and user hits Enter (empty)
    with patch("os.getenv", return_value=""), \
         patch("builtins.input", side_effect=["n", "", "http://test", "", "n", "n"]):
        interactive_distill(handlers)

    mock_handler.assert_not_called()
    out = capsys.readouterr().out
    assert "требует явных" in out

    # Same for interactive_parse
    with patch("os.getenv", return_value=""), \
         patch("builtins.input", side_effect=["n", "", "", "n", "y", "n", "http://test", ""]):
        interactive_parse(handlers)

    mock_handler.assert_not_called()


def test_batch_plan_and_dry_run_prints_models(tmp_path, capsys):
    h = create_human_file(tmp_path)
    args = argparse.Namespace(
        llm_base_url="http://mock-llm:8000/v1",
        llm_model="model-A",
        llm_synthesis_model="model-B",
        llm_api_key_env="DISTILL_API_KEY",
        distill_prompt_dir="prompts",
        chunk_tokens=30000,
        max_total_input_tokens=400000,
        distill_max_chunks=None,
        distill_thoughts="drop",
        distill_dry_run=True,
        yes=True,
        distill_overwrite=False,
    )

    run_distill_batch([h], args, output_dir=str(tmp_path))
    out = capsys.readouterr().out
    assert "модели: чанки=model-A, synthesis=model-B" in out
    assert "[dry-run]" in out

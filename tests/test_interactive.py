from unittest.mock import patch, MagicMock
from utils.interactive import (
    prompt_input,
    prompt_bool,
    run_interactive_menu,
    interactive_validate,
    interactive_distill,
)
from utils.cli_v3 import build_distill_config


def test_prompt_input_default():
    with patch("builtins.input", return_value=""):
        res = prompt_input("Enter name", default="default_val")
        assert res == "default_val"


def test_prompt_input_custom():
    with patch("builtins.input", return_value="my_custom_input"):
        res = prompt_input("Enter name", default="default_val")
        assert res == "my_custom_input"


def test_prompt_bool_default():
    with patch("builtins.input", return_value=""):
        assert prompt_bool("Proceed?", default=True) is True
        assert prompt_bool("Proceed?", default=False) is False


def test_prompt_bool_variations():
    for val in ["y", "Y", "yes", "YES", "да", "1"]:
        with patch("builtins.input", return_value=val):
            assert prompt_bool("Proceed?", default=False) is True

    for val in ["n", "no", "нет", "0", "anything_else"]:
        with patch("builtins.input", return_value=val):
            assert prompt_bool("Proceed?", default=True) is False


def test_interactive_validate_call():
    mock_validate = MagicMock()
    handlers = {"validate": mock_validate}

    with patch("builtins.input", return_value="custom_path.json"):
        interactive_validate(handlers)

    mock_validate.assert_called_once()
    args = mock_validate.call_args[0][0]
    assert args.input_file == "custom_path.json"


def test_run_interactive_menu_exit():
    handlers = {}
    with patch("builtins.input", return_value="0"):
        # Should cleanly exit without loop
        run_interactive_menu(handlers)


def test_interactive_distill_builds_valid_config():
    captured_args = []
    handlers = {"distill": lambda args: captured_args.append(args)}

    # Inputs:
    # 1. is_dir (y)
    # 2. input_dir ("output_data")
    # 3. llm_base_url ("http://mock:8000/v1")
    # 4. llm_model ("model-test")
    # 5. llm_synthesis_model ("")
    # 6. dry_run (y)
    # 7. distill_overwrite (n)
    inputs = [
        "y",
        "output_data",
        "http://mock:8000/v1",
        "model-test",
        "",
        "y",
        "n",
    ]
    with patch("builtins.input", side_effect=inputs):
        interactive_distill(handlers)

    assert len(captured_args) == 1
    args = captured_args[0]
    # Verify build_distill_config works without any AttributeError
    cfg = build_distill_config(args)
    assert cfg.llm_base_url == "http://mock:8000/v1"
    assert cfg.llm_model == "model-test"
    assert cfg.llm_api_key_env == "DISTILL_API_KEY"
    assert cfg.prompt_dir == "prompts"
    assert cfg.dry_run is True
    assert cfg.overwrite is False
    assert cfg.llm_stream is True


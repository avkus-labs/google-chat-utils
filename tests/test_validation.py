import os
from utils.validation import (
    validate_studio_export,
    validate_json_file,
)


def test_validate_example_file():
    example_path = os.path.join("data", "Example")
    assert os.path.isfile(example_path)

    result = validate_json_file(example_path)
    assert result.is_valid is True
    assert result.format_type == "studio_raw"
    assert len(result.errors) == 0
    assert result.validated_model is not None


def test_validate_intermediate_format():
    intermediate_data = {
        "source_file_name": "test.json",
        "parsed_at_timestamp": "2026-10-31T00:00:00Z",
        "run_settings": {"model": "gemini-1.5-pro"},
        "dialogue_history": [
            {
                "role": "user",
                "parts": [{"type": "text", "content": "Hello"}],
                "turn_id": 1
            }
        ],
        "tool_configurations": []
    }
    result = validate_studio_export(intermediate_data)
    assert result.is_valid is True
    assert result.format_type == "intermediate"
    assert len(result.errors) == 0


def test_validate_invalid_intermediate():
    # dialogue_history is not a list
    invalid_data = {
        "dialogue_history": "invalid_not_a_list",
        "tool_configurations": []
    }
    result = validate_studio_export(invalid_data)
    assert result.is_valid is False
    assert result.format_type == "intermediate"
    assert len(result.errors) > 0


def test_validate_invalid_temperature():
    bad_studio_data = {
        "runSettings": {
            "temperature": 5.0,  # exceeds max 2.0
            "model": "gemini-2.0"
        },
        "chunkedPrompt": {"chunks": []}
    }
    result = validate_studio_export(bad_studio_data)
    assert result.is_valid is False
    assert result.format_type == "studio_raw"
    assert any("temperature" in err for err in result.errors)


def test_validate_unrecognized_json():
    random_json = {"some_unknown_key": "some_value"}
    result = validate_studio_export(random_json)
    assert result.is_valid is False
    assert result.format_type == "unknown"


def test_validate_nonexistent_file():
    result = validate_json_file("nonexistent_path_to_file.json")
    assert result.is_valid is False
    assert "File not found" in result.errors[0]


def test_validate_corrupt_json_string():
    result = validate_studio_export("{not valid json: 123}")
    assert result.is_valid is False
    assert "Invalid JSON syntax" in result.errors[0]


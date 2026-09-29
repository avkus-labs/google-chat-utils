# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commonly Used Commands

### Environment Setup

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### Testing & Linting

```bash
# Run all tests (run from project root)
pytest

# Run a single test file
pytest tests/test_parsing.py
pytest tests/test_reconstruction.py
pytest tests/test_studio_json_reconstruction.py

# Run a single test function
pytest tests/test_parsing.py -k test_parse_example1

# Run tests with coverage
coverage run -m pytest && coverage report

# Lint code
pylint utils/ tests/
```

### CLI Commands (`utils/cli_v3.py`)

All commands can be run directly from the repository root:

- **Parse Google AI Studio Chat Exports:**
  ```bash
  # Parse single file (generates intermediate.json, raw_rag.md, human.md in output_prefix)
  python utils/cli_v3.py parse --input_file <path_to_chat_file> --output_prefix output_data/

  # Parse directory of chat exports
  python utils/cli_v3.py parse --input_dir data/ --output_prefix output_data/

  # Parse and automatically send human.md to Memory Compiler daily log
  python utils/cli_v3.py parse --input_file <path_to_chat_file> --output_prefix output_data/ --log_to_memory
  ```

- **Reconstruct Python Code:**
  ```bash
  python utils/cli_v3.py reconstruct \
      --input_json <path_to_intermediate.json> \
      --output_py <output_script_name.py> \
      --template_dir templates/ \
      --template_name gemini_studio_vanilla.py.tpl \
      --model_name "gemini-2.5-flash"
  ```
  *(Note: `--model_name` is required. Available templates: `gemini_studio_vanilla.py.tpl`, `gemini_studio_dynamic_si.py.tpl`).*

- **Apply Overrides to Raw Studio JSON:**
  ```bash
  python utils/cli_v3.py apply_overrides_to_studio_json \
      --input_studio_json <path_to_raw.json> \
      --output_studio_json <path_to_modified.json> \
      --si_file <path_to.si> \
      --fi_file <path_to.fi> \
      --li_file <path_to.li> \
      --fi_mode replace \
      --li_mode replace
  ```

- **Log Text / Markdown to Memory Compiler:**
  ```bash
  python utils/cli_v3.py log --input_file <path_to_file.md> --section "Custom Section Title"
  ```

### Schema Transformation

```bash
# OpenAI JSON Schema -> Gemini SchemaData (JSON)
python -m utils.transformation.schema_transformer \
    --openai_to_gemini data/example_openai_schema.json output_data/example_gemini_schema.json

# Gemini SchemaData (JSON) -> OpenAI JSON Schema
python -m utils.transformation.schema_transformer \
    --gemini_to_openai data/example_gemini_schema.json output_data/example_openai_schema_out.json

# Gemini SchemaData (JSON) -> Python code for genai.types.Schema
python -m utils.transformation.schema_transformer \
    --gemini_to_python data/example_gemini_schema.json output_data/example_gemini_schema.py
```

## High-Level Architecture

The repository parses Google AI Studio chat session exports, converts them into a structured intermediate object model, exports Markdown for RAG/Memory Compiler, and reconstructs executable Python scripts or modified Studio JSON files.

- **`utils/core/` (Data Models):**
  - `chat_elements.py`: Defines object-oriented models for chats (`IntermediateChatData`, `ChatMessage`, and part types: `TextPart`, `ThoughtsPart`, `ExecutableCodePart`, `CodeExecutionResultPart`, `FunctionCallPart`, `FunctionResponsePart`, `InlineDataPart`, `UriReferencePart`). Handles serialization (`to_dict`) and deserialization (`from_dict`).
  - `schema_elements.py`: Models for Gemini and OpenAI JSON schemas (`SchemaElement`, `Property`).

- **`utils/parsing/` (Ingestion & Extraction):**
  - `google_studio_parser.py`: Implements `GoogleAIStudioJSONParser`. Normalizes raw chat chunks, extracts system instructions and role turns (user/model), checks for companion override files (`.si` system instruction, `.fi` first input, `.li` last input), and generates both RAG Markdown (`_raw_rag.md`, `_human.md`) and intermediate JSON (`_intermediate.json`).

- **`utils/reconstruction/` (Code Generation):**
  - `gemini_code_reconstructor.py`: Implements `GeminiAPICodeReconstructor`. Reconstructs runnable Python scripts targeting Google GenAI SDK using templates in `templates/` (e.g. `gemini_studio_vanilla.py.tpl`).
  - `studio_json_modifier.py`: Modifies raw Studio JSON by patching chunks directly with `.si`, `.fi`, and `.li` override files.

- **`utils/transformation/` (Schema Conversion):**
  - `schema_transformer.py`: Standalone CLI & converter between OpenAI JSON Schema, Gemini SchemaData, and Python `google.genai.types.Schema` code.

- **`utils/cli_v3.py` (Unified CLI):**
  - Orchestrates parser, reconstructor, Studio JSON modifier, and logging subcommands. Handles path normalization across Windows and Linux.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commonly Used Commands

### Installation

1.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate # for Linux/macOS
    # venv\Scripts\activate # for Windows
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Linting

To run the linter, use the following command:
```bash
pylint utils/ tests/
```

### Running Tests

-   To run all tests, navigate to the `utils` directory and run:
    ```bash
    pytest
    ```
-   To run a single test file:
    ```bash
    pytest tests/test_parsing.py
    ```
- To run tests with coverage:
    ```bash
    coverage run -m pytest && coverage report
    ```

### Parsing a Chat

-   To parse a single Google AI Studio chat export:
    ```bash
    python utils/cli_v3.py parse --input_file <path_to_chat_file> --output_prefix <output_directory>
    ```
- To parse all JSON files in a directory:
    ```bash
    python utils/cli_v3.py parse --input_dir data/ --output_prefix output_data/
    ```

### Reconstructing Python Code

-   To reconstruct Python code from a parsed chat:
    ```bash
    python utils/cli_v3.py reconstruct \
        --input_json <path_to_intermediate.json> \
        --output_py <output_python_file.py> \
        --template_dir templates/ \
        --template_name gemini_studio_vanilla.py.tpl
    ```

### Reconstructing a Studio JSON File

- To reconstruct a valid JSON file for Google AI Studio from an intermediate JSON file:
    ```bash
    python utils/cli_v3.py reconstruct_studio_json \
        --input_intermediate_json <path_to_intermediate.json> \
        --output_studio_json_file <output_studio_json_file>
    ```

### Transforming Schemas
- **OpenAI JSON Schema → Gemini SchemaData (JSON):**
  ```bash
  python -m utils.transformation.schema_transformer \
      --openai_to_gemini data/example_openai_schema.json output_data/example_gemini_schema.json
  ```
- **Gemini SchemaData (JSON) → OpenAI JSON Schema:**
  ```bash
  python -m utils.transformation.schema_transformer \
      --gemini_to_openai data/example_gemini_schema.json output_data/example_openai_schema_out.json
  ```
- **Gemini SchemaData (JSON) → Python-код для genai.types.Schema:**
  ```bash
  python -m utils.transformation.schema_transformer \
      --gemini_to_python data/example_gemini_schema.json output_data/example_gemini_schema.py
  ```

## Code Architecture

The project is structured as a Python library with a command-line interface. The core logic is in the `utils` directory, which is further divided into the following key modules:

-   `core`: Contains the data models for representing chat elements.
-   `parsing`: Includes the `GoogleAIStudioJSONParser` for parsing chat exports and generating Markdown.
-   `reconstruction`: Contains the `GeminiAPICodeReconstructor` for generating Python code from parsed chats.
-   `transformation`: Provides the `SchemaTransformer` for converting JSON Schema between different formats.
-   `cli_v3.py`: The main entry point for the command-line interface.
-   `tests`: Contains unit tests for the various components of the library.
-   `templates`: Stores the templates used for code reconstruction.

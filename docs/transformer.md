# Трансформер схем (`SchemaTransformer`)

Этот компонент отвечает за преобразование JSON Schema между различными форматами: внутренним представлением `SchemaData`, словарем Python в стиле OpenAI и строкой Python-кода для `genai.types.Schema`.

## Класс `SchemaTransformer`

Обрабатывает преобразования, связанные с JSON Schema:
1.  Конвертация `SchemaData` в Python-код для `genai.types.Schema`.
2.  Конвертация JSON-схемы OpenAI в `SchemaData`.
3.  Конвертация `SchemaData` обратно в JSON-схему OpenAI.

### Публичные методы

*   `gemini_schema_obj_to_python_code(self, schema_obj: SchemaData) -> str`
*   `openai_to_gemini_schema(self, openai_schema_dict: Dict[str, Any]) -> SchemaData`
*   `gemini_schema_to_openai_dict(self, schema_obj: SchemaData) -> Dict[str, Any]`

---

## Использование через CLI

Модуль `schema_transformer` можно вызывать напрямую из командной строки для быстрой конвертации файлов.

### Примеры команд:

*   **OpenAI JSON Schema → Gemini SchemaData (JSON):**
    ```bash
    python -m utils.transformation.schema_transformer \
        --openai_to_gemini data/example_openai_schema.json output_data/example_gemini_schema.json
    ```
*   **Gemini SchemaData (JSON) → OpenAI JSON Schema:**
    ```bash
    python -m utils.transformation.schema_transformer \
        --gemini_to_openai data/example_gemini_schema.json output_data/example_openai_schema_out.json
    ```
*   **Gemini SchemaData (JSON) → Python-код (`.py`):**
    ```bash
    python -m utils.transformation.schema_transformer \
        --gemini_to_python data/example_gemini_schema.json output_data/example_gemini_schema.py
    ```

*Все примеры схем для тестирования находятся в папке `data/`.*

---

## Пример программного использования

```python
import json
from utils.core.schema_elements import SchemaData
from utils.transformation.schema_transformer import SchemaTransformer

# Инициализация трансформера
transformer = SchemaTransformer()

# 1. Пример: OpenAI schema (dict) -> SchemaData object
openai_schema = {
    "type": "object",
    "properties": {
        "location": {"type": "string", "description": "Город и штат"},
        "unit": {"type": ["string", "null"], "enum": ["celsius", "fahrenheit"]}
    },
    "required": ["location"]
}

schema_data_obj = transformer.openai_to_gemini_schema(openai_schema)
print("--- SchemaData Object (из OpenAI dict) ---")
print(schema_data_obj.properties.get('unit'))


# 2. Пример: SchemaData object -> Python code for genai.types.Schema
python_code_for_gemini = transformer.gemini_schema_obj_to_python_code(schema_data_obj)
print("\\n--- Python-код для genai.types.Schema ---")
print(python_code_for_gemini)


# 3. Пример: SchemaData object -> OpenAI schema (dict)
reverted_openai_schema = transformer.gemini_schema_to_openai_dict(schema_data_obj)
print("\\n--- OpenAI Schema (dict) (из SchemaData) ---")
print(json.dumps(reverted_openai_schema, indent=2, ensure_ascii=False))

# Проверка, что nullable свойство сохранилось
assert reverted_openai_schema.get('properties', {}).get('unit', {}).get('type') == ["string", "null"]

```

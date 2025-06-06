# Трансформер схем (`SchemaTransformer`)

Этот компонент отвечает за преобразование JSON Schema между различными форматами: внутренним представлением `SchemaData`, словарем Python в стиле OpenAI и строкой Python-кода для `genai.types.Schema` (используется в Gemini API).

## Класс `SchemaTransformer`

Обрабатывает преобразования, связанные с JSON Schema:
1.  Конвертация объекта `SchemaData` в Python-код для `genai.types.Schema`.
2.  Конвертация JSON-схемы OpenAI (словарь) в объект `SchemaData`.
3.  Конвертация объекта `SchemaData` обратно в JSON-схему OpenAI (словарь).

### Инициализация

#### `__init__(self)`

*   **Описание:** Инициализирует трансформер схем. На данный момент конструктор не выполняет сложной логики и не принимает аргументов.

### Публичные методы

#### `gemini_schema_obj_to_python_code(self, schema_obj: SchemaData, current_indent: str = "    ") -> str`

*   **Описание:** Рекурсивно преобразует объект `SchemaData` в строку Python-кода, представляющую объект `genai.types.Schema`. Этот код затем может быть использован при генерации скриптов для Gemini API.
*   **Параметры:**
    *   `schema_obj: SchemaData`: Объект `SchemaData` для преобразования.
    *   `current_indent: str`: Текущий уровень отступа для форматирования генерируемого кода (по умолчанию 4 пробела).
*   **Возвращает:** Строку Python-кода для инициализации `genai.types.Schema`.

#### `openai_to_gemini_schema(self, openai_schema_dict: Dict[str, Any]) -> SchemaData`

*   **Описание:** Рекурсивно преобразует словарь JSON Schema в стиле OpenAI в объект `SchemaData`. Типы данных в `SchemaData` (например, `type="OBJECT"`) сохраняются в верхнем регистре. Обрабатывает конструкции OpenAI, такие как `type: ["string", "null"]` для определения `nullable`.
*   **Параметры:**
    *   `openai_schema_dict: Dict[str, Any]`: Словарь, представляющий JSON Schema в стиле OpenAI.
*   **Возвращает:** Объект `SchemaData`, представляющий ту же схему.

#### `gemini_schema_to_openai_dict(self, schema_obj: SchemaData) -> Dict[str, Any]`

*   **Описание:** Рекурсивно преобразует объект `SchemaData` обратно в словарь JSON Schema в стиле OpenAI. Типы данных (например, `"object"`) приводятся к нижнему регистру. Корректно обрабатывает свойство `nullable` для различных типов согласно спецификациям OpenAI.
*   **Параметры:**
    *   `schema_obj: SchemaData`: Объект `SchemaData` для преобразования.
*   **Возвращает:** Словарь, представляющий JSON Schema в стиле OpenAI.

### Пример использования

```python
import json
from google_chat_utils_v3.core.schema_elements import SchemaData
from google_chat_utils_v3.transformation.schema_transformer import SchemaTransformer

# Инициализация трансформера
transformer = SchemaTransformer()

# 1. Пример: OpenAI schema (dict) -> SchemaData object
openai_schema = {
    "type": "object",
    "properties": {
        "location": {"type": "string", "description": "Город и штат, например, San Francisco, CA"},
        "unit": {"type": ["string", "null"], "enum": ["celsius", "fahrenheit"]}
    },
    "required": ["location"]
}

print("--- OpenAI Schema (dict) ---")
print(json.dumps(openai_schema, indent=2, ensure_ascii=False))

schema_data_obj = transformer.openai_to_gemini_schema(openai_schema)
print("\n--- SchemaData Object (из OpenAI dict) ---")
print(schema_data_obj)
# Вывод покажет внутреннее представление SchemaData, например:
# SchemaData(type='OBJECT', description='None', nullable=False, properties=True, items=False, enum=None, required=['location'])
# Для детального просмотра свойств нужно будет обратиться к ним напрямую:
if schema_data_obj.properties:
    print(f"Свойство 'location': {schema_data_obj.properties.get('location')}")
    print(f"Свойство 'unit': {schema_data_obj.properties.get('unit')}")


# 2. Пример: SchemaData object -> Python code for genai.types.Schema
print("\n--- Python-код для genai.types.Schema (из SchemaData) ---")
# Используем schema_data_obj из предыдущего шага или создадим новый:
example_schema_data = SchemaData(
    type="OBJECT",
    description="Параметры для функции get_weather",
    properties={
        "city": SchemaData(type="STRING", description="Название города"),
        "days": SchemaData(type="INTEGER", description="Количество дней прогноза", nullable=True)
    },
    required=["city"]
)
python_code_for_gemini = transformer.gemini_schema_obj_to_python_code(example_schema_data)
print(python_code_for_gemini)
# Ожидаемый вывод (отформатированный Python-код):
# genai.types.Schema(
#     type=genai.types.Type.OBJECT,
#     description='Параметры для функции get_weather',
#     properties={
#         'city': genai.types.Schema(type=genai.types.Type.STRING, description='Название города'),
#         'days': genai.types.Schema(type=genai.types.Type.INTEGER, description='Количество дней прогноза', nullable=True)
#     },
#     required=['city']
# )

# 3. Пример: SchemaData object -> OpenAI schema (dict)
print("\n--- OpenAI Schema (dict) (из SchemaData) ---")
# Используем schema_data_obj, полученный после преобразования из OpenAI
reverted_openai_schema = transformer.gemini_schema_to_openai_dict(schema_data_obj)
print(json.dumps(reverted_openai_schema, indent=2, ensure_ascii=False))
# Ожидается, что reverted_openai_schema будет очень похож на исходный openai_schema

# Проверка типа для unit (должен быть списком ["string", "null"])
# print(f"Тип 'unit' в восстановленной OpenAI схеме: {reverted_openai_schema.get('properties', {}).get('unit', {}).get('type')}")
assert reverted_openai_schema.get('properties', {}).get('unit', {}).get('type') == ["string", "null"]

```

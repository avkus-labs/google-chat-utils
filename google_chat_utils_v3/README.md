# Утилиты для работы с чатами Google AI Studio (google-chat-utils v3)

Версия 3 этой библиотеки представляет собой значительно переработанный и улучшенный набор инструментов, построенный на принципах объектно-ориентированного программирования. Она предназначена для парсинга JSON-экспортов чатов из Google AI Studio, их преобразования в удобные Python-объекты, генерации Markdown-представлений для RAG-систем и воссоздания исполняемых Python-скриптов для Gemini API.

## Ключевые особенности v3

*   **Объектно-ориентированная архитектура:** Код реорганизован в классы для лучшей модульности, читаемости и расширяемости.
*   **Типизация:** Широкое использование type hints для повышения надежности кода.
*   **Подробные Docstrings:** Каждый класс и публичный метод снабжен документацией.
*   **Сохранение функциональности:** Вся основная функциональность предыдущих версий сохранена и улучшена.

## Основные классы и их назначение

*   **Модели данных (`google_chat_utils_v3.core`)**:
    *   `SchemaData` и `FunctionDefinition` (`core.schema_elements`): Для представления JSON Schema и описаний функций (инструментов).
    *   `IntermediateChatData`, `RunSettingsData`, `SystemInstruction`, `DialogueTurn`, `ChatMessagePart` (и его наследники), `ToolConfiguration` (`core.chat_elements`): Представляют все аспекты чата в виде Python-объектов.
*   **Парсер (`google_chat_utils_v3.parsing`)**:
    *   `GoogleAIStudioJSONParser`: Загружает JSON-файлы из Google AI Studio, анализирует их и преобразует в объект `IntermediateChatData`. Также генерирует Markdown.
*   **Реконструктор кода (`google_chat_utils_v3.reconstruction`)**:
    *   `GeminiAPICodeReconstructor`: На основе объекта `IntermediateChatData` и текстовых шаблонов (`.py.tpl`) создает исполняемый Python-скрипт для Gemini API.
*   **Трансформер схем (`google_chat_utils_v3.transformation`)**:
    *   `SchemaTransformer`: Преобразует JSON Schema между форматом OpenAI, объектами `SchemaData` и Python-кодом для `genai.types.Schema`.

## Установка

```bash
# (Предполагается, что зависимости остаются прежними или будут указаны дополнительно)
# Клонировать репозиторий (если еще не сделано):
# git clone <URL_РЕПОЗИТОРИЯ>
# cd <ПАПКА_РЕПОЗИТОРИЯ>/google_chat_utils_v3

# Установка зависимостей (если есть файл requirements.txt):
# pip install -r requirements.txt

# Или установка отдельных библиотек, если они известны (например, google-generativeai):
# pip install google-generativeai
```
*Примечание: Инструкции по установке могут потребовать обновления после финализации зависимостей для v3.*

## Использование CLI (`cli_v3.py`)

Интерфейс командной строки `cli_v3.py` (будет реализован) позволит легко использовать основные функции библиотеки.

**Предполагаемые команды:**

1.  **Парсинг (`parse`)**
    *   Парсинг одного файла:
        ```bash
        python google_chat_utils_v3/cli_v3.py parse --input_file path/to/your/chat_export.json --output_dir path/to/output_directory
        ```
    *   Парсинг всех JSON-файлов в директории:
        ```bash
        python google_chat_utils_v3/cli_v3.py parse --input_dir path/to/input_json_files/ --output_dir path/to/output_directory
        ```
    Эта команда создаст в `output_dir` файлы `.json` (промежуточный формат) и `.md` (для RAG) для каждого входного файла.

2.  **Реконструкция кода (`reconstruct`)**
    ```bash
    python google_chat_utils_v3/cli_v3.py reconstruct \
        --input_json path/to/intermediate_chat_data.json \
        --output_py path/to/generated_script.py \
        --template_dir path/to/templates_v3/ \
        --template_name gemini_studio_default.py.tpl \
        --api_key_var_name "MY_API_KEY"
    ```
    Эта команда создаст Python-скрипт (`generated_script.py`) на основе промежуточного JSON-файла и указанного шаблона.

## Программное использование (Python)

Вы также можете импортировать и использовать классы напрямую в своих Python-скриптах.

```python
from google_chat_utils_v3.parsing.google_studio_parser import GoogleAIStudioJSONParser
from google_chat_utils_v3.reconstruction.gemini_code_reconstructor import GeminiAPICodeReconstructor
from google_chat_utils_v3.core.chat_elements import IntermediateChatData # Главный объект данных
from google_chat_utils_v3.transformation.schema_transformer import SchemaTransformer # Если нужна работа со схемами
import os # Для работы с путями
from typing import Optional # Для type hinting

# --- Пример Парсинга ---
# parser = GoogleAIStudioJSONParser()
# chat_file = "path/to/your/chat_export.json" # Замените на реальный путь
# intermediate_data: Optional[IntermediateChatData] = parser.parse(chat_file)
# if intermediate_data:
#     markdown_output = parser.to_markdown(intermediate_data)
#     print("--- Markdown Output (Начало) ---")
#     print(markdown_output[:500] + "...")
# else:
#     print(f"Файл не найден или не удалось разобрать: {chat_file}")
print("Программный пример парсинга (показан в документации парсера docs/parser.md).")


# --- Пример Реконструкции Кода ---
# Предполагается, что 'intermediate_data' уже загружен и содержит данные чата
# template_dir_path = "google_chat_utils_v3/templates" # Укажите корректный путь

# if intermediate_data and os.path.isdir(template_dir_path):
#     reconstructor = GeminiAPICodeReconstructor(template_dir=template_dir_path)
#     python_code = reconstructor.reconstruct(
#         intermediate_data=intermediate_data,
#         template_name="gemini_studio_default.py.tpl", # Убедитесь, что этот шаблон существует
#         api_key_var_name="MY_GEMINI_API_KEY"
#     )
#     print("\n--- Сгенерированный Python Код (Начало) ---")
#     print(python_code[:1000] + "...")
# elif not intermediate_data: # Добавлено для полноты примера
#     print("Пропустили реконструкцию: intermediate_data не загружен.")
# else:
#     print(f"Пропустили реконструкцию: директория шаблонов не найдена - {template_dir_path}")
print("Программный пример реконструкции (показан в документации реконструктора docs/reconstructor.md).")


# --- Пример Трансформации Схем ---
# schema_transformer = SchemaTransformer()
# openai_schema = {
#     "type": "object",
#     "properties": {"param1": {"type": "string", "description": "Параметр 1"}}
# }
# schema_data_instance = schema_transformer.openai_to_gemini_schema(openai_schema)
# print(f"\n--- SchemaData из OpenAI ---")
# print(schema_data_instance)
# python_code_for_schema = schema_transformer.gemini_schema_obj_to_python_code(schema_data_instance)
# print(f"\n--- Python код для Schema ---")
# print(python_code_for_schema)
print("Программный пример трансформации схем (показан в документации трансформера docs/transformer.md).")

```

## Детальная документация

Более подробная информация о каждом модуле, классе и их API доступна в разделе [Документация](./docs/index.md).

## Планы на будущее

*   Реализация `cli_v3.py` для удобного использования из командной строки.
*   Добавление юнит-тестов.
*   Возможность поддержки других форматов чатов и LLM API.

## Обратная связь

Мы приветствуем ваши отзывы и предложения по улучшению этой библиотеки!

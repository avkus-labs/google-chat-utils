# 🚀 google-chat-utils v3: Объектно-ориентированный подход 🚀

**Мощный и гибкий набор инструментов v3 для парсинга чатов Google AI Studio, их объектного представления, генерации Markdown для RAG и реконструкции Python-кода для Gemini API с использованием новой объектно-ориентированной архитектуры.**

---

## ✨ Ключевые особенности v3
*   **Полностью объектно-ориентированный дизайн:** Логика разделена на классы для улучшенной модульности, читаемости и расширяемости.
*   **Детальные модели данных (`core`):** Структурированное представление всех элементов чата (настройки, история, сообщения, части сообщений, схемы, инструменты).
*   **Продвинутый парсинг JSON-экспорта:** Загрузка и анализ JSON-файлов из Google AI Studio с помощью класса `GoogleAIStudioJSONParser`.
*   **Генерация Markdown:** Создание Markdown-представления чата с кастомными тегами, оптимизированного для RAG-систем, через метод `to_markdown` парсера.
*   **Гибкая реконструкция Python-кода:** Генерация исполняемых Python-скриптов для Gemini API с помощью класса `GeminiAPICodeReconstructor` и текстовых шаблонов.
*   **Трансформация JSON Schema:** Утилиты в классе `SchemaTransformer` для преобразования JSON Schema между форматами OpenAI и Gemini.
*   **Типизация и документация:** Код снабжен type hints и подробными docstrings.

---

## 📦 Установка

1.  Клонируйте репозиторий (если вы этого еще не сделали):
    ```bash
    git clone https://github.com/avkus/google_ai_studio_chat_parser_v3.git # Замените URL, если он другой
    cd google_ai_studio_chat_parser_v3
    ```
2.  (Опционально) Создайте и активируйте виртуальное окружение:
    ```bash
    python -m venv venv
    source venv/bin/activate # для Linux/macOS
    # venv\Scripts\activate # для Windows
    ```
3.  Установите зависимости (если они будут вынесены в `requirements.txt`):
    ```bash
    # pip install -r requirements.txt
    ```
    Основная зависимость для работы с Gemini API:
    ```bash
    pip install google-generativeai
    ```

*Примечание: Убедитесь, что у вас установлен Python 3.9+.*

---

## 📝 Быстрый старт (Использование)

### 1. Использование через командную строку (`cli_v3.py`)

Интерфейс командной строки `cli_v3.py` (в разработке) предоставит удобный доступ к основным функциям.

**Предполагаемые команды:**

*   **Парсинг чата Google AI Studio (`parse`)**
    *   Парсинг одного файла:
        ```bash
        python google_chat_utils_v3/cli_v3.py parse --input_file path/to/your/chat_export.json --output_dir path/to/output_v3
        ```
    *   Парсинг всех JSON-файлов в директории:
        ```bash
        python google_chat_utils_v3/cli_v3.py parse --input_dir path/to/input_json_files/ --output_dir path/to/output_v3
        ```
    Эта команда создаст в `output_v3` файлы `*_intermediate.json` (промежуточный объектный формат) и `*_rag.md` (для RAG) для каждого входного файла.

*   **Реконструкция Python-кода для Gemini API (`reconstruct`)**
    ```bash
    python google_chat_utils_v3/cli_v3.py reconstruct \
        --input_json path/to/output_v3/chat_export_intermediate.json \
        --output_py path/to/output_v3/reconstructed_chat.py \
        --template_dir google_chat_utils_v3/templates/ \
        --template_name gemini_studio_default.py.tpl \
        --api_key_var_name "MY_API_KEY"
    ```
    Эта команда сгенерирует Python-скрипт на основе промежуточного JSON-файла и указанного шаблона.

### 2. Программное использование (Python API)

Классы библиотеки можно импортировать и использовать в ваших собственных Python-скриптах.

```python
from google_chat_utils_v3.parsing.google_studio_parser import GoogleAIStudioJSONParser
from google_chat_utils_v3.reconstruction.gemini_code_reconstructor import GeminiAPICodeReconstructor
from google_chat_utils_v3.core.chat_elements import IntermediateChatData
from google_chat_utils_v3.transformation.schema_transformer import SchemaTransformer
import os
from typing import Optional # Для type hinting

# --- Пример Парсинга ---
# parser = GoogleAIStudioJSONParser()
# # Замените на реальный путь к вашему файлу
# # file_path = "path/to/your/google_ai_studio_export.json"
# # try:
# #     intermediate_data: Optional[IntermediateChatData] = parser.parse(file_path)
# #     if intermediate_data:
# #         print(f"Парсинг успешен: {intermediate_data.source_file_name}")
# #         markdown_output = parser.to_markdown(intermediate_data)
# #         # print("\nMarkdown для RAG:\n", markdown_output[:500] + "...")
# #         # Сохранение Markdown:
# #         # with open("parsed_chat.md", "w", encoding="utf-8") as f:
# #         #     f.write(markdown_output)
# # except FileNotFoundError:
# #     print(f"Файл не найден: {file_path}")
# # except Exception as e:
# #     print(f"Ошибка парсинга: {e}")
print("Подробные примеры программного использования см. в /docs/parser.md")

# --- Пример Реконструкции Кода ---
# # Предполагается, что 'intermediate_data' уже загружен (см. пример выше)
# # template_dir = "google_chat_utils_v3/templates" # Укажите корректный путь
# # if intermediate_data and os.path.exists(template_dir):
# #     reconstructor = GeminiAPICodeReconstructor(template_dir=template_dir)
# #     python_script = reconstructor.reconstruct(
# #         intermediate_data=intermediate_data,
# #         template_name="gemini_studio_default.py.tpl", # Убедитесь, что шаблон существует
# #         api_key_var_name="MY_GEMINI_API_KEY"
# #     )
# #     # print("\nСгенерированный Python скрипт:\n", python_script[:1000] + "...")
# #     # Сохранение скрипта:
# #     # with open("reconstructed_script.py", "w", encoding="utf-8") as f:
# #     #     f.write(python_script)
# # elif not intermediate_data:
# #    print("Пропустили реконструкцию: intermediate_data не загружен.")
# # else:
# #    print(f"Пропустили реконструкцию: директория шаблонов не найдена - {template_dir}")
print("Подробные примеры программного использования см. в /docs/reconstructor.md")

# --- Пример Трансформации Схем ---
# schema_transformer = SchemaTransformer()
# openai_schema_example = {
#    "type": "object", "properties": {"location": {"type": "string"}}
# }
# schema_data = schema_transformer.openai_to_gemini_schema(openai_schema_example)
# print(f"\nSchemaData: {schema_data.type}, {schema_data.properties}")
# python_code = schema_transformer.gemini_schema_obj_to_python_code(schema_data)
# print(f"Python для genai.types.Schema:\n{python_code}")
print("Подробные примеры программного использования см. в /docs/transformer.md")

```

---

## 🏛️ Архитектура v3

Библиотека `google-chat-utils v3` построена на следующих основных компонентах:

*   **`google_chat_utils_v3.core`**: Содержит базовые модели данных.
    *   `schema_elements.py`: Классы `SchemaData` и `FunctionDefinition` для представления JSON Schema и описаний функций.
    *   `chat_elements.py`: Классы, представляющие структуру чата: `IntermediateChatData` (корневой объект), `RunSettingsData`, `SystemInstruction`, `DialogueTurn`, `ToolConfiguration` и различные типы `ChatMessagePart` (например, `TextPart`, `FunctionCallPart`, `InlineDataPart` и др.).
*   **`google_chat_utils_v3.parsing`**:
    *   `google_studio_parser.py`: Класс `GoogleAIStudioJSONParser` для парсинга экспортов из Google AI Studio и генерации Markdown.
*   **`google_chat_utils_v3.reconstruction`**:
    *   `gemini_code_reconstructor.py`: Класс `GeminiAPICodeReconstructor` для генерации Python-кода для Gemini API из `IntermediateChatData` с использованием шаблонов.
*   **`google_chat_utils_v3.transformation`**:
    *   `schema_transformer.py`: Класс `SchemaTransformer` для преобразования JSON Schema между различными форматами (OpenAI dict ↔ `SchemaData` object ↔ Gemini API Python code).
*   **`google_chat_utils_v3.templates`**: Директория для хранения `.py.tpl` шаблонов, используемых реконструктором кода.
*   **`google_chat_utils_v3.docs`**: Подробная документация по API библиотеки.
*   **`google_chat_utils_v3.cli_v3.py`**: Интерфейс командной строки (в разработке).

---

## 📚 Детальная документация

Более подробная информация о каждом модуле, классе и их API доступна в разделе [Документация](./docs/index.md).

---

## 🤝 Вклад и дальнейшее развитие

Мы приветствуем ваши отзывы, идеи по улучшению и сообщения об ошибках! Пожалуйста, используйте раздел "Issues" в репозитории проекта.

Планируемые улучшения:
*   Завершение реализации и тестирование `cli_v3.py`.
*   Добавление комплексных юнит-тестов.
*   Расширение поддержки различных типов URI и сложных мультимодальных сценариев.

---

✨ Надеемся, обновленная библиотека `google-chat-utils v3` станет еще более удобным и мощным инструментом для вашей работы! ✨

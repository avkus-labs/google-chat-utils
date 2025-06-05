# 🚀 google-chat-utils v3: Объектно-ориентированный подход 🚀

**Мощный и гибкий набор инструментов v3 для парсинга чатов Google AI Studio, их объектного представления, генерации Markdown для RAG и реконструкции Python-кода для Gemini API с использованием новой объектно-ориентированной архитектуры.**

Включает также утилиту для объединения Markdown-файлов.

---

## ✨ Ключевые особенности v3
*   **Полностью объектно-ориентированный дизайн:** Логика разделена на классы для улучшенной модульности, читаемости и расширяемости.
*   **Детальные модели данных (`core`):** Структурированное представление всех элементов чата.
*   **Продвинутый парсинг JSON-экспорта:** Загрузка и анализ JSON-файлов из Google AI Studio с помощью класса `GoogleAIStudioJSONParser`.
*   **Генерация Markdown для RAG:** Создание Markdown-представления чата с кастомными тегами через метод `to_markdown` парсера.
*   **Гибкая реконструкция Python-кода:** Генерация исполняемых Python-скриптов для Gemini API с помощью класса `GeminiAPICodeReconstructor` и текстовых шаблонов.
*   **Трансформация JSON Schema:** Утилиты в классе `SchemaTransformer` для преобразования JSON Schema между форматами OpenAI и Gemini.
*   **Утилита для объединения Markdown (`tools/markdown_merger.py`):** Позволяет склеивать несколько Markdown-файлов в один.
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

Интерфейс командной строки `cli_v3.py` предоставляет удобный доступ к основным функциям.

*   **Парсинг чата Google AI Studio (`parse`)**
    *   Парсинг одного файла:
        ```bash
        python google_chat_utils_v3/cli_v3.py parse --input_file path/to/your/chat_export.json --output_dir path/to/output_base_dir
        ```
        Результат будет сохранен в `path/to/output_base_dir/chat_export/intermediate.json` и `path/to/output_base_dir/chat_export/rag.md`.

    *   Парсинг всех JSON-файлов в директории:
        ```bash
        python google_chat_utils_v3/cli_v3.py parse --input_dir path/to/input_json_files/ --output_dir path/to/output_base_dir
        ```
        Для каждого файла в `input_json_files` будет создана своя подпапка в `output_base_dir`.

*   **Реконструкция Python-кода для Gemini API (`reconstruct`)**
    ```bash
    python google_chat_utils_v3/cli_v3.py reconstruct \
        --input_json path/to/output_base_dir/chat_export/intermediate.json \
        --output_py reconstructed_script.py \
        --template_dir google_chat_utils_v3/templates/ \
        --template_name gemini_studio_default.py.tpl \
        --api_key_var_name "MY_API_KEY"
    ```
    Сгенерированный `reconstructed_script.py` будет сохранен в `path/to/output_base_dir/chat_export/`.

    *Примечание: Для полноценной работы связки `parse` -> `reconstruct` через промежуточный JSON требуется доработка сериализации/десериализации `IntermediateChatData`.*

### 2. Утилита объединения Markdown (`tools/markdown_merger.py`)
    ```bash
    python tools/markdown_merger.py \
        --input docs/parser.md docs/reconstructor.md \
        --output docs/combined_api.md \
        --separator "\n---\n" \
        --include_filenames --filename_header_level 2
    ```
    Эта команда объединит `parser.md` и `reconstructor.md` в `combined_api.md`, вставляя имена файлов как заголовки H2 и стандартный разделитель.

    ```bash
    python tools/markdown_merger.py \
        --input path/to/markdown_folder/ \
        --output all_in_folder_merged.md \
        --recursive
    ```
    Эта команда рекурсивно найдет и объединит все `.md` файлы из `path/to/markdown_folder/`.


### 3. Программное использование (Python API)

Классы библиотеки можно импортировать и использовать в ваших собственных Python-скриптах. Подробные примеры смотрите в соответствующей документации в папке `docs/`.

```python
# Пример импорта основных классов
from google_chat_utils_v3.parsing.google_studio_parser import GoogleAIStudioJSONParser
from google_chat_utils_v3.reconstruction.gemini_code_reconstructor import GeminiAPICodeReconstructor
from google_chat_utils_v3.transformation.schema_transformer import SchemaTransformer
from google_chat_utils_v3.core.chat_elements import IntermediateChatData
from typing import Optional # Для type hinting

# Использование:
# parser = GoogleAIStudioJSONParser()
# intermediate_data: Optional[IntermediateChatData] = parser.parse("path/to/chat.json")
# if intermediate_data:
#     md = parser.to_markdown(intermediate_data)
#     reconstructor = GeminiAPICodeReconstructor(template_dir="google_chat_utils_v3/templates")
#     py_code = reconstructor.reconstruct(intermediate_data, "gemini_studio_default.py.tpl")
```

---

## 🏛️ Архитектура v3

Библиотека `google-chat-utils v3` построена на следующих основных компонентах:

*   **`google_chat_utils_v3.core`**: Базовые модели данных (`SchemaData`, `FunctionDefinition`, `IntermediateChatData`, `ChatMessagePart` и др.).
*   **`google_chat_utils_v3.parsing`**: `GoogleAIStudioJSONParser` для парсинга и генерации Markdown.
*   **`google_chat_utils_v3.reconstruction`**: `GeminiAPICodeReconstructor` для генерации Python-кода.
*   **`google_chat_utils_v3.transformation`**: `SchemaTransformer` для преобразования JSON Schema.
*   **`google_chat_utils_v3.templates`**: Шаблоны `.py.tpl` для реконструктора.
*   **`google_chat_utils_v3.docs`**: Подробная документация по API.
*   **`google_chat_utils_v3.cli_v3.py`**: Интерфейс командной строки.
*   **`tools/markdown_merger.py`**: Утилита для объединения Markdown-файлов.

---

## 📚 Детальная документация

Более подробная информация о каждом модуле, классе и их API доступна в разделе [Документация](./docs/index.md).

---

## 🤝 Вклад и дальнейшее развитие

Мы приветствуем ваши отзывы, идеи по улучшению и сообщения об ошибках! Пожалуйста, используйте раздел "Issues" в репозитории проекта.

Планируемые улучшения:
*   Реализация полноценной сериализации/десериализации `IntermediateChatData` для `cli_v3.py`.
*   Добавление комплексных юнит-тестов.
*   Расширение поддержки различных типов URI и сложных мультимодальных сценариев в парсере и реконструкторе.

---

✨ Надеемся, обновленная библиотека `google-chat-utils v3` станет еще более удобным и мощным инструментом для вашей работы! ✨

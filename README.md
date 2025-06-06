# 🚀 google-chat-utils v3: Объектно-ориентированный подход 🚀

**Мощный и гибкий набор инструментов v3 для парсинга чатов Google AI Studio, их объектного представления, генерации Markdown для RAG и реконструкции Python-кода для Gemini API с использованием новой объектно-ориентированной архитектуры.**

Включает также утилиту для объединения Markdown-файлов.

---

## ✨ Ключевые особенности v3
*   **Полностью объектно-ориентированный дизайн:** Логика разделена на классы для улучшенной модульности, читаемости и расширяемости.
*   **Детальные модели данных (`core`):** Структурированное представление всех элементов чата.
*   **Продвинутый парсинг JSON-экспорта:** Загрузка и анализ JSON-файлов из Google AI Studio с помощью класса `GoogleAIStudioJSONParser`.
*   **Генерация Markdown для RAG:** Создание Markdown-представления чата с кастомными тегами через метод `to_markdown` парсера.
*   **Гибкая реконструкция Python-кода:** Генерация исполняемых Python-скриптов для Gemini API с помощью класса `GeminiAPICodeReconstructor` и текстовых шаблонов. Теперь поддерживаются оверрайды для первого (`fi_file`) и последнего (`li_file`) пользовательских сообщений.
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
        python utils/cli_v3.py parse --input_file data/SecOps-Flash --output_prefix output_data/
        ```
        Результат будет сохранен в `output_data/SecOps-Flash_intermediate.json` и `output_data/SecOps-Flash_raw_rag.md`.

    *   Парсинг всех JSON-файлов в директории:
        ```bash
        python utils/cli_v3.py parse --input_dir data/ --output_prefix output_data/
        ```
        Для каждого файла в `data/` будет создана своя подпапка в `output_data/`.
    
    - `--output_prefix` (или `-o`) — префикс для имён выходных файлов и директорий. По умолчанию: `output_data/`.
    - Для Windows и Linux/Unix можно использовать прямой слэш (`/`) в путях — Python корректно обработает их на любой ОС.

*   **Реконструкция Python-кода для Gemini API (`reconstruct`)**
    ```bash
    python utils/cli_v3.py reconstruct \
        --input_json output_data/Example_intermediate.json \
        --output_py Example_reconstructed.py \
        --template_dir templates/ \
        --template_name gemini_studio_vanilla.py.tpl \
        --api_key_var_name "MY_API_KEY" \
        --model_name "gemini-pro" \
        --si_file data/Example.si \
        --fi_file data/Example.fi \
        --li_file data/Example.li
    ```
    - `--si_file` — путь к файлу с системной инструкцией (опционально).
    - `--fi_file` — путь к файлу с первым пользовательским сообщением (опционально, first instruction/first message).
    - `--li_file` — путь к файлу с последним пользовательским сообщением (опционально, last instruction/last message). Его содержимое будет добавлено в конец истории диалога.
    - Если какой-либо из файлов-оверрайдов не указан — соответствующее сообщение не добавляется.

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

## 🔥 Быстрые примеры трансформации схем (SchemaTransformer CLI)

**Преобразование между форматами OpenAI JSON Schema, Gemini SchemaData и Python-кодом для genai.types.Schema — теперь доступно через CLI!**

### 🚦 Примеры команд:

- 🟢 **OpenAI JSON Schema → Gemini SchemaData (JSON):**
  ```bash
  python -m google_chat_utils_v3.transformation.schema_transformer \
      --openai_to_gemini data/example_openai_schema.json output_data/example_gemini_schema.json
  ```
- 🟡 **Gemini SchemaData (JSON) → OpenAI JSON Schema:**
  ```bash
  python -m google_chat_utils_v3.transformation.schema_transformer \
      --gemini_to_openai data/example_gemini_schema.json output_data/example_openai_schema_out.json
  ```
- 🟣 **Gemini SchemaData (JSON) → Python-код для genai.types.Schema:**
  ```bash
  python -m google_chat_utils_v3.transformation.schema_transformer \
      --gemini_to_python data/example_gemini_schema.json output_data/example_gemini_schema.py
  ```

**Все примеры схем для тестирования лежат в папке `data/`.**

- 📂 Входные и выходные файлы удобно хранить в `data/` и `output_data/` соответственно.
- 📄 Примеры CLI-команд можно адаптировать под свои схемы.

---

## 📚 Документация

- Основная документация теперь находится в папке [`docs_v3/`](./docs_v3/)
- Краткие справки по каждому модулю:
  - [`docs_v3/parser.md`](./docs_v3/parser.md)
  - [`docs_v3/reconstructor.md`](./docs_v3/reconstructor.md)
  - [`docs_v3/transformer.md`](./docs_v3/transformer.md)
  - [`docs_v3/core_models.md`](./docs_v3/core_models.md)
  - [`docs_v3/index.md`](./docs_v3/index.md)

---

## 🤝 Вклад и дальнейшее развитие

Мы приветствуем ваши отзывы, идеи по улучшению и сообщения об ошибках! Пожалуйста, используйте раздел "Issues" в репозитории проекта.

Планируемые улучшения:
*   Реализация полноценной сериализации/десериализации `IntermediateChatData` для `cli_v3.py`.
*   Добавление комплексных юнит-тестов.
*   Расширение поддержки различных типов URI и сложных мультимодальных сценариев в парсере и реконструкторе.

---

✨ Надеемся, обновленная библиотека `google-chat-utils v3` станет еще более удобным и мощным инструментом для вашей работы! ✨

## 🆕 Реконструкция JSON для Google AI Studio

Воссоздайте валидный JSON-файл для Studio с учётом оверрайдов:

```bash
python -m utils.cli_v3 reconstruct_studio_json \
    --input_intermediate_json output_data/Example6_intermediate.json \
    --output_studio_json_file output_data/Example6
```

- Оверрайды: `data/Example6.si` и/или `data/Example6.fi` (если есть).
- Итоговый файл: `output_data/Example6` (без расширения, валидный JSON для Studio).

# 🚀 google-chat-utils v0.4.0: Интеграция с Memory Compiler и ООП-архитектура 🚀

**Мощный и гибкий набор инструментов для парсинга чатов Google AI Studio, их объектного представления, генерации Markdown для RAG, реконструкции Python-кода и интеграции с Memory Compiler.**

---

## ✨ Ключевые особенности

*   **Интеграция с Memory Compiler:**
    *   **Автоматическая отправка в память:** Используйте флаг `--log_to_memory` (`-l`) с командой `parse` для автоматической отправки сгенерированного `human.md` в ваш Memory Compiler.
    *   **Ручная отправка логов:** Новая команда `log` позволяет отправлять содержимое любого текстового файла в Memory Compiler.
*   **Полностью объектно-ориентированный дизайн:** Логика разделена на классы (`GoogleAIStudioJSONParser`, `GeminiAPICodeReconstructor`, `SchemaTransformer`) для улучшенной модульности и расширяемости.
*   **Продвинутый парсинг и реконструкция:**
    *   Анализ JSON-экспортов из Google AI Studio.
    *   Реконструкция исполняемых Python-скриптов для Gemini API с поддержкой оверрайдов.
    *   Восстановление JSON-файлов, которые можно импортировать обратно в Google AI Studio.
*   **Трансформация JSON Schema:** Утилиты для преобразования схем между форматами OpenAI и Gemini.
*   **Типизация и документация:** Код снабжен type hints и подробными docstrings.

---

## 📦 Установка

1.  Клонируйте репозиторий:
    ```bash
    git clone https://github.com/avkus-labs/google-chat-utils.git
    cd Google-Chat-Utils
    ```
2.  Создайте и активируйте виртуальное окружение:
    ```bash
    python -m venv venv
    source venv/bin/activate # для Linux/macOS
    # venv\Scripts\activate # для Windows
    ```
3.  Установите зависимости:
    ```bash
    pip install -r requirements.txt
    ```

*Примечание: Убедитесь, что у вас установлен Python 3.9+.*

---

## 📝 Быстрый старт (Использование через CLI)

Все команды выполняются через главный скрипт `utils/cli_v3.py`. Пути к файлам можно указывать с прямым слэшем (`/`) — Python корректно обработает их на любой ОС.

### 1. Парсинг чата (`parse`)

*   **Парсинг одного файла:**
    ```bash
    python utils/cli_v3.py parse --input_file data/Example.json --output_prefix output_data/
    ```
    *Результат будет сохранен в `output_data/Example_intermediate.json`, `output_data/Example_raw_rag.md` и `output_data/Example_human.md`.*

*   **Парсинг всех JSON-файлов в директории:**
    ```bash
    python utils/cli_v3.py parse --input_dir data/ --output_prefix output_data/
    ```

*   **Парсинг с автоматической отправкой в Memory Compiler:**
    ```bash
    python utils/cli_v3.py parse --input_file data/Example.json -l
    ```
    *Содержимое `human.md` будет отправлено в Memory Compiler.*

### 2. Отправка лога в Memory Compiler (`log`)

Отправка содержимого любого текстового файла в указанную секцию Memory Compiler.

```bash
python utils/cli_v3.py log --input_file "path/to/your/file.md" --section "Your Section Name"
```

### 3. Реконструкция Python-кода (`reconstruct`)

```bash
python utils/cli_v3.py reconstruct \
    --input_json output_data/Example_intermediate.json \
    --output_py output_data/Example_reconstructed.py \
    --template_dir templates/ \
    --template_name gemini_studio_vanilla.py.tpl
```
*Для изменения системной инструкции или сообщений используйте файлы-оверрайды (`.si`, `.fi`, `.li`), как описано в `CLAUDE.md`.*

### 4. Реконструкция JSON для Google AI Studio (`reconstruct_studio_json`)

```bash
python utils/cli_v3.py reconstruct_studio_json \
    --input_intermediate_json output_data/Example_intermediate.json \
    --output_studio_json_file output_data/Example_studio.json
```

### 5. Трансформация схем (`schema_transformer`)

*   **OpenAI → Gemini:**
    ```bash
    python -m utils.transformation.schema_transformer \
        --openai_to_gemini data/example_openai_schema.json output_data/example_gemini_schema.json
    ```
*   **Gemini → OpenAI:**
    ```bash
    python -m utils.transformation.schema_transformer \
        --gemini_to_openai data/example_gemini_schema.json output_data/example_openai_schema_out.json
    ```

---

## 🏛️ Архитектура

*   **`utils/core`**: Базовые модели данных.
*   **`utils/parsing`**: `GoogleAIStudioJSONParser` для парсинга и генерации Markdown.
*   **`utils/reconstruction`**: `GeminiAPICodeReconstructor` для генерации Python-кода.
*   **`utils/transformation`**: `SchemaTransformer` для преобразования JSON Schema.
*   **`utils/cli_v3.py`**: Главный интерфейс командной строки.
*   **`templates/`**: Шаблоны для реконструкции кода.
*   **`docs/`**: Подробная документация по API.

---

## 📚 Документация

Подробная документация по каждому модулю и его API находится в папке [`docs/`](./docs/).

---

## 🤝 Вклад

Мы приветствуем ваши отзывы, идеи и сообщения об ошибках! Пожалуйста, используйте раздел "Issues".

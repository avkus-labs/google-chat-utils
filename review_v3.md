# Обзор и методология запуска: google_ai_studio_chat_parser_v3

Этот документ описывает назначение, эволюцию и методологию запуска третьей, объектно-ориентированной версии проекта.

---

### Обзор проекта `google_ai_studio_chat_parser_v3`

**Основное назначение и эволюция**

Третья версия, `google_ai_studio_chat_parser_v3`, представляет собой кульминацию развития проекта. Она переходит от набора скриптов к **полноценной объектно-ориентированной библиотеке**. Это уже не просто парсер, а гибкий и расширяемый фреймворк для работы с чатами Google AI Studio.

Основной фокус v3 — **модульность, структурированность и расширяемость**.

**Ключевые улучшения и возможности v3**

*   **Объектно-ориентированная архитектура:** Вся логика инкапсулирована в классах (`GoogleAIStudioJSONParser`, `GeminiAPICodeReconstructor`, `SchemaTransformer`), что улучшает читаемость и позволяет легко использовать их в других Python-проектах.
*   **Детальные модели данных (`core`):** Появился пакет `core`, который определяет строго типизированные модели для всех элементов чата, обеспечивая надежность при работе с данными.
*   **Мощный CLI с подкомандами:** Интерфейс командной строки (`utils/cli_v3.py`) использует подкоманды (`parse`, `reconstruct`, `reconstruct_studio_json`), что делает его более организованным.
*   **Гибкие оверрайды для сообщений:** V3 вводит поддержку файлов-оверрайдов для системной инструкции (`.si`), первого (`.fi`) и последнего (`.li`) сообщения, что крайне полезно для отладки промптов.
*   **Реконструкция JSON для Studio:** Появилась уникальная функция `reconstruct_studio_json`, которая позволяет воссоздать валидный JSON-файл для импорта обратно в Google AI Studio, замыкая цикл "экспорт -> модификация -> импорт".
*   **Отдельная утилита для Markdown:** Включена утилита `tools/markdown_merger.py` для объединения Markdown-файлов.

V3 — это профессиональный инструмент, который превращает обработку чатов в управляемый инженерный процесс.

---

### Методология запуска `google_ai_studio_chat_parser_v3`

#### Шаг 1: Подготовка

1.  **Установка:**
    ```bash
    # Установить основную зависимость
    pip install google-generativeai
    ```
2.  **Размещение файлов:** Рекомендуется хранить исходные чаты в папке `data/`, а результаты — в `output_data/`.

#### Шаг 2: Парсинг (через `cli_v3.py parse`)

-   **Парсинг всех файлов в папке:**
    ```bash
    python google_ai_studio_chat_parser_v3/utils/cli_v3.py parse --input_dir data/ --output_prefix output_data/
    ```

#### Шаг 3: Реконструкция кода (через `cli_v3.py reconstruct`)

-   **Пример команды:**
    ```bash
    python google_ai_studio_chat_parser_v3/utils/cli_v3.py reconstruct \
        --input_json output_data/Example_intermediate.json \
        --output_py reconstructed_Example.py \
        --template_dir google_ai_studio_chat_parser_v3/templates/ \
        --template_name gemini_studio_vanilla.py.tpl \
        --si_file data/Example.si \
        --fi_file data/Example.fi \
        --li_file data/Example.li
    ```

#### Шаг 4: Реконструкция JSON для Studio (через `cli_v3.py reconstruct_studio_json`)

-   **Пример команды:**
    ```bash
    python -m google_ai_studio_chat_parser_v3.utils.cli_v3 reconstruct_studio_json \
        --input_intermediate_json output_data/Example_intermediate.json \
        --output_studio_json_file output_data/Example_for_studio
    ```
-   **Результат:** Создает файл, который можно напрямую импортировать в интерфейс Google AI Studio.

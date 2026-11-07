# 🚀 google-chat-utils v0.7.3: Инкрементальная дистилляция, интерактивный режим 🚀

**Мощный и гибкий набор инструментов для парсинга чатов Google AI Studio, их объектного представления, генерации Markdown для RAG, дистилляции через LLM, реконструкции Python-кода и интеграции с Google Drive и Memory Compiler.**

---

## ✨ Ключевые особенности

*   **Интерактивный режим терминала (`utils/interactive.py`, v0.7.0):**
    *   Полноценное текстовое меню для пошаговой работы с утилитами без заучивания флагов.
    *   Запуск по команде `python utils/cli_v3.py interactive` или просто вызовом `python utils/cli_v3.py` без параметров.
*   **Pydantic-валидация экспортов (`utils/validation/`, v0.7.0):**
    *   Строгие модели валидации сырых экспортов Google AI Studio и промежуточных JSON (`validate_studio_export`).
    *   Команда CLI `validate` для быстрой проверки корректности файлов.
    *   Автоматическая валидация при парсинге (`parse`).
*   **Структурированное логирование (v0.7.0):**
    *   Централизованный модуль `utils/logging_config.py` с уровнями DEBUG/INFO/WARNING/ERROR.
    *   Флаги CLI `-v` (`--verbose`), `--log-level`, `--log-file`.
    *   Устранены все deprecation-предупреждения `datetime.utcnow()`.
*   **Интеграция с Google Drive (`utils/drive/`, v0.6.0):**
    *   **Скачивание чатов по имени:** Команда `fetch-drive` ищет файл в папке "Google AI Studio" и сохраняет его локально.
    *   **Сквозной пайплайн:** Флаг `--parse` автоматически запускает парсинг сразу после скачивания (`fetch-drive --parse --distill`).
    *   **OAuth2 авторизация:** Интерактивная команда `auth-drive` и поддержка `.env` (`GDRIVE_REFRESH_TOKEN`).
*   **Дистилляция чатов (v0.5.0, v0.7.1, v0.7.2, v0.7.3):**
    *   **Стриминг ответов (SSE, v0.7.3):** по умолчанию все запросы к LLM стримятся (`stream: true`). Первые байты приходят без ожидания полной генерации, предотвращая таймауты промежуточных шлюзов и балансировщиков (OmniRoute). Отключение стриминга — флагом `--llm_no_stream`.
    *   **Отдельная модель для synthesis (v0.7.2):** флаг `--llm_synthesis_model` позволяет направить финальный шаг структурирования и формирования JSON на более сильную модель, а чанки обрабатывать на быстрой/дешёвой `--llm_model`.
    *   **Инкрементальная обработка (v0.7.1):** готовые `_distilled.md` пропускаются по умолчанию, не тратя токены LLM; принудительная перегенерация — флагом `--distill_overwrite`.
    *   **Атомарная запись:** запись через временный файл `.tmp` + `os.replace` защищает существующие файлы от повреждения при сбоях.
    *   **Подпапки вывода:** `parse` складывает артефакты каждого файла в `<output_prefix>/<safe_stem>/`.
    *   **Команда `distill`:** Дистилляция готовых `_human.md` через LLM (редакция секретов, чанкинг, верификация).
    *   **`parse --distill`:** Дистилляция сразу после парсинга.
    *   **Кэш:** Повторный запуск переиспользует результаты (`.distill_cache/`).
*   **Интеграция с Memory Compiler:**
    *   **Автоматическая отправка в память:** Флаг `--log_to_memory` (`-l`) с командой `parse` или `fetch-drive`.
    *   **Ручная отправка логов:** Команда `log` для отправки любого текстового файла в Memory Compiler.
*   **Полностью объектно-ориентированный дизайн:** Логика разделена на классы (`GoogleAIStudioJSONParser`, `GeminiAPICodeReconstructor`, `SchemaTransformer`).
*   **Продвинутый парсинг и реконструкция:**
    *   Анализ JSON-экспортов из Google AI Studio.
    *   Реконструкция исполняемых Python-скриптов для Gemini API с поддержкой оверрайдов.
    *   Модификация и применение оверрайдов к сырым JSON-файлам Studio (`apply_overrides_to_studio_json`).
*   **Трансформация JSON Schema:** Утилиты для преобразования схем между форматами OpenAI, Gemini SchemaData и кодом `google.genai.types.Schema`.
*   **Тестирование и CI/CD:** Полное покрытие тестами (109 тестов), линтинг `ruff`, CI на GitHub Actions.

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

*Примечание: Требуется Python 3.9+.*

---

## 📝 Быстрый старт (Использование через CLI)

Все команды выполняются через единый интерфейс `utils/cli_v3.py`. Пути можно указывать с прямым слэшем (`/`) на любой ОС.

### 0. Интерактивный режим и валидация

*   **Интерактивное меню (Terminal UI):**
    ```bash
    python utils/cli_v3.py
    # или явно:
    python utils/cli_v3.py interactive
    ```
    Позволяет пошагово запускать любые действия (парсинг, реконструкцию, валидацию, дистилляцию, работу с Google Drive) с интерактивными подсказками.

*   **Проверка структуры JSON через Pydantic (`validate`):**
    ```bash
    python utils/cli_v3.py validate -i data/Example
    ```

### 1. Скачивание чата из Google Drive (`fetch-drive`)

*   **Простое скачивание по имени:**
    ```bash
    python utils/cli_v3.py fetch-drive --chat_name "Название чата" --output_dir input_data/
    ```

*   **Сквозной пайплайн (скачать + распарсить + дистиллировать):**
    ```bash
    python utils/cli_v3.py fetch-drive --chat_name "Название чата" --parse --distill --distill_dry_run --llm_base_url "http://..." --llm_model "model"
    ```

*   **Авторизация Google Drive:**
    ```bash
    python utils/cli_v3.py auth-drive --client_secrets client_secret.json
    ```

### 2. Парсинг чата (`parse`)

*   **Парсинг одного файла:**
    ```bash
    python utils/cli_v3.py parse --input_file data/Example --output_prefix output_data/
    ```
    *Результат сохраняется в `output_data/Example/Example_intermediate.json`, `_raw_rag.md` и `_human.md`.*

*   **Парсинг с дистилляцией:**
    ```bash
    python utils/cli_v3.py parse --input_file data/Example --distill --distill_dry_run --llm_base_url "http://..." --llm_model "model"
    ```

*   **Парсинг всех файлов в папке:**
    ```bash
    python utils/cli_v3.py parse --input_dir data/ --output_prefix output_data/
    ```

*   **Парсинг с отправкой в Memory Compiler:**
    ```bash
    python utils/cli_v3.py parse --input_file data/Example -l
    ```

### 3. Дистилляция готовых `_human.md` (`distill`)

По умолчанию готовые `_distilled.md` **пропускаются** (токены не расходуются). Для принудительной перегенерации используйте флаг `--distill_overwrite`.

*   **Сухой прогон (оценка плана и токенов):**
    ```bash
    python utils/cli_v3.py distill --input_file output_data/Example/Example_human.md --distill_dry_run --llm_base_url "http://..." --llm_model "model"
    ```
*   **Реальный запуск (с пропуском уже готовых файлов):**
    ```bash
    python utils/cli_v3.py distill --input_file output_data/Example/Example_human.md --llm_base_url "http://..." --llm_model "model" --yes
    ```
*   **Принудительная перегенерация (`--distill_overwrite`):**
    ```bash
    python utils/cli_v3.py distill --input_dir output_data --distill_overwrite --llm_base_url "http://..." --llm_model "model" --yes
    ```
*   **Раздельные модели для чанков и synthesis (`--llm_synthesis_model`):**
    ```bash
    python utils/cli_v3.py distill --input_file output_data/Example/Example_human.md --llm_base_url "http://..." --llm_model gemini-3.1-flash-lite --llm_synthesis_model <более сильная> --yes
    ```
*   **Отключение стриминга (`--llm_no_stream`):**
    ```bash
    python utils/cli_v3.py distill --input_file output_data/Example/Example_human.md --llm_no_stream --llm_base_url "http://..." --llm_model "model" --yes
    ```
*   **Строгий режим верификации (`--distill_strict`):**
    ```bash
    python utils/cli_v3.py distill --input_file output_data/Example/Example_human.md --distill_strict --llm_base_url "http://..." --llm_model "model" --yes
    ```
    В строгом режиме при пропуске хотя бы одного хода диалога или ошибках в якорях ходов дистилляция прерывается с ошибкой, а файл `_distilled.md` не записывается (кэш успешных чанков сохраняется для возможности продолжения).
*   **Режим чатов «только System Instruction» (`--distill_si_only`):**
    ```bash
    # Режим документа (по умолчанию)
    python utils/cli_v3.py distill --input_file output_data/BDX/BDX_human.md --distill_si_only document --llm_base_url "http://..." --llm_model "model" --yes

    # Пропуск с ошибкой (прежнее поведение)
    python utils/cli_v3.py distill --input_file output_data/BDX/BDX_human.md --distill_si_only skip --llm_base_url "http://..." --llm_model "model"
    ```
    Если файл содержит только System Instruction без ходов диалога (ручная очистка владельца), в режиме `document` создаётся структурированный документ базы знаний с `chunks: 0`, дословным сохранением инструкции и метаданными synthesis за один вызов LLM.

#### Верификация качества и целостности

После дистилляции выполняется детерминированная проверка качества без обращения к LLM:
*   **Статусы верификации (`verification.status`):**
    *   `ok` — 100% покрытие ходов, корректные якоря, код найден в источнике, секретов не обнаружено.
    *   `warning` — найдены пропуски ходов диалога, якоря-заглушки (`(ходы N–N)`, `(ходы [не указаны])`), некорректные номера ходов или подозрительные блоки кода (>30% отсутствующих строк).
    *   `error` — в готовом документе обнаружены неэкранированные секреты (токены, ключи).
*   **Компактный блок во frontmatter:** блок `verification:` содержит `status`, число пропущенных ходов со сжатыми диапазонами (например, `1-9, 43-54`), `anchor_issues`, число подозрительных блоков кода и отношение длины `length_ratio`.
*   **Контрольная сумма (`source_sha256`):** вычисляется детерминированно по исходному тексту диалога после перевода переводов строк CRLF → LF (universal newlines), что гарантирует совпадение хэшей независимо от платформы (Windows/Linux).

#### Почему стрим (SSE)?

По умолчанию клиент отправляет запросы в режиме стриминга (`stream: true`), читая Server-Sent Events (SSE). Без стриминга клиент ждёт полной генерации ответа, из-за чего промежуточные прокси и роутеры (в частности, OmniRoute) обрывают соединение по внутренним таймаутам ожидания заголовков:
1. `[504] ... requestQueue.maxWaitMs=15000ms` (переменная `RATE_LIMIT_MAX_WAIT_MS`, дефолт 15000 мс; в веб-панели OmniRoute: Settings → Resilience → «Max queue wait»);
2. `[504] Direct response did not start within 30000ms — retrying on a fresh socket` (переменная `OMNIROUTE_DIRECT_HEADERS_TIMEOUT_MS`, дефолт 30000 мс; `open-sse/utils/directResponseStartTimeout.ts`);
3. После обрыва шлюз повторяет запрос на резервном аккаунте, в то время как первый запрос ещё генерируется провайдером → `409 duplicate request` (например, у xkiro).

При активном стриминге первые байты (включая ранний keep-alive от роутера) поступают незамедлительно, предотвращая срабатывание обоих таймаутов. Если вы явно отключаете стриминг флагом `--llm_no_stream`, убедитесь, что в OmniRoute увеличены значения `RATE_LIMIT_MAX_WAIT_MS` и `OMNIROUTE_DIRECT_HEADERS_TIMEOUT_MS`.

### 4. Отправка лога в Memory Compiler (`log`)

```bash
python utils/cli_v3.py log --input_file "path/to/your/file.md" --section "Your Section Name"
```

### 5. Реконструкция Python-кода (`reconstruct`)

```bash
python utils/cli_v3.py reconstruct \
    --input_json output_data/Example/Example_intermediate.json \
    --output_py output_data/Example/Example_reconstructed.py \
    --template_dir templates/ \
    --template_name gemini_studio_vanilla.py.tpl \
    --model_name "gemini-2.5-flash"
```

### 6. Применение оверрайдов к Studio JSON (`apply_overrides_to_studio_json`)

```bash
python utils/cli_v3.py apply_overrides_to_studio_json \
    --input_studio_json data/Example \
    --output_studio_json output_data/Example_overridden.json \
    --si_file data/Example.si \
    --fi_file data/Example.fi \
    --fi_mode replace \
    --li_mode append
```

### 7. Трансформация схем (`schema_transformer`)

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

*   **`utils/core`**: Базовые модели данных (`IntermediateChatData`, `ChatMessage`, классы `Part`).
*   **`utils/parsing`**: `GoogleAIStudioJSONParser` для парсинга и генерации Markdown.
*   **`utils/distillation`**: Конвейер дистилляции — `chunker`, `redactor`, `llm_client`, `verifier`, `pipeline`, `safe_stem`.
*   **`utils/drive`**: Модули Google Drive (`auth.py`, `client.py`).
*   **`utils/reconstruction`**: `GeminiAPICodeReconstructor` для генерации Python-кода.
*   **`utils/transformation`**: `SchemaTransformer` для преобразования JSON Schema.
*   **`utils/cli_v3.py`**: Главный интерфейс командной строки.
*   **`templates/`**: Шаблоны генерации скриптов.
*   **`docs/`**: Подробная документация.

---

## 🧪 Тестирование

Запуск полного набора тестов:
```bash
pytest
```

Проверка стиля и типов линтером:
```bash
ruff check utils/ tests/
```

---

## 🤝 Вклад

Мы приветствуем ваши отзывы, идеи и сообщения об ошибках! Пожалуйста, используйте раздел "Issues".

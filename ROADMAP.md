# ROADMAP.md

Этот файл содержит актуальный план развития проекта Google Chat Utils и статус реализации задач.

## 📌 Статус задач и бэклог

### 1. Архитектура и CLI
- [x] **Подпапки вывода для `parse`:** Каждый входной файл → отдельная подпапка `<output_prefix>/<safe_stem>/` (`_intermediate.json`, `_raw_rag.md`, `_human.md`). *(задача 001, v0.5.0)*
- [x] **Команда `distill`:** Дистилляция готовых `_human.md` через LLM с чанкингом, кэшированием и верификацией. *(задача 001, v0.5.0)*
- [x] **Интеграция с Memory Compiler:** Автоматическая отправка логов (`--log_to_memory`) и подкоманда `log`. *(v0.4.0)*
- [x] **Интеграция Google Drive в CLI:** Добавлены подкоманды `fetch-drive` и `auth-drive` в `utils/cli_v3.py`. *(v0.6.0)*
- [x] **Расширение CLI:** Добавление интерактивного режима (`interactive mode`) для пошагового выполнения операций парсинга, валидации и реконструкции. *(v0.7.0)*
- [x] **Валидация данных:** Внедрение Pydantic-схем для строгой валидации входящих JSON-экспортов из Google AI Studio и промежуточных файлов (`utils/validation/export_validator.py`, команда `validate`). *(v0.7.0)*
- [x] **Улучшение логгирования:** Структурированное логирование (модуль `logging`, `utils/logging_config.py`), флаги `--verbose`, `--log-level`, `--log-file`, устранение deprecation warning `datetime.utcnow()`. *(v0.7.0)*

### 2. Функциональность (Парсинг, Дистилляция, Реконструкция)
- [x] **Модули работы с Google Drive:** Созданы `utils/drive/auth.py` (OAuth2 user-flow, refresh-токен) и `utils/drive/client.py` (`GoogleDriveChatFetcher` — поиск по имени в папке "Google AI Studio", скачивание raw JSON). *(задача 002)*
- [x] **Сквозной пайплайн Drive → Parse → Distill:** Возможность запускать парсинг и дистилляцию прямо при скачивании с Drive (`fetch-drive --parse --distill`). *(v0.6.0)*
- [x] **Конвейер дистилляции чатов:** Модули `chunker`, `redactor` (11 regex-паттернов секретов), `llm_client`, `verifier`, `safe_stem`, `pipeline`. *(v0.5.0)*
- [ ] **Поддержка других AI-платформ:** Исследование возможности расширения парсера для работы с экспортами чатов из других сервисов (например, ChatGPT, Claude).
- [ ] **Интерактивные шаблоны:** Разработка системы динамических шаблонов для реконструкции кода с передачей параметров через аргументы CLI.
- [ ] **Улучшение Markdown RAG:** Дополнительная оптимизация формата Markdown (семантические якоря, метатеги) для лучшей индексации в LLM.

### 3. Инструменты (Transformation & Tools)
- [x] **Трансформация схем (SchemaTransformer):** Двусторонняя конвертация JSON Schema (OpenAI ↔ Gemini SchemaData ↔ Python `google.genai.types.Schema`).
- [x] **Модификатор Studio JSON:** Утилита `utils/studio_json_modifier.py` (команда `apply_overrides_to_studio_json`) для применения оверрайдов (`.si`, `.fi`, `.li`).
- [x] **Инструмент объединения Markdown:** `tools/markdown_merger.py`.
- [ ] **Расширение `SchemaTransformer`:** Добавление поддержки конвертации между схемами JSON Schema и Pydantic-моделями.
- [ ] **GUI прототип:** Создание простого веб-интерфейса для визуального управления парсингом и реконструкцией.

### 4. Тестирование и Качество
- [x] **Покрытие тестами дистилляции:** 6 тестовых файлов (`safe_stem`, `redactor`, `chunker`, `llm_client`, `verifier`, `pipeline`), 73 теста. *(v0.5.0)*
- [x] **Тесты клиента Google Drive:** `tests/test_drive_fetch.py` (мокирование `google-api-python-client`). *(задача 002)*
- [x] **Актуализация и исправление legacy-тестов:** Восстановлены `tests/test_parsing.py`, `tests/test_reconstruction.py` и `tests/test_studio_json_reconstruction.py` под актуальные данные. *(v0.6.0)*
- [x] **Покрытие тестами модуля `transformation`:** Создан `tests/test_transformation.py` для тестирования `schema_transformer.py`. *(v0.6.0)*
- [x] **CI/CD:** Настроен GitHub Actions Workflow (`.github/workflows/ci.yml`) с матрицей Python 3.10-3.12, проверкой линтером ruff и запуском pytest. *(v0.6.0)*

## 📈 История версий (см. CHANGELOG.md)
- [0.7.0] — Интерактивный режим CLI (`interactive`), Pydantic-валидация JSON-экспортов (`validate`), структурированное логирование (`logging`), исправление deprecation warning `datetime.utcnow()`.
- [0.6.0] — Полноценная интеграция Google Drive (`fetch-drive`, `auth-drive`), сквозной пайплайн, тесты трансформера, фиксы тестов и CI/CD GitHub Actions.
- [0.5.0] — Подпапки вывода, команда `distill`, LLM-дистилляция, редакция секретов, верификатор.
- [0.4.0] — Интеграция с Memory Compiler (`--log_to_memory`, команда `log`).
- [3.0.0] — ООП-архитектура, CLI v3 (`parse`, `reconstruct`, `apply_overrides_to_studio_json`).
- [2.0.0] — JSON-экспорты, SchemaTransformer.
- [1.0.0] — Начальная версия.

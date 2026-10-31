---
type: report
id: "004"
slug: distill-synthesis-model
status: completed
executor: Antigravity
repo: avkus-labs/google-chat-utils
branch: feature/distill-synthesis-model-004
trust_tier: ai-verified-against-repo
last_verified_head: feature/distill-synthesis-model-004
generated: {by: antigravity, at: 2026-10-31}
---

# Отчёт 004: Отдельная модель для synthesis (`--llm_synthesis_model`)

## 1. Реализованный функционал

1. **Флаг `--llm_synthesis_model`:**
   - Добавлен аргумент `--llm_synthesis_model` (дефолт `""`) в общую функцию опций дистилляции `_add_distill_options` (`utils/cli_v3.py`). Доступен в командах `parse`, `distill`, `fetch-drive`.
   - В `build_distill_config`: чтение через `getattr(args, "llm_synthesis_model", "") or ""` с сохранением полной обратной совместимости.
   - В `DistillConfig` (`utils/distillation/pipeline.py`): добавлено поле `llm_synthesis_model: str = ""`, свойство `@property def synthesis_model(self) -> str` и функция `synthesis_model(cfg: DistillConfig) -> str`, возвращающие `cfg.llm_synthesis_model or cfg.llm_model`.

2. **Изоляция использования модели synthesis:**
   - Модель `cfg.synthesis_model` используется исключительно для:
     1. Вызова synthesis (`chat_completion(..., cfg.synthesis_model, synth_prompt, ...)`).
     2. Ключа кэша synthesis (`cache_key(merged, synth_tpl, cfg.synthesis_model, cfg.llm_base_url)`).
     3. Повторного вызова при невалидном JSON в `_parse_json_with_retry`.
   - Все чанки диалога и их ключи кэша строго используют `cfg.llm_model`. При смене synthesis-модели кэш чанков сохраняется и переиспользуется.

3. **Frontmatter `_distilled.md`:**
   - Поле `generated.by` всегда содержит модель чанков (`cfg.llm_model`).
   - Если `synthesis_model` отличается от `llm_model`, в frontmatter добавляется верхнеуровневый ключ `synthesis_model: "<имя>"`.
   - Если модели совпадают или synthesis-модель не задана, ключ `synthesis_model` в frontmatter не записывается.

4. **План дистилляции и dry-run:**
   - В выводе плана (`run_distill_batch` и `distill_human_markdown`) выводится строка моделей:
     `  модели: чанки=<A>, synthesis=<B>`.

5. **Интерактивный режим (`utils/interactive.py`):**
   - В `interactive_distill` и `interactive_parse` (при выборе дистилляции) добавлен опрос: `Модель для synthesis (Enter = та же):` со значением по умолчанию `""`.
   - Убран устаревший дефолт `"qwen2.5:14b"`: дефолтом выступает `os.getenv("DISTILLER_MODEL", "")`.
   - При отсутствии переменной окружения и пустом ответе пользователя выводится отказ с понятным сообщением об ошибке («требует явных --llm_base_url и --llm_model (без дефолтов)»), выполнение функции прерывается без падения по исключению.

---

## 2. Анализ полей `distill_preset`, `distill_concurrency`, `distill_retries`

В соответствии с разделом 2.7 (в) задания проведено исследование репозитория:
- Поиск `git grep` показал, что атрибуты `distill_preset`, `distill_concurrency`, `distill_retries` присутствуют **исключительно** в `utils/interactive.py` при ручной сборке объекта `argparse.Namespace` (в функциях `interactive_parse`, `interactive_distill`, `interactive_fetch_drive`).
- Ни в `cli_v3.py`, ни в `pipeline.py`, ни в одном тесте эти атрибуты не читаются и не используются.
- **Статус:** Это неиспользуемые («мёртвые») поля. В соответствии с инструкцией они оставлены в `interactive.py` без изменений до отдельного решения владельца репозитория.

---

## 3. Список изменённых и созданных файлов

| Файл | Статус | Описание |
|---|---|---|
| `utils/distillation/pipeline.py` | Изменён | Добавлено `llm_synthesis_model`, property/функция `synthesis_model`, вызовы synthesis и retry по synthesis-модели, ключ кэша synthesis по synthesis-модели, вывод моделей в плане, ключ `synthesis_model` в frontmatter. |
| `utils/cli_v3.py` | Изменён | Добавлен флаг `--llm_synthesis_model` в `_add_distill_options`, маппинг в `build_distill_config`, строка моделей в плане `run_distill_batch`. |
| `utils/interactive.py` | Изменён | Добавлен вопрос о synthesis-модели, удалён дефолт `"qwen2.5:14b"`, проверка на непустые base_url и model. |
| `tests/test_distill_overwrite.py` | Изменён | Обновлены два интерактивных теста для передачи явных параметров модели без опоры на удалённый дефолт `"qwen2.5:14b"`. |
| `tests/test_synthesis_model.py` | Создан | 10 тестов: вызовы LLM, retry, кэширование, frontmatter, парсинг CLI-флагов, отказ интерактива без модели, вывод плана в dry-run. |
| `pyproject.toml` | Изменён | Patch-bump версии: `0.7.1` -> `0.7.2`. |
| `CHANGELOG.md` | Изменён | Добавлена секция `[0.7.2] - 2026-10-31`. |
| `README.md` | Изменён | Документирован флаг `--llm_synthesis_model` и пример раздельного использования моделей. |
| `CLAUDE.md` | Изменён | Добавлен пример вызова `distill` с `--llm_synthesis_model`. |
| `.env.example` | Изменён | Добавлена переменная `DISTILL_SYNTHESIS_MODEL=gpt-4o`. |

---

## 4. Реальные команды и вывод

### 4.1. Проверка последних коммитов в `origin/main`
```powershell
git fetch origin; git log origin/main --oneline -5
```
Вывод:
```
0c0f630 docs: update report 003
5598925 feat(distill): incremental skip of existing _distilled.md, --distill_overwrite flag (task 003)
9ee61c2 docs(agents): task 003 distill-overwrite-flag for Antigravity; state update
19446b2 feat: v0.7.0 - interactive CLI mode, Pydantic validation, structured logging, utcnow fix
6668093 feat(distillation): EN prompts + RU translations, OKF-compatible frontmatter, status marks; state update, drop done tasks 001/002
```

### 4.2. Запуск unit-тестов
```powershell
python -m pytest
```
Вывод:
```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: E:\AI-Ecosystem\Google-Chat-Utils
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.13.0
collected 119 items

tests\test_chunker.py ...........                                        [  9%]
tests\test_distill_overwrite.py ........                                 [ 15%]
tests\test_drive_fetch.py ..                                             [ 17%]
tests\test_interactive.py ......                                         [ 22%]
tests\test_llm_client.py ...........                                     [ 31%]
tests\test_logging.py ....                                               [ 35%]
tests\test_parsing.py ...                                                [ 37%]
tests\test_pipeline.py ..........                                        [ 46%]
tests\test_reconstruction.py ..                                          [ 47%]
tests\test_redactor.py ...............                                   [ 60%]
tests\test_safe_stem.py ..............                                   [ 72%]
tests\test_studio_json_reconstruction.py .                               [ 73%]
tests\test_synthesis_model.py ..........                                 [ 81%]
tests\test_transformation.py ...                                         [ 84%]
tests\test_validation.py .......                                         [ 89%]
tests\test_verifier.py ............                                      [100%]

============================ 119 passed in 29.84s =============================
```

### 4.3. Проверка линтером ruff
```powershell
python -m ruff check utils/ tests/
```
Вывод:
```
All checks passed!
```

### 4.4. Проверка CLI команды в режиме dry-run с отдельной synthesis-моделью
```powershell
python utils/cli_v3.py distill --input_dir output_data --distill_dry_run --llm_base_url http://example.invalid/v1 --llm_model A --llm_synthesis_model B
```
Вывод:
```
🚀 Запуск команды [distill] 🚀
План дистилляции:
  модели: чанки=A, synthesis=B
  Настройка Hermes Agent и выбор моделей #2_human.md: ходов=169, чанков=12, ~вход=261783 ток., ~выход=52356 ток.
    редакция секретов: {'sk_key': 26, 'bearer': 2}
Итого: файлов=1, ~вход=261783 токенов
[dry-run] Вызовы LLM пропущены.
```

---

## 5. Аномалии и что НЕ проверено

- **Реальные вызовы LLM:** В соответствии с Cost guard реальные сетевые вызовы не производились (все тесты используют изолированные моки и `tmp_path`, в CLI проверен `--distill_dry_run`).
- **Слияние с `main`:** Самостоятельный мерж в ветку `main` не выполнялся согласно правилу задачи (ветка `feature/distill-synthesis-model-004` подготовлена для приёмки).


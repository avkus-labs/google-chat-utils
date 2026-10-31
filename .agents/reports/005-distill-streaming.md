---
type: report
id: "005"
slug: distill-streaming
status: completed
executor: Antigravity
repo: avkus-labs/google-chat-utils
branch: feature/distill-streaming-005
trust_tier: ai-verified-against-repo
last_verified_head: feature/distill-streaming-005
generated: {by: antigravity, at: 2026-10-31}
---

# Отчёт 005: Стриминг в клиенте дистилляции (`chat_completion`)

## 1. Реализованный функционал

1. **Стриминг по умолчанию в `chat_completion` (`stream=True`):**
   - Клиент `utils/distillation/llm_client.py` переведён на Server-Sent Events (SSE) стриминг через `httpx.stream("POST", url, json={**payload, "stream": True}, headers=headers, timeout=httpx.Timeout(timeout, connect=30.0))`.
   - Первые байты приходят незамедлительно, предотвращая таймауты OmniRoute (`requestQueue.maxWaitMs=15000ms`, `Direct response did not start within 30000ms`) и повторные запросы, вызывавшие `409 duplicate request`.
   - Семантика таймаута: `httpx.Timeout(timeout, connect=30.0)` задаёт паузу между байтами/чанками (read timeout), а не общее время всего запроса (по умолчанию 600.0 с).

2. **Сохранение пути без стриминга (`stream=False`):**
   - Прежняя логика вызова через блокирующий `httpx.post` полностью сохранена для режима `stream=False`.
   - Существующие тесты для `httpx.post` сохранены и переведены на явную проверку `stream=False`.

3. **Флаг CLI `--llm_no_stream`:**
   - Добавлен аргумент `--llm_no_stream` (`action="store_true"`) в общую функцию опций дистилляции `_add_distill_options` (`utils/cli_v3.py`). Доступен в командах `parse`, `distill`, `fetch-drive`.
   - `build_distill_config`: маппит `cfg.llm_stream = not getattr(args, "llm_no_stream", False)`.
   - В `DistillConfig` добавлено поле `llm_stream: bool = True`.
   - `pipeline.py` передаёт `stream=cfg.llm_stream` во все вызовы `chat_completion` (обработка чанков, synthesis, повторный вызов при невалидном JSON).
   - Интерактивный режим читает флаг через `getattr(args, "llm_no_stream", False)` без добавления лишних интерактивных вопросов.

4. **Обработка ошибок и ретраи:**
   - Код ответа проверяется до вычитывания тела:
     - `RETRYABLE_STATUS` (429, 500, 502, 503, 504): до 2 ретраев с экспоненциальным backoff `2 ** attempt`.
     - Прочие `>= 400`: немедленный `LLMFatalError` с первыми 200 символами тела ошибки, прочитанного через `resp.read()`.
   - Обрыв соединения до получения `[DONE]` или `finish_reason` либо ошибка чтения в середине потока (`httpx.HTTPError`) классифицируются как сетевая ошибка с теми же ретраями.
   - Частично собранный контент при ретрае гарантированно отбрасывается.
   - Событие с объектом `error` в потоке считается сетевой ошибкой и инициирует ретрай.

5. **Проверка завершения и сборка контента:**
   - `finish_reason` извлекается из последнего события, где он не `None`. Если итоговый `finish_reason != "stop"` (например, `"length"`), выбрасывается `ChunkFailedError`.
   - Пустой контент при `finish_reason == "stop"` возвращает пустую строку `""`.

---

## 2. Учтённые форматы SSE-событий

Парсер построчно обрабатывает `resp.iter_lines()`:
- `data: {"choices": [{"delta": {"content": "текст"}}]}` — контент извлекается и конкатенируется в итоговый буфер.
- `data: [DONE]` — штатное окончание генерации; цикл чтения завершается.
- `: keep-alive comment` — комментарии SSE (начинающиеся с `:`) игнорируются без ошибок.
- `\n` / пустые строки — игнорируются без ошибок.
- `event: ping` / строки, не начинающиеся с `data:` — игнорируются без ошибок.
- `data: {"choices": []}` / события с пустым списком `choices` (например, статистика usage) — игнорируются без ошибок.
- `data: {"choices": [{"delta": {"reasoning_content": "...", "reasoning": "...", "thinking": "..."}}]}` — поля рассуждений фильтруются и не попадают в результат (читается исключительно `delta.get("content")`).
- `data: not-a-json` — невалидный JSON в keep-alive логируется в `logger.debug` и пропускается без падения.
- `data: {"error": {"message": "..."}}` — событие ошибки в потоке трансформируется в `httpx.HTTPError` и уходит на retry.

---

## 3. Список изменённых файлов

| Файл | Статус | Описание |
|---|---|---|
| `utils/distillation/llm_client.py` | Изменён | Добавлен стриминг по умолчанию (`stream=True`) через `httpx.stream`, построчный парсер SSE, проверка статуса до чтения тела, ретраи при обрывах и событиях ошибки, фильтрация рассуждений, сохранение `stream=False` через `httpx.post`. |
| `utils/distillation/pipeline.py` | Изменён | Добавлено поле `llm_stream: bool = True` в `DistillConfig`, передача `stream=cfg.llm_stream` во все вызовы `chat_completion` (чанки, synthesis, retry). |
| `utils/cli_v3.py` | Изменён | Добавлен флаг `--llm_no_stream` в `_add_distill_options`, маппинг в `build_distill_config`. |
| `tests/test_llm_client.py` | Изменён | Прежние тесты переведены на `stream=False`; добавлен класс `TestChatCompletionStream` (9 тестов стриминга: сборка deltas, keep-alive, 429 retry/exhausted, 401 fatal, обрыв потока, error event, mid-stream drop с очисткой буфера, пустой контент). |
| `tests/test_pipeline.py` | Изменён | Добавлены тесты передачи флага `cfg.llm_stream` в `chat_completion` и класс `TestCliStreamFlag` (проверка парсинга `--llm_no_stream` в `parse`, `distill`, `fetch-drive` и `build_distill_config`). |
| `tests/test_synthesis_model.py` | Изменён | В сигнатуры вспомогательных функций `fake_chat` добавлены `*args, **kwargs` для совместимости с передачей `stream`. |
| `pyproject.toml` | Изменён | Patch-bump версии: `0.7.2` -> `0.7.3`. |
| `CHANGELOG.md` | Изменён | Добавлена секция `[0.7.3] - 2026-10-31`. |
| `README.md` | Изменён | Документирован флаг `--llm_no_stream`, добавлен раздел «Почему стрим (SSE)?» с перечислением таймаутов OmniRoute. |
| `CLAUDE.md` | Изменён | Добавлен пример запуска с `--llm_no_stream`, обновлено описание `llm_client.py`. |
| `.agents/reports/005-distill-streaming.md` | Создан | Итоговый отчёт о выполнении задачи 005. |

---

## 4. Реальные команды и вывод

### 4.1. Проверка последних коммитов origin/main
```powershell
git fetch origin; git log origin/main --oneline -8
```
Вывод:
```
d9177d0 feat(distill): separate synthesis model flag --llm_synthesis_model (task 004)
0c0f630 docs: update report 003
5598925 feat(distill): incremental skip of existing _distilled.md, --distill_overwrite flag (task 003)
9ee61c2 docs(agents): task 003 distill-overwrite-flag for Antigravity; state update
19446b2 feat: v0.7.0 - interactive CLI mode, Pydantic validation, structured logging, utcnow fix
6668093 feat(distillation): EN prompts + RU translations, OKF-compatible frontmatter, status marks; state update, drop done tasks 001/002
f880d3f feat: integrate Google Drive into CLI, fix test suite, add CI/CD and sync docs
a4ff9db sync
```

### 4.2. Переключение на ветку задачи
```powershell
git switch -c feature/distill-streaming-005 origin/main
```
Вывод:
```
Switched to a new branch 'feature/distill-streaming-005'
branch 'feature/distill-streaming-005' set up to track 'origin/main'.
```

### 4.3. Запуск полного набора тестов
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
collected 132 items

tests\test_chunker.py ...........                                        [  8%]
tests\test_distill_overwrite.py ........                                 [ 14%]
tests\test_drive_fetch.py ..                                             [ 15%]
tests\test_interactive.py ......                                         [ 20%]
tests\test_llm_client.py ....................                            [ 35%]
tests\test_logging.py ....                                               [ 38%]
tests\test_parsing.py ...                                                [ 40%]
tests\test_pipeline.py ..............                                    [ 51%]
tests\test_reconstruction.py ..                                          [ 53%]
tests\test_redactor.py ...............                                   [ 64%]
tests\test_safe_stem.py ..............                                   [ 75%]
tests\test_studio_json_reconstruction.py .                               [ 75%]
tests\test_synthesis_model.py ..........                                 [ 83%]
tests\test_transformation.py ...                                         [ 85%]
tests\test_validation.py .......                                         [ 90%]
tests\test_verifier.py ............                                      [100%]

============================= 132 passed in 9.77s =============================
```

### 4.4. Проверка линтером ruff
```powershell
python -m ruff check utils/ tests/
```
Вывод:
```
All checks passed!
```

### 4.5. Проверка CLI команды distill dry-run
```powershell
python utils/cli_v3.py distill --input_dir output_data --distill_dry_run --llm_base_url http://example.invalid/v1 --llm_model A
```
Вывод:
```
В output_data нет файлов *_human.md.
```

---

## 5. Выявленные аномалии

1. **Сигнатуры моков в `tests/test_synthesis_model.py`:**
   В тестах задачи 004 моки `fake_chat`, `fake_chat_1`, `fake_chat_2` имели строго фиксированный список аргументов `(base_url, model, prompt, api_key, timeout=120)`. При вызове из `pipeline.py` нового именованного аргумента `stream=cfg.llm_stream` возникал `TypeError: got an unexpected keyword argument 'stream'`. В сигнатуры этих моков добавлены `*args, **kwargs`.

2. **Состояние рабочего каталога:**
   В рабочей копии имелись незакоммиченные изменения пользователя в `requirements.txt` (добавлен `python-dotenv`), `utils/cli_v3.py` (вызов `load_dotenv()`), `utils/drive/auth.py` (порт `8080`), а также файлы в `input_data/` и `output_data/`. Все эти изменения сохранены нетронутыми.

---

## 6. Что НЕ проверено (граница ответственности)

- **Реальный шлюз (OmniRoute / xkiro):**
  В соответствии с разделом 5 (Cost guard) и разделом 1 задачи реальные сетевые запросы к OmniRoute/LLM и использование реальных ключей были запрещены. Проверка выполнена строго на мок-тестах (`httpx.stream` и `httpx.post`).
  Поведение на реальном шлюзе с большими диалогами проверяется владельцем репозитория в рамках приёмки.


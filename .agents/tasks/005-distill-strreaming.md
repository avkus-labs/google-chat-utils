---
type: task
id: "005"
slug: distill-streaming
status: completed
executor: Antigravity
repo: avkus-labs/google-chat-utils
branch: feature/distill-streaming-005
depends_on: "003 и 004 влиты в main (все три правят DistillConfig, _add_distill_options, build_distill_config, interactive.py)"
trust_tier: ai-verified-against-repo
last_verified_head: 9ee61c2 (+ локальный 696e803 с тикетом 004; origin/main мог уйти вперёд — сначала git fetch)
generated: {by: claude, at: 2026-10-31}
---

# 005 — Стриминг в клиенте дистилляции (`chat_completion`)

## Цель
Убрать зависимость от таймаутов OmniRoute на «ответ ещё не начался». Сейчас клиент шлёт запрос без `stream`, и первые байты приходят только после полной генерации. Подтверждено логами OmniRoute 2026-10-31 и кодом OmniRoute:
- `[504] ... requestQueue.maxWaitMs=15000ms` (env `RATE_LIMIT_MAX_WAIT_MS`, дефолт 15000; в панели Settings → Resilience → «Max queue wait»);
- `[504] Direct response did not start within 30000ms — retrying on a fresh socket` (только env `OMNIROUTE_DIRECT_HEADERS_TIMEOUT_MS`, дефолт 30000; `open-sse/utils/directResponseStartTimeout.ts`);
- после обрыва роутер повторяет запрос на другом аккаунте, а первый ещё выполняется → `409 duplicate request` у xkiro.
Со стримом первые байты приходят сразу (в OmniRoute для стримовых клиентов есть ранний keep-alive), так что оба таймаута не должны срабатывать. Агенты с контекстом 200k работают именно потому, что стримят. ⚠️ Что это полностью устраняет проблему, ожидание, не проверено: проверяет владелец реальным прогоном после приёмки.

## 1. Проверенные факты (не перепроверять)
- `utils/distillation/llm_client.py`: `chat_completion(base_url, model, prompt, api_key="", timeout=600.0) -> str` — payload `{"model", "messages":[user]}` (стр. ~73), `httpx.post(url, json=payload, headers=headers, timeout=timeout)` (стр. ~78). Ретраи: `MAX_RETRIES` с backoff `2**attempt` на `httpx.HTTPError` и `RETRYABLE_STATUS` (429/5xx); прочие 4xx → `LLMFatalError`; `finish_reason != "stop"` → `ChunkFailedError`.
- `pipeline.py` вызывает `chat_completion` из двух мест (чанки и synthesis, плюс повторный вызов в `_parse_json_with_retry`); тесты pipeline мокают `utils.distillation.pipeline.chat_completion`, их менять не нужно.
- `tests/test_llm_client.py` мокает `utils.distillation.llm_client.httpx.post` (тесты: success, url, retry 429, 429 exhausted, 401, finish_reason length) — эти тесты сохранить, переведя на `stream=False`.
- `cache_key(...)` от способа доставки ответа не зависит — НЕ добавлять в него `stream`.

## 2. Требуемое поведение
1. `chat_completion(..., timeout=600.0, stream=True)`. Старый путь (`httpx.post`, без стрима) остаётся под `stream=False`.
2. Стрим: `with httpx.stream("POST", url, json={**payload, "stream": True}, headers=..., timeout=httpx.Timeout(timeout, connect=30.0)) as resp:`. Статус проверять ДО чтения тела: `RETRYABLE_STATUS` → ретрай с тем же backoff, прочие `>=400` → `LLMFatalError` (тело прочитать через `resp.read()` и взять `[:200]`).
3. Разбор SSE построчно (`resp.iter_lines()`): строки `data: <json>`; `data: [DONE]` — конец. Игнорировать без ошибки: пустые строки, комментарии (`: ...`), строки, не начинающиеся с `data:`, события с пустым `choices` (например, `usage`), нераспознаваемый JSON в keep-alive (логировать на DEBUG, не падать). Контент собирать из `choices[0].delta.content` (если `None`/нет — пропускать). Поля рассуждений (`reasoning_content`, `reasoning`, `thinking`) в результат НЕ включать.
4. `finish_reason` брать из последнего события, где он не `None`. Если он не `"stop"` → `ChunkFailedError(f"finish_reason={...!r}")` (как сейчас).
5. Событие с объектом `error` в потоке, обрыв соединения до `[DONE]`/`finish_reason` (в т.ч. `httpx.HTTPError` в середине чтения) → считать сетевой ошибкой: те же ретраи, затем `LLMFatalError("Network error after retries: ...")`. Частично собранный контент при ретрае отбрасывать.
6. Пустой итоговый контент при `finish_reason == "stop"` — вернуть пустую строку как раньше (не новое поведение).
7. Флаг `--llm_no_stream` (store_true) в `_add_distill_options` → `DistillConfig.llm_stream: bool = True`; `pipeline.py` передаёт `stream=cfg.llm_stream` во все вызовы `chat_completion`. Интерактивный режим: вопроса не добавлять, читать через `getattr(args, "llm_no_stream", False)`.
8. Таймаут: `timeout` в `httpx.Timeout(timeout, connect=30.0)` задаёт паузу между байтами (read), а не длительность всего запроса — оставить значение 600 по умолчанию и описать это в docstring.

## 3. Тесты (только моки, без сети)
- Новые тесты стрима мокают `utils.distillation.llm_client.httpx.stream` (контекст-менеджер с `status_code` и `iter_lines`).
- Сборка контента из нескольких `delta`, `[DONE]`; keep-alive комментарии и пустые строки игнорируются; событие с пустым `choices` игнорируется; `reasoning_content` не попадает в результат.
- `finish_reason: "length"` → `ChunkFailedError`.
- 429 → ретрай → успех; 429 исчерпан → `LLMFatalError`; 401 → сразу `LLMFatalError` без ретраев.
- Обрыв потока без `finish_reason` → ретрай, затем `LLMFatalError`; `error` в событии → ретрай; частичный контент не попадает в ответ следующей попытки.
- `stream=False` — прежние тесты через `httpx.post`, без изменений логики.
- Парсинг `--llm_no_stream` в `parse`, `distill`, `fetch-drive`; `cfg.llm_stream` доходит до `chat_completion` (проверка через мок в тесте pipeline).
- Существующие тесты не ослаблять; `python -m pytest` целиком.

## 4. Документация
`README.md`, `CLAUDE.md` (флаги), `CHANGELOG.md`, версия в `pyproject.toml` (patch-bump от значения после 004). Отдельный абзац «Почему стрим»: перечислить три сообщения OmniRoute из раздела «Цель» и сказать, что при `--llm_no_stream` нужны `RATE_LIMIT_MAX_WAIT_MS` и `OMNIROUTE_DIRECT_HEADERS_TIMEOUT_MS`.

## 5. Cost guard
- Реальные вызовы LLM и любые сетевые запросы ЗАПРЕЩЕНЫ (нет `--llm_base_url/--llm_model`, ключей нет): только моки и `--distill_dry_run`.
- Не менять `prompts/`, `chunk_tokens`, `max_total_input_tokens`; `.distill_cache` не удалять; данные — только `tmp_path`, ничего в `input_data/` и `output_data/`.

## 6. Команды
PowerShell:
```powershell
git fetch origin; git log origin/main --oneline -8
git switch -c feature/distill-streaming-005 origin/main
python -m pytest
python -m ruff check utils/ tests/
python utils/cli_v3.py distill --input_dir output_data --distill_dry_run --llm_base_url http://example.invalid/v1 --llm_model A
```
bash:
```bash
git fetch origin && git log origin/main --oneline -8
git switch -c feature/distill-streaming-005 origin/main
python -m pytest
python -m ruff check utils/ tests/
python utils/cli_v3.py distill --input_dir output_data --distill_dry_run --llm_base_url http://example.invalid/v1 --llm_model A
```
`ruff` на `pipeline.py` уже даёт ~15 стилевых замечаний (UP/FA/I) до задачи: новых не добавлять, старые не чинить. `test_drive_fetch.py` требует `googleapiclient` (`requirements.txt`).

## 7. Вне скоупа и запреты
- Не менять формат дистиллята, промпты, верификатор, редактор секретов, логику перезаписи (003) и выбор synthesis-модели (004).
- Не менять OmniRoute и его настройки; не придумывать факты, номера строк, хэши; открытые вопросы эскалировать.
- Не мержить в `main` самостоятельно: ветка `feature/distill-streaming-005`, приёмка независимая.
- Секреты не цитировать, транскрипты и `.env` не коммитить.

## 8. Отчёт → `.agents/reports/005-distill-streaming.md`
Реальные команды и вывод (passed/failed), список изменённых файлов, какие форматы SSE-событий учтены, аномалии, что НЕ проверено (реальный шлюз).
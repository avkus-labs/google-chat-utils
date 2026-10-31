---
type: task
id: "004"
slug: distill-synthesis-model
status: open
executor: Antigravity
repo: avkus-labs/google-chat-utils
branch: feature/distill-synthesis-model-004
depends_on: "003 (принять и влить в main раньше: обе задачи правят DistillConfig, _add_distill_options, build_distill_config, interactive.py)"
trust_tier: ai-verified-against-repo
last_verified_head: 9ee61c2
generated: {by: claude, at: 2026-10-30}
---

# 004 — Отдельная модель для synthesis: `--llm_synthesis_model`

## Цель
Чанки можно гнать на дешёвой lite-модели, а synthesis (один вызов на весь дистиллят, валидный JSON, классификация) — на более сильной. Сейчас на оба шага идёт одна `--llm_model`.

## 1. Проверенные факты (не перепроверять)
- `pipeline.py` использует `cfg.llm_model` в четырёх местах: вызов чанка (~стр. 175), ключ кэша чанка (~167), вызов synthesis (~191) и ключ кэша synthesis (~186), повторный вызов `_parse_json_with_retry` (~244); плюс `generated.by` в frontmatter (~272 и ~305).
- `cache_key(chunk_text, prompt_template, model, base_url)` в `utils/distillation/llm_client.py` — модель уже входит в ключ; менять функцию не нужно.
- `chat_completion(base_url, model, prompt, api_key, timeout)` — модель аргументом; менять не нужно.
- Флаги дистилляции общие: `_add_distill_options` (`cli_v3.py`, ~стр. 306) для `parse`, `distill`, `fetch-drive`; конфиг собирает `build_distill_config` (~стр. 330); проверки `--llm_base_url/--llm_model` — `cli_v3.py` ~172, ~393, ~469.
- `utils/interactive.py` собирает `Namespace` вручную (ветки parse ~стр. 87 и distill ~стр. 159) — новые атрибуты читать через `getattr(args, "...", default)`.
- ⚠️ Расхождение, найденное при подготовке: `interactive.py` (стр. ~93 и ~170) подставляет дефолт модели `"qwen2.5:14b"` (из `DISTILLER_MODEL` или литерала). Решение владельца по 001: у `--llm_base_url/--llm_model` НЕТ дефолтов и автодетекта. Также в `Namespace` интерактива есть `distill_preset`, `distill_concurrency`, `distill_retries` — в `_add_distill_options` таких флагов нет; не проверено, используются ли они где-то. Эти два пункта см. раздел 2.7.
- ⚠️ Не проверено: что в `main` на момент старта нет изменений сверх `9ee61c2` — сначала `git fetch`, при расхождении сообщить.

## 2. Требуемое поведение
1. Флаг `--llm_synthesis_model` (добавить в `_add_distill_options` → доступен в `parse`, `distill`, `fetch-drive`). Пусто/не задан = используется `--llm_model` (поведение как сейчас).
2. `DistillConfig.llm_synthesis_model: str = ""`; свойство или функция `synthesis_model(cfg)` → `cfg.llm_synthesis_model or cfg.llm_model`.
3. Synthesis-модель используется ТОЛЬКО для: вызова synthesis, ключа кэша synthesis и повторного вызова в `_parse_json_with_retry`. Чанки и их ключи кэша — на `llm_model`, без изменений (кэш чанков при смене synthesis-модели остаётся валидным).
4. Тот же `--llm_base_url` и тот же ключ (`--llm_api_key_env`) для обеих моделей. Отдельный base_url/ключ для synthesis — вне скоупа (если нужен, эскалировать).
5. Frontmatter `_distilled.md`: `generated.by` = модель чанков (как сейчас); если synthesis-модель отличается — добавить top-level ключ `synthesis_model: "<имя>"` (через `json.dumps`, как остальные строки). Если совпадает — ключ не писать.
6. План (`plan_line`/вывод `run_distill_batch`) и dry-run: одна строка `модели: чанки=<A>, synthesis=<B>`.
7. `interactive.py`: (а) для дистилляции дополнительный вопрос `Модель для synthesis (Enter = та же):`, дефолт пустая строка → `llm_synthesis_model`; (б) убрать подстановку дефолта `"qwen2.5:14b"`: дефолт — `os.getenv("DISTILLER_MODEL", "")`, при пустом ответе — отказ с понятным сообщением (как в `cli_v3.py`: «требует явных --llm_base_url и --llm_model»); (в) про `distill_preset/concurrency/retries` — только сообщить в отчёте, используются они или мёртвые; не удалять без решения.
8. Совместимость: отсутствие нового атрибута у `args` (старые вызовы, интерактив) → `getattr(args, "llm_synthesis_model", "")`.

## 3. Тесты (только моки, `tmp_path`)
- `chat_completion` замокан с записью `model` в каждом вызове: чанки → `A`, synthesis → `B`, retry при невалидном JSON → `B`.
- Без флага: все вызовы на `A`.
- Ключи кэша: смена synthesis-модели не инвалидирует кэш чанков (второй прогон: чанки из кэша, synthesis — новый вызов).
- Frontmatter: ключ `synthesis_model` есть при `B != A`, отсутствует при совпадении/пустом.
- Парсинг флага в `parse`, `distill`, `fetch-drive`; интерактив пробрасывает значение; интерактив без модели → отказ без дефолта.
- Существующие тесты не ослаблять; `python -m pytest` целиком.

## 4. Документация
`README.md`, `CLAUDE.md` (список флагов), `CHANGELOG.md`, версия в `pyproject.toml` (patch-bump от значения после 003). Пример: `--llm_model gemini-3.1-flash-lite --llm_synthesis_model <более сильная>` (имена моделей — плейсхолдеры, не хардкодить).

## 5. Cost guard
- Реальные вызовы LLM ЗАПРЕЩЕНЫ (нет `--llm_base_url/--llm_model`, ключей нет): только моки `patch("utils.distillation.pipeline.chat_completion")` и `--distill_dry_run`.
- Не менять `prompts/`, `chunk_tokens`, `max_total_input_tokens`; `.distill_cache` не удалять; данные — только `tmp_path`, ничего в `input_data/` и `output_data/`.

## 6. Команды
PowerShell:
```powershell
git fetch origin; git log origin/main --oneline -5
git switch -c feature/distill-synthesis-model-004 origin/main
python -m pytest
python -m ruff check utils/ tests/
python utils/cli_v3.py distill --input_dir output_data --distill_dry_run --llm_base_url http://example.invalid/v1 --llm_model A --llm_synthesis_model B
```
bash:
```bash
git fetch origin && git log origin/main --oneline -5
git switch -c feature/distill-synthesis-model-004 origin/main
python -m pytest
python -m ruff check utils/ tests/
python utils/cli_v3.py distill --input_dir output_data --distill_dry_run --llm_base_url http://example.invalid/v1 --llm_model A --llm_synthesis_model B
```
`ruff` на `pipeline.py` уже даёт ~15 стилевых замечаний (UP/FA/I) до задачи: новых не добавлять, старые не чинить. `test_drive_fetch.py` требует `googleapiclient` (`requirements.txt`).

## 7. Вне скоупа и запреты
- Не менять формат тела дистиллята, промпты, верификатор, редактор секретов, логику перезаписи из 003.
- Не придумывать факты, номера строк, хэши; открытые вопросы эскалировать.
- Не мержить в `main` самостоятельно: ветка `feature/distill-synthesis-model-004`, приёмка независимая.
- Секреты не цитировать, транскрипты и `.env` не коммитить.

## 8. Отчёт → `.agents/reports/004-distill-synthesis-model.md`
Реальные команды и вывод (passed/failed), список изменённых файлов, ответ по `distill_preset/concurrency/retries`, аномалии, что НЕ проверено.
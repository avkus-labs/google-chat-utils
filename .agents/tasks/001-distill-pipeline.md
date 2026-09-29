---
type: task
id: "001"
slug: distill-pipeline
status: open
executor: local Claude Code (Windows / PowerShell)
repo: avkus-labs/google-chat-utils
branch: main
trust_tier: ai-verified-against-repo
last_verified_head: 538a658
generated: {by: claude, at: 2026-09-30}
---

# 001 — Подпапки вывода + LLM-дистилляция human.md

## Цель
1. `parse` складывает вывод каждого входного файла в отдельную подпапку.
2. Опция `--distill`: `_human.md` → LLM-дистиллятор → `_distilled.md` (концентрированный источник для OmniWiki `sources`: суть + путь к решениям, без шума).
3. Детерминированный верификатор результата (без LLM).

## 1. Проверенные факты (не перепроверять, кроме отмеченного ⚠️)
- `utils/cli_v3.py`: `process_single_parse_file` (стр. ~58–104) пишет 3 файла плоско: `f"{prefix}{name}_intermediate.json|_raw_rag.md|_human.md"`; `--output_prefix` по умолчанию `output_data/`; вход `--input_file` | `--input_dir`.
- `utils/parsing/google_studio_parser.py:533` `to_human_markdown`: заголовки `### **User**` / `### **Model**`; мысли модели — `<details><summary>🧠 Model Thoughts</summary>…</details>`; system instruction — блок цитаты `> `.
- Реальный образец (Hermes): 169 ходов (76 user / 93 model), `_human.md` = 628 130 символов, 119 блоков кода. Оценка ≈ 250k токенов (chars/2.5 — оценка, не замер) → один вызов невозможен, нужен чанкинг.
- В `_human.md` образца есть настоящие секреты (API-ключи, Bearer, Linear key): редакция ДО отправки в LLM обязательна.
- Промпты уже лежат: `prompts/distiller_chunk_prompt.md` (плейсхолдеры `{chunk_index}`, `{chunk_total}`), `prompts/distiller_synthesis_prompt.md` (ответ — маленький JSON). Их текст не менять; только загрузка.
- ⚠️ Не проверено: какой бэкенд/модель будет у пользователя. Поэтому всё через конфиг, без дефолтов на конкретный провайдер.

## 2. Что сделать

### Часть A — подпапки
- Вывод: `<base>/<safe_stem>/<safe_stem>_intermediate.json`, `_raw_rag.md`, `_human.md` (+ `_distilled.md` при `--distill`). `--output_prefix` теперь трактуется как базовая папка; обновить help и README.
- `safe_stem`: заменить `<>:"/\|?*` и управляющие символы на `_`, убрать хвостовые точки/пробелы; кириллицу и `#` оставить. Коллизия имён в одном прогоне → суффикс `-2`, `-3`.
- Существующие плоские файлы в `output_data/` НЕ трогать и не переносить.

### Часть B — `--distill`
Флаги (по умолчанию дистилляция ВЫКЛЮЧЕНА):
- `--distill`; `--distill_dry_run` (ничего не вызывает, печатает план); `--yes` (пропустить подтверждение);
- `--llm_base_url` и `--llm_model` — ОБЯЗАТЕЛЬНЫ при `--distill`, без дефолтов и без автодетекта из переменных окружения;
- `--llm_api_key_env` (имя переменной с ключом, по умолчанию `DISTILL_API_KEY`); ключ не логировать и не писать в файлы;
- `--distill_prompt_dir` (по умолчанию `prompts/`); `--chunk_tokens` (30000); `--max_total_input_tokens` (400000, жёсткий стоп); `--distill_max_chunks N` (для пробных прогонов); `--distill_thoughts drop|keep` (по умолчанию `drop`).
Транспорт: OpenAI-совместимый `POST {base_url}/chat/completions` через `requests` (или `httpx`), без новых тяжёлых SDK. `google-generativeai` для этого этапа НЕ использовать. Провайдер не переключать молча.

Пайплайн для одного `_human.md`:
1. Вырезать блок System Instruction, заменить строкой `[system instruction omitted: N chars, sha1 xxxx]`.
2. При `drop` — удалить `<details>…Model Thoughts…</details>`.
3. Редакция секретов регулярками (`sk-…`, `Bearer …`, `lin_api_…`, `ghs_/ghp_/gho_…`, `AIza…`, `token=`/`apiKey`/`api_key` значения, JWT `eyJ….….…`) → `[REDACTED]`. Логировать только счётчики по типам, не значения.
4. Пронумеровать ходы: `### **User** [#N]` (только во входе LLM).
5. Нарезать на чанки ≤ `chunk_tokens` (оценка chars/2.5) по границам ходов; не резать внутри ```-блока; ход больше лимита — резать по абзацам вне кода, помечая `(продолжение)`.
6. Вызвать chunk-промпт на каждый чанк. `finish_reason` ≠ `stop` → чанк провален, частичный результат не писать.
7. Склеить ответы чанков; один вызов synthesis-промпта на склеенный текст → JSON (`title, summary, keywords, tags, decisions_made, lessons_learned, topics_covered, open_questions`); невалидный JSON → 1 повтор, затем ошибка.
8. Записать `<stem>_distilled.md`: OKF-frontmatter (`type: source`, `title`, `status: active`, `trust_tier: ai-generated`, `generated: {by: <llm_model>, at}`, `original_source`, `source_sha256` от human.md, `chunks`, `summary`, `keywords`, `tags`) + тело + раздел `## Ключевая информация` (решения, уроки, темы, открытые вопросы).
Кэш: `<subfolder>/.distill_cache/`, ключ = sha256(текст чанка + промпт + модель); повторный запуск переиспользует. Флага `--force` НЕ делать; пересчёт = удалить `.distill_cache` вручную.
Ошибки: 429/5xx — до 2 повторов с backoff; 401/403/4xx — стоп сразу; ни при каких условиях не менять модель/бэкенд молча.

### Часть C — верификатор (без LLM, запускается после дистилляции)
Результат — в блок `verification:` frontmatter и в консоль; выходные файлы не удалять и не менять.
- Покрытие ходов: какие `#N` не упомянуты ни в одной ссылке «(ходы A–B)» → список пропусков (warning).
- Каждый ```-блок в distilled должен встречаться в источнике как подстрока (с нормализацией пробелов) → иначе список подозрительных блоков (warning с номерами).
- В distilled нет секретных паттернов (иначе ERROR, exit code 1 после записи).
- Frontmatter парсится; отношение длин distilled/source.

### Часть D — тесты и доки
- pytest (каталог `tests/`), без сети: `safe_stem`, чанкер (не режет в блоках кода, границы ходов, нумерация), редакция, верификатор; LLM-клиент подменять заглушкой.
- Обновить README (команды под Windows и Linux), CHANGELOG, ROADMAP; `python -m ruff check` на изменённых файлах.

## 3. Cost guard
- Ожидаемо для образца Hermes: ≈ 250k токенов входа → ≈ 9 чанков + 1 synthesis, ≈ 40–55k токенов выхода (оценка).
- Всегда сначала dry-run: печатает по каждому файлу число ходов, чанков, оценку входных/выходных токенов; для `--input_dir` — одна общая сводка и одно подтверждение. Оценка > `--max_total_input_tokens` → отказ, код выхода 2.
- Первый реальный прогон — только с `--distill_max_chunks 2`, потом решение пользователя.
- Запрещено: `--distill` без явных `--llm_base_url/--llm_model`; прогон на всю `input_data/` без dry-run и подтверждения; любые «форс»-режимы без кэша; повторный прогон без кэша «на всякий случай».
- Жёсткий стоп: если dry-run показал масштаб заметно больше ожидаемого (чанков > 15 на файл) — остановиться и спросить.

## 4. Вне скоупа и запреты
- Не менять текст промптов и не «улучшать» их; замечания — в отчёт.
- Не удалять/переносить существующие файлы в `output_data/`, `input_data/`; не менять `.gitignore`, не переписывать историю git.
- Не коммитить `input_data/`, `output_data/`, `.env`, ключи, транскрипты; в тестах не использовать реальные ключи.
- Не изобретать факты, номера строк и хэши; открытые вопросы — в отчёт, не решать самому.
- Реальные вызовы LLM в тестах запрещены.

## 5. Команды (PowerShell)
```powershell
git checkout main; git pull
python -m pytest -q
python utils/cli_v3.py parse --input_file "input_data/<file>" --output_prefix output_data/
python utils/cli_v3.py parse --input_file "input_data/<file>" --output_prefix output_data/ --distill --distill_dry_run --llm_base_url "<URL>" --llm_model "<MODEL>"
```
(bash: те же команды, разделитель путей `/`.) Значения `<URL>`/`<MODEL>` даёт пользователь.

## 6. Формат отчёта → `.agents/reports/001-distill-pipeline.md`
Реальные команды и вывод, числа из фактического dry-run (ходы/чанки/токены), результат pytest/ruff, аномалии верификатора, что НЕ проверено (например, реальный вызов LLM). После каждого шага: `✅ <что сделано>`.

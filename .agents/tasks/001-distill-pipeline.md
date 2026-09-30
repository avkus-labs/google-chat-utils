---
type: task
id: "001"
slug: distill-pipeline
status: done-pending-llm-credentials
executor: local Claude Code (Windows / PowerShell)
repo: avkus-labs/google-chat-utils
branch: main
trust_tier: ai-verified-against-repo
last_verified_head: b2e18e8
generated: {by: claude, at: 2026-09-30}
updated: {by: claude, at: 2026-09-30, reason: "финальные решения владельца по 11 пунктам обсуждения"}
completed: {by: claude, at: 2026-09-30, report: ".agents/reports/001-distill-pipeline.md", note: "реализация+тесты+линт+dry-run выполнены; реальный вызов LLM ждёт --llm_base_url/--llm_model от владельца"}
---

# 001 — Подпапки вывода + LLM-дистилляция human.md + команда `distill`

## Цель
1. `parse` складывает вывод каждого входного файла в отдельную подпапку.
2. Опция `--distill`: `_human.md` → LLM-дистиллятор → `_distilled.md` (концентрированный источник для OmniWiki `sources`: суть + путь к решениям, без шума).
3. Отдельная команда `distill` для уже готовых `_human.md` без повторного парсинга.
4. Детерминированный верификатор результата (без LLM).

## 1. Проверенные факты (не перепроверять, кроме отмеченного ⚠️)
- `utils/cli_v3.py`: `process_single_parse_file` (стр. ~58–104) пишет 3 файла плоско: `f"{prefix}{name}_intermediate.json|_raw_rag.md|_human.md"`; `--output_prefix` по умолчанию `output_data/`; вход `--input_file` | `--input_dir`.
- `utils/parsing/google_studio_parser.py:533` `to_human_markdown`: заголовки `### **User**` / `### **Model**`; мысли модели — `<details><summary>🧠 Model Thoughts</summary>…</details>`; system instruction — блок цитаты `> `.
- Реальный образец (Hermes): 169 ходов (76 user / 93 model), `_human.md` = 628 130 символов, 119 блоков кода. Оценка ≈ 314k токенов (628130/2.0) → один вызов невозможен, нужен чанкинг.
- В `_human.md` образца есть настоящие секреты (API-ключи, Bearer, Linear key): редакция ДО отправки в LLM обязательна.
- Промпты уже лежат: `prompts/distiller_chunk_prompt.md` (плейсхолдеры `{chunk_index}`, `{chunk_total}`), `prompts/distiller_synthesis_prompt.md` (ответ — маленький JSON). Их текст не менять; только загрузка.
- ⚠️ Не проверено: какой бэкенд/модель будет у пользователя. Поэтому всё через конфиг, без дефолтов на конкретный провайдер.

## 2. Что сделать

### Структура модуля
- `utils/distillation/` — отдельный пакет:
  - `chunker.py` — нарезка на чанки по ходам
  - `redactor.py` — редакция секретов
  - `llm_client.py` — транспорт через `httpx`
  - `verifier.py` — детерминированный верификатор
  - `pipeline.py` — общая точка входа `distill_human_markdown(path, cfg)`
- `utils/cli_v3.py` только диспетчер подкоманд (`parse`, `distill`, `log`, `apply_overrides_to_studio_json`, `reconstruct`).

### Часть A — подпапки
- Вывод: `<base>/<safe_stem>/<safe_stem>_intermediate.json`, `_raw_rag.md`, `_human.md` (+ `_distilled.md` при `--distill`). `--output_prefix` теперь трактуется как базовая папка; обновить help и README.
- `safe_stem`: заменить `<>:"/\|?*` и управляющие символы на `_`; **`#` заменить на `_`** (якорь в Markdown-ссылках и `file://`); убрать хвостовые точки/пробелы; кириллицу оставить.
- **Идемпотентность:** при совпадении имени папки — перезапись файлов внутри неё. Суффикс `-2`, `-3` только при явном флаге `--no-overwrite`.
- Существующие плоские файлы в `output_data/` НЕ трогать и не переносить.

### Часть B — `--distill`
Флаги (по умолчанию дистилляция ВЫКЛЮЧЕНА):
- `--distill`; `--distill_dry_run` (ничего не вызывает, печатает план); `--yes` (пропустить подтверждение);
- `--llm_base_url` и `--llm_model` — ОБЯЗАТЕЛЬНЫ при `--distill`, без дефолтов и без автодетекта из переменных окружения;
- `--llm_api_key_env` (имя переменной с ключом, по умолчанию `DISTILL_API_KEY`); ключ не логировать и не писать в файлы;
- `--distill_prompt_dir` (по умолчанию `prompts/`); `--chunk_tokens` (30000); `--max_total_input_tokens` (400000, жёсткий стоп); `--distill_max_chunks N` (для пробных прогонов); `--distill_thoughts drop|keep` (по умолчанию `drop`).

Транспорт: **`httpx`** (добавить в `requirements.txt`), OpenAI-совместимый `POST {base_url}/chat/completions`. `google-generativeai` для этого этапа НЕ использовать. Провайдер не переключать молча.

Пайплайн для одного `_human.md`:
1. Вырезать блок System Instruction, заменить строкой `[system instruction omitted: N chars, sha1 xxxx]`.
2. При `drop` — удалить `<details>…Model Thoughts…</details>`.
3. Редакция секретов регулярками → `[REDACTED]`. Логировать только счётчики по типам, не значения.
   Паттерны:
   - `sk-[A-Za-z0-9_-]{20,}`
   - `Bearer\s+[A-Za-z0-9_\-.]{20,}`
   - `lin_api_[A-Za-z0-9_-]{20,}`
   - `gh[psor]_[A-Za-z0-9]{36,}`
   - `AIza[A-Za-z0-9_-]{35}`
   - `token=[A-Za-z0-9%_-]{20,}` / `apiKey` / `api_key` значения в URL
   - JWT: `eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}`
   - AWS: `AKIA[0-9A-Z]{16}`
   - Slack: `xox[baprs]-[0-9A-Za-z_-]{10,}`
   - Приватные ключи: `-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+PRIVATE KEY-----`
4. Пронумеровать ходы: `### **User** [#N]` (только во входе LLM).
5. Нарезать на чанки ≤ `chunk_tokens` **оценка `chars / 2.0`**, защитный буфер 20% (резать на `0.8 × chunk_tokens` расчётных токенов). По границам ходов; не резать внутри ```-блока; ход больше лимита — резать по абзацам вне кода, помечая `(продолжение)`.
6. Гигантский код-блок (> лимита чанка) — принудительно делить по строкам с закрытием/переоткрытием ``` и маркером: `[... код разбит на части для дистилляции: часть k/N ...]`.
7. Вызвать chunk-промпт на каждый чанк. `finish_reason` ≠ `stop` → чанк провален, частичный результат не писать.
8. Склеить ответы чанков; один вызов synthesis-промпта на склеенный текст → JSON (`title, summary, keywords, tags, decisions_made, lessons_learned, topics_covered, open_questions`); невалидный JSON → 1 повтор, затем ошибка.
9. Записать `<stem>_distilled.md`: OKF-frontmatter (`type: source`, `title`, `status: active`, `trust_tier: ai-generated`, `generated: {by: <llm_model>, at}`, `original_source`, `source_sha256` от human.md, `chunks`, `summary`, `keywords`, `tags`) + тело + раздел `## Ключевая информация` (решения, уроки, темы, открытые вопросы).

Кэш: `<subfolder>/.distill_cache/`, ключ = `sha256(текст чанка + промпт + модель + base_url)`; повторный запуск переиспользует. Флага `--force` НЕ делать; пересчёт = удалить `.distill_cache` вручную.

Ошибки: 429/5xx — до 2 повторов с backoff; 401/403/4xx — стоп сразу; ни при каких условиях не менять модель/бэкенд молча.

### Часть B2 — команда `distill` (вторая точка входа)
- `python utils/cli_v3.py distill --input_file "<path>/<stem>_human.md" [флаги]`
- `python utils/cli_v3.py distill --input_dir "<dir>" [флаги]`
- Флаги те же, что у `parse --distill`. Новых флагов кроме `--output_dir` не вводить.
- Вывод: `<stem>_distilled.md` в той же папке, где лежит входной файл. `<stem>` = имя входного файла без суффикса `_human`. Необязательный `--output_dir` меняет папку. Кэш: `<папка вывода>/.distill_cache/`.
- `--input_dir`: только файлы `*_human.md`, без рекурсии. Одна общая сводка dry-run и одно подтверждение на весь набор.
- **Существующие файлы не перезаписывать.** Если `<stem>_distilled.md` уже есть — остановиться и сообщить. `--force` нет.
- Если во входном файле нет заголовков `### **User**` / `### **Model**` — ошибка и код выхода 2, к LLM не обращаться.
- Редакция секретов запускается всегда, даже если файл уже редактировался.
- Общая логика в `pipeline.py::distill_human_markdown(path, cfg)` — вызывается и из `parse --distill`, и из `distill`. Дублировать пайплайн нельзя.

### Часть C — верификатор (без LLM, запускается после дистилляции)
Результат — в блок `verification:` frontmatter и в консоль; выходные файлы не удалять и не менять.
- Покрытие ходов: парсить ссылки регуляркой `r'\(ходы?\s+(\d+)(?:[–-](\d+))?\)'`. Если 0 совпадений на весь файл — одно общее предупреждение `turn_anchors_missing`. Если ссылки есть — список пропущенных диапазонов (warning).
- Каждый ```-блок в distilled должен встречаться в источнике как подстрока (построчно с нормализацией: удаление концевых пробелов, `\r\n` → `\n`, игнорирование пустых строк в начале/конце) → иначе список подозрительных блоков (warning с номерами).
- В distilled нет секретных паттернов (иначе ERROR, exit code 1 после записи).
- Frontmatter парсится; отношение длин distilled/source.

### Часть D — тесты и доки
- pytest (каталог `tests/`), без сети: `safe_stem`, чанкер (не режет в блоках кода, границы ходов, нумерация, гигантский код-блок), редакция, верификатор, идемпотентность перезаписи, код выхода 2 для файла без заголовков, стоп на существующем `_distilled.md`, фильтр `*_human.md`.
- LLM-клиент подменяется заглушкой через `unittest.mock.patch` на `httpx.Client.post` (без реальных сокетов).
- Обновить README (команды под Windows и Linux), CHANGELOG, ROADMAP; `python -m ruff check` на изменённых файлах.

## 3. Cost guard
- Ожидаемо для образца Hermes: ≈ 314k токенов входа → ≈ 13 чанков + 1 synthesis, ≈ 50–70k токенов выхода (оценка).
- Всегда сначала dry-run: печатает по каждому файлу число ходов, чанков, оценку входных/выходных токенов; для `--input_dir` — одна общая сводка и одно подтверждение. Оценка > `--max_total_input_tokens` → отказ, код выхода 2.
- Первый реальный прогон — только с `--distill_max_chunks 2`, потом решение пользователя.
- Запрещено: `--distill` без явных `--llm_base_url/--llm_model`; прогон на всю `input_data/` без dry-run и подтверждения; любые «форс»-режимы без кэша; повторный прогон без кэша «на всякий случай».
- Жёсткий стоп: если dry-run показал масштаб заметно больше ожидаемого (чанков > 15 на файл) — остановиться и спросить.
- Последовательные вызовы, без параллелизма.

## 4. Вне скоупа и запреты
- Не менять текст промптов и не «улучшать» их; замечания — в отчёт.
- Не удалять/переносить существующие файлы в `output_data/`, `input_data/`; не менять `.gitignore`, не переписывать историю git.
- Не коммитить `input_data/`, `output_data/`, `.env`, ключи, транскрипты; в тестах не использовать реальные ключи.
- Не изобретать факты, номера строк и хэши; открытые вопросы — в отчёт, не решать самому.
- Реальные вызовы LLM в тестах запрещены.
- Секреты в `input_data/`/`output_data/` (ключи `sk-f92…`, `sk-97e…`, `sk-493…`, `lin_ap…`) — вне скоупа этого тикета; ротацию и чистку истории делает владелец отдельно.

## 5. Команды (PowerShell)
```powershell
git checkout main; git pull
python -m pytest -q
python utils/cli_v3.py parse --input_file "input_data/<file>" --output_prefix output_data/
python utils/cli_v3.py parse --input_file "input_data/<file>" --output_prefix output_data/ --distill --distill_dry_run --llm_base_url "<URL>" --llm_model "<MODEL>"
python utils/cli_v3.py distill --input_file "output_data/<stem>_human.md" --distill_dry_run --llm_base_url "<URL>" --llm_model "<MODEL>"
python utils/cli_v3.py distill --input_dir "output_data/" --distill_dry_run --llm_base_url "<URL>" --llm_model "<MODEL>"
```
(bash: те же команды, разделитель путей `/`.) Значения `<URL>`/`<MODEL>` даёт пользователь.

## 6. Формат отчёта → `.agents/reports/001-distill-pipeline.md`
Реальные команды и вывод, числа из фактического dry-run (ходы/чанки/токены), результат pytest/ruff, аномалии верификатора, что НЕ проверено (например, реальный вызов LLM). После каждого шага: `✅ <что сделано>`.

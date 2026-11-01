---
type: task
id: "007"
slug: distill-si-only
status: open
executor: Antigravity
repo: avkus-labs/google-chat-utils
branch: feature/distill-si-only-007
trust_tier: ai-verified-against-repo
last_verified_head: 80c5a15
generated: {by: claude, at: 2026-11-01}
---

# 007 — Чаты «только System Instruction» (без ходов User/Model)

## Цель
Часть чатов Google AI Studio (пример: `Bitrix Deobfuscation Expert (BDX) md`) содержит только `### System Instruction`: владелец вручную вычистил реплики и оставил концентрат решений внутри инструкции. Сейчас такой файл отклоняется (`exit=2`), и ценный документ не попадает в базу знаний. Нужен отдельный режим «документ».

## 1. Проверенные факты (не перепроверять)
- Лог батча владельца (`/tmp/distill_all.log`): `Ошибка: В файле нет заголовков '### **User**' / '### **Model**'`, `exit=2`, ходов 0, чанков 0. Файл: 15 КБ, 292 строки, начинается `# Chat: <название>`, затем `### System Instruction`, все строки инструкции в виде blockquote (`> ...`), диалога нет.
- `pipeline.py:73-81` `validate_turn_headers` бросает `DistillError(exit_code=2)`, если в первых 200 000 символах нет `### **User**` и `### **Model**`; в `prepare` System Instruction заменяется заглушкой (`chunker.extract_and_omit_system_instruction`, `SI_SECTION_RE` в `chunker.py:19`), то есть для диалогов инструкция по замыслу отбрасывается.
- Для режима «документ» дистилляция диалога не подходит: нет ходов, якорей `(ходы A–B)` и покрытия ходов.
- ⚠️ Не проверено: сколько ещё «нулевых» чатов того же вида (владелец говорит «несколько»); у других могла быть другая причина, их нужно сверить по списку (см. раздел 6).

## 2. Требуемое поведение
1. Детектор `is_si_only(text)`: в тексте есть `### System Instruction` и нет ни одного заголовка `### **User**`/`### **Model**` (после удаления мыслей).
2. Новый флаг `--distill_si_only {document,skip}` (в `_add_distill_options` → `parse`, `distill`, `fetch-drive`; `DistillConfig.si_only: str = "document"`). `skip` — прежнее поведение (отказ с понятным сообщением, `exit=2`).
3. Режим `document`:
   a. Взять текст секции `### System Instruction` целиком (как есть, blockquote не снимать), прогнать через `redact_secrets`.
   b. Оценка токенов `chars / 2.0`; если больше `chunk_tokens` — `DistillError` («документ слишком большой для режима SI-only, нужна ручная обработка»), без чанкинга.
   c. Один вызов synthesis (`cfg.synthesis_model`, тот же шаблон `prompts/distiller_synthesis_prompt.md`, вход в `<distilled_text kind="document">...</distilled_text>`) для метаданных; поля `resolution`, `failed_approaches`, `error_signatures` для документа не использовать (не писать во frontmatter).
   d. Записать `<stem>_distilled.md` (атомарно, правила перезаписи как у обычных файлов): frontmatter как у обычного дистиллята, но `chunks: 0`, `source_kind: system_instruction`, `verification:` только `status` и секреты (без `turn_coverage`, без `length_ratio`); тело — `# <title>`, абзац `description`, затем исходная секция System Instruction ДОСЛОВНО (после редакции секретов), затем `## Ключевая информация` из метаданных (как сейчас).
   e. `trust_tier: ai-generated` (не `human-reviewed`).
4. `plan_line` для режима: `режим=SI-документ, ~вход=<N> ток.`; в `dry-run` вызовы LLM пропускаются.
5. Файлы, где одновременно есть SI и ходы, идут по обычному пути (режим не применяется).
6. Верификатор: для `source_kind: system_instruction` проверка покрытия ходов пропускается (не предупреждение), проверка секретов остаётся.

## 3. Тесты (только моки, без сети, `tmp_path`)
- Файл формата BDX (SI-blockquote, без ходов) → `_distilled.md` создан, тело содержит SI дословно, `chunks: 0`, `source_kind`, нет `turn_coverage`; `chat_completion` вызван ровно один раз (synthesis).
- `--distill_si_only skip` → `DistillError` с `exit_code=2`, файл не создан.
- Файл с SI и ходами → обычный путь, число вызовов LLM как раньше.
- Секрет в SI → заменён на `[REDACTED]` в теле; верификатор не видит секретов.
- Документ больше `chunk_tokens` → `DistillError`.
- `--distill_dry_run` → вызовов LLM нет, `plan_line` содержит `SI-документ`.
- Существующие тесты не ослаблять; `python -m pytest` целиком.

## 4. Документация
`README.md`, `CLAUDE.md`, `CHANGELOG.md`, версия (patch-bump). Описать режим и флаг.

## 5. Cost guard
Реальные вызовы LLM и сеть ЗАПРЕЩЕНЫ: только моки и `--distill_dry_run`. Не менять `chunk_tokens`, `max_total_input_tokens`; реальный `.distill_cache` не трогать; данные только в `tmp_path`, ничего в `input_data/`, `output_data/`. Реальный документ BDX не коммитить.

## 6. Команды
PowerShell:
```powershell
git fetch origin; git switch -c feature/distill-si-only-007 origin/main
python -m pytest
python -m ruff check utils/ tests/
Select-String -Path "output_data\*\*_human.md" -Pattern "^### \*\*(User|Model)\*\*" -NotMatch -List | Select-Object -ExpandProperty Path
```
(последняя команда — только для поиска файлов без ходов; результат приложить к отчёту списком путей, содержимое файлов не публиковать)
bash:
```bash
git fetch origin && git switch -c feature/distill-si-only-007 origin/main
python -m pytest
python -m ruff check utils/ tests/
grep -L -E '^### \*\*(User|Model)\*\*' output_data/*/*_human.md
```
`ruff` на `pipeline.py` уже даёт ~15 стилевых замечаний до задачи: новых не добавлять, старые не чинить.

## 7. Вне скоупа и запреты
Не менять логику диалогов, чанкинг, верификацию диалогов (006), выбор моделей, стриминг; не добавлять виртуальных реплик пользователя; не придумывать факты и хэши; открытое эскалировать. Не мержить в `main` самостоятельно: ветка `feature/distill-si-only-007`, приёмка независимая. Секреты не цитировать.

## 8. Отчёт → `.agents/reports/007-distill-si-only.md`
Реальные команды и вывод (passed/failed), список изменённых файлов, список найденных файлов без ходов (только пути), аномалии, что НЕ проверено.

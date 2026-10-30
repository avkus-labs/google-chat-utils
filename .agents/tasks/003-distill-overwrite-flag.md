---
type: task
id: "003"
slug: distill-overwrite-flag
status: open
executor: Antigravity
repo: avkus-labs/google-chat-utils
branch: feature/distill-overwrite-003
trust_tier: ai-verified-against-repo
last_verified_head: 19446b2
generated: {by: claude, at: 2026-10-30}
---

# 003 — Инкрементальная дистилляция: пропуск готовых `_distilled.md` + флаг `--distill_overwrite`

## Цель
В папке уже лежат готовые `_distilled.md`, к ним добавляют новые `_human.md`. Дистилляция должна обработать только новые файлы, не падая и не тратя токены на готовые; перезапись готовых — только по явному флагу.

## 1. Проверенные факты (не перепроверять)
- `utils/distillation/pipeline.py:131-133`: если `<stem>_distilled.md` существует, `distill_human_markdown` бросает `DistillError("...перезапись запрещена...")`. Это закреплено тестом `tests/test_pipeline.py:~117` (второй запуск → `pytest.raises(DistillError)`, LLM не вызывается) — тест остаётся валидным.
- `utils/cli_v3.py:347-388` `run_distill_batch`: план и лимит `max_total_input_tokens` считаются по ВСЕМ файлам, включая готовые; затем цикл вызывает LLM по файлам по порядку и при первой `DistillError` делает `sys.exit`. Следствие: если готовый файл стоит в середине списка, предыдущие новые уже потратили токены, а последующие новые не обработаны.
- Общие флаги дистилляции: `_add_distill_options` (`cli_v3.py:306`), используется командами `parse`, `distill`, `fetch-drive`; конфиг собирает `build_distill_config` (`cli_v3.py:330`); `DistillConfig` в `pipeline.py`.
- Интерактивный режим `utils/interactive.py` (`interactive_distill`, ~стр. 159, и ветка parse ~стр. 87) собирает `Namespace` вручную — новый атрибут читать через `getattr(args, "distill_overwrite", False)`.
- Перезапись папок и файлов `parse` (`os.makedirs(..., exist_ok=True)`) уже действует по умолчанию — не менять.
- Кэш `.distill_cache` ключуется по `sha256(chunk + prompt + model + base_url)`: смена промпта = промах кэша = повторные вызовы LLM. Это ожидаемо, не чинить.
- ⚠️ Не проверено: реальный прогон с LLM (нет `--llm_base_url/--llm_model`) — он в этой задаче запрещён.

## 2. Требуемое поведение
1. **По умолчанию (без флага):** готовый `_distilled.md` = пропуск, не ошибка. Проверка до плана и до подтверждения: пропущенные файлы НЕ входят в план, в `Итого` и в лимит токенов. Для каждого пропущенного — строка `⏭ пропуск (уже есть): <путь>`; в конце — `пропущено N, к обработке M`. Если к обработке 0 — сообщение и код выхода 0, без запроса подтверждения. Подсказка в сообщении: `--distill_overwrite` для перегенерации. Относится и к одиночному `--input_file`.
2. **`--distill_overwrite`:** готовые файлы включаются в план (помечать `перезапись`) и регенерируются.
3. **Запись атомарная** (во всех режимах): писать во временный файл рядом + `os.replace`; при любой ошибке до конца старый `_distilled.md` остаётся нетронутым.
4. **Кэш не трогать и не очищать** при перезаписи.
5. `distill_human_markdown` без `cfg.overwrite=True` по-прежнему бросает `DistillError` на существующий файл (защита от прямого вызова; существующий тест не менять).
6. Новый атрибут `DistillConfig.overwrite: bool = False`; флаг `--distill_overwrite` добавить в `_add_distill_options` (значит, он доступен в `parse`, `distill`, `fetch-drive`) и передать в `build_distill_config`.
7. Интерактивный режим: в сценариях с дистилляцией вопрос `Перезаписать уже готовые _distilled.md?` (default = Нет), результат → `distill_overwrite`.

## 3. Тесты (только с моками LLM, `tmp_path`)
- batch: [готовый, новый] → LLM вызван только для нового; готовый не изменён; код выхода 0; токены готового не в `Итого`.
- batch, порядок [новый, готовый, новый] → оба новых обработаны.
- все готовые → 0 вызовов LLM, выход 0, без запроса подтверждения.
- с `--distill_overwrite` → готовый регенерирован (вызовы LLM есть, содержимое заменено).
- сбой LLM при перезаписи → старый файл цел (проверка атомарности).
- парсинг флага для `parse`, `distill`, `fetch-drive`; интерактивный режим выставляет атрибут.
- Существующие тесты не ослаблять; `python -m pytest` целиком.

## 4. Документация
`README.md`, `CLAUDE.md` (список CLI), `CHANGELOG.md`, версия `0.7.1` в `pyproject.toml`; описать поведение по умолчанию (пропуск) и флаг.

## 5. Cost guard
- Реальные вызовы LLM ЗАПРЕЩЕНЫ: `--llm_base_url/--llm_model` не заданы, ключей нет. Только моки (`unittest.mock.patch("utils.distillation.pipeline.chat_completion")`) и `--distill_dry_run`.
- Не удалять `.distill_cache`, не менять `prompts/`, `chunk_tokens`, `max_total_input_tokens`.
- Тестовые данные — только в `tmp_path`; ничего не добавлять в `input_data/` и `output_data/`.

## 6. Команды
PowerShell:
```powershell
git fetch origin; git switch -c feature/distill-overwrite-003 origin/main
python -m pytest
python -m ruff check utils/ tests/
python utils/cli_v3.py distill --input_dir output_data --distill_dry_run
```
bash:
```bash
git fetch origin && git switch -c feature/distill-overwrite-003 origin/main
python -m pytest
python -m ruff check utils/ tests/
python utils/cli_v3.py distill --input_dir output_data --distill_dry_run
```
Замечание: `ruff` на `pipeline.py` и так выдаёт ~15 стилевых замечаний (UP/FA/I), были до задачи; новых не добавлять, существующие не чинить. `tests/test_drive_fetch.py` требует `googleapiclient` — если не установлен, поставить из `requirements.txt`.

## 7. Вне скоупа и запреты
- Не менять формат `_distilled.md`, промпты, верификатор, редактор секретов, логику `parse`.
- Не придумывать факты, номера строк, хэши; открытые вопросы — эскалировать, не решать самому.
- Не мержить в `main` самостоятельно: ветка `feature/distill-overwrite-003`, приёмка независимая.
- Секреты не цитировать, транскрипты и `.env` не коммитить.

## 8. Отчёт → `.agents/reports/003-distill-overwrite-flag.md`
Реальные команды и вывод (число тестов passed/failed), список изменённых файлов, аномалии, что НЕ проверено.

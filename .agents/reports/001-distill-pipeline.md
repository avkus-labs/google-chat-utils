---
type: report
task: "001"
slug: distill-pipeline
executor: local Claude Code (Windows / PowerShell)
generated: {by: claude, at: 2026-09-30}
---

# Отчёт по задаче 001 — Подпапки вывода + LLM-дистилляция + команда `distill`

## Итог

Реализация, юнит-тесты, линт и реальный `--distill_dry_run` на существующем Hermes `_human.md` выполнены. Реальные вызовы LLM НЕ выполнялись: `--llm_base_url` и `--llm_model` владельцем ещё не даны (по условию задачи дефолтов и автодетекта нет).

## ✅ Шаг 1 — Обновление текста задачи и сверка промптов

- `.agents/tasks/001-distill-pipeline.md` переписан под финальные решения владельца (таблица противоречий: новое побеждает; маркер разрезки кода язык-нейтральный; структура `utils/distillation/`).
- Промпты прочитаны напрямую:
  - `prompts/distiller_chunk_prompt.md`: плейсхолдеры `{chunk_index}`, `{chunk_total}` — единственные; формат ссылок `(ходы 12–15)` прописан явно в `<rules>` → верификатор покрытия ходов будет срабатывать по назначению.
  - `prompts/distiller_synthesis_prompt.md`: плейсхолдеров нет, ожидает один валидный JSON без ```-обёртки с полями `title, summary, keywords, tags, decisions_made, lessons_learned, topics_covered, open_questions`.
- Тексты промптов не изменены.

## ✅ Шаг 2 — Часть A: подпапки вывода

- `utils/cli_v3.py`: `process_single_parse_file` теперь пишет `<output_prefix>/<safe_stem>/<safe_stem>_{intermediate.json,raw_rag.md,human.md}`; `--output_prefix` трактуется как базовая папка. Перезапись идемпотентна (никаких `-2`, `-3`).
- `utils/distillation/safe_stem.py`: `<>:"/\|?*#%&` и управляющие символы → `_`, хвостовые точки/пробелы убираются, кириллица и внутренние пробелы сохраняются.
- Существующие плоские файлы в `output_data/` не тронуты.
- ⚠️ Не выполнено: сквозной прогон `parse` на реальном входном файле (создал бы новые файлы с секретами в `output_data/`; решение за владельцем).

## ✅ Шаг 3 — Часть B: пайплайн дистилляции

`utils/distillation/`:
- `chunker.py` — вырезка System Instruction (плейсхолдер с длиной и sha1), удаление Model Thoughts (при `drop`), нумерация ходов `[#N]`, чанкинг по границам ходов (оценка токенов `chars/2.0`, буфер 20%), принудительная разрезка гигантских код-блоков с закрытием/переоткрытием ``` и маркером `[... код разбит на части для дистилляции: часть k/N ...]`.
- `redactor.py` — 11 regex-паттернов (sk-, JWT, Bearer, lin_api_, gh*_ / ghp_..., AIza, AKIA, xox[baprs]-, PEM-ключи, URL-параметры `token=`/`apiKey=`, key-value секреты). В лог — только счётчики.
- `llm_client.py` — `httpx`, OpenAI-совместимый `POST {base_url}/chat/completions`; 429/5xx → до 2 повторов с backoff; 401/4xx → стоп; `finish_reason != stop` → чанк провален. Кэш `.distill_cache/<sha256>.json`, ключ = `sha256(chunk + prompt + model + base_url)`.
- `pipeline.py` — общая точка входа `distill_human_markdown(path, cfg)`, вызывается и из `parse --distill`, и из команды `distill` (дублирования пайплайна нет). Существующий `_distilled.md` → остановка, перезаписи нет, `--force` нет. Невалидный synthesis-JSON → 1 повтор → ошибка.

## ✅ Шаг 4 — Команда `distill`

- `python utils/cli_v3.py distill --input_file|--input_dir` с тем же набором флагов; `--input_dir` берёт только `*_human.md` без рекурсии; одна общая сводка и одно подтверждение на набор.
- Файл без заголовков `### **User**`/`### **Model**` → ошибка, код выхода 2, к LLM не обращаемся.
- `--llm_base_url`/`--llm_model` обязательны, дефолтов и автодетекта нет.

## ✅ Шаг 5 — Часть C: верификатор

- `verifier.py` (без LLM): покрытие ходов (0 совпадений → одно общее предупреждение `turn_anchors_missing`, иначе список пропущенных), дословность ```-блоков с нормализацией пробелов (warning, не фатально), секретные паттерны в результате → `status: error` (файл уже записан, код выхода 1), валидность frontmatter + отношение длин.
- Поправлен баг, найденный при ревью: `findall` для паттернов с группами захвата занизил бы счётчики → заменено на `finditer`.

## ✅ Шаг 6 — Тесты и линт

```
$ python -m pytest tests/ -q --ignore=tests/test_studio_json_reconstruction.py \
    --ignore=tests/test_parsing.py --ignore=tests/test_reconstruction.py
73 passed in 1.50s

$ python -m ruff check utils/distillation/ utils/cli_v3.py
All checks passed!
```

Новые тестовые файлы (все без сети, LLM-клиент подменён моками, реальных секретов нет): `test_safe_stem.py`, `test_redactor.py`, `test_chunker.py`, `test_llm_client.py`, `test_verifier.py`, `test_pipeline.py` (включая проверку, что `distill` и `parse --distill` используют один пайплайн; стоп на существующем `_distilled.md`; код выхода 2 без заголовков ходов; фильтр `*_human.md`).

### Предсуществующие падения тестов (НЕ чинил, вне скоупа 001)
- `tests/test_studio_json_reconstruction.py` — импортирует несуществующий модуль `utils.reconstruction.studio_json_reconstructor` (последнее изменение: `1c9a5e3 refactoring`).
- `tests/test_parsing.py::test_parse_example1`, `::test_parse_with_si_fi` — файлы `data/Example1`, `data/Example6.si` удалены в коммите `9e3d874` (чистка репо).
- `tests/test_reconstruction.py::test_reconstruct_python_code` — зависит от `output_data/Example6_intermediate.json`, которого больше нет.

## ✅ Шаг 7 — Реальный dry-run на Hermes

```
$ python utils/cli_v3.py distill --input_file "output_data/Настройка Hermes Agent и выбор моделей #2_human.md" \
    --distill_dry_run --llm_base_url http://placeholder --llm_model placeholder

План дистилляции:
  Настройка Hermes Agent и выбор моделей #2_human.md: ходов=169, чанков=12, ~вход=261783 ток., ~выход=52356 ток.
    редакция секретов: {'sk_key': 26, 'bearer': 2}
Итого: файлов=1, ~вход=261783 токенов
[dry-run] Вызовы LLM пропущены.
```

- ходов=169 — совпадает с проверенными фактами задачи (76 user / 93 model).
- чанков=12 < 15 → жёсткий стоп не сработал; 261 783 ток. < 400 000 → лимит не превышен.
- 26 вхождений `sk-…` — ровно то, что зафиксировано в стейте (`Настройка Hermes Agent…`, 26 вхождений одного ключа) + 2 Bearer-токена. Всё вырезано ДО любых сетевых вызовов; в dry-run сеть не дёргалась вовсе.
- Оценка выхода ~52 356 ток. против ожидавшихся 40–55k — в пределах прогноза.

## ❌ Что НЕ проверено

1. Реальный вызов LLM (ни одного сетевого запроса не сделано; нужны `--llm_base_url` и `--llm_model` от владельца).
2. Сквозной прогон `parse` с записью в подпапки на реальном входном файле.
3. Поведение кэша на повторном реальном прогоне (покрыто юнит-тестом, не живым запуском).
4. Секреты `sk-f92…`, `sk-97e…`, `sk-493…`, `lin_ap…` в истории git и в `input_data/`/`output_data/` — вне скоупа 001, ротация и чистка истории остаются за владельцем (зафиксировано в стейте, ничего не трогал).

## Следующий шаг владельца

```
python utils/cli_v3.py distill --input_file "output_data/Настройка Hermes Agent и выбор моделей #2_human.md" \
    --distill_max_chunks 2 --llm_base_url "<URL>" --llm_model "<MODEL>"
```
(первый реальный прогон — только с `--distill_max_chunks 2`, затем решение о полном прогоне.)

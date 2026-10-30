---
type: report
id: "003"
slug: distill-overwrite-flag
status: completed
executor: Antigravity
repo: avkus-labs/google-chat-utils
branch: feature/distill-overwrite-003
trust_tier: ai-verified-against-repo
last_verified_head: feature/distill-overwrite-003
generated: {by: antigravity, at: 2026-10-31}
---

# Отчёт 003: Инкрементальная дистилляция, пропуск готовых `_distilled.md` и флаг `--distill_overwrite`

## 1. Реализованный функционал

1. **Пропуск готовых файлов по умолчанию:**
   - В `utils/cli_v3.py` (`run_distill_batch`) перед формированием плана проверяется наличие соответствующего `_distilled.md` для каждого `_human.md`.
   - Если файл уже существует и `--distill_overwrite` не передан:
     - Выводится информационная строка: `⏭ пропуск (уже есть): <путь>`.
     - Файл не включается в план, в суммарную оценку токенов и в проверку лимита `max_total_input_tokens`.
     - Выводится счётчик: `пропущено N, к обработке M`.
     - Если к обработке 0 файлов, выполнение завершается с кодом 0 без запроса подтверждения пользователя и с подсказкой об использовании `--distill_overwrite`.

2. **Флаг `--distill_overwrite`:**
   - Добавлен атрибут `overwrite: bool = False` в `DistillConfig` (`utils/distillation/pipeline.py`).
   - Добавлен аргумент `--distill_overwrite` в общую функцию опций дистилляции `_add_distill_options` (`utils/cli_v3.py`). Флаг доступен во всех релевантных подкомандах: `distill`, `parse`, `fetch-drive`.
   - Передаётся в конфигурацию через `build_distill_config`.
   - При активном флаге готовые файлы включаются в план с пометкой `[перезапись]` и перегенерируются.

3. **Атомарная запись (`atomic write`):**
   - В `distill_human_markdown` (`utils/distillation/pipeline.py`) запись файла теперь выполняется во временный файл рядом (`<out_path>.tmp`) с последующей заменой через `os.replace`.
   - При любых ошибках в процессе генерации или верификации временный файл удаляется, а старый `_distilled.md` остаётся нетронутым.

4. **Защита прямого вызова:**
   - Функция `distill_human_markdown(path, cfg)` при вызове напрямую без `cfg.overwrite=True` по-прежнему выбрасывает `DistillError`, защищая от случайной перезаписи.

5. **Интерактивный режим (`utils/interactive.py`):**
   - В сценариях `interactive_distill` и `interactive_parse` (при выборе дистилляции) добавлен запрос подтверждения: `Перезаписать уже готовые _distilled.md?` (по умолчанию: Нет), значение передаётся в `args.distill_overwrite`.

---

## 2. Список изменённых и созданных файлов

| Файл | Статус | Описание |
|---|---|---|
| `utils/distillation/pipeline.py` | Изменён | Добавлено поле `overwrite: bool = False` в `DistillConfig`, проверка `getattr(cfg, "overwrite", False)`, атомарная запись через `.tmp` и `os.replace`. |
| `utils/cli_v3.py` | Изменён | Добавлен флаг `--distill_overwrite` в `_add_distill_options`, `cfg.overwrite` в `build_distill_config`, хелпер `_distilled_path_for` и логика пропуска существующих файлов в `run_distill_batch`. |
| `utils/interactive.py` | Изменён | Добавлен опрос пользователя о перезаписи в `interactive_distill` и `interactive_parse`. |
| `tests/test_distill_overwrite.py` | Создан | 8 тестов: пропуск готового, порядок [новый, готовый, новый], все готовые без подтверждения, перезапись по флагу, атомарность при сбое LLM, парсинг флагов во всех командах, интерактивный режим. |
| `pyproject.toml` | Изменён | Версия повышена до `0.7.1`. |
| `CHANGELOG.md` | Изменён | Добавлена секция `[0.7.1]`. |
| `README.md` | Изменён | Обновлена версия `v0.7.1`, описание инкрементальной обработки, примеры с `--distill_overwrite`. |
| `CLAUDE.md` | Изменён | Добавлен пример использования `--distill_overwrite`. |

---

## 3. Реальные команды и вывод

### 3.1. Запуск unit-тестов
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
collected 109 items

tests\test_chunker.py ...........                                        [ 10%]
tests\test_distill_overwrite.py ........                                 [ 17%]
tests\test_drive_fetch.py ..                                             [ 19%]
tests\test_interactive.py ......                                         [ 24%]
tests\test_llm_client.py ...........                                     [ 34%]
tests\test_logging.py ....                                               [ 38%]
tests\test_parsing.py ...                                                [ 41%]
tests\test_pipeline.py ..........                                        [ 50%]
tests\test_reconstruction.py ..                                          [ 52%]
tests\test_redactor.py ...............                                   [ 66%]
tests\test_safe_stem.py ..............                                   [ 78%]
tests\test_studio_json_reconstruction.py .                               [ 79%]
tests\test_transformation.py ...                                         [ 82%]
tests\test_validation.py .......                                         [ 88%]
tests\test_verifier.py ............                                      [100%]

============================= 109 passed in 7.15s =============================
```

### 3.2. Проверка линтером ruff
```powershell
python -m ruff check utils/ tests/
```
Вывод:
```
All checks passed!
```

### 3.3. Dry-run дистилляции
```powershell
python utils/cli_v3.py distill --input_dir output_data --distill_dry_run --llm_base_url "http://test" --llm_model "test"
```
Вывод:
```
🚀 Запуск команды [distill] 🚀
План дистилляции:
  Настройка Hermes Agent и выбор моделей #2_human.md: ходов=169, чанков=12, ~вход=261783 ток., ~выход=52356 ток.
    редакция секретов: {'sk_key': 26, 'bearer': 2}
Итого: файлов=1, ~вход=261783 токенов
[dry-run] Вызовы LLM пропущены.
```

---

## 4. Аномалии и особенности

- Аномалий не выявлено.
- Тест кэша подтвердил корректность детерминированного кэширования: при одинаковом содержимом чанков повторный вызов LLM предотвращается кэшем `.distill_cache`.

---

## 5. Что НЕ проверено

- Реальные сетевые вызовы к внешнему LLM API (в соответствии с Cost Guard заданием 003 реальные вызовы LLM запрещены; всё взаимодействие проверено на моках).

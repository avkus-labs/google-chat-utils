# Отчёт по задаче 006: Целостность дистилляции, пустые ответы, строгая верификация

**ID задачи:** 006  
**Ветка:** `feature/distill-integrity-006`  
**Дата:** 2026-11-01  
**Исполнитель:** Antigravity (Gemini 3.8 Flash)  
**Репозиторий:** `avkus-labs/google-chat-utils`  
**Статус:** completed  

---

## 1. Краткое резюме проделанной работы

1. **006.A — Пустой ответ = ошибка, защита кэша:**
   - В `utils/distillation/llm_client.py` для обоих режимов (`stream=True` и `stream=False`): если `content.strip() == ""` при завершении генерации, возбуждается `ChunkFailedError("empty response")` с попытками повтора (`MAX_RETRIES`).
   - В `DistillCache`: метод `put(key, content)` игнорирует пустое/пробельное содержимое; метод `get(key)` возвращает `None` (промах кэша), если в файле кэша хранится пустая строка или пробелы (защита от отравленного кэша).
   - В `pipeline.py`: пустой ответ на шаге synthesis вызывает `DistillError("Synthesis вернул пустой ответ.", exit_code=1)`.

2. **006.B — Честный статус верификации и `--distill_strict`:**
   - В `utils/distillation/verifier.py`:
     - Статус `status: warning` выставляется при наличии любого из условий:
       - Непокрытые ходы диалога (`turn_coverage.missed`).
       - Ошибки в якорях (`anchor_issues`): вырожденные якоря-диапазоны вида `(ходы 5–5)`, вырожденные заглушки `(ходы N–N)`, `(ходы [не указаны])`, `(ходы [не указан])`, номера ходов вне диапазона `1..turn_count`.
       - Подозрительные блоки кода (>30% ненайденных строк).
     - Статус `status: error` выставляется только при наличии неэкранированных секретов.
     - Статус `status: ok` — при полном покрытии и отсутствии предупреждений.
   - Во frontmatter документа формируется компактный блок `verification:` с полями `status`, `turn_coverage` (число и сжатые диапазоны, например `пропущено 72, диапазоны: 1-9, 43-54`), `anchor_issues`, `code_blocks`, `length_ratio`.
   - Добавлен флаг `--distill_strict` (CLI и `DistillConfig.strict: bool = False`): при покрытии ходов < 100% или любых `anchor_issues` дистилляция прерывается с `DistillError`, выходной файл не записывается, кэш успешных чанков сохраняется.

3. **006.C — Проверка кода без ложных срабатываний:**
   - Реализована нормализация текста `_normalize()`: CRLF → LF, удаление пробелов на концах строк, схлопывание серий пробелов/табов в один пробел, типографские знаки в ASCII (`…` → `...`, кавычки, тире).
   - Построчная проверка: блок считается подозрительным только если в источнике не найдено более 30% его непустых строк (порог от 2 строк). Блоки, все строки которых найдены в источнике, но склеены иначе, подозрительными не считаются.

4. **006.D — Чаты без реплик пользователя (ручная чистка):**
   - В `prepare()`: если после удаления мыслей и System Instruction в диалоге нет заголовков `### **User**`, в начало текста добавляется ненумеруемая пометка `[примечание пайплайна: в диалоге нет реплик пользователя (удалены при ручной очистке); подтверждений со стороны пользователя нет]`. Нумерация ходов и `turn_count` не меняются.
   - В `plan_line()` для таких файлов добавляется метка `⚠ нет реплик пользователя`.
   - Если суммарное содержимое ходов (без заголовков) короче 200 символов, файл отклоняется с сообщением `Нет содержимого для дистилляции (суммарный текст ходов < 200 символов)`.
   - В промпты `distiller_chunk_prompt.md` и `distiller_chunk_prompt_ru.md` в секцию `<status_marks>` добавлено правило: при отсутствии реплик пользователя или наличии пометки пайплайна статус `[подтверждено]` не используется; всё исходящее от модели помечается `[предложено моделью]`.

5. **006.E — Документация и версионирование:**
   - Обновлены `pyproject.toml` (версия bump до `0.7.4`), `CHANGELOG.md`, `README.md`, `CLAUDE.md`.
   - Задокументировано, что `source_sha256` вычисляется по тексту после нормализации переводов строк universal newlines (CRLF → LF).

---

## 2. Реальные команды проверки и вывод тестов

### Запуск полного набора тестов:
```powershell
python -m pytest
```
**Вывод:**
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: E:\AI-Ecosystem\Google-Chat-Utils
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.13.0
collected 185 items

tests\test_chunker.py ...........                                        [  5%]
tests\test_distill_overwrite.py .........                                [ 10%]
tests\test_drive_fetch.py ..                                             [ 11%]
tests\test_interactive.py .......                                        [ 15%]
tests\test_llm_client.py ............................                    [ 30%]
tests\test_logging.py ....                                               [ 32%]
tests\test_parsing.py ...                                                [ 34%]
tests\test_pipeline.py .................................                 [ 52%]
tests\test_reconstruction.py ..                                          [ 53%]
tests\test_redactor.py ...............                                   [ 61%]
tests\test_safe_stem.py ..............                                   [ 69%]
tests\test_si_only.py ...............                                    [ 77%]
tests\test_studio_json_reconstruction.py .                               [ 77%]
tests\test_synthesis_model.py ..........                                 [ 83%]
tests\test_transformation.py ...                                         [ 84%]
tests\test_validation.py .......                                         [ 88%]
tests\test_verifier.py .....................                             [100%]

============================= 185 passed in 8.82s =============================
```

### Проверка стиля и линтинга (ruff):
```powershell
python -m ruff check utils/ tests/
```
**Вывод:**
```text
All checks passed!
```

---

## 3. Список изменённых файлов

- `utils/distillation/llm_client.py` — проверка непустого ответа (`ChunkFailedError`), защита кэша от пустых значений.
- `utils/distillation/verifier.py` — честные статусы (`ok`/`warning`/`error`), детекция якорей-заглушек и якорей вне диапазона, нормализация и построчная проверка блоков кода.
- `utils/distillation/pipeline.py` — флаг `strict`, поддержка `prepare` для чатов без реплик пользователя, порог длины текста <200 символов, рендеринг компактного блока `verification:`.
- `utils/cli_v3.py` — CLI флаг `--distill_strict`, передача в `build_distill_config`.
- `utils/interactive.py` — добавление параметров в вызовы интерактивного режима.
- `prompts/distiller_chunk_prompt.md`, `prompts/distiller_chunk_prompt_ru.md` — правило запрета `[подтверждено]` при отсутствии реплик пользователя.
- `tests/test_verifier.py` — новые тесты на честные статусы, якоря-заглушки, построчную проверку кода, нормализацию CRLF и многоточия.
- `tests/test_llm_client.py` — тесты на ошибку при пустом ответе (stream и non-stream) и защиту кэша.
- `tests/test_pipeline.py` — тесты на `--distill_strict`, пустой ответ synthesis, чаты без реплик пользователя, порог <200 символов.
- `tests/test_distill_overwrite.py`, `tests/test_synthesis_model.py` — адаптация фикстур под порог >200 символов.
- `pyproject.toml` — версия 0.7.4.
- `CHANGELOG.md`, `README.md`, `CLAUDE.md` — документация.
- `.agents/tasks/006-distill-integrity.md` — статус `completed`.

---

## 4. Что НЕ проверено и аномалии

- Реальные вызовы к шлюзу LLM с боевыми API-ключами не выполнялись (в соответствии с Cost Guard и ограничениями задачи; все проверки проведены на моках и модульных тестах).
- Защита данных: директории `input_data/` и `output_data/` не изменялись в рамках коммита (использовались только фикстуры `tmp_path`).

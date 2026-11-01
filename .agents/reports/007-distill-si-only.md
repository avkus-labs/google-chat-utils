# Отчёт по задаче 007: Чаты «только System Instruction» (режим документа)

**ID задачи:** 007  
**Ветка:** `feature/distill-si-only-007`  
**Дата:** 2026-11-01  
**Исполнитель:** Antigravity (Gemini 3.8 Flash)  
**Репозиторий:** `avkus-labs/google-chat-utils`  
**Статус:** completed  

---

## 1. Краткое резюме проделанной работы

1. **Детектор `is_si_only(text)`:**
   - Функция определяет, содержит ли файл секцию `### System Instruction` и при этом не содержит ни одного заголовка `### **User**` или `### **Model**` (после удаления тегов мыслей).

2. **CLI флаг и конфигурация `--distill_si_only`:**
   - Добавлен флаг `--distill_si_only {document,skip}` с дефолтом `document` во все релевантные команды (`parse`, `distill`, `fetch-drive` и интерактивный режим `interactive.py`).
   - Поле `si_only: str = "document"` включено в `DistillConfig`.

3. **Режим `document` (`distill_si_document`):**
   - Текст System Instruction извлекается дословно (сохраняя blockquote `> ...`).
   - Проводится через `redact_secrets` для маскирования конфиденциальных данных.
   - Проверяется лимит токенов (`chars / 2.0 <= cfg.chunk_tokens`). Если текст превышает размер одного чанка, возбуждается понятная ошибка `DistillError` с рекомендацией ручной обработки.
   - Выполняется ровно один вызов LLM на synthesis-модели с шаблоном `prompts/distiller_synthesis_prompt.md`, обёрнутым в `<distilled_text kind="document">`.
   - Ответ парсится через `_parse_json_with_retry`.
   - Формируется `_distilled.md` (атомарно через `.tmp` файл):
     - Frontmatter содержит `chunks: 0`, `source_kind: system_instruction`, `trust_tier: ai-generated`.
     - Поля диалога (`turn_coverage`, `resolution`, `failed_approaches`, `error_signatures`) исключены.
     - Тело содержит заголовок `# <title>`, аннотацию, секцию `## System Instruction` с текстом инструкции и `## Ключевая информация`.

4. **Режим `skip`:**
   - При `--distill_si_only skip` возбуждается `DistillError(..., exit_code=2)` с пояснением, воспроизводя прежнее поведение без поломки пайплайна.

5. **Верификатор:**
   - В `utils/distillation/verifier.py` добавлен параметр `source_kind: Optional[str] = None`. Для `source_kind == "system_instruction"` проверка покрытия ходов пропускается (не генерирует предупреждений), а проверка секретов остаётся в силе.

6. **Поиск файлов без ходов в `output_data`:**
   - Выполнен поиск файлов в `output_data`, не содержащих заголовков `### **User**` / `### **Model**`.

---

## 2. Реальные команды проверки и вывод

### Поиск файлов без ходов в `output_data`:
```powershell
Get-ChildItem -Path output_data -Filter "*_human.md" -Recurse | Where-Object { (Select-String -Path $_.FullName -Pattern "^### \*\*(User|Model)\*\*").Count -eq 0 } | Select-Object -ExpandProperty FullName
```
**Результат:**
В текущем каталоге `output_data/` найден ровно 1 файл `_human.md`:
- `output_data\Анализ проекта PartScout_ Hermes\Анализ проекта PartScout_ Hermes_human.md` (содержит 184 хода диалога).
Других файлов без ходов в локальном репозитории на момент проверки не обнаружено.

### Запуск тестов:
```powershell
python -m pytest tests/test_si_only.py
```
**Вывод:**
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: E:\AI-Ecosystem\Google-Chat-Utils
configfile: pyproject.toml
plugins: anyio-4.13.0
collected 11 items

tests\test_si_only.py ...........                                        [100%]

============================= 11 passed in 1.48s ==============================
```

### Запуск полного набора тестов:
```powershell
python -m pytest
```
**Вывод:**
```text
============================= 185 passed in 8.82s =============================
```

### Проверка линтером ruff:
```powershell
python -m ruff check utils/ tests/
```
**Вывод:**
```text
All checks passed!
```

---

## 3. Список изменённых файлов

- `utils/distillation/pipeline.py` — функция `distill_si_document()`, детектор `is_si_only()`, обработка `_SIOnlySignal`, поддержка `source_kind` в `render_distilled()`.
- `utils/distillation/verifier.py` — поддержка `source_kind="system_instruction"` (пропуск проверки покрытия ходов).
- `utils/cli_v3.py` — CLI опция `--distill_si_only {document,skip}`, обработка SI-only файлов в батче.
- `utils/interactive.py` — значение `distill_si_only` по умолчанию в аргументах интерактивного меню.
- `tests/test_si_only.py` — 11 новых тестов для режима SI-only (создание документа, dry-run, режим skip, смешанный диалог, лимит токенов, редакция секретов, frontmatter).
- `pyproject.toml` — версия `0.7.5`.
- `CHANGELOG.md`, `README.md`, `CLAUDE.md` — описание режима и флага `--distill_si_only`.
- `.agents/tasks/007-distill-si-only.md` — статус `completed`.

---

## 4. Что НЕ проверено и аномалии

- Реальные вызовы LLM не выполнялись (в соответствии с ограничениями Cost Guard, использовались только моки).
- Реальный файл BDX в репозитории отсутствует (не коммитится согласно ограничениям).
- Локальная директория `output_data/` содержит только один диалог `PartScout: Hermes`.

# 🧰 utils

Главный пакет с утилитами для работы с чатами Google AI Studio, дистилляции контента, работы с Google Drive и Gemini API.

## Структура
- `core/` — базовые модели данных (`chat_elements.py`, `schema_elements.py`)
- `parsing/` — парсер экспортов чатов (`google_studio_parser.py`)
- `distillation/` — пайплайн LLM-дистилляции (`pipeline.py`, `chunker.py`, `redactor.py`, `verifier.py`, `llm_client.py`, `safe_stem.py`)
- `drive/` — интеграция с Google Drive API (`auth.py`, `client.py`)
- `reconstruction/` — реконструктор Python-кода (`gemini_code_reconstructor.py`)
- `transformation/` — трансформация JSON Schema (`schema_transformer.py`)
- `templates/` — шаблоны для генерации кода
- `studio_json_modifier.py` — утилита для применения оверрайдов к "сырым" JSON-файлам Studio
- `cli_v3.py` — единый CLI-интерфейс

## Применение оверрайдов к Studio JSON

Перед парсингом и реконструкцией можно модифицировать сырой Studio JSON:
```bash
python utils/cli_v3.py apply_overrides_to_studio_json \
  --input_studio_json data/Example \
  --output_studio_json output_data/Example_overridden.json \
  --si_file data/Example.si \
  --fi_file data/Example.fi \
  --li_file data/Example.li \
  --fi_mode replace \
  --li_mode append
```

- Поддерживаются режимы: `fi_mode` (`replace`/`prepend`), `li_mode` (`replace`/`append`).

---

Документация: см. `../docs/`

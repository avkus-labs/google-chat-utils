# 🧰 utils

Главный пакет с утилитами для работы с чатами Google AI Studio и Gemini API.

## Структура
- `core/` — базовые модели данных
- `parsing/` — парсер экспортов чатов
- `reconstruction/` — реконструктор Python-кода
- `transformation/` — трансформация JSON Schema
- `templates/` — шаблоны для генерации кода
- `studio_json_modifier.py` — утилита для применения оверрайдов к "сырым" JSON-файлам Studio

## Быстрые ссылки
- [core](./core/README.md)
- [parsing](./parsing/README.md)
- [reconstruction](./reconstruction/README.md)
- [transformation](./transformation/README.md)
- [templates](./templates/README.md)

## Новое: Применение оверрайдов к Studio JSON

Перед парсингом и реконструкцией используйте команду:
```bash
python utils/cli_v3.py apply_overrides_to_studio_json \
  --input_studio_json data/Example \
  --output_studio_json data/Example_overridden.json \
  --si_file data/Example.si \
  --fi_file data/Example.fi \
  --li_file data/Example.li \
  --fi_mode replace \
  --li_mode append
```

- Поддерживаются режимы: `fi_mode` (`replace`/`prepend`), `li_mode` (`replace`/`append`).
- После применения оверрайдов используйте `parse` и `reconstruct` только с подготовленными файлами.

---

Документация: см. `../docs/` 
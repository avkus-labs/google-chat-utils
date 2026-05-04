# 📑 utils.parsing

Модуль для парсинга экспортов чатов Google AI Studio.

## Основной класс
- `GoogleAIStudioJSONParser` — парсинг JSON-файлов, генерация Markdown

## Пример использования
```python
from utils.parsing.google_studio_parser import GoogleAIStudioJSONParser
parser = GoogleAIStudioJSONParser()
data = parser.parse('data/Example1')
md = parser.to_markdown(data)
```

## Особенности вывода
- Все выходные файлы кладутся в `output_data/` без подпапок.
- Имена файлов формируются на основе имени входного файла (например, `Example6_intermediate.json`, `Example6_raw_rag.md`).

**Примечание:** Парсер работает только с "сырыми" JSON-файлами Studio, в которые все необходимые оверрайды уже были применены (например, с помощью `studio_json_modifier.py` или команды `apply_overrides_to_studio_json`).

---

Документация: см. `../docs/parser.md` 
# 🔄 utils.transformation

Модуль для трансформации JSON Schema между форматами (OpenAI, Gemini, Python-код).

## Основной класс
- `SchemaTransformer` — преобразование схем

## Примеры CLI
```bash
python -m utils.transformation.schema_transformer --openai_to_gemini data/example_openai_schema.json output_data/example_gemini_schema.json
python -m utils.transformation.schema_transformer --gemini_to_openai data/example_gemini_schema.json output_data/example_openai_schema_out.json
python -m utils.transformation.schema_transformer --gemini_to_python data/example_gemini_schema.json output_data/example_gemini_schema.py
```

## Пример Python
```python
from utils.transformation.schema_transformer import SchemaTransformer
tr = SchemaTransformer()
schema = tr.openai_to_gemini_schema({...})
```

---

Документация: см. `../docs/transformer.md` 
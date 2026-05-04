# 📚 Документация по проекту google-chat-utils v3

Добро пожаловать! Здесь собраны все основные сведения, примеры и справка по работе с утилитами для парсинга, реконструкции, трансформации и генерации кода для Google AI Studio и Gemini API.

## 🗂️ Структура
- [core](./core_models.md) — модели данных
- [parser](./parser.md) — парсер экспортов
- [reconstructor](./reconstructor.md) — генерация Python-кода
- [transformer](./transformer.md) — трансформация схем

## 🚀 Быстрые примеры CLI
- Применение оверрайдов к Studio JSON:
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
- Парсинг:
  ```bash
  python -m utils.cli_v3 parse --input_file data/Example_overridden.json --output_prefix output_data/
  ```
- Реконструкция:
  ```bash
  python -m utils.cli_v3 reconstruct --input_json output_data/Example_overridden_intermediate.json --output_py output_data/Example_reconstructed.py --template_dir utils/templates/ --template_name gemini_studio_default.py.tpl --api_key_var_name "MY_API_KEY" --model_name gemini-pro
  ```
- Объединение Markdown:
  ```bash
  python tools/markdown_merger.py --input output_data/Example1_raw_rag.md output_data/Example2_raw_rag.md --output output_data/combined_examples_rag.md --separator "\n---\n" --include_filenames
  ```
- Трансформация схем:
  ```bash
  python -m utils.transformation.schema_transformer --openai_to_gemini data/example_openai_schema.json output_data/example_gemini_schema.json
  ```

## 🧑‍💻 Пример Python-кода
```python
from utils.parsing.google_studio_parser import GoogleAIStudioJSONParser
parser = GoogleAIStudioJSONParser()
data = parser.parse('data/Example_overridden.json')
md = parser.to_markdown(data)
```

## 🆕 Реконструкция JSON для Google AI Studio

Воссоздайте валидный JSON-файл для Studio с учётом оверрайдов:

```bash
python -m utils.cli_v3 reconstruct_studio_json \
    --input_intermediate_json output_data/Example6_intermediate.json \
    --output_studio_json_file output_data/Example6
```

- Оверрайды: `data/Example6.si` и/или `data/Example6.fi` (если есть).
- Итоговый файл: `output_data/Example6` (без расширения, валидный JSON для Studio).

---

Для подробностей см. отдельные разделы документации!

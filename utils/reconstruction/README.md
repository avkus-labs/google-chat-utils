# 🛠️ utils.reconstruction

Модуль для реконструкции Python-кода для Gemini API.

## Основной класс
- `GeminiAPICodeReconstructor` — генерация Python-скриптов по данным чата и шаблонам

## Пример использования
```python
from utils.reconstruction.gemini_code_reconstructor import GeminiAPICodeReconstructor
reconstructor = GeminiAPICodeReconstructor(template_dir='utils/templates')
py_code = reconstructor.reconstruct(intermediate_data, 'gemini_studio_default.py.tpl')
```

**Примечание:** Реконструктор работает только с промежуточным JSON (`IntermediateChatData`), в который все необходимые оверрайды уже были применены на этапе подготовки (например, с помощью `studio_json_modifier.py`).

## 🆕 reconstruct_studio_json

Воссоздаёт валидный JSON-файл для Google AI Studio из промежуточного формата:

```bash
python -m utils.cli_v3 reconstruct_studio_json \
    --input_intermediate_json output_data/Example6_intermediate.json \
    --output_studio_json_file output_data/Example6
```

- Оверрайды: `data/Example6.si` и/или `data/Example6.fi` (если есть).
- Итоговый файл: `output_data/Example6` (без расширения, валидный JSON для Studio).

---

Документация: см. `../docs/reconstructor.md` 
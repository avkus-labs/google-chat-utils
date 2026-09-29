# 📚 Документация по проекту google-chat-utils v0.4.0

Добро пожаловать! Здесь собраны все основные сведения, примеры и справка по работе с утилитами для парсинга, реконструкции, трансформации и интеграции с Memory Compiler.

## 🗂️ Структура документации

- [core](./core_models.md) — модели данных
- [parser](./parser.md) — парсер экспортов
- [reconstructor](./reconstructor.md) — генерация Python-кода
- [transformer](./transformer.md) — трансформация схем

---

## 🚀 Быстрые примеры CLI

Все команды выполняются через главный скрипт `utils/cli_v3.py`.

### 1. Парсинг чата (`parse`)

- **Парсинг с автоматической отправкой в Memory Compiler:**
  ```bash
  python utils/cli_v3.py parse --input_file data/Example.json --log_to_memory
  ```
- **Парсинг директории:**
  ```bash
  python utils/cli_v3.py parse --input_dir data/ --output_prefix output_data/
  ```

### 2. Отправка лога в Memory Compiler (`log`)

```bash
python utils/cli_v3.py log --input_file "path/to/your/file.md" --section "Your Section Name"
```

### 3. Реконструкция Python-кода (`reconstruct`)

```bash
python utils/cli_v3.py reconstruct \
    --input_json output_data/Example_intermediate.json \
    --output_py output_data/Example_reconstructed.py \
    --template_dir templates/ \
    --template_name gemini_studio_vanilla.py.tpl
```

### 4. Реконструкция JSON для Google AI Studio (`reconstruct_studio_json`)

```bash
python utils/cli_v3.py reconstruct_studio_json \
    --input_intermediate_json output_data/Example_intermediate.json \
    --output_studio_json_file output_data/Example_studio.json
```

### 5. Трансформация схем (OpenAI → Gemini)

```bash
python -m utils.transformation.schema_transformer \
    --openai_to_gemini data/example_openai_schema.json \
    --output_gemini_file output_data/example_gemini_schema.json
```

---

## 🧑‍💻 Пример программного использования

```python
from utils.parsing.google_studio_parser import GoogleAIStudioJSONParser
from utils.core.chat_elements import IntermediateChatData

# Инициализация парсера
parser = GoogleAIStudioJSONParser()

# Парсинг файла
intermediate_data: IntermediateChatData | None = parser.parse_file('data/Example.json')

# Генерация Markdown, если парсинг успешен
if intermediate_data:
    markdown_output = parser.to_markdown(intermediate_data, "human")
    print("Markdown сгенерирован.")
```

---

Для подробностей по API каждого модуля см. соответствующие разделы документации.

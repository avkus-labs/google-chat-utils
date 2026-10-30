# 📚 Документация по проекту google-chat-utils v0.7.0

Добро пожаловать! Здесь собраны все основные сведения, примеры и справка по работе с утилитами для парсинга, дистилляции, реконструкции, трансформации и интеграции с Google Drive и Memory Compiler.

## 🗂️ Структура документации

- [core](./core_models.md) — модели данных
- [parser](./parser.md) — парсер экспортов
- [reconstructor](./reconstructor.md) — генерация Python-кода
- [transformer](./transformer.md) — трансформация схем

---

## 🚀 Быстрые примеры CLI

Все команды выполняются через главный скрипт `utils/cli_v3.py`.

### 1. Парсинг чата (`parse`)

- **Парсинг одного файла в подпапку:**
  ```bash
  python utils/cli_v3.py parse --input_file data/Example --output_prefix output_data/
  ```
- **Парсинг с автоматической отправкой в Memory Compiler:**
  ```bash
  python utils/cli_v3.py parse --input_file data/Example --log_to_memory
  ```
- **Парсинг директории:**
  ```bash
  python utils/cli_v3.py parse --input_dir data/ --output_prefix output_data/
  ```

### 2. Дистилляция Markdown (`distill`)

- **Сухой прогон (оценка токенов):**
  ```bash
  python utils/cli_v3.py distill --input_file output_data/Example/Example_human.md --distill_dry_run --llm_base_url "http://..." --llm_model "model"
  ```
- **Запуск дистилляции:**
  ```bash
  python utils/cli_v3.py distill --input_file output_data/Example/Example_human.md --llm_base_url "http://..." --llm_model "model" --yes
  ```

### 3. Отправка лога в Memory Compiler (`log`)

```bash
python utils/cli_v3.py log --input_file "path/to/your/file.md" --section "Your Section Name"
```

### 4. Реконструкция Python-кода (`reconstruct`)

```bash
python utils/cli_v3.py reconstruct \
    --input_json output_data/Example/Example_intermediate.json \
    --output_py output_data/Example/Example_reconstructed.py \
    --template_dir templates/ \
    --template_name gemini_studio_vanilla.py.tpl \
    --model_name "gemini-2.5-flash"
```

### 5. Применение оверрайдов к Studio JSON (`apply_overrides_to_studio_json`)

```bash
python utils/cli_v3.py apply_overrides_to_studio_json \
    --input_studio_json data/Example \
    --output_studio_json output_data/Example_overridden.json \
    --si_file data/Example.si \
    --fi_file data/Example.fi \
    --fi_mode replace \
    --li_mode append
```

### 6. Трансформация схем (OpenAI → Gemini)

```bash
python -m utils.transformation.schema_transformer \
    --openai_to_gemini data/example_openai_schema.json output_data/example_gemini_schema.json
```

---

## 🧑‍💻 Пример программного использования

```python
from utils.parsing.google_studio_parser import GoogleAIStudioJSONParser
from utils.core.chat_elements import IntermediateChatData

# Инициализация парсера
parser = GoogleAIStudioJSONParser()

# Парсинг файла
intermediate_data: IntermediateChatData | None = parser.parse('data/Example')

# Генерация Markdown, если парсинг успешен
if intermediate_data:
    markdown_output = parser.to_markdown(intermediate_data, "human")
    print("Markdown сгенерирован.")
```

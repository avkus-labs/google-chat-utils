# Реконструктор кода (`GeminiAPICodeReconstructor`)

Этот компонент отвечает за генерацию исполняемого Python-скрипта для Gemini API на основе объекта `IntermediateChatData` и текстовых шаблонов.

## Класс `GeminiAPICodeReconstructor`

### Инициализация

#### `__init__(self, template_dir: str)`
*   **Описание:** Инициализирует реконструктор с указанием пути к директории с шаблонами.
*   **Параметры:**
    *   `template_dir: str`: Путь к директории с файлами `.py.tpl`.
*   **Исключения:**
    *   `FileNotFoundError`: Если `template_dir` не существует.

### Публичные методы

#### `reconstruct(self, intermediate_data: IntermediateChatData, template_name: str, api_key_var_name: str = "YOUR_API_KEY", **kwargs) -> str`
*   **Описание:** Основной метод, генерирующий Python-скрипт. Он загружает шаблон, подготавливает код (настройки, история, инструменты) и подставляет его в плейсхолдеры.
*   **Параметры:**
    *   `intermediate_data: IntermediateChatData`: Объект с данными чата.
    *   `template_name: str`: Имя файла шаблона.
    *   `api_key_var_name: str`: Имя переменной для API-ключа.
    *   `**kwargs`: Дополнительные параметры, такие как `si_file`, `fi_file`, `li_file` для оверрайдов.
*   **Возвращает:** Строку, содержащую полный Python-код.

---

## Использование через CLI

Команда `reconstruct` в `utils/cli_v3.py` позволяет гибко управлять реконструкцией.

### Базовый пример

```bash
python utils/cli_v3.py reconstruct \
    --input_json output_data/Example_intermediate.json \
    --output_py output_data/Example_reconstructed.py \
    --template_dir templates/ \
    --template_name gemini_studio_vanilla.py.tpl \
    --api_key_var_name "MY_API_KEY"
```

### Использование файлов-оверрайдов

Можно динамически изменять системную инструкцию (`.si`), первое (`.fi`) и последнее (`.li`) сообщения.

*   `--si_file`: Путь к файлу с системной инструкцией.
*   `--fi_file`: Путь к файлу с первым пользовательским сообщением.
*   `--li_file`: Путь к файлу с последним пользовательским сообщением.

**Пример с заменой системной инструкции:**

```bash
python utils/cli_v3.py reconstruct \
    --input_json output_data/Example_intermediate.json \
    --output_py output_data/Example_reconstructed_si.py \
    --template_dir templates/ \
    --template_name gemini_studio_vanilla.py.tpl \
    --si_file data/new_system_instruction.si
```

---

## Пример программного использования

```python
from utils.parsing.google_studio_parser import GoogleAIStudioJSONParser
from utils.reconstruction.gemini_code_reconstructor import GeminiAPICodeReconstructor
from utils.core.chat_elements import IntermediateChatData
from typing import Optional

# 1. Получаем intermediate_data от парсера
parser = GoogleAIStudioJSONParser()
intermediate_data: Optional[IntermediateChatData] = parser.parse_file("data/Example.json")

if intermediate_data:
    try:
        # 2. Инициализируем реконструктор
        reconstructor = GeminiAPICodeReconstructor(template_dir="templates/")

        # 3. Генерируем Python-код с использованием шаблона и оверрайда
        python_script_code = reconstructor.reconstruct(
            intermediate_data=intermediate_data,
            template_name="gemini_studio_vanilla.py.tpl",
            api_key_var_name="MY_GEMINI_API_KEY",
            li_file="data/add_this_at_the_end.li" # Добавляем последнее сообщение
        )

        # 4. Сохраняем результат
        with open("output_data/reconstructed_script.py", "w", encoding="utf-8") as py_file:
            py_file.write(python_script_code)
        
        print("Скрипт успешно реконструирован в output_data/reconstructed_script.py")

    except FileNotFoundError as e:
        print(f"Ошибка: Директория с шаблонами не найдена - {e}")
    except Exception as e:
        print(f"Произошла ошибка при реконструкции: {e}")
```

**Примечание:** Приватные методы класса (начинающиеся с `_`) не документируются здесь, так как они предназначены для внутреннего использования.

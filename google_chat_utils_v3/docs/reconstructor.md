# Реконструктор кода (`GeminiAPICodeReconstructor`)

Этот компонент отвечает за генерацию исполняемого Python-скрипта для Gemini API на основе объекта `IntermediateChatData` (полученного от парсера) и текстовых шаблонов.

## Класс `GeminiAPICodeReconstructor`

Воссоздает исполняемый Python-скрипт для Gemini API из объекта `IntermediateChatData`, используя текстовые шаблоны.

### Инициализация

#### `__init__(self, template_dir: str)`

*   **Описание:** Инициализирует реконструктор с указанием пути к директории, содержащей файлы шаблонов. Если директория не найдена, выбрасывается исключение `FileNotFoundError`. Также инициализирует внутренний экземпляр `SchemaTransformer` для преобразования схем.
*   **Параметры:**
    *   `template_dir: str`: Путь к директории с файлами шаблонов (`.py.tpl`).
*   **Исключения:**
    *   `FileNotFoundError`: Если указанная `template_dir` не существует.

### Публичные методы

#### `reconstruct(self, intermediate_data: IntermediateChatData, template_name: str, api_key_var_name: str = "YOUR_API_KEY") -> str`

*   **Описание:** Основной метод, который генерирует полный Python-скрипт. Он загружает указанный шаблон, подготавливает различные части кода (настройки модели, системную инструкцию, историю диалога, конфигурацию инструментов и генерации) на основе данных из `intermediate_data` и затем подставляет их в соответствующие плейсхолдеры в шаблоне.
*   **Параметры:**
    *   `intermediate_data: IntermediateChatData`: Объект, содержащий все данные чата.
    *   `template_name: str`: Имя файла шаблона (например, `"gemini_studio_default.py.tpl"`), который должен находиться в `template_dir`, указанной при инициализации.
    *   `api_key_var_name: str`: Имя переменной Python, которая будет содержать API-ключ в сгенерированном скрипте. По умолчанию `"YOUR_API_KEY"`. Разработчик должен будет заменить это значение на свой реальный ключ или установить переменную окружения с таким именем.
*   **Возвращает:** Строку, содержащую полный Python-код сгенерированного скрипта. Если файл шаблона не найден или произошла ошибка при его чтении, возвращается строка с комментарием об ошибке.

### Шаблоны (`.py.tpl`)

Реконструктор использует текстовые файлы с расширением `.py.tpl` в качестве шаблонов для генерации кода. Эти шаблоны представляют собой обычные Python-скрипты, в которых определенные участки заменены на плейсхолдеры. В процессе реконструкции эти плейсхолдеры заменяются на сгенерированные строки кода.

Основные плейсхолдеры, которые могут использоваться в шаблонах:

*   `{api_key_var_name}`: Имя переменной для API-ключа.
*   `{timestamp}`: Временная метка парсинга исходного файла.
*   `{source_file_name}`: Имя исходного файла чата.
*   `{model_name_repr}`: Строковое представление имени модели (например, `'gemini-pro'`).
*   `{system_instruction_repr}`: Строковое представление системной инструкции (или `'None'`).
*   `{history_code_str}`: Строка кода, представляющая историю диалога (`contents` для API).
*   `{tools_code_str}`: Строка кода для конфигурации инструментов (`tools` для `GenerativeModel`).
*   `{tool_config_code_str}`: Строка кода для конфигурации вызова инструментов (`tool_config` для `GenerativeModel`).
*   `{generation_config_code_str}`: Строка кода для объекта `GenerationConfig`, включающего такие параметры как температура, top_k, top_p, max_output_tokens, а также `response_mime_type` и `response_schema` (если применимо).

Разработчики могут создавать собственные шаблоны для различных сценариев использования Gemini API.

### Пример использования

```python
from google_chat_utils_v3.core.chat_elements import IntermediateChatData # Предполагается, что он загружен парсером
from google_chat_utils_v3.reconstruction.gemini_code_reconstructor import GeminiAPICodeReconstructor
from typing import Optional # Для type hinting

# Предположим, у вас есть объект intermediate_data, полученный от GoogleAIStudioJSONParser
# intermediate_data: Optional[IntermediateChatData] = ... (загружен ранее parser.parse())

# Пример создания dummy intermediate_data для демонстрации
from google_chat_utils_v3.core.chat_elements import RunSettingsData, DialogueTurn, TextPart
import datetime
intermediate_data = IntermediateChatData(
    source_file_name="dummy_chat.json",
    parsed_at_timestamp=datetime.datetime.utcnow().isoformat() + "Z",
    run_settings=RunSettingsData(model="gemini-pro"),
    system_instruction=None,
    dialogue_history=[DialogueTurn(role="user", parts=[TextPart(content="Hello")])],
    tool_configurations=[]
)
# Конец dummy intermediate_data

# Путь к директории с вашими шаблонами .py.tpl
# Для примера, создадим временную директорию и шаблон
import os
temp_template_dir = "temp_templates_for_docs"
os.makedirs(temp_template_dir, exist_ok=True)
dummy_template_name = "my_default_template.py.tpl"
dummy_template_content = "# Timestamp: {timestamp}\\n# Source: {source_file_name}\\nmodel_name = {model_name_repr}\\nhistory = {history_code_str}"
with open(os.path.join(temp_template_dir, dummy_template_name), 'w') as f:
    f.write(dummy_template_content)
template_directory = temp_template_dir
# Конец создания временного шаблона

# Инициализация реконструктора
try:
    reconstructor = GeminiAPICodeReconstructor(template_dir=template_directory)

    # Имя файла шаблона (без пути к директории)
    chosen_template_name = dummy_template_name # Используем наш временный шаблон

    # Генерация Python-кода
    python_script_code = reconstructor.reconstruct(
        intermediate_data=intermediate_data,
        template_name=chosen_template_name,
        api_key_var_name="MY_API_KEY"
    )

    print("--- Сгенерированный Python-скрипт ---")
    print(python_script_code)

    # Вы можете сохранить этот код в .py файл:
    # with open("reconstructed_chat.py", "w", encoding="utf-8") as py_file:
    #     py_file.write(python_script_code)

except FileNotFoundError as e:
    print(f"Ошибка: Директория с шаблонами не найдена - {e}")
except Exception as e:
    print(f"Произошла ошибка при реконструкции: {e}")
finally:
    # Очистка временной директории и файла
    if os.path.exists(temp_template_dir):
        try:
            os.remove(os.path.join(temp_template_dir, dummy_template_name))
            os.rmdir(temp_template_dir)
        except OSError as e_clean:
            print(f"Ошибка при очистке временных файлов: {e_clean}")

```

**Примечание:** Приватные методы класса (начинающиеся с `_`), такие как `_generate_contents_code`, `_generate_tools_code`, и т.д., не документируются здесь, так как они предназначены для внутреннего использования. Они адаптируют логику из `reconstructor_v2.py` для работы с новыми классами данных и `SchemaTransformer`.

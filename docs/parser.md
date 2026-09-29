# Парсер (`GoogleAIStudioJSONParser`)

Основной компонент, отвечающий за чтение JSON-экспортов из Google AI Studio, их преобразование в унифицированный формат `IntermediateChatData` и генерацию Markdown-представлений.

## Класс `GoogleAIStudioJSONParser`

### Инициализация

#### `__init__(self)`
*   **Описание:** Инициализирует парсер.

### Публичные методы

#### `parse_file(self, file_path: str) -> Optional[IntermediateChatData]`
*   **Описание:** Главный метод для парсинга файла. Выполняет полный цикл чтения, анализа и преобразования данных в объект `IntermediateChatData`.
*   **Параметры:**
    *   `file_path: str`: Путь к JSON-файлу.
*   **Возвращает:** Объект `IntermediateChatData` или `None` в случае ошибки.

#### `to_markdown(self, intermediate_data: IntermediateChatData, style: str) -> str`
*   **Описание:** Генерирует Markdown-представление чата.
*   **Параметры:**
    *   `intermediate_data: IntermediateChatData`: Объект с данными чата.
    *   `style: str`: Стиль генерируемого Markdown. Может быть `"raw_rag"` (для RAG-систем с XML-тегами) или `"human"` (форматированный для человека).
*   **Возвращает:** Строку с Markdown-разметкой.

---

##  CLI: Интеграция с Memory Compiler

Командный интерфейс `cli_v3.py` предоставляет удобные команды для работы с парсером и `Memory Compiler`.

### Команда `parse`

*   **Описание:** Парсит JSON-файлы и генерирует `intermediate.json`, `raw_rag.md` и `human.md`.
*   **Пример:**
    ```bash
    python utils/cli_v3.py parse --input_file data/Example.json --output_prefix output_data/
    ```
*   **Интеграция с Memory Compiler:**
    *   Флаг `--log_to_memory` (или `-l`) автоматически отправляет содержимое сгенерированного `human.md` в ваш Memory Compiler.
    *   **Пример:**
        ```bash
        python utils/cli_v3.py parse --input_file data/Example.json --log_to_memory
        ```

### Команда `log`

*   **Описание:** Позволяет вручную отправить содержимое любого текстового файла (.md, .txt) в Memory Compiler.
*   **Пример:**
    ```bash
    python utils/cli_v3.py log --input_file "path/to/your/report.md" --section "Daily Report"
    ```

---

## Пример программного использования

```python
from utils.parsing.google_studio_parser import GoogleAIStudioJSONParser
from utils.core.chat_elements import IntermediateChatData
from typing import Optional

# Инициализация парсера
parser = GoogleAIStudioJSONParser()

# Путь к вашему JSON-файлу
chat_file_path = "data/Example.json"

# Парсинг файла
intermediate_data: Optional[IntermediateChatData] = parser.parse_file(chat_file_path)

if intermediate_data:
    print(f"Файл '{intermediate_data.source_file_name}' успешно разобран.")
    
    # Генерация Markdown для RAG
    rag_md = parser.to_markdown(intermediate_data, "raw_rag")
    
    # Генерация человекочитаемого Markdown
    human_md = parser.to_markdown(intermediate_data, "human")
    
    # Сохранение человекочитаемого Markdown в файл
    with open("output_data/chat_human.md", "w", encoding="utf-8") as md_file:
        md_file.write(human_md)
    print("Человекочитаемый Markdown сохранен в output_data/chat_human.md")
else:
    print(f"Не удалось разобрать файл: {chat_file_path}")
```

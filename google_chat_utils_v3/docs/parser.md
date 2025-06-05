# Парсер (`GoogleAIStudioJSONParser`)

Основной компонент, отвечающий за чтение и преобразование JSON-файлов, экспортированных из Google AI Studio, в унифицированный формат `IntermediateChatData`.

## Класс `GoogleAIStudioJSONParser`

Парсит экспорт чатов Google AI Studio JSON в объект `IntermediateChatData`.

### Инициализация

#### `__init__(self)`

*   **Описание:** Инициализирует парсер. На данный момент конструктор не принимает аргументов и не выполняет сложной логики.
*   **Параметры:** Нет.

### Публичные методы

#### `parse(self, file_path_or_data: Union[str, Dict[str, Any]]) -> Optional[IntermediateChatData]`

*   **Описание:** Главный метод парсинга. Принимает либо путь к JSON-файлу, либо уже загруженный словарь Python. Выполняет полный цикл чтения (если нужно), анализа данных и преобразования их в объект `IntermediateChatData`.
*   **Параметры:**
    *   `file_path_or_data: Union[str, Dict[str, Any]]`: Путь к JSON-файлу (строка) или словарь с данными чата.
*   **Возвращает:** Объект `IntermediateChatData`, содержащий все разобранные данные, или `None` в случае ошибки загрузки или парсинга файла.

#### `to_markdown(self, intermediate_data: IntermediateChatData) -> str`

*   **Описание:** Генерирует Markdown-представление чата на основе объекта `IntermediateChatData`. Markdown содержит специальную XML-подобную разметку для различных элементов чата (настройки, системная инструкция, история диалога, инструменты и т.д.), что делает его пригодным для использования в RAG-системах.
*   **Параметры:**
    *   `intermediate_data: IntermediateChatData`: Объект с данными чата, полученный от метода `parse`.
*   **Возвращает:** Строку, содержащую Markdown-разметку.

### Вспомогательные функции модуля

#### `load_json_file(file_path: str) -> Optional[Dict[str, Any]]`

*   **Описание:** Читает JSON-файл по указанному пути. Возвращает содержимое в виде словаря Python или `None` в случае ошибки. Эта функция используется внутри метода `parse`, но может быть полезна и отдельно.
*   **Параметры:**
    *   `file_path: str`: Путь к JSON-файлу.
*   **Возвращает:** Словарь с данными из JSON-файла или `None`, если файл не найден, не может быть декодирован или произошла другая ошибка чтения.

### Пример использования

```python
from google_chat_utils_v3.parsing.google_studio_parser import GoogleAIStudioJSONParser
from google_chat_utils_v3.core.chat_elements import IntermediateChatData # Optional нужен для type hinting
from typing import Optional # Для type hinting Optional[IntermediateChatData]


# Инициализация парсера
parser = GoogleAIStudioJSONParser()

# Путь к вашему JSON-файлу из Google AI Studio
chat_file_path = "path/to/your/chat_export.json"

# Парсинг файла
intermediate_data: Optional[IntermediateChatData] = parser.parse(chat_file_path)

if intermediate_data:
    print(f"Файл '{intermediate_data.source_file_name}' успешно разобран.")
    print(f"Модель: {intermediate_data.run_settings.model}")

    if intermediate_data.system_instruction:
        print(f"Системная инструкция: {intermediate_data.system_instruction.text[:50]}...")

    print(f"Количество ходов в диалоге: {len(intermediate_data.dialogue_history)}")
    if intermediate_data.dialogue_history:
        first_turn = intermediate_data.dialogue_history[0]
        print(f"  Первый ход: роль - {first_turn.role}, частей - {len(first_turn.parts)}")

    # Генерация Markdown
    markdown_output = parser.to_markdown(intermediate_data)
    # print("
--- Markdown для RAG ---")
    # print(markdown_output[:500] + "...") # Вывести начало Markdown

    # Вы можете сохранить markdown_output в файл:
    # with open("chat_export.md", "w", encoding="utf-8") as md_file:
    #     md_file.write(markdown_output)
else:
    print(f"Не удалось разобрать файл: {chat_file_path}")

# Также можно передать уже загруженный словарь
# loaded_json_data = {"runSettings": {"model":"gemini-pro"}, ...} # Пример
# intermediate_data_from_dict = parser.parse(loaded_json_data)
# if intermediate_data_from_dict:
#     print(f"Данные из словаря успешно разобраны. Модель: {intermediate_data_from_dict.run_settings.model}")
```

**Примечание:** Приватные методы класса (начинающиеся с `_`) не документируются здесь, так как они предназначены для внутреннего использования, но их логика основана на функциях из `parser_v2.py` и адаптирована для работы с новыми классами данных из `core.chat_elements` и `core.schema_elements`.

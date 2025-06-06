# 🧩 utils.core

Модуль базовых моделей данных для всей библиотеки.

## Основные классы
- `SchemaData` — универсальная модель JSON Schema
- `FunctionDefinition` — описание функций для function calling
- `IntermediateChatData` — объектное представление чата
- `ChatMessagePart` и наследники — части сообщений (текст, код, данные и др.)

## Пример использования
```python
from utils.core.schema_elements import SchemaData
schema = SchemaData(type="STRING", description="Пример строки")
```

---

Документация: см. `../docs/core_models.md` 
# Модели данных ядра (`core`)

В этом разделе описаны основные классы данных, используемые в библиотеке `google-chat-utils v3` для представления информации о чатах, их элементах и JSON схемах. Эти классы находятся в модулях `google_chat_utils_v3.core.schema_elements` и `google_chat_utils_v3.core.chat_elements`.

## Модели для JSON Schema (`core.schema_elements`)

Эти классы предназначены для работы с JSON Schema, особенно в контексте описания параметров функций и схем ответов.

### `SchemaData`

Представляет рекурсивное определение JSON Schema. Используется для описания структуры данных.

**Атрибуты:**

*   `type: str`: Тип элемента схемы (например, `"OBJECT"`, `"STRING"`, `"ARRAY"`, `"INTEGER"`, `"BOOLEAN"`, `"NUMBER"`). Типы обычно указываются в верхнем регистре.
*   `description: Optional[str]`: Описание элемента схемы.
*   `nullable: Optional[bool]`: Указывает, может ли элемент схемы быть `null`. По умолчанию `False`.
*   `properties: Optional[Dict[str, 'SchemaData']]`: Словарь дочерних объектов `SchemaData` для типа `"OBJECT"`. Ключи - имена свойств.
*   `items: Optional['SchemaData']`: Объект `SchemaData`, описывающий элементы для типа `"ARRAY"`.
*   `enum: Optional[List[Any]]`: Список возможных значений для элемента схемы.
*   `required: Optional[List[str]]`: Список имен обязательных свойств для типа `"OBJECT"`.

### `FunctionParameter`

Это псевдоним (type alias) для класса `SchemaData`. Используется для явного указания, что `SchemaData` описывает параметр функции.

`FunctionParameter = SchemaData`

### `FunctionDefinition`

Представляет определение одной функции (инструмента), которую может вызывать модель.

**Атрибуты:**

*   `name: str`: Имя функции. Должно быть непустым.
*   `description: str`: Описание того, что делает функция.
*   `parameters_schema: SchemaData`: Объект `SchemaData`, определяющий параметры функции. Обычно это схема типа `"OBJECT"`.

## Модели для элементов чата (`core.chat_elements`)

Эти классы представляют различные компоненты чата, от общих настроек до отдельных частей сообщений.

### `RunSettingsData`

Хранит и предоставляет доступ к данным из секции `runSettings` JSON-экспорта Google AI Studio.

**Атрибуты:**

*   `model: Optional[str]`: Название используемой модели (например, `"gemini-pro"`).
*   `temperature: Optional[float]`: Температура генерации.
*   `top_p: Optional[float]`: Значение Top-P для нуклеусного сэмплинга.
*   `top_k: Optional[int]`: Значение Top-K для сэмплинга.
*   `max_output_tokens: Optional[int]`: Максимальное количество токенов в ответе.
*   `response_mime_type: Optional[str]`: MIME-тип ожидаемого ответа (например, `"application/json"`).
*   `response_schema: Optional[SchemaData]`: Объект `SchemaData`, описывающий схему ответа (если `response_mime_type` это JSON).
*   `function_declarations: Optional[List[FunctionDefinition]]`: Список объектов `FunctionDefinition`, описывающих доступные функции (инструменты).
*   `enable_code_execution: Optional[bool]`: Флаг, включен ли инструмент выполнения кода. По умолчанию `False`.
*   `enable_search_as_tool: Optional[bool]`: Флаг, включен ли инструмент поиска Google. По умолчанию `False`.
*   `enable_browse_as_tool: Optional[bool]`: Флаг, включен ли инструмент веб-браузинга. По умолчанию `False`.
*   `raw_settings: Optional[Dict[str, Any]]`: Исходный словарь `runSettings` для доступа к полям, не покрытым явными атрибутами.

### `SystemInstruction`

Представляет системную инструкцию для модели.

**Атрибуты:**

*   `text: str`: Текст системной инструкции.
*   `source: Optional[str]`: Необязательное поле для указания источника инструкции.

### `ChatMessagePart`

Абстрактный базовый класс для части сообщения чата. Одно сообщение (ход диалога) может состоять из нескольких частей разных типов.

### Наследники `ChatMessagePart`

*   **`TextPart(content: str)`**: Представляет простую текстовую часть сообщения.
    *   `content: str`: Текстовое содержимое.
*   **`ThoughtsPart(content: str)`**: Представляет "мысли" модели в процессе генерации ответа.
    *   `content: str`: Содержимое мыслей.
*   **`ExecutableCodePart(code_content: str, language: str = "PYTHON")`**: Представляет блок кода, предназначенный для выполнения (например, инструментом интерпретации кода).
    *   `code_content: str`: Исходный код.
    *   `language: str`: Язык программирования (по умолчанию `"PYTHON"`).
*   **`CodeExecutionResultPart(output_content: str, outcome: str = "OK")`**: Представляет результат выполнения кода.
    *   `output_content: str`: Вывод результата выполнения.
    *   `outcome: str`: Итог выполнения (например, `"OK"`, `"ERROR"`, `"TIMEOUT"`).
*   **`FunctionCallPart(name: str, args: Dict[str, Any])`**: Представляет вызов функции (инструмента) моделью.
    *   `name: str`: Имя вызываемой функции.
    *   `args: Dict[str, Any]`: Словарь аргументов для функции.
*   **`FunctionResponsePart(name: str, response_content: Dict[str, Any])`**: Представляет ответ от вызова функции (инструмента).
    *   `name: str`: Имя функции, на вызов которой это ответ.
    *   `response_content: Dict[str, Any]`: Словарь, содержащий результат выполнения функции.
*   **`InlineDataPart(mime_type: str, base64_data: str)`**: Представляет встроенные данные (обычно для изображений или других медиа), закодированные в Base64. Соответствует `inlineData` в формате Google AI Studio.
    *   `mime_type: str`: MIME-тип данных.
    *   `base64_data: str`: Строка данных в кодировке Base64.
*   **`UriReferencePart(source_type: str, identifier: str, mime_type: Optional[str] = None)`**: Представляет ссылку на данные по URI. Охватывает различные части на основе URI, такие как `driveImage`, `fileData`, `youtubeVideo` и т.д.
    *   `source_type: str`: Тип источника (например, `"google_drive_image"`, `"file_uri"`).
    *   `identifier: str`: URI или ID, идентифицирующий ресурс.
    *   `mime_type: Optional[str]`: Необязательный MIME-тип содержимого по ссылке.

### `DialogueTurn`

Представляет один ход (turn) в диалоге, содержащий одну или несколько частей сообщения.

**Атрибуты:**

*   `role: str`: Роль участника, совершающего этот ход (например, `"user"`, `"model"`).
*   `parts: List[ChatMessagePart]`: Список объектов `ChatMessagePart`, составляющих этот ход.
*   `turn_id: Optional[str]`: Необязательный идентификатор этого хода.
*   `token_count: Optional[int]`: Необязательное количество токенов для этого хода.
*   `finish_reason: Optional[str]`: Необязательная причина, по которой модель завершила генерацию этого хода.
*   `citations: Optional[List[Dict[str, Any]]]`: Необязательный список метаданных цитирования (для grounding).

### `ToolConfiguration`

Представляет информацию о настроенных инструментах для модели. Основан на структуре `tools_info` из промежуточного JSON.

**Атрибуты:**

*   `type: str`: Тип инструмента (например, `"code_execution"`, `"function_declaration"`, `"google_search_enabled"`).
*   `functions: Optional[List[FunctionDefinition]]`: Список объектов `FunctionDefinition`, если тип инструмента - `"function_declaration"`.

### `IntermediateChatData`

Корневой объект данных, агрегирующий всю разобранную информацию о чате. Этот объект является основным результатом работы парсера и входными данными для реконструктора.

**Атрибуты:**

*   `source_file_name: str`: Имя исходного файла.
*   `parsed_at_timestamp: str`: Временная метка парсинга (ISO формат UTC).
*   `source_platform: str`: Платформа-источник данных (по умолчанию `"Google AI Studio"`).
*   `run_settings: RunSettingsData`: Объект с настройками запуска.
*   `system_instruction: Optional[SystemInstruction]`: Объект с системной инструкцией (может отсутствовать).
*   `dialogue_history: List[DialogueTurn]`: Список ходов диалога.
*   `tool_configurations: Optional[List[ToolConfiguration]]`: Список сконфигурированных инструментов.

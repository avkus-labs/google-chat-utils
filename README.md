# 🦾 Google AI Studio Chat Parser v2

**Мощный инструмент для парсинга чатов Google AI Studio, стандартизации истории, генерации Markdown для RAG и реконструкции Python-кода для Gemini API.**

---

## 🚀 Возможности
- Парсинг экспортов чатов Google AI Studio (JSON, txt, без расширения)
- Извлечение настроек запуска, системной инструкции, истории диалога, инструментов (function calling, code execution)
- Генерация промежуточного стандартизированного JSON
- Генерация Markdown с мета-тегами для RAG
- Реконструкция Python-скрипта для Gemini API по шаблонам (vanilla, dynamic SI, Google-style)
- Поддержка мультимодальных сообщений, function calling, code execution, кастомных инструментов
- Красивый, информативный и дружелюбный вывод в консоль с эмодзи

---

## 📦 Установка
1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/your-org/google_ai_studio_chat_parser_v2.git
   cd google_ai_studio_chat_parser_v2
   ```
2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

---

## 📝 Быстрый старт

### 1. Парсинг чата Google AI Studio

```bash
python src/parser_v2.py --input_file input_data/Example1 --output_dir output_data
```

**Пример вывода:**
```
🚀 Запуск parser_v2.py 🚀
----------------------------------------------------
📄 Входной файл: input_data/Example1
📁 Папка вывода: output_data
----------------------------------------------------
⚙️  Извлечение настроек сессии (runSettings)... ✔️
📝 Извлечение системной инструкции... ✔️
🗣️  Обработка истории диалога... ✔️ (обработано X ходов)
💾 Форматирование и сохранение "промежуточного JSON" в: output_data/Example1.json... ✔️
💾 Форматирование и сохранение Markdown для RAG в: output_data/Example1.md... ✔️
----------------------------------------------------
✨ Парсинг файла input_data/Example1 успешно завершен! ✨
   Промежуточный JSON: output_data/Example1.json
   Markdown для RAG: output_data/Example1.md
```

### 2. Реконструкция Python-кода для Gemini API

```bash
python src/reconstructor_v2.py --input_json output_data/Example1.json --output_py output_data/reconstructed_Example1_vanilla.py --template_path templates/gemini_studio_vanilla.py.tpl
```

**Пример вывода:**
```
🚀 Запуск reconstructor_v2.py 🚀
ℹ️  Входной JSON: output_data/Example1.json
ℹ️  Шаблон: templates/gemini_studio_vanilla.py.tpl
----------------------------------------------------
⚙️  Загрузка промежуточного JSON... ✔️
⚙️  Воссоздание списка contents... ✔️
⚙️  Воссоздание конфигурации инструментов (tools)... ✔️
⚙️  Воссоздание схемы ответа (response_schema)... ✔️
🐍 Генерация Python-кода по шаблону... ✔️
💾 Сохранение Python-файла в: output_data/reconstructed_Example1_vanilla.py... ✔️
----------------------------------------------------
✨ Реконструкция Python-кода успешно завершена! ✨
   Выходной файл: output_data/reconstructed_Example1_vanilla.py
```

---

## 🧩 Шаблоны для реконструкции
- `gemini_studio_vanilla.py.tpl` — максимально чистый, похожий на экспорт Google AI Studio
- `gemini_studio_dynamic_si.py.tpl` — поддержка динамической подгрузки системной инструкции из `.si`-файла
- `gemini_studio_google_vanilla.py.tpl` — стиль экспорта Google AI Studio (импорты, структура)

Выбор шаблона осуществляется через аргумент `--template_path`.

---

## 🛠️ Архитектура
- **src/parser_v2.py** — основной парсер, CLI, генерация JSON и Markdown
- **src/reconstructor_v2.py** — реконструктор Python-кода по шаблону
- **src/schema_transformer.py** — преобразование схем между форматами OpenAI ↔ Gemini
- **templates/** — шаблоны Python-кода для разных сценариев
- **output_data/** — все результаты работы

---

## 🤝 Авторы и вклад
- Проект создан с заботой о разработчиках и RAG-инженерах
- Вдохновлён лучшими практиками Google AI Studio, OpenAI, Gemini API
- Добро пожаловать к обсуждению и развитию!

---

## 🏁 Итог
**Проект завершён! Все этапы автоматизации, стандартизации и реконструкции реализованы.**

✨ Спасибо за использование! Если есть идеи или баги — создавайте issue или pull request! ✨

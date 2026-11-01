---
type: log
status: active
trust_tier: ai-verified-against-repo
project: google-chat-utils
repo: avkus-labs/google-chat-utils
branch: main
last_verified_head: 1cab1d0
generated: {by: claude, at: 2026-11-01}
---

# google-chat-utils — session snapshot 2026-11-01

Архив: `.agents/states/session-2026-09-30-distill-001.md` (история 001, ветки, решения 09-30).

## Состояние кода (main, `1cab1d0`)
- Влиты и отчитаны исполнителем (Antigravity): 003 (пропуск готовых `_distilled.md` + `--distill_overwrite`), 004 (`--llm_synthesis_model`), 005 (стриминг SSE, `--llm_no_stream` для отката). Независимая приёмка 003–005 НЕ проведена: Claude проверил только наличие флагов в CLI и 130 passed (без `test_drive_fetch.py` — нет `googleapiclient` в песочнице). Файл задания 005 в репо назван `005-distill-strreaming.md` (опечатка).
- Подготовка (`prepare`): System Instruction и мысли удаляются, секреты заменяются на `[REDACTED]`, ходы нумеруются `[#N]`, затем чанки. `source_sha256` считается по тексту после universal newlines (CRLF→LF), а не по сырым байтам (сверено: хэш frontmatter совпал с исходником только после такой конвертации).
- Промпты (EN рабочие, `*_ru.md` переводы): статусы `[подтверждено]/[предложено моделью]/[опровергнуто]/[не проверено]`, якоря `(ходы A–B)`, `<fragment>`/`<distilled_text>`-обёртки; synthesis: `resolution`, `failed_approaches`, `error_signatures`. Frontmatter OKF-совместим: `description`, ISO-8601 UTC `generated.at`, `synthesis_model` только если отличается.

## Решения владельца
- `_distilled.md` идёт в OmniWiki как готовый источник (второй LLM-проход не делаем; перелинкует линтер OmniWiki; в `runner.py` источник с `type` во frontmatter считается pre-processed и копируется без обогащения).
- Перезапись: `parse` перезаписывает по умолчанию; для `_distilled.md` — пропуск готовых, перегенерация только с `--distill_overwrite` (003).
- Выбор модели дистиллятора владелец делает сам по прогонам на одном чате; ключи (утечки в `input_data/`/`output_data/`) — не обсуждать, решение владельца.

## Что показал сравнительный прогон (источник 184 хода, 11 чанков; 2026-11-01)
- Полное покрытие ходов только у `th/mimo-v2.6-flash:free` (59 блоков). Qwen/Qwen не покрыл ~72 хода, DeepSeek/DeepSeek — 1–27, 30–56, 182 (+ якоря-заглушки), lite — 1–131. У всех `verification.status: ok`: покрытие и код дают только warning (`verifier.py:45,97`).
- Причина дыр (подтверждена кодом, не логами): пустой ответ чанка принимается и кэшируется (`pipeline.py:181,194`). ⚠️ Гипотеза: «`TO: 0`, ~5 с, 200» в логах OmniRoute — те самые пустые ответы; логами не подтверждено.
- ⚠️ Не объяснено: у G-Q синтез знает про Taos, а тело его не содержит; в текущем коде `body == merged == вход synthesis` (`pipeline.py:197,211`), так что на `1cab1d0` такого быть не должно — вероятно, прогон шёл на более старой версии.
- Выборочная проверка mimo: из 6 просмотренных «ненайденных» код-блоков фальсификаций нет (ложные срабатывания из-за пробелов терминала и `…`/`...`; один блок — пересказ в комментариях внутри ```). Из `[подтверждено]` проверено 1 решение — верно. Остальное не проверено.
- Пробельный мусор терминала ≈ 15% объёма источника.

## Открытое
- Аудит дистилляции 48 чатов (batch 2026-11-01, `c53507d`, 2026-11-01; Claude, скриптом по якорям ходов; содержание и статусы НЕ читались): дистиллятов 45 (44 на `th/deepseek-v4.1-flash:free`, 1 на `xkiro/qwen/qwen3.8-max:free`), все `verification.status: ok`. Покрытие ходов: полное у 22, мелкие дыры (1–3 хода) у 9, **<80% у 14** (худшие: «Настройка Hermes Agent и выбор моделей _2» — только ходы 172–175 из 175; «Prompt Engineering_ Your AI Guide» 14%; «Branch of Architect-Orchestrator-Gemini» (350 ходов) 27%; «Google Chat Utils» 29%; «Передача логов MITM-сессии» 42%; «Deep-Sea Salvage — Roblox Core» 51%; PartScout (Qwen) 58%; «Branch of Deep-Sea Salvage — documentaions» 59%; «Оптимизация инструкции для ИИ-ассистента» 63%; «Deep-Sea Salvage — Game Dev» 63%; «Platon_ SI-DEV v4.0 Production Build» 67%; «Исправление запуска noVNC в Docker» 72%; «CDX Bitrix Core Decode» 75%; N8NEX 76%). `verification.length_ratio` обманчив (у «Hermes Agent _2» 0.31 при 4 покрытых ходах из 175). Шесть дистиллятов с нечётным числом ``` (сломанная разметка): Branch of Deep-Sea Salvage — documentaions, Deep-Sea Salvage — Game Dev, Deep-Sea Salvage — Roblox Core, Google Chat Utils, Архитектура LLM Wiki и OKF, Настройка Hermes Agent и выбор моделей _2. Без дистиллята 3 чата: BDX md (только SI → 007), Architect-Orchestrator-Gemini (16 чанков > `MAX_CHUNKS_PER_FILE=15`, отказ по дизайну; нужен `--chunk_tokens` больше), «Настройка Claude Code Pi Agent и выбор моделей _1» (52 хода, 3 чанка; причина в репо не видна, нужна строка лога). Секретов в дистиллятах по паттернам redactor не найдено. Таблица: `audit.csv` у владельца. Рекомендация: 14 тяжёлых + 2 без дистиллята перезапускать после влития 006 (пустой ответ = ошибка, не кэшируется); в A/B-прогоне полное покрытие дала только `th/mimo-v2.6-flash:free` (одна выборка). В OmniWiki 14 тяжёлых не загружать.
- Тикет 006 (`.agents/tasks/006-distill-integrity.md`): пустой ответ = ошибка и не в кэш; статусы `ok/warning/error` + `--distill_strict`; построчная проверка кода; чаты без реплик пользователя (пометка пайплайна, без виртуальных реплик; статусы только `[предложено моделью]`). Статус: open, владелец передаёт Antigravity.
- Сообщение владельца: на ~40 чатах несколько дали «0» после ручной чистки (удалены все реплики пользователя, возможно ветка-«мануал»). Не воспроизведено; что именно «0» — не уточнено (`ходов=0`/`чанков=0`/пустое тело).
- OmniRoute (вне этого репо): для запросов без стрима действуют `maxWaitMs` очереди (Settings → Resilience, env `RATE_LIMIT_MAX_WAIT_MS`, дефолт 15000) и `OMNIROUTE_DIRECT_HEADERS_TIMEOUT_MS` (дефолт 30000, только env); при стриме не должны срабатывать (⚠️ ожидание, не проверено). Round-robin у провайдера xkiro залипает на #1 при `sticky=1`, у Token Harbor с теми же настройками ротирует — причина не найдена.
- Дефолт `--distill_thoughts drop` — подтвердить; `.agents/AGENTS.md` не создавался; дубли чатов-веток в базе знаний не отлавливаются.
- Верификатор не проверяет статусы (`[подтверждено]` без подтверждения пользователя) — не автоматизируется, только ручная выборка.

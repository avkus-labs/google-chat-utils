---
type: task
id: "008"
slug: distill-rerun-heavy
status: open
executor: Antigravity (запуск на машине владельца, где доступен шлюз)
repo: avkus-labs/google-chat-utils
branch: feature/distill-rerun-008
trust_tier: ai-verified-against-repo
last_verified_head: a3f9226
generated: {by: claude, at: 2026-11-01}
---

# 008 — Перезапуск дистилляции для 16 чатов с потерями (после 006/007)

## Цель
Аудит партии из 48 чатов (2026-11-01, скриптом по якорям ходов) нашёл 14 дистиллятов с покрытием ходов < 80% и 2 чата без дистиллята. Нужно перегенерировать их уже с проверками 006 (пустой ответ = ошибка, `--distill_strict`) и убедиться, что покрытие ≥ 95%.

## 1. Проверенные факты (не перепроверять)
- В `main` (`a3f9226`) влиты 006 и 007 (коммиты `0cfc71c`, `a3f9226`); отчёты `.agents/reports/006-*.md`, `007-*.md` есть. Независимая приёмка ещё не проведена (если в ходе работы найдёте дефект 006 — остановиться и сообщить, не чинить).
- Проблемные чаты (папка в `output_data/` | ходов | покрытие якорями, %):
  1. Настройка Hermes Agent и выбор моделей _2 | 175 | 2.3
  2. Prompt Engineering_ Your AI Guide | 64 | 14.1
  3. Branch of Architect-Orchestrator-Gemini | 350 | 26.9
  4. Google Chat Utils | 24 | 29.2
  5. Передача логов MITM-сессии | 48 | 41.7
  6. Deep-Sea Salvage — Roblox Core | 71 | 50.7
  7. Анализ проекта PartScout_ Hermes | 194 | 57.7
  8. Branch of Deep-Sea Salvage — documentaions | 41 | 58.5
  9. Оптимизация инструкции для ИИ-ассистента | 8 | 62.5
  10. Deep-Sea Salvage — Game Dev | 100 | 63.0
  11. Platon_ SI-DEV v4.0 Production Build | 6 | 66.7
  12. Исправление запуска noVNC в Docker | 179 | 72.1
  13. CDX Bitrix Core Decode | 8 | 75.0
  14. N8NEX | 277 | 75.5
  Без дистиллята: 15. Architect-Orchestrator-Gemini (16 чанков при `chunk_tokens=30000` > `MAX_CHUNKS_PER_FILE=15`: отказ по дизайну); 16. Настройка Claude Code Pi Agent и выбор моделей _1 (52 хода, 3 чанка; причины в репо нет, строка из лога батча не приложена).
- Причина дыр: пустые ответы чанков принимались и кэшировались (до 006). Это подтверждено кодом, не логами.
- Объём (оценка `chars/2`): пункты 1–14 ≈ 1.96 млн токенов входа, пункт 15 ≈ 0.40 млн, пункт 16 ≈ 0.07 млн; выход ≈ 20% от входа. Модели бесплатные, но прогон займёт часы.
- Чат `Bitrix Deobfuscation Expert (BDX) md` (только System Instruction) обрабатывается режимом 007, в этот тикет не входит, кроме отдельного пункта 4.2.
- Скрипт аудита: `tools/audit_distill.py` (добавлен вместе с этим тикетом). Он механический: смысл и статусы не оценивает.

## 2. Что сделать
1. Ветка `feature/distill-rerun-008` от `origin/main`. Перед запуском сохранить текущие дистилляты: `git tag backup-distill-before-008` (старые файлы остаются в истории).
2. Сухой прогон плана для всех 16 (по одному `--input_file`), `--distill_dry_run`: записать в отчёт `чанков` и `~вход` по каждому файлу. Если какой-то файл даёт > 15 чанков — для него `--chunk_tokens 40000` (для Architect-Orchestrator-Gemini ожидается около 12 чанков). Если суммарный `~вход` заметно больше 2.5 млн токенов — остановиться и спросить.
3. Запуск по одному файлу, модель чанков и synthesis одна (`th/mimo-v2.6-flash:free` через `--llm_base_url` шлюза владельца), флаги: `--distill_overwrite --distill_strict --yes`. Для 15 добавить `--chunk_tokens 40000`. `--force`-подобных флагов нет и не требуется; кэш не удалять.
4. После каждого файла — строка вывода верификации в отчёт. Файл, на котором `--distill_strict` сработал (DistillError), не обходить `--no-strict` и не править руками: записать причину и перейти к следующему.
5. В конце: `python tools/audit_distill.py output_data audit_after_008.csv` и в отчёт — таблица по 16 чатам: покрытие до → после, число блоков, `verification.status`.
6. Критерий приёмки: покрытие ≥ 95% у не менее 14 из 16 чатов; для остальных — понятная причина в отчёте. Пустых блоков `Без значимого содержания` быть не должно.

## 3. Cost guard
- Сначала только `--distill_dry_run` (раздел 2.2). Реальный запуск — по одному файлу, начиная с самого маленького (пункт 11).
- Если первый реальный файл показывает ошибки 429/504/пустые ответы чаще чем у 1 чанка из 5 — остановиться и сообщить (не повторять в цикле).
- Запрещено: `--distill_no_cache`-подобные обходы, `--llm_no_stream` (стрим снимает таймауты OmniRoute), смена промптов, `chunk_tokens` ниже 25000 без согласования.
- Секреты не цитировать; `.env`, логи и кэш не коммитить.

## 4. Команды
PowerShell:
```powershell
git fetch origin; git switch -c feature/distill-rerun-008 origin/main
git tag backup-distill-before-008
python utils/cli_v3.py distill --input_file "output_data/Platon_ SI-DEV v4.0 Production Build/Platon_ SI-DEV v4.0 Production Build_human.md" --llm_base_url "<шлюз>/v1" --llm_model "th/mimo-v2.6-flash:free" --llm_synthesis_model "th/mimo-v2.6-flash:free" --distill_dry_run
python utils/cli_v3.py distill --input_file "<тот же файл>" --llm_base_url "<шлюз>/v1" --llm_model "th/mimo-v2.6-flash:free" --llm_synthesis_model "th/mimo-v2.6-flash:free" --distill_overwrite --distill_strict --yes
python tools/audit_distill.py output_data audit_after_008.csv
```
bash: те же команды, без смены синтаксиса (пути с пробелами в кавычках).
Имена папок точно как в списке выше (проверить `ls output_data`).

## 5. Вне скоупа
Не менять код дистилляции и промпты; не трогать остальные 32 чата; не загружать результат в OmniWiki; открытое эскалировать. Не мержить в `main` самостоятельно: приёмка независимая.

## 6. Отчёт → `.agents/reports/008-distill-rerun-heavy.md`
Реальные команды и вывод, таблица до/после, список файлов, где strict отказал, аномалии, что НЕ проверено.

---
type: log
status: archived
trust_tier: ai-verified-against-repo
project: google-chat-utils
repo: avkus-labs/google-chat-utils
branch: main
last_verified_head: e4b2c87
generated: {by: claude, at: 2026-09-30}
---

# google-chat-utils — session snapshot 2026-09-30

## Ветки (обновлено 2026-09-30: dev влит в main FF, dev удалён; на origin только `main`)
- `main` = 7a40ca3. `dev` = 9e3d874 (+ этот стейт). Расхождения нет: main целиком предок dev (0 behind / 3 ahead) — main можно догнать fast-forward, конфликтов не будет.
- dev опережает main на 3 коммита: `dedcb1a` feat: команда `log` + CHANGELOG; `601a53f` docs: ROADMAP.md; `9e3d874` «sync» (Avkus, 2026-09-30) — крупная чистка/пересборка: удалены cursor_*.md, data/, html/, comands, .pylintrc, review_v3.md, prompt_translation_*.md, старые output_data; добавлены pyproject.toml, docs/html/* (pdoc-подобная генерация), новые output_data по одному чату, обновлены README/CLAUDE.md/docs/*.md, utils/cli_v3.py (~60 строк), requirements.txt.
- ⚠️ Не проверено: содержимое новых output_data (~57k строк, кириллические имена) — выглядит как реальные данные чата; решить, нужны ли они в приватном репо.
- Ветка `jules_wip_12867920756126502440` была полностью смерджена в main (PR #1, #2 → тогда ещё `master`) и УДАЛЕНА на origin 2026-09-30 по запросу владельца.

## Почему «просит pull request»
- Репозиторий private в организации на бесплатном плане: `GET /rules/branches/main` и `/rulesets` → 403 «Upgrade to GitHub Pro». Защита веток/rulesets недоступна → принудительного требования PR нет. `.github/` (CODEOWNERS, workflows) отсутствует; в CLAUDE.md/ROADMAP/.claude/settings.json требований PR нет.
- Значит запрос PR — не правило, а подсказка: GitHub UI («Compare & pull request» после push в dev) или привычка Jules/агента. Классическую branch protection API отдаёт 403 из-за прав GitHub App (нужен admin) — не проверено напрямую, но на Free для private repo она недоступна.
- Итог: dev → main можно вливать напрямую (`git merge --ff-only`), PR — по желанию для истории/ревью.

## Решения 2026-09-30
- dev → main влит fast-forward (main = 538a658 + последующие), ветка dev удалена. Ветка jules удалена ранее.
- Новая функция: `parse` → подпапка на каждый входной файл (3 файла + `_distilled.md`); опция `--distill` (human.md → LLM-дистиллятор → источник для OmniWiki). Задание: `.agents/tasks/001-distill-pipeline.md`. Промпты: `prompts/distiller_chunk_prompt.md`, `prompts/distiller_synthesis_prompt.md`.
- QA-агент (QAR) в конвейер НЕ включаем: проверки (покрытие ходов, дословность код-блоков, секреты, валидность YAML) делаются детерминированным верификатором. QAR — опционально позже для выборочной калибровки.
- Старые промпты DDA v2.4 / QAR v1.3.1/v3.0 не переиспользуются как есть (причины — в переписке сессии: режим Markdown «не дистиллировать», JSON-обёртка вокруг большого Markdown).

## 🔴 Секреты в репозитории (сообщено один раз)
- `input_data/Настройка Hermes Agent и выбор моделей #2` (26 вхождений одного ключа `sk-f92…`) и `output_data/…_human.md`, `…_raw_rag.md`, `…_intermediate.json`: рабочие на вид ключи — `sk-f92…` (ANTHROPIC_AUTH_TOKEN, mitm-gpe), `sk-97e…` (apiKey), `sk-493…` (в `token=` CDP-URL), `lin_ap…` (Linear, 48 симв.). Закоммичены в `9e3d874` и теперь в main. Репо private, но нужно: ротация этих ключей, затем чистка истории (filter-repo) и `input_data/`/`output_data/` в `.gitignore`. Историю не трогал — ждёт решения владельца.

## Решения 2026-09-30 (консультация по 001, без клона — ответы через чат, сверены точечно по коду в отдельной сессии с доступом к репо)
- Финальные решения владельца по `001` — новое побеждает текст тикета (пять пунктов): коллизия имён папок → перезапись по умолчанию (идемпотентность), суффикс `-2`/`-3` только под `--no-overwrite`; `safe_stem` — `#` принудительно вырезается (`#2` → `_2`), кириллица остаётся; транспорт — `httpx` (не `requests`); оценка токенов — `chars/2.0` + буфер 20% (резать на `0.8 × chunk_tokens`), не `chars/2.5`; ключ кэша дистилляции — `sha256(chunk + prompt + model + base_url)`, `base_url` добавлен. `.agents/tasks/001-distill-pipeline.md` пока не обновлён под эти пять пунктов — это сделать при следующей правке тикета.
- Маркер разрезки гигантского код-блока при чанкинге: `[... код разбит на части для дистилляции: часть k/N ...]` (язык-нейтрально, без `//`).
- Структура кода дистилляции согласована: пакет `utils/distillation/` (`chunker.py`, `redactor.py`, `llm_client.py`, `verifier.py`, `pipeline.py`) с общей точкой входа `distill_human_markdown(path, cfg)`, вызываемой и из `parse --distill`, и из команды `distill`; `utils/cli_v3.py` — только диспетчер подкоманд.
- Формат `(ходы A–B)` для верификатора покрытия ходов подтверждён чтением `prompts/distiller_chunk_prompt.md` — правило явно прописано («К каждому смысловому блоку добавляй ссылку на ходы»), верификатор пункта 10 из `001` рабочий.
- Проверено соответствие формата Drive-файла и парсера: реальный экспорт Studio — `runSettings` + `chunkedPrompt.chunks[]` (чанк с `role`/`text` напрямую, без `parts`) — уже покрыт веткой `utils/parsing/google_studio_parser.py` (~строка 328, "text прямо в чанке без parts"). Новый парсер под фичу "получить чат с Drive по имени" не нужен, только тонкий слой Drive API (Studio и хранилище чатов — один Google-аккаунт, один набор OAuth-кредов). Пункт добавлен в `ROADMAP.md` (раздел «Функциональность»), тикет под него намеренно не создан — решение отложено владельцем.
- Отдельно: `client.interactions.create(...)` ("Get code"/экспорт в буфер из Studio) — не тот же артефакт, что файл на Drive; не содержит истории чанками, для парсинга бесполезен. Тот же эндпоинт фигурирует в [[antigravity-interactions-api-500-incident]] (HTTP 500/524, другая модель) — не тот же кейс, но канал с историей нестабильности.
- Секреты в репозитории (см. раздел выше) — статус не изменился, всё ещё не ротировано, всё ещё вне скоупа `001`.

## Задача 001 — статус: реализация завершена (2026-09-30)
- Код: `utils/distillation/` (safe_stem, chunker, redactor, llm_client, verifier, pipeline), обновлён `utils/cli_v3.py` (подпапки, `--distill`, команда `distill`).
- Тесты: 73 passed (ruff clean). Предсуществующие поломки в `test_parsing.py`, `test_reconstruction.py`, `test_studio_json_reconstruction.py` — не чинились (вне скоупа).
- Сухой прогон на Hermes: ходов=169, чанков=12, ~вход=261 783 ток., ~выход=52 356 ток. Редакция: sk_key=26, bearer=2.
- Отчёт: `.agents/reports/001-distill-pipeline.md`.
- Текст тикета `.agents/tasks/001-distill-pipeline.md` обновлён под все финальные решения; статус `done-pending-llm-credentials`.
- Реальный вызов LLM заблокирован: владелец ещё не дал `--llm_base_url` / `--llm_model`.

## Открытый бэклог
- Ротация ключей + чистка истории + .gitignore для input_data/output_data (решение владельца).
- Выбор бэкенда/модели для дистиллятора (параметры `--llm_base_url/--llm_model`) — всё ещё не дан; без него реальный (не dry-run) прогон запрещён.
- Дефолт `--distill_thoughts drop` — подтвердить.
- Судьба существующих плоских файлов в `output_data/`; `.agents/AGENTS.md` не создавался.
- Фича "получить чат с Drive по имени" — оформлена тикетом `.agents/tasks/002-drive-auth-security-docs.md` для Jules (Drive OAuth + аудит безопасности всего кода + синхронизация документации); статус `open`, работает в отдельной ветке `feature/drive-auth-security-002`, PR не мержить самостоятельно. Способ авторизации (OAuth user-flow vs service account) помечен в тикете как ⚠️ не проверено — Jules должен подтвердить эмпирически.

---
type: log
status: active
trust_tier: ai-verified-against-repo
project: google-chat-utils
repo: avkus-labs/google-chat-utils
branch: main
last_verified_head: 538a658
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

## Открытый бэклог
- Ротация ключей + чистка истории + .gitignore для input_data/output_data (решение владельца).
- Выбор бэкенда/модели для дистиллятора (параметры `--llm_base_url/--llm_model`); дефолт `--distill_thoughts drop` — подтвердить.
- Судьба существующих плоских файлов в `output_data/`; `.agents/AGENTS.md` не создавался.

import argparse
import os
import sys
import json
import subprocess

# === Определение корня проекта ===
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Цветовые коды ANSI
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"

SEPARATOR = f"{CYAN}{'-'*56}{RESET}"


try:
    from utils.parsing.google_studio_parser import GoogleAIStudioJSONParser
    from utils.reconstruction.gemini_code_reconstructor import GeminiAPICodeReconstructor
    from utils.core.chat_elements import TextPart, ThoughtsPart, ExecutableCodePart, CodeExecutionResultPart, FunctionCallPart, FunctionResponsePart, InlineDataPart, UriReferencePart
    from utils.distillation.safe_stem import safe_stem
    from utils.distillation import pipeline as distill_pipeline
except Exception as e:
    print(f'{BOLD}{RED}IMPORT ERROR: {e}{RESET}')
    import traceback
    tb_str = traceback.format_exc()
    print(f'{BOLD}{RED}{tb_str}{RESET}')
    sys.exit(1)

def ensure_dir(path):
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)

def part_to_dict(part):
    if hasattr(part, 'content') and isinstance(part, (TextPart, ThoughtsPart)):
        return {"type": part.__class__.__name__.replace("Part", "").lower(), "content": part.content}
    if isinstance(part, ExecutableCodePart):
        return {"type": "executable_code", "language": part.language, "code_content": part.code_content}
    if isinstance(part, CodeExecutionResultPart):
        return {"type": "code_execution_result", "outcome": part.outcome, "output_content": part.output_content}
    if isinstance(part, FunctionCallPart):
        return {"type": "function_call", "name": part.name, "args": part.args}
    if isinstance(part, FunctionResponsePart):
        return {"type": "function_response", "name": part.name, "response_content": part.response_content}
    if isinstance(part, InlineDataPart):
        return {"type": "inline_data", "mime_type": part.mime_type, "base64_data": part.base64_data}
    if isinstance(part, UriReferencePart):
        return {"type": "uri_reference", "source_type": part.source_type, "identifier": part.identifier, "mime_type": part.mime_type}
    return {"type": part.__class__.__name__}

def process_single_parse_file(input_file_path: str, parser_instance: GoogleAIStudioJSONParser, output_prefix: str):
    """Парсит один файл в подпапку <output_prefix>/<safe_stem>/.

    Возвращает путь к записанному _human.md при успехе, иначе False.
    """
    if not os.path.isfile(input_file_path):
        print(f"{RED}❌ Ошибка: Входной файл не найден: {input_file_path}{RESET}", file=sys.stderr)
        return False

    print(f"{BOLD}{BLUE}🚀 Запуск команды [parse] 🚀{RESET}")
    print(SEPARATOR)
    print(f"{BOLD}📄 Входной файл:{RESET} {os.path.normpath(input_file_path)}")
    print(f"{BOLD}📁 Output prefix:{RESET} {os.path.normpath(output_prefix)}")
    print(SEPARATOR)

    intermediate_data = parser_instance.parse(input_file_path)
    if intermediate_data:
        file_name_without_ext = os.path.splitext(os.path.basename(input_file_path))[0]
        # Задача 001: вывод в отдельную подпапку на каждый входной файл;
        # --output_prefix трактуется как базовая папка. Перезапись идемпотентна.
        stem = safe_stem(file_name_without_ext)
        out_dir = os.path.join(PROJECT_ROOT, output_prefix, stem)
        os.makedirs(out_dir, exist_ok=True)
        json_out_path = os.path.join(out_dir, f"{stem}_intermediate.json")
        md_out_path = os.path.join(out_dir, f"{stem}_raw_rag.md")
        human_md_out_path = os.path.join(out_dir, f"{stem}_human.md")
        try:
            os.makedirs(os.path.dirname(json_out_path), exist_ok=True)
            with open(json_out_path, 'w', encoding='utf-8') as f_json:
                json.dump(intermediate_data.to_dict(), f_json, indent=2, ensure_ascii=False)
            print(f"  {GREEN}💾 Промежуточный JSON сохранён: {os.path.normpath(json_out_path)} ✔️{RESET}")
        except Exception as e:
            print(f"  {RED}❌ Ошибка при сохранении промежуточного JSON: {json_out_path}: {e}{RESET}", file=sys.stderr)
            return False

        markdown_content = parser_instance.to_markdown(intermediate_data)
        try:
            os.makedirs(os.path.dirname(md_out_path), exist_ok=True)
            with open(md_out_path, 'w', encoding='utf-8') as f_md:
                f_md.write(markdown_content)
            print(f"  {GREEN}💾 Markdown для RAG сохранён: {os.path.normpath(md_out_path)} ✔️{RESET}")
        except Exception as e:
            print(f"  {RED}❌ Ошибка при сохранении Markdown: {md_out_path}: {e}{RESET}", file=sys.stderr)
            return False

        human_markdown_content = parser_instance.to_human_markdown(intermediate_data)
        try:
            os.makedirs(os.path.dirname(human_md_out_path), exist_ok=True)
            with open(human_md_out_path, 'w', encoding='utf-8') as f_human_md:
                f_human_md.write(human_markdown_content)
            print(f"  {GREEN}💾 Читаемый Markdown сохранён: {os.path.normpath(human_md_out_path)} ✔️{RESET}")
        except Exception as e:
            print(f"  {RED}❌ Ошибка при сохранении читаемого Markdown: {human_md_out_path}: {e}{RESET}", file=sys.stderr)
            return False

        print(f"{SEPARATOR}")
        print(f"{GREEN}✨ Команда [parse] успешно завершена! ✨{RESET}")

        # --- Integration with Memory Compiler ---
        if getattr(parser_instance, 'log_to_memory', False):
            log_to_memory_compiler(human_markdown_content, "Google-Chat-Utils", f"Import: {file_name_without_ext}")

        return human_md_out_path
    else:
        print(f"  {RED}Не удалось распарсить файл: {input_file_path}{RESET}", file=sys.stderr)
        return False

def log_to_memory_compiler(content, project_name, section):
    """Call the external Memory Compiler to log this event."""
    # We assume the default path for now, or could use an env var
    compiler_path = os.environ.get("MEMORY_COMPILER_PATH", "E:/Claude-Memory-Compiler")
    append_script = os.path.join(compiler_path, "scripts", "append.py")

    if not os.path.exists(append_script):
        print(f"  {YELLOW}⚠️ Memory Compiler не найден по пути: {compiler_path}. Пропуск логирования.{RESET}")
        return

    print(f"  {BLUE}📝 Отправка данных в Memory Compiler ({section})...{RESET}")

    # We use a temp file to pass large content to avoid shell limits
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Run uv run python E:/Claude-Memory-Compiler/scripts/append.py ...
        cmd = [
            "uv", "run", "--directory", compiler_path,
            "python", append_script,
            "--project", project_name,
            "--section", section,
            "--file", tmp_path
        ]

        # Use subprocess.run and hide output unless it fails
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  {GREEN}✅ Данные успешно добавлены в дневной лог!{RESET}")
        else:
            print(f"  {RED}❌ Ошибка при логировании в Memory Compiler: {result.stderr}{RESET}")
    except Exception as e:
        print(f"  {RED}❌ Ошибка при вызове Memory Compiler: {e}{RESET}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def handle_parse(args):
    """Обработка команды 'parse': подпапка на каждый файл + опциональная дистилляция."""
    parser_gai = GoogleAIStudioJSONParser()
    parser_gai.log_to_memory = getattr(args, 'log_to_memory', False)
    output_prefix = args.output_prefix if args.output_prefix else "output_data/"

    if getattr(args, 'distill', False) and (not args.llm_base_url or not args.llm_model):
        print(f"{RED}Ошибка: --distill требует явных --llm_base_url и --llm_model (без дефолтов и автодетекта).{RESET}", file=sys.stderr)
        sys.exit(2)

    input_files = []
    if args.input_file:
        input_files = [args.input_file]
    elif args.input_dir:
        if not os.path.isdir(args.input_dir):
            print(f"Ошибка: Входная директория не найдена: {args.input_dir}", file=sys.stderr)
            sys.exit(2)
        print(f"Обработка всех JSON-совместимых файлов в директории: {args.input_dir}...")
        for filename in os.listdir(args.input_dir):
            if filename.lower().endswith(('.json', '.jsonl', '.txt')) or '.' not in filename:
                file_path = os.path.join(args.input_dir, filename)
                if os.path.isfile(file_path):
                    input_files.append(file_path)
            else:
                print(f"  Пропуск не-JSON файла: {filename}")
    else:
        print("Ошибка: Необходимо указать --input_file или --input_dir для команды parse.", file=sys.stderr)
        sys.exit(2)

    human_md_files = []
    successful_parses = 0
    for file_path in input_files:
        result_path = process_single_parse_file(file_path, parser_gai, output_prefix)
        if result_path:
            successful_parses += 1
            human_md_files.append(result_path)
    print(f"Успешно распарсено и сохранено {successful_parses} файлов.")

    # Дистилляция уже готовых _human.md общим батчем (одна сводка, одно подтверждение)
    if getattr(args, 'distill', False) and human_md_files:
        run_distill_batch(human_md_files, args)


def handle_reconstruct(args):
    print(f"{BOLD}{MAGENTA}🚀 Запуск команды [reconstruct] 🚀{RESET}")
    print(SEPARATOR)
    print(f"{BOLD}📄 Входной JSON:{RESET} {os.path.normpath(args.input_json)}")
    print(f"{BOLD}📁 Output Python:{RESET} {os.path.normpath(args.output_py)}")
    print(f"{BOLD}🧩 Шаблон:{RESET} {os.path.normpath(args.template_name)}")
    print(SEPARATOR)
    input_json_full_path = os.path.join(PROJECT_ROOT, args.input_json)
    if not os.path.isfile(input_json_full_path):
        print(f"{RED}❌ Ошибка: Входной JSON не найден: {input_json_full_path}{RESET}", file=sys.stderr)
        return
    template_dir_full_path = os.path.join(PROJECT_ROOT, args.template_dir)
    if not os.path.isdir(template_dir_full_path):
        print(f"{RED}❌ Ошибка: Директория шаблонов не найдена: {template_dir_full_path}{RESET}", file=sys.stderr)
        return
    output_directory_for_script = os.path.dirname(input_json_full_path)
    os.makedirs(output_directory_for_script, exist_ok=True)
    full_output_py_path = os.path.join(output_directory_for_script, args.output_py)
    print(f"{YELLOW}ВНИМАНИЕ: Корректная десериализация IntermediateChatData из JSON пока не реализована.{RESET}")
    print(f"{YELLOW}Команда reconstruct требует полностью совместимый JSON (например, оригинальный экспорт AI Studio).{RESET}")
    try:
        parser_gai_for_reconstruct = GoogleAIStudioJSONParser()
        intermediate_data_for_reconstruct = parser_gai_for_reconstruct.parse(input_json_full_path)
        if not intermediate_data_for_reconstruct:
            print(f"{RED}Ошибка: Не удалось распарсить JSON в IntermediateChatData: {input_json_full_path}. Проверьте формат.{RESET}", file=sys.stderr)
            return
        if hasattr(intermediate_data_for_reconstruct, 'run_settings'):
            intermediate_data_for_reconstruct.run_settings.model = args.model_name
    except Exception as e:
        print(f"{RED}Ошибка при парсинге JSON: {e}{RESET}", file=sys.stderr)
        return
    print(f"{BOLD}Реконструкция Python-скрипта из:{RESET} {input_json_full_path}")
    print(f"{BOLD}Используется директория шаблонов:{RESET} {template_dir_full_path}")
    print(f"{BOLD}Используется шаблон:{RESET} {args.template_name}")
    reconstructor = GeminiAPICodeReconstructor(template_dir=template_dir_full_path)
    try:
        python_script = reconstructor.reconstruct(
            intermediate_data=intermediate_data_for_reconstruct,
            template_name=args.template_name,
            api_key_var_name=args.api_key_var_name,
            model_name=args.model_name
        )
        with open(full_output_py_path, 'w', encoding='utf-8') as f:
            f.write(python_script)
        print(f"{GREEN}💾 Python-скрипт сохранён: {os.path.normpath(full_output_py_path)} ✔️{RESET}")
        print(f"{SEPARATOR}")
        print(f"{GREEN}✨ Команда [reconstruct] успешно завершена! ✨{RESET}")
    except FileNotFoundError as e:
        print(f"{RED}Ошибка при реконструкции (проблема с шаблоном?): {e}{RESET}", file=sys.stderr)
    except Exception as e:
        print(f"{RED}Неожиданная ошибка при реконструкции: {e}{RESET}", file=sys.stderr)

def handle_apply_overrides(args):
    cmd = [
        sys.executable, os.path.join(os.path.dirname(__file__), 'studio_json_modifier.py'),
        '--input_studio_json', args.input_studio_json,
        '--output_studio_json', args.output_studio_json
    ]
    if args.si_file:
        cmd += ['--si_file', args.si_file]
    if args.fi_file:
        cmd += ['--fi_file', args.fi_file]
    if args.li_file:
        cmd += ['--li_file', args.li_file]
    if args.fi_mode:
        cmd += ['--fi_mode', args.fi_mode]
    if args.li_mode:
        cmd += ['--li_mode', args.li_mode]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f'{RED}Ошибка при применении оверрайдов!{RESET}', file=sys.stderr)
    else:
        print(f'{GREEN}Оверрайды успешно применены!{RESET}')

def handle_log(args):
    """Обработка команды 'log' для ручного логирования файлов в Memory Compiler."""
    input_file = args.input_file
    if not os.path.isfile(input_file):
        print(f"{RED}❌ Ошибка: Файл не найден: {input_file}{RESET}", file=sys.stderr)
        return

    section = args.section if args.section else f"Manual Log: {os.path.basename(input_file)}"

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"{BOLD}{BLUE}🚀 Запуск команды [log] 🚀{RESET}")
        print(SEPARATOR)
        print(f"{BOLD}📄 Файл:{RESET} {os.path.normpath(input_file)}")
        print(f"{BOLD}📁 Раздел:{RESET} {section}")
        print(SEPARATOR)

        log_to_memory_compiler(content, "Google-Chat-Utils", section)
    except Exception as e:
        print(f"{RED}❌ Ошибка при чтении файла {input_file}: {e}{RESET}", file=sys.stderr)

def _add_distill_options(p):
    """Общие флаги дистилляции для команд 'parse', 'distill' и 'fetch-drive'."""
    p.add_argument("--distill_dry_run", action="store_true",
                   help="Только план (ходы/чанки/оценка токенов), без вызова LLM.")
    p.add_argument("--yes", action="store_true",
                   help="Пропустить подтверждение перед вызовом LLM.")
    p.add_argument("--llm_base_url", default="",
                   help="Base URL OpenAI-совместимого API. Обязателен при дистилляции, дефолтов нет.")
    p.add_argument("--llm_model", default="",
                   help="Имя модели. Обязательно при дистилляции, дефолтов нет.")
    p.add_argument("--llm_api_key_env", default="DISTILL_API_KEY",
                   help="Имя переменной окружения с ключом (по умолчанию DISTILL_API_KEY).")
    p.add_argument("--distill_prompt_dir", default="prompts",
                   help="Папка с промптами дистиллятора (по умолчанию prompts/).")
    p.add_argument("--chunk_tokens", type=int, default=30000,
                   help="Целевой размер чанка в токенах (оценка). По умолчанию 30000.")
    p.add_argument("--max_total_input_tokens", type=int, default=400000,
                   help="Жёсткий лимит суммарной оценки входа. По умолчанию 400000.")
    p.add_argument("--distill_max_chunks", type=int, default=None,
                   help="Ограничить число чанков на файл (для пробных прогонов).")
    p.add_argument("--distill_thoughts", choices=["drop", "keep"], default="drop",
                   help="Что делать с Model Thoughts (по умолчанию drop).")


def build_distill_config(args, output_dir=None):
    """Собрать DistillConfig из аргументов CLI."""
    cfg = distill_pipeline.DistillConfig()
    cfg.llm_base_url = args.llm_base_url
    cfg.llm_model = args.llm_model
    cfg.llm_api_key_env = args.llm_api_key_env
    cfg.prompt_dir = args.distill_prompt_dir
    cfg.chunk_tokens = args.chunk_tokens
    cfg.max_total_input_tokens = args.max_total_input_tokens
    cfg.max_chunks = args.distill_max_chunks
    cfg.distill_thoughts = args.distill_thoughts
    cfg.dry_run = args.distill_dry_run
    cfg.assume_yes = args.yes
    cfg.output_dir = output_dir
    return cfg


def run_distill_batch(human_files, args, output_dir=None):
    """Общий flow дистилляции (задача 001): план → подтверждение → последовательные вызовы."""
    cfg = build_distill_config(args, output_dir)

    preps = []
    for path in human_files:
        try:
            distill_pipeline.validate_turn_headers(path)
            preps.append((path, distill_pipeline.prepare(path, cfg)))
        except distill_pipeline.DistillError as e:
            print(f"{RED}Ошибка: {e}{RESET}", file=sys.stderr)
            sys.exit(e.exit_code)

    print(f"{BOLD}План дистилляции:{RESET}")
    total_tokens = 0
    for path, prep in preps:
        print(distill_pipeline.plan_line(path, prep))
        if prep.redaction_counts:
            print(f"    редакция секретов: {prep.redaction_counts}")
        total_tokens += prep.estimated_input_tokens
    print(f"Итого: файлов={len(preps)}, ~вход={total_tokens} токенов")

    if total_tokens > cfg.max_total_input_tokens:
        print(f"{RED}Отказ: оценка входа {total_tokens} > лимита {cfg.max_total_input_tokens}.{RESET}", file=sys.stderr)
        sys.exit(2)

    if cfg.dry_run:
        print(f"{YELLOW}[dry-run] Вызовы LLM пропущены.{RESET}")
        return

    if not cfg.assume_yes:
        answer = input("Запустить дистилляцию? [y/N] ")
        if answer.strip().lower() not in ("y", "yes", "да"):
            print("Отменено.")
            return

    for path, _ in preps:
        try:
            distill_pipeline.distill_human_markdown(path, cfg)
        except distill_pipeline.DistillError as e:
            print(f"{RED}Ошибка дистилляции {os.path.basename(path)}: {e}{RESET}", file=sys.stderr)
            sys.exit(e.exit_code)


def handle_distill(args):
    """Команда 'distill': дистилляция готовых _human.md без повторного парсинга."""
    if not args.llm_base_url or not args.llm_model:
        print(f"{RED}Ошибка: команда distill требует явных --llm_base_url и --llm_model (без дефолтов).{RESET}", file=sys.stderr)
        sys.exit(2)

    human_files = []
    if args.input_file:
        if not os.path.isfile(args.input_file):
            print(f"{RED}Ошибка: Файл не найден: {args.input_file}{RESET}", file=sys.stderr)
            sys.exit(2)
        human_files = [args.input_file]
    elif args.input_dir:
        if not os.path.isdir(args.input_dir):
            print(f"{RED}Ошибка: Директория не найдена: {args.input_dir}{RESET}", file=sys.stderr)
            sys.exit(2)
        for filename in sorted(os.listdir(args.input_dir)):
            if filename.endswith("_human.md"):
                full = os.path.join(args.input_dir, filename)
                if os.path.isfile(full):
                    human_files.append(full)
        if not human_files:
            print(f"{YELLOW}В {args.input_dir} нет файлов *_human.md.{RESET}")
            return
    else:
        print("Ошибка: Необходимо указать --input_file или --input_dir для команды distill.", file=sys.stderr)
        sys.exit(2)

    print(f"{BOLD}{BLUE}🚀 Запуск команды [distill] 🚀{RESET}")
    run_distill_batch(human_files, args, output_dir=args.output_dir)


def handle_auth_drive(args):
    """Команда 'auth-drive': интерактивная авторизация в Google Drive."""
    try:
        from utils.drive.auth import run_interactive_auth
    except ImportError as e:
        print(f"{RED}Ошибка: Зависимости Google Drive не установлены ({e}). Установите их: pip install -r requirements.txt{RESET}", file=sys.stderr)
        sys.exit(1)
    try:
        run_interactive_auth(client_secrets_file=args.client_secrets, token_path=args.token_path)
    except Exception as e:
        print(f"{RED}Ошибка авторизации Google Drive: {e}{RESET}", file=sys.stderr)
        sys.exit(1)


def handle_fetch_drive(args):
    """Команда 'fetch-drive': поиск и скачивание чата из Google Drive."""
    try:
        from utils.drive.client import GoogleDriveChatFetcher
    except ImportError as e:
        print(f"{RED}Ошибка: Зависимости Google Drive не установлены ({e}). Установите их: pip install -r requirements.txt{RESET}", file=sys.stderr)
        sys.exit(1)

    print(f"{BOLD}{BLUE}🚀 Запуск команды [fetch-drive] 🚀{RESET}")
    print(SEPARATOR)
    print(f"{BOLD}🔍 Имя чата:{RESET} {args.chat_name}")
    print(f"{BOLD}📁 Целевая папка:{RESET} {os.path.normpath(args.output_dir)}")
    print(SEPARATOR)

    try:
        fetcher = GoogleDriveChatFetcher()
        downloaded_path = fetcher.fetch_chat_file(
            chat_name=args.chat_name,
            output_dir=args.output_dir,
            folder_id=args.folder_id
        )
        print(f"{GREEN}✅ Чат успешно скачан: {os.path.normpath(downloaded_path)}{RESET}")

        if args.parse:
            print(f"\n{BOLD}{CYAN}▶️ Автоматический запуск парсинга...{RESET}")
            parser_instance = GoogleAIStudioJSONParser()
            output_prefix = args.output_prefix if args.output_prefix else "output_data/"
            human_path = process_single_parse_file(downloaded_path, parser_instance, output_prefix)
            if human_path and getattr(args, 'log_to_memory', False):
                with open(human_path, 'r', encoding='utf-8') as f:
                    log_to_memory_compiler(f.read(), "Google-Chat-Utils", f"Import: {os.path.basename(downloaded_path)}")
            if human_path and getattr(args, 'distill', False):
                if not args.llm_base_url or not args.llm_model:
                    print(f"{RED}Ошибка: --distill требует указания --llm_base_url и --llm_model{RESET}", file=sys.stderr)
                    sys.exit(2)
                run_distill_batch([human_path], args)
    except Exception as e:
        print(f"{RED}❌ Ошибка: {e}{RESET}", file=sys.stderr)
        sys.exit(1)


def handle_validate(args):
    """Команда 'validate': проверка структуры JSON через Pydantic схему."""
    from utils.validation import validate_json_file
    print(f"{BOLD}{BLUE}🚀 Запуск команды [validate] 🚀{RESET}")
    print(SEPARATOR)
    print(f"{BOLD}📄 Проверяемый файл:{RESET} {os.path.normpath(args.input_file)}")
    print(SEPARATOR)

    result = validate_json_file(args.input_file)
    if result.is_valid:
        print(f"{GREEN}✅ Файл успешно прошёл валидацию!{RESET}")
        print(f"  Формат: {BOLD}{result.format_type}{RESET}")
        if result.warnings:
            for w in result.warnings:
                print(f"  {YELLOW}⚠️  Предупреждение: {w}{RESET}")
    else:
        print(f"{RED}❌ Ошибка валидации!{RESET}")
        print(f"  Определённый формат: {BOLD}{result.format_type}{RESET}")
        for err in result.errors:
            print(f"  {RED}- {err}{RESET}", file=sys.stderr)
        sys.exit(1)


def handle_interactive(args=None):
    """Команда 'interactive': запуск интерактивного меню."""
    from utils.interactive import run_interactive_menu
    handlers = {
        "parse": handle_parse,
        "reconstruct": handle_reconstruct,
        "apply_overrides_to_studio_json": handle_apply_overrides,
        "validate": handle_validate,
        "distill": handle_distill,
        "fetch-drive": handle_fetch_drive,
        "auth-drive": handle_auth_drive,
        "log": handle_log,
    }
    run_interactive_menu(handlers)


def main():
    """Main function for the CLI."""
    parser = argparse.ArgumentParser(
        description="Google Chat Utils v3 CLI: Parse AI Studio exports and reconstruct Gemini API code.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Включить подробный отладочный вывод (DEBUG).")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO", help="Уровень логирования (по умолчанию: INFO).")
    parser.add_argument("--log-file", help="Файл для сохранения логов.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands. Use <command> --help for more details.", required=True)

    # --- Parser for the 'parse' command ---
    parse_parser = subparsers.add_parser("parse",
        help="Parse Google AI Studio JSON export file(s).",
        description="Parses Google AI Studio JSON export files, creates an intermediate JSON representation and a Markdown file suitable for RAG systems."
    )
    input_group = parse_parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input_file", "-i", metavar="FILE_PATH",
                             help="Path to a single input JSON file (from Google AI Studio).")
    input_group.add_argument("--input_dir", "-d", metavar="DIR_PATH",
                             help="Directory containing input JSON files (from Google AI Studio).")
    parse_parser.add_argument("--output_prefix", "-o", metavar="OUTPUT_PREFIX", default="output_data/",
                              help="Базовая папка вывода: каждый входной файл получает подпапку <имя>/. По умолчанию: output_data/")
    parse_parser.add_argument("--log_to_memory", "-l", action="store_true",
                              help="Добавить результат обработки (human.md) в дневной лог Memory Compiler.")
    parse_parser.add_argument("--distill", action="store_true",
                              help="После парсинга дистиллировать _human.md через LLM (требует --llm_base_url и --llm_model).")
    _add_distill_options(parse_parser)
    parse_parser.set_defaults(func=handle_parse)

    # --- Parser for the 'reconstruct' command ---
    reconstruct_parser = subparsers.add_parser("reconstruct",
        help="Reconstruct Python script from intermediate JSON.",
        description="Reconstructs an executable Python script for the Gemini API from an intermediate JSON file."
    )
    reconstruct_parser.add_argument("--input_json", "-ij", metavar="PATH_TO_INTERMEDIATE_JSON", required=True,
                                    help="Path to the intermediate JSON file.")
    reconstruct_parser.add_argument("--output_py", "-op", metavar="FILENAME.py", required=True,
                                    help="Name of the output Python script. It will be saved in the same directory as input_json.")
    reconstruct_parser.add_argument("--template_dir", "-td", metavar="PATH_TO_TEMPLATES", required=True,
                                    help="Path to the directory containing .py.tpl template files.")
    reconstruct_parser.add_argument("--template_name", "-tn", metavar="TEMPLATE_FILENAME", required=True,
                                    help="Name of the template file within the template directory.")
    reconstruct_parser.add_argument("--api_key_var_name", "-ak", default="YOUR_API_KEY",
                                    help="Name of the API key variable in the generated script. Default: YOUR_API_KEY")
    reconstruct_parser.add_argument("--model_name", metavar="MODEL_NAME", required=True,
                                    help="Model name to use for code reconstruction (str, required).")
    reconstruct_parser.set_defaults(func=handle_reconstruct)

    # --- Parser for the 'apply_overrides_to_studio_json' command ---
    apply_parser = subparsers.add_parser("apply_overrides_to_studio_json",
        help="Apply .si/.fi/.li overrides to Google AI Studio raw JSON.",
        description="Modifies a raw Studio JSON file by applying overrides from .si/.fi/.li files."
    )
    apply_parser.add_argument('--input_studio_json', required=True, help='Path to input raw Studio JSON')
    apply_parser.add_argument('--output_studio_json', required=True, help='Path to output modified Studio JSON')
    apply_parser.add_argument('--si_file', required=False, help='Path to .si file (system instruction)')
    apply_parser.add_argument('--fi_file', required=False, help='Path to .fi file (first user message)')
    apply_parser.add_argument('--li_file', required=False, help='Path to .li file (last user message)')
    apply_parser.add_argument('--fi_mode', choices=['replace', 'prepend'], default='replace', help='Mode for .fi: replace or prepend (default: replace)')
    apply_parser.add_argument('--li_mode', choices=['replace', 'append'], default='replace', help='Mode for .li: replace or append (default: replace)')
    apply_parser.set_defaults(func=handle_apply_overrides)

    # --- Parser for the 'log' command ---
    log_parser = subparsers.add_parser("log",
        help="Log any .md or text file to the Memory Compiler daily log.",
        description="Reads a text file and appends its content to the Google-Chat-Utils daily log in the Memory Compiler."
    )
    log_parser.add_argument("--input_file", "-i", metavar="FILE_PATH", required=True,
                            help="Path to the file you want to log.")
    log_parser.add_argument("--section", "-s", metavar="SECTION_NAME",
                            help="Title for the section in the daily log. Default: Manual Log: <filename>")
    log_parser.set_defaults(func=handle_log)

    # --- Parser for the 'distill' command ---
    distill_parser = subparsers.add_parser("distill",
        help="Distill existing _human.md files via LLM (no re-parsing).",
        description="Дистилляция готовых _human.md: редакция секретов, чанкинг, вызовы LLM, верификация."
    )
    distill_input_group = distill_parser.add_mutually_exclusive_group(required=True)
    distill_input_group.add_argument("--input_file", "-i", metavar="FILE_PATH",
                                     help="Путь к одному _human.md файлу.")
    distill_input_group.add_argument("--input_dir", "-d", metavar="DIR_PATH",
                                     help="Директория с _human.md файлами (без рекурсии, только *_human.md).")
    distill_parser.add_argument("--output_dir", metavar="DIR_PATH", default=None,
                                help="Папка для _distilled.md и кэша. По умолчанию: рядом со входным файлом.")
    _add_distill_options(distill_parser)
    distill_parser.set_defaults(func=handle_distill)

    # --- Parser for the 'auth-drive' command ---
    auth_drive_parser = subparsers.add_parser("auth-drive",
        help="Interactive OAuth2 authorization for Google Drive.",
        description="Запускает интерактивный OAuth2 flow для получения refresh-токена Google Drive."
    )
    auth_drive_parser.add_argument("--client_secrets", default="client_secret.json",
                                   help="Путь к client_secret.json. По умолчанию: client_secret.json")
    auth_drive_parser.add_argument("--token_path", default=".gdrive_token.json",
                                   help="Путь для сохранения токена. По умолчанию: .gdrive_token.json")
    auth_drive_parser.set_defaults(func=handle_auth_drive)

    # --- Parser for the 'fetch-drive' command ---
    fetch_drive_parser = subparsers.add_parser("fetch-drive",
        help="Fetch chat export from Google Drive by name.",
        description="Поиск и скачивание файла чата из Google Drive (папка 'Google AI Studio')."
    )
    fetch_drive_parser.add_argument("--chat_name", "-c", required=True,
                                    help="Имя чата или подстрока для поиска на Google Drive.")
    fetch_drive_parser.add_argument("--output_dir", "-d", default="input_data",
                                    help="Папка для сохранения скачанного файла. По умолчанию: input_data")
    fetch_drive_parser.add_argument("--folder_id", default=None,
                                    help="ID папки на Google Drive (по умолчанию ищет папку 'Google AI Studio').")
    fetch_drive_parser.add_argument("--parse", action="store_true",
                                    help="Автоматически запустить парсинг после успешного скачивания.")
    fetch_drive_parser.add_argument("--output_prefix", "-o", default="output_data/",
                                    help="Базовая папка вывода при парсинге. По умолчанию: output_data/")
    fetch_drive_parser.add_argument("--log_to_memory", "-l", action="store_true",
                                    help="Отправить результат в Memory Compiler (если указан --parse).")
    fetch_drive_parser.add_argument("--distill", action="store_true",
                                    help="Дистиллировать результат через LLM (если указан --parse).")
    _add_distill_options(fetch_drive_parser)
    fetch_drive_parser.set_defaults(func=handle_fetch_drive)

    # --- Parser for the 'validate' command ---
    validate_parser = subparsers.add_parser("validate",
        help="Validate JSON export file using Pydantic schemas.",
        description="Проверяет валидность JSON-экспорта Google AI Studio или промежуточного файла."
    )
    validate_parser.add_argument("--input_file", "-i", required=True,
                                 help="Путь к JSON файлу для проверки.")
    validate_parser.set_defaults(func=handle_validate)

    # --- Parser for the 'interactive' command ---
    interactive_parser = subparsers.add_parser("interactive",
        help="Start interactive terminal menu.",
        description="Запускает пошаговое интерактивное текстовое меню."
    )
    interactive_parser.set_defaults(func=handle_interactive)

    if len(sys.argv) == 1:
        if sys.stdin.isatty():
            handle_interactive()
            return
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    from utils.logging_config import setup_logging
    setup_logging(
        level=getattr(args, "log_level", "INFO"),
        log_file=getattr(args, "log_file", None),
        verbose=getattr(args, "verbose", False)
    )
    args.func(args)

if __name__ == "__main__":
    main()

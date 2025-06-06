print('START CLI')
try:
    import argparse
    import os
    import sys
    import json
    from utils.parsing.google_studio_parser import GoogleAIStudioJSONParser, load_json_file
    from utils.reconstruction.gemini_code_reconstructor import GeminiAPICodeReconstructor
    from utils.core.chat_elements import IntermediateChatData, TextPart, ThoughtsPart, ExecutableCodePart, CodeExecutionResultPart, FunctionCallPart, FunctionResponsePart, InlineDataPart, UriReferencePart
except Exception as e:
    print(f'IMPORT ERROR: {e}')
    import traceback; traceback.print_exc()
    sys.exit(1)

# === Определение корня проекта ===
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

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
    if not os.path.isfile(input_file_path):
        print(f"{RED}❌ Ошибка: Входной файл не найден: {input_file_path}{RESET}", file=sys.stderr)
        return False

    print(f"{BOLD}{BLUE}🚀 Запуск команды [parse] 🚀{RESET}")
    print(SEPARATOR)
    print(f"{BOLD}📄 Входной файл:{RESET} {input_file_path}")
    print(f"{BOLD}📁 Output prefix:{RESET} {output_prefix}")
    print(SEPARATOR)

    intermediate_data = parser_instance.parse(input_file_path)
    if intermediate_data:
        file_name_without_ext = os.path.splitext(os.path.basename(input_file_path))[0]
        prefix = output_prefix
        if prefix.endswith(f"{file_name_without_ext}_") or prefix.endswith(f"{file_name_without_ext}"):
            json_out_path = os.path.join(PROJECT_ROOT, f"{prefix}intermediate.json")
            md_out_path = os.path.join(PROJECT_ROOT, f"{prefix}raw_rag.md")
        else:
            json_out_path = os.path.join(PROJECT_ROOT, f"{prefix}{file_name_without_ext}_intermediate.json")
            md_out_path = os.path.join(PROJECT_ROOT, f"{prefix}{file_name_without_ext}_raw_rag.md")
        try:
            with open(json_out_path, 'w', encoding='utf-8') as f_json:
                json.dump(intermediate_data.to_dict(), f_json, indent=2, ensure_ascii=False)
            print(f"  {GREEN}💾 Промежуточный JSON сохранён: {json_out_path} ✔️{RESET}")
        except Exception as e:
            print(f"  {RED}❌ Ошибка при сохранении промежуточного JSON: {json_out_path}: {e}{RESET}", file=sys.stderr)
            return False

        markdown_content = parser_instance.to_markdown(intermediate_data)
        try:
            with open(md_out_path, 'w', encoding='utf-8') as f_md:
                f_md.write(markdown_content)
            print(f"  {GREEN}💾 Markdown для RAG сохранён: {md_out_path} ✔️{RESET}")
        except Exception as e:
            print(f"  {RED}❌ Ошибка при сохранении Markdown: {md_out_path}: {e}{RESET}", file=sys.stderr)
            return False
        print(f"{SEPARATOR}")
        print(f"{GREEN}✨ Команда [parse] успешно завершена! ✨{RESET}")
        return True
    else:
        print(f"  {RED}Не удалось распарсить файл: {input_file_path}{RESET}", file=sys.stderr)
        return False

def handle_parse(args):
    """Обработка команды 'parse' с новой структурой имён файлов."""
    parser_gai = GoogleAIStudioJSONParser()
    output_prefix = args.output_prefix if args.output_prefix else "output_data/"
    if args.input_file:
        process_single_parse_file(args.input_file, parser_gai, output_prefix)
    elif args.input_dir:
        if not os.path.isdir(args.input_dir):
            print(f"Ошибка: Входная директория не найдена: {args.input_dir}", file=sys.stderr)
            return
        print(f"Обработка всех JSON-совместимых файлов в директории: {args.input_dir}...")
        processed_count = 0
        successful_parses = 0
        for filename in os.listdir(args.input_dir):
            if filename.lower().endswith(('.json', '.jsonl', '.txt')) or '.' not in filename:
                file_path = os.path.join(args.input_dir, filename)
                if os.path.isfile(file_path):
                    if process_single_parse_file(file_path, parser_gai, output_prefix):
                        successful_parses += 1
                    processed_count += 1
            else:
                print(f"  Пропуск не-JSON файла: {filename}")
        print(f"\nОбработано {processed_count} потенциальных файлов из {args.input_dir}.")
        print(f"Успешно распарсено и сохранено {successful_parses} файлов.")
    else:
        print("Ошибка: Необходимо указать --input_file или --input_dir для команды parse.", file=sys.stderr)


def handle_reconstruct(args):
    print(f"{BOLD}{MAGENTA}🚀 Запуск команды [reconstruct] 🚀{RESET}")
    print(SEPARATOR)
    print(f"{BOLD}📄 Входной JSON:{RESET} {args.input_json}")
    print(f"{BOLD}📁 Output Python:{RESET} {args.output_py}")
    print(f"{BOLD}🧩 Шаблон:{RESET} {args.template_name}")
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
            si_file=args.si_file,
            fi_file=args.fi_file,
            li_file=args.li_file
        )
        with open(full_output_py_path, 'w', encoding='utf-8') as f:
            f.write(python_script)
        print(f"{GREEN}💾 Python-скрипт сохранён: {full_output_py_path} ✔️{RESET}")
        print(f"{SEPARATOR}")
        print(f"{GREEN}✨ Команда [reconstruct] успешно завершена! ✨{RESET}")
    except FileNotFoundError as e:
        print(f"{RED}Ошибка при реконструкции (проблема с шаблоном?): {e}{RESET}", file=sys.stderr)
    except Exception as e:
        print(f"{RED}Неожиданная ошибка при реконструкции: {e}{RESET}", file=sys.stderr)


def main():
    """Main function for the CLI."""
    parser = argparse.ArgumentParser(
        description="Google Chat Utils v3 CLI: Parse AI Studio exports and reconstruct Gemini API code.",
        formatter_class=argparse.RawTextHelpFormatter # For better help text formatting
    )
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
                              help="Префикс для имён выходных файлов. Например: output_data/. По умолчанию: output_data/")
    parse_parser.set_defaults(func=handle_parse)

    # --- Parser for the 'reconstruct' command ---
    reconstruct_parser = subparsers.add_parser("reconstruct",
        help="Reconstruct Python script from intermediate JSON.",
        description="Reconstructs an executable Python script for the Gemini API from an intermediate JSON file (typically one produced by the 'parse' command, though direct AI Studio JSON might also work if rich enough for the parser)."
    )
    reconstruct_parser.add_argument("--input_json", "-ij", metavar="PATH_TO_INTERMEDIATE_JSON", required=True,
                                    help="Path to the intermediate JSON file (e.g., output_v3_data/MyChat/intermediate.json).")
    reconstruct_parser.add_argument("--output_py", "-op", metavar="FILENAME.py", required=True,
                                    help="Name of the output Python script (e.g., reconstructed_chat.py). It will be saved in the same directory as the input_json.")
    reconstruct_parser.add_argument("--template_dir", "-td", metavar="PATH_TO_TEMPLATES", required=True,
                                    help="Path to the directory containing .py.tpl template files.")
    reconstruct_parser.add_argument("--template_name", "-tn", metavar="TEMPLATE_FILENAME", required=True,
                                    help="Name of the template file within the template directory (e.g., gemini_studio_default.py.tpl).")
    reconstruct_parser.add_argument("--api_key_var_name", "-ak", default="YOUR_API_KEY",
                                    help="Name of the API key variable in the generated script. Default: YOUR_API_KEY")
    reconstruct_parser.add_argument("--model_name", metavar="MODEL_NAME", required=True,
                                    help="Model name to use for code reconstruction (str, required).")
    reconstruct_parser.add_argument("--si_file", metavar="PATH_TO_SI_FILE", required=False,
                                    help="Путь к файлу с системной инструкцией для override.")
    reconstruct_parser.add_argument("--fi_file", metavar="PATH_TO_FI_FILE", required=False,
                                    help="Путь к файлу с первым user message для prepend.")
    reconstruct_parser.add_argument("--li_file", metavar="PATH_TO_LI_FILE", required=False,
                                    help="Путь к файлу с последним user message для append (last instruction/last message).")
    reconstruct_parser.set_defaults(func=handle_reconstruct)

    if len(sys.argv) == 1: # If no command is provided, print help and exit
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()

"""
Interactive CLI mode for Google Chat Utils.

Provides a terminal UI menu for parsing, reconstructing, validating,
distilling, and managing Google AI Studio chat files.
"""

import argparse
import os
from typing import Callable, Dict, Any, Optional

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"

SEPARATOR = f"{CYAN}{'='*60}{RESET}"
THIN_SEP = f"{CYAN}{'-'*60}{RESET}"


def prompt_input(message: str, default: Optional[str] = None) -> str:
    """Prompt user for text input with an optional default value."""
    if default:
        prompt_text = f"{BOLD}{message}{RESET} [{CYAN}{default}{RESET}]: "
    else:
        prompt_text = f"{BOLD}{message}{RESET}: "

    try:
        val = input(prompt_text).strip()
        return val if val else (default or "")
    except (KeyboardInterrupt, EOFError):
        print(f"\n{YELLOW}Ввод отменен.{RESET}")
        return default or ""


def prompt_bool(message: str, default: bool = False) -> bool:
    """Prompt user for yes/no confirmation."""
    default_str = "Y/n" if default else "y/N"
    prompt_text = f"{BOLD}{message}{RESET} ({default_str}): "
    try:
        val = input(prompt_text).strip().lower()
        if not val:
            return default
        return val in ("y", "yes", "д", "да", "1", "true")
    except (KeyboardInterrupt, EOFError):
        print(f"\n{YELLOW}Ввод отменен.{RESET}")
        return default


def print_banner():
    print(SEPARATOR)
    print(f"{BOLD}{GREEN}       Google Chat Utils — Интерактивный терминал (v0.7.0){RESET}")
    print(f"{CYAN}       Инструменты для чатов Google AI Studio & Gemini API{RESET}")
    print(SEPARATOR)


def print_menu():
    print(f"\n{BOLD}Выберите действие:{RESET}")
    print(f"  {CYAN}1.{RESET} [parse]          Парсинг экспорта AI Studio (JSON -> Intermediate + MD)")
    print(f"  {CYAN}2.{RESET} [reconstruct]    Реконструкция Python-кода Gemini API из JSON")
    print(f"  {CYAN}3.{RESET} [validate]       Проверка структуры JSON через Pydantic схему")
    print(f"  {CYAN}4.{RESET} [apply]          Применить .si/.fi/.li оверрайды к Studio JSON")
    print(f"  {CYAN}5.{RESET} [distill]        Дистилляция готовых _human.md через LLM")
    print(f"  {CYAN}6.{RESET} [fetch-drive]    Скачать чат из Google Drive")
    print(f"  {CYAN}7.{RESET} [auth-drive]     Настроить авторизацию Google Drive OAuth2")
    print(f"  {CYAN}8.{RESET} [log]            Записать файл в Memory Compiler дневной лог")
    print(f"  {RED}0.{RESET} Выход")
    print(THIN_SEP)


def interactive_parse(handlers: Dict[str, Callable[[Any], None]]):
    print(f"\n{BOLD}{BLUE}--- 1. Парсинг экспорта Google AI Studio ---{RESET}")
    is_dir = prompt_bool("Парсить директорию целиком (иначе один файл)?", default=False)
    if is_dir:
        input_dir = prompt_input("Путь к директории", default="data")
        input_file = None
    else:
        input_file = prompt_input("Путь к JSON файлу", default="data/Example")
        input_dir = None

    output_prefix = prompt_input("Базовая папка для вывода", default="output_data/")
    log_to_memory = prompt_bool("Логировать в Memory Compiler?", default=False)
    distill = prompt_bool("Запустить дистилляцию через LLM после парсинга?", default=False)

    llm_base_url = None
    llm_model = None
    if distill:
        llm_base_url = prompt_input("LLM Base URL", default=os.getenv("DISTILLER_BASE_URL", "http://localhost:11434/v1"))
        llm_model = prompt_input("LLM Model", default=os.getenv("DISTILLER_MODEL", "qwen2.5:14b"))

    args = argparse.Namespace(
        input_file=input_file,
        input_dir=input_dir,
        output_prefix=output_prefix,
        log_to_memory=log_to_memory,
        distill=distill,
        llm_base_url=llm_base_url,
        llm_model=llm_model,
        distill_preset=None,
        distill_concurrency=None,
        distill_retries=None,
        force=False,
        dry_run=False
    )
    handlers["parse"](args)


def interactive_reconstruct(handlers: Dict[str, Callable[[Any], None]]):
    print(f"\n{BOLD}{BLUE}--- 2. Реконструкция Python кода Gemini API ---{RESET}")
    input_json = prompt_input("Путь к входному JSON", default="output_data/Example/Example_intermediate.json")
    output_py = prompt_input("Имя выходного .py скрипта", default="Example_reconstructed.py")
    template_dir = prompt_input("Директория шаблонов", default="utils/templates")
    template_name = prompt_input("Имя шаблона", default="chat_generation_script.py.tpl")
    model_name = prompt_input("Имя модели Gemini", default="gemini-2.5-pro")
    api_key_var = prompt_input("Переменная окружения для API-ключа", default="GEMINI_API_KEY")

    args = argparse.Namespace(
        input_json=input_json,
        output_py=output_py,
        template_dir=template_dir,
        template_name=template_name,
        model_name=model_name,
        api_key_var_name=api_key_var
    )
    handlers["reconstruct"](args)


def interactive_validate(handlers: Dict[str, Callable[[Any], None]]):
    print(f"\n{BOLD}{BLUE}--- 3. Валидация JSON через Pydantic ---{RESET}")
    input_file = prompt_input("Путь к JSON файлу", default="data/Example")
    args = argparse.Namespace(input_file=input_file)
    handlers["validate"](args)


def interactive_apply(handlers: Dict[str, Callable[[Any], None]]):
    print(f"\n{BOLD}{BLUE}--- 4. Применение оверрайдов к Studio JSON ---{RESET}")
    input_json = prompt_input("Путь к исходному Studio JSON", default="data/Example")
    output_json = prompt_input("Путь для сохранения модифицированного JSON", default="output_data/Example_modified.json")
    si_file = prompt_input("Путь к .si файлу (Enter если нет)", default="data/Example.si")
    fi_file = prompt_input("Путь к .fi файлу (Enter если нет)", default="data/Example.fi")
    li_file = prompt_input("Путь к .li файлу (Enter если нет)", default="")

    args = argparse.Namespace(
        input_studio_json=input_json,
        output_studio_json=output_json,
        si_file=si_file if si_file else None,
        fi_file=fi_file if fi_file else None,
        li_file=li_file if li_file else None,
        fi_mode="replace",
        li_mode="replace"
    )
    handlers["apply_overrides_to_studio_json"](args)


def interactive_distill(handlers: Dict[str, Callable[[Any], None]]):
    print(f"\n{BOLD}{BLUE}--- 5. Дистилляция _human.md через LLM ---{RESET}")
    is_dir = prompt_bool("Обработать директорию (иначе один файл)?", default=False)
    if is_dir:
        input_dir = prompt_input("Директория с _human.md", default="output_data")
        input_file = None
    else:
        input_file = prompt_input("Путь к файлу _human.md", default="output_data/Example/Example_human.md")
        input_dir = None

    llm_base_url = prompt_input("LLM Base URL", default=os.getenv("DISTILLER_BASE_URL", "http://localhost:11434/v1"))
    llm_model = prompt_input("LLM Model", default=os.getenv("DISTILLER_MODEL", "qwen2.5:14b"))
    dry_run = prompt_bool("Dry run (без реальных вызовов LLM)?", default=False)

    args = argparse.Namespace(
        input_file=input_file,
        input_dir=input_dir,
        output_dir=None,
        llm_base_url=llm_base_url,
        llm_model=llm_model,
        distill_preset=None,
        distill_concurrency=None,
        distill_retries=None,
        force=False,
        dry_run=dry_run
    )
    handlers["distill"](args)


def interactive_fetch_drive(handlers: Dict[str, Callable[[Any], None]]):
    print(f"\n{BOLD}{BLUE}--- 6. Скачивание чата из Google Drive ---{RESET}")
    chat_name = prompt_input("Имя чата или подстрока для поиска")
    if not chat_name:
        print(f"{RED}Имя чата не может быть пустым.{RESET}")
        return
    output_dir = prompt_input("Папка для сохранения", default="input_data")
    auto_parse = prompt_bool("Автоматически распарсить после скачивания?", default=True)

    args = argparse.Namespace(
        chat_name=chat_name,
        output_dir=output_dir,
        folder_id=None,
        parse=auto_parse,
        output_prefix="output_data/",
        log_to_memory=False,
        distill=False,
        llm_base_url=None,
        llm_model=None,
        distill_preset=None,
        distill_concurrency=None,
        distill_retries=None,
        force=False,
        dry_run=False
    )
    handlers["fetch-drive"](args)


def interactive_auth_drive(handlers: Dict[str, Callable[[Any], None]]):
    print(f"\n{BOLD}{BLUE}--- 7. Настройка Google Drive OAuth2 ---{RESET}")
    client_secrets = prompt_input("Путь к client_secret.json", default="client_secret.json")
    token_path = prompt_input("Путь для сохранения .gdrive_token.json", default=".gdrive_token.json")
    args = argparse.Namespace(client_secrets=client_secrets, token_path=token_path)
    handlers["auth-drive"](args)


def interactive_log(handlers: Dict[str, Callable[[Any], None]]):
    print(f"\n{BOLD}{BLUE}--- 8. Запись в Memory Compiler лог ---{RESET}")
    input_file = prompt_input("Путь к файлу для логирования")
    section = prompt_input("Заголовок секции", default=f"Manual Log: {os.path.basename(input_file)}")
    args = argparse.Namespace(input_file=input_file, section=section)
    handlers["log"](args)


def run_interactive_menu(handlers: Dict[str, Callable[[Any], None]]):
    """Main interactive loop."""
    print_banner()

    actions = {
        "1": lambda: interactive_parse(handlers),
        "2": lambda: interactive_reconstruct(handlers),
        "3": lambda: interactive_validate(handlers),
        "4": lambda: interactive_apply(handlers),
        "5": lambda: interactive_distill(handlers),
        "6": lambda: interactive_fetch_drive(handlers),
        "7": lambda: interactive_auth_drive(handlers),
        "8": lambda: interactive_log(handlers),
    }

    while True:
        try:
            print_menu()
            choice = input(f"{BOLD}Ваш выбор (0-8): {RESET}").strip()
            if choice == "0" or choice.lower() in ("q", "quit", "exit"):
                print(f"{GREEN}До свидания! 👋{RESET}")
                break
            action = actions.get(choice)
            if action:
                action()
            else:
                print(f"{YELLOW}Неверный выбор. Введите число от 0 до 8.{RESET}")
        except (KeyboardInterrupt, EOFError):
            print(f"\n{GREEN}Выход из интерактивного режима. 👋{RESET}")
            break
        except Exception as e:
            print(f"\n{RED}❌ Произошла ошибка: {e}{RESET}")

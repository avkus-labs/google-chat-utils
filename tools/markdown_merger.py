import argparse
import os
import sys
from typing import List, Optional, Set

def find_markdown_files(paths: List[str], recursive: bool) -> List[str]:
    """
    Finds all Markdown files (.md) from a list of paths (files or directories).
    Если paths содержит только одну папку, поиск всегда рекурсивный.

    Args:
        paths: A list of strings, where each string can be a path to a .md file
               or a directory.
        recursive: If True, search directories recursively. Otherwise, search
                   only the top-level of directories.

    Returns:
        A sorted list of unique paths to .md files.
    """
    markdown_files: Set[str] = set()
    # Если paths содержит ровно один элемент и это папка — всегда рекурсивно
    force_recursive = False
    if len(paths) == 1 and os.path.isdir(paths[0]):
        force_recursive = True
    for path_item in paths:
        if os.path.isfile(path_item):
            if path_item.lower().endswith(".md"):
                markdown_files.add(os.path.abspath(path_item))
            else:
                print(f"Предупреждение: Входной файл '{path_item}' не является Markdown (.md) файлом и будет проигнорирован.", file=sys.stderr)
        elif os.path.isdir(path_item):
            if recursive or force_recursive:
                for root, _, files in os.walk(path_item):
                    for file in files:
                        if file.lower().endswith(".md"):
                            markdown_files.add(os.path.abspath(os.path.join(root, file)))
            else:
                for item in os.listdir(path_item):
                    full_item_path = os.path.join(path_item, item)
                    if os.path.isfile(full_item_path) and item.lower().endswith(".md"):
                        markdown_files.add(os.path.abspath(full_item_path))
        else:
            print(f"Предупреждение: Указанный путь '{path_item}' не является файлом или директорией и будет проигнорирован.", file=sys.stderr)

    return sorted(list(markdown_files))

def merge_markdown_files(
    input_files: List[str],
    output_file: str,
    separator: Optional[str] = "\n\n---\n\n", # Default separator
    include_filenames: bool = False,
    filename_header_level: int = 0 # 0 for comment, 1-6 for header level
) -> None:
    """
    Merges content from multiple Markdown files into a single output file.

    Args:
        input_files: A list of paths to Markdown files to be merged.
        output_file: Path to the output Markdown file.
        separator: String to insert between the content of merged files.
                   If None, no separator is added.
        include_filenames: If True, include the source filename before its content.
        filename_header_level: If include_filenames is True, this determines how
                               the filename is included. 0 means as an HTML comment.
                               1-6 means as a Markdown header of that level (e.g., H2).
    """
    merged_content = []

    print(f"Начинается объединение {len(input_files)} Markdown файлов в '{output_file}'...")

    for i, file_path in enumerate(input_files):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if include_filenames:
                if filename_header_level > 0 and filename_header_level <= 6:
                    header_prefix = "#" * filename_header_level
                    merged_content.append(f"{header_prefix} Источник: {os.path.basename(file_path)}\n\n")
                else: # Default to comment
                    merged_content.append(f"<!-- MERGED_FROM: {os.path.basename(file_path)} -->\n\n")

            merged_content.append(content)

            if separator and i < len(input_files) - 1:
                merged_content.append(separator)

            print(f"  [+] Добавлен файл: {file_path}")

        except FileNotFoundError:
            print(f"Ошибка: Файл не найден '{file_path}'. Пропускается.", file=sys.stderr)
        except Exception as e:
            print(f"Ошибка при чтении файла '{file_path}': {e}. Пропускается.", file=sys.stderr)

    try:
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir: # If output_file includes a path
            os.makedirs(output_dir, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as outfile:
            outfile.write("".join(merged_content))
        print(f"\n✅ Успешно объединено {len(input_files)} файлов в '{output_file}'.")
    except Exception as e:
        print(f"\n❌ Ошибка при записи в выходной файл '{output_file}': {e}", file=sys.stderr)

def main():
    """Main function for the Markdown Merger CLI."""
    parser = argparse.ArgumentParser(
        description="Утилита для объединения нескольких Markdown файлов в один.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "--input", "-i",
        nargs='+',
        required=True,
        metavar="PATH",
        help="Один или несколько путей к входным Markdown файлам (.md) или директориям, содержащим .md файлы."
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        metavar="OUTPUT_FILE",
        help="Путь к выходному объединенному Markdown файлу."
    )
    parser.add_argument(
        "--separator", "-s",
        default="\n\n---\n\n", # Default to two newlines, then ---, then two newlines
        help="Строка-разделитель для вставки между содержимым объединенных файлов. \n"
             "Используйте escape-последовательности для спецсимволов (например, '\\n' для новой строки). \n"
             "По умолчанию: \"\\n\\n---\\n\\n\""
    )
    parser.add_argument(
        "--include_filenames", "-fn",
        action="store_true",
        help="Включить имя исходного файла перед его содержимым в объединенном файле."
    )
    parser.add_argument(
        "--filename_header_level", "-fhl",
        type=int,
        default=0,
        choices=range(0, 7), # 0 for comment, 1-6 for header levels
        help="Если --include_filenames указан, определяет как будет отображаться имя файла: \n"
             "0 - как HTML комментарий (<!-- MERGED_FROM: ... -->) (по умолчанию), \n"
             "1-6 - как Markdown заголовок соответствующего уровня (например, H2 если указано 2)."
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Если указан, и среди входных путей есть директории, поиск .md файлов в них будет осуществляться рекурсивно."
    )

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    # Process separator string to interpret escape sequences like \n
    processed_separator = args.separator.replace("\\n", "\n").replace("\\t", "\t")
    print(f"ℹ️  Разделитель будет: {repr(processed_separator)}")

    # Find all markdown files from input paths
    print("📄 Поиск Markdown файлов...")
    markdown_files_to_merge = find_markdown_files(args.input, args.recursive)

    if not markdown_files_to_merge:
        print("❌ Не найдено Markdown файлов для объединения. Проверьте входные пути.", file=sys.stderr)
        sys.exit(1)

    print(f"➕ Найдено {len(markdown_files_to_merge)} Markdown файлов для объединения:")
    for md_file in markdown_files_to_merge:
        print(f"   ➖ {md_file}")

    merge_markdown_files(
        markdown_files_to_merge,
        args.output,
        separator=processed_separator,
        include_filenames=args.include_filenames,
        filename_header_level=args.filename_header_level
    )
    print(f"✅ Объединение завершено. Итоговый файл: {args.output}")

if __name__ == "__main__":
    main()

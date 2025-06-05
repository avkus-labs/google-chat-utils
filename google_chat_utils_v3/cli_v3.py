import argparse
import os
import sys
import json
from google_chat_utils_v3.parsing.google_studio_parser import GoogleAIStudioJSONParser, load_json_file
from google_chat_utils_v3.reconstruction.gemini_code_reconstructor import GeminiAPICodeReconstructor
from google_chat_utils_v3.core.chat_elements import IntermediateChatData # Still needed for type hints

def ensure_dir(path):
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)

def process_single_parse_file(input_file_path: str, base_output_dir: str, parser_instance: GoogleAIStudioJSONParser):
    """Helper function to parse a single file and save outputs to a dedicated subdirectory."""
    if not os.path.isfile(input_file_path):
        print(f"Error: Input file not found: {input_file_path}", file=sys.stderr)
        return False

    print(f"Processing input file: {input_file_path}...")
    intermediate_data = parser_instance.parse(input_file_path)
    if intermediate_data:
        file_name_without_ext = os.path.splitext(os.path.basename(input_file_path))[0]
        # Create specific output subdirectory for this file
        specific_output_subdir = os.path.join(base_output_dir, file_name_without_ext)
        ensure_dir(specific_output_subdir)

        # Standardized output filenames
        json_out_path = os.path.join(specific_output_subdir, "intermediate.json")
        md_out_path = os.path.join(specific_output_subdir, "rag.md")

        try:
            # Placeholder for IntermediateChatData serialization
            temp_dict_for_json = {
                "source_platform": intermediate_data.source_platform,
                "source_file_name": intermediate_data.source_file_name,
                "parsed_at_timestamp": intermediate_data.parsed_at_timestamp,
                "run_settings": intermediate_data.run_settings.raw_settings,
                "system_instruction": intermediate_data.system_instruction.text if intermediate_data.system_instruction else None,
                "dialogue_history": [{"role": t.role, "num_parts": len(t.parts), "finish_reason": t.finish_reason, "parts_preview": [p.__class__.__name__ for p in t.parts][:3]} for t in intermediate_data.dialogue_history],
                "tool_configurations": [{"type": tc.type, "num_functions": len(tc.functions) if tc.functions else 0} for tc in intermediate_data.tool_configurations]
            }
            with open(json_out_path, 'w', encoding='utf-8') as f_json:
                json.dump(temp_dict_for_json, f_json, indent=2, ensure_ascii=False)
            print(f"  💾 Intermediate JSON saved to: {json_out_path}")
        except Exception as e:
            print(f"  ❌ Error saving intermediate JSON to {json_out_path}: {e}", file=sys.stderr)
            return False

        markdown_content = parser_instance.to_markdown(intermediate_data)
        try:
            with open(md_out_path, 'w', encoding='utf-8') as f_md:
                f_md.write(markdown_content)
            print(f"  💾 Markdown for RAG saved to: {md_out_path}")
        except Exception as e:
            print(f"  ❌ Error saving Markdown to {md_out_path}: {e}", file=sys.stderr)
            return False
        print(f"  File {input_file_path} processed successfully.")
        return True
    else:
        print(f"  Could not parse file: {input_file_path}", file=sys.stderr)
        return False

def handle_parse(args):
    """Handles the 'parse' command with new output structure."""
    parser_gai = GoogleAIStudioJSONParser()

    # Base output directory
    base_output_dir = args.output_dir
    # No need to create base_output_dir here, process_single_parse_file will create subdirs

    if args.input_file:
        process_single_parse_file(args.input_file, base_output_dir, parser_gai)
    elif args.input_dir:
        if not os.path.isdir(args.input_dir):
            print(f"Error: Input directory not found: {args.input_dir}", file=sys.stderr)
            return

        print(f"Processing all JSON-compatible files in directory: {args.input_dir}...")
        processed_count = 0
        successful_parses = 0
        for filename in os.listdir(args.input_dir):
            # Consider more robust file type checking if needed
            if filename.lower().endswith(('.json', '.jsonl', '.txt')) or '.' not in filename :
                file_path = os.path.join(args.input_dir, filename)
                if os.path.isfile(file_path): # Ensure it's a file
                    if process_single_parse_file(file_path, base_output_dir, parser_gai):
                        successful_parses +=1
                    processed_count += 1
            else:
                print(f"  Skipping non-JSON-like file: {filename}")

        print(f"\nProcessed {processed_count} potential file(s) from {args.input_dir}.")
        print(f"Successfully parsed and saved {successful_parses} file(s).")
    else:
        # This case should not be reached due to argparse mutually_exclusive_group(required=True)
        print("Error: Either --input_file or --input_dir must be specified for parse command.", file=sys.stderr)


def handle_reconstruct(args):
    """Handles the 'reconstruct' command with new output structure."""
    if not os.path.isfile(args.input_json):
        print(f"Error: Input JSON file not found: {args.input_json}", file=sys.stderr)
        return

    if not os.path.isdir(args.template_dir):
        print(f"Error: Template directory not found: {args.template_dir}", file=sys.stderr)
        return

    # Determine output directory from the input_json path
    # e.g., if input_json is "output_data/MyChatSession/intermediate.json",
    # output_dir_for_script becomes "output_data/MyChatSession"
    output_dir_for_script = os.path.dirname(args.input_json)

    # Ensure this directory exists (it should if created by 'parse')
    if not os.path.isdir(output_dir_for_script):
        print(f"Warning: Output directory inferred from input JSON path does not exist: {output_dir_for_script}", file=sys.stderr)
        print(f"Attempting to create it or save in current directory if it's empty path.", file=sys.stderr)
        if output_dir_for_script: # Only try to create if path is not empty
             ensure_dir(output_dir_for_script)
        else: # If dirname is empty (e.g. input_json is just a filename), save to CWD
            output_dir_for_script = "."


    # Construct the full output path for the Python script
    # args.output_py is now just the filename
    full_output_py_path = os.path.join(output_dir_for_script, args.output_py)

    print(f"WARNING: Proper deserialization of IntermediateChatData from JSON is not yet implemented.", file=sys.stderr)
    print(f"The reconstruct command requires a fully compatible JSON (e.g. original AI Studio format) for the parser to load it into IntermediateChatData.", file=sys.stderr)

    try:
        parser_gai_for_reconstruct = GoogleAIStudioJSONParser()
        # This parse method expects the Google AI Studio format, not necessarily our intermediate format.
        intermediate_data_for_reconstruct = parser_gai_for_reconstruct.parse(args.input_json)
        if not intermediate_data_for_reconstruct:
             print(f"Error: Could not parse the provided JSON into IntermediateChatData: {args.input_json}. Make sure it's a valid Google AI Studio export or a compatible rich format.", file=sys.stderr)
             return
    except Exception as e:
        print(f"Error parsing intermediate JSON into IntermediateChatData object: {e}", file=sys.stderr)
        return

    print(f"Reconstructing Python script from: {args.input_json}")
    print(f"Using template directory: {args.template_dir}")
    print(f"Using template file: {args.template_name}")

    reconstructor = GeminiAPICodeReconstructor(template_dir=args.template_dir)

    try:
        python_script = reconstructor.reconstruct(
            intermediate_data=intermediate_data_for_reconstruct,
            template_name=args.template_name,
            api_key_var_name=args.api_key_var_name
        )

        with open(full_output_py_path, 'w', encoding='utf-8') as f:
            f.write(python_script)
        print(f"💾 Python script saved to: {full_output_py_path}")

    except FileNotFoundError as e:
        print(f"Error during reconstruction (template file issue?): {e}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred during reconstruction: {e}", file=sys.stderr)


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
    parse_parser.add_argument("--output_dir", "-o", metavar="BASE_OUTPUT_DIR", default="output_v3_data",
                              help="Base directory to save output. A subdirectory named after each input file (without extension) will be created here. Default: output_v3_data")
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
    reconstruct_parser.set_defaults(func=handle_reconstruct)

    if len(sys.argv) == 1: # If no command is provided, print help and exit
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()

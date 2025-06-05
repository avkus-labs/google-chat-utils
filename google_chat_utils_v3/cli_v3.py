import argparse
import os
import sys
import json # For reconstructor's input if it's ever directly a string
from google_chat_utils_v3.parsing.google_studio_parser import GoogleAIStudioJSONParser, load_json_file
from google_chat_utils_v3.reconstruction.gemini_code_reconstructor import GeminiAPICodeReconstructor
from google_chat_utils_v3.core.chat_elements import IntermediateChatData

def handle_parse(args):
    """Handles the 'parse' command."""
    parser_gai = GoogleAIStudioJSONParser()

    # Ensure output directory exists
    try:
        os.makedirs(args.output_dir, exist_ok=True)
        print(f"Output directory: {os.path.abspath(args.output_dir)}")
    except OSError as e:
        print(f"Error: Could not create output directory {args.output_dir}: {e}", file=sys.stderr)
        return

    if args.input_file:
        if not os.path.isfile(args.input_file):
            print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
            return

        print(f"Processing single input file: {args.input_file}...")
        intermediate_data = parser_gai.parse(args.input_file)
        if intermediate_data:
            base_name = os.path.splitext(os.path.basename(args.input_file))[0]
            json_out_path = os.path.join(args.output_dir, f"{base_name}_intermediate.json")
            md_out_path = os.path.join(args.output_dir, f"{base_name}_rag.md")

            try:
                # Save intermediate JSON
                # Need to convert IntermediateChatData to dict first if not using a custom serializer
                # For now, assuming we might need a to_dict() method or similar for full serialization.
                # The parser_v2.py's format_intermediate_json created a dict then dumped.
                # Let's simulate that by accessing raw_settings and other key components for now
                # This part needs a proper IntermediateChatData.to_dict() method for clean serialization.
                # Placeholder for serialization:
                temp_dict_for_json = {
                    "source_platform": intermediate_data.source_platform,
                    "source_file_name": intermediate_data.source_file_name,
                    "parsed_at_timestamp": intermediate_data.parsed_at_timestamp,
                    "run_settings": intermediate_data.run_settings.raw_settings, # Using raw for now
                    "system_instruction": intermediate_data.system_instruction.text if intermediate_data.system_instruction else None,
                    # Dialogue history and tool_configs would need more complex serialization
                    "dialogue_history": [{"role": t.role, "num_parts": len(t.parts)} for t in intermediate_data.dialogue_history], # Simplified
                    "tool_configurations": [{"type": tc.type, "num_functions": len(tc.functions) if tc.functions else 0} for tc in intermediate_data.tool_configurations] # Simplified
                }
                with open(json_out_path, 'w', encoding='utf-8') as f_json:
                    json.dump(temp_dict_for_json, f_json, indent=2, ensure_ascii=False)
                print(f"💾 Intermediate JSON saved to: {json_out_path}")
            except Exception as e:
                print(f"❌ Error saving intermediate JSON to {json_out_path}: {e}", file=sys.stderr)

            # Save Markdown
            markdown_content = parser_gai.to_markdown(intermediate_data)
            try:
                with open(md_out_path, 'w', encoding='utf-8') as f_md:
                    f_md.write(markdown_content)
                print(f"💾 Markdown for RAG saved to: {md_out_path}")
            except Exception as e:
                print(f"❌ Error saving Markdown to {md_out_path}: {e}", file=sys.stderr)
            print(f"File {args.input_file} processed.")
        else:
            print(f"Could not parse file: {args.input_file}", file=sys.stderr)

    elif args.input_dir:
        if not os.path.isdir(args.input_dir):
            print(f"Error: Input directory not found: {args.input_dir}", file=sys.stderr)
            return

        print(f"Processing all JSON files in directory: {args.input_dir}...")
        processed_count = 0
        for filename in os.listdir(args.input_dir):
            if filename.lower().endswith(('.json', '.jsonl')): # Process .json and .jsonl
                file_path = os.path.join(args.input_dir, filename)
                print(f"  Processing: {file_path}")
                # Re-use single file logic by setting args.input_file temporarily (or call a helper)
                # This is a bit of a hack for reusing the above block directly.
                # A better way would be a dedicated function: process_single_parse_file(filepath, output_dir, parser_instance)

                current_intermediate_data = parser_gai.parse(file_path)
                if current_intermediate_data:
                    base_name = os.path.splitext(filename)[0]
                    json_out_path = os.path.join(args.output_dir, f"{base_name}_intermediate.json")
                    md_out_path = os.path.join(args.output_dir, f"{base_name}_rag.md")

                    # Placeholder for serialization (same as above)
                    temp_dict_for_json_batch = {
                        "source_platform": current_intermediate_data.source_platform,
                        "source_file_name": current_intermediate_data.source_file_name,
                        "parsed_at_timestamp": current_intermediate_data.parsed_at_timestamp,
                        "run_settings": current_intermediate_data.run_settings.raw_settings,
                        "system_instruction": current_intermediate_data.system_instruction.text if current_intermediate_data.system_instruction else None,
                        "dialogue_history": [{"role": t.role, "num_parts": len(t.parts)} for t in current_intermediate_data.dialogue_history],
                        "tool_configurations": [{"type": tc.type, "num_functions": len(tc.functions) if tc.functions else 0} for tc in current_intermediate_data.tool_configurations]
                    }
                    try:
                        with open(json_out_path, 'w', encoding='utf-8') as f_json:
                            json.dump(temp_dict_for_json_batch, f_json, indent=2, ensure_ascii=False)
                        print(f"  💾 Intermediate JSON saved to: {json_out_path}")
                    except Exception as e:
                        print(f"  ❌ Error saving intermediate JSON for {filename}: {e}", file=sys.stderr)

                    markdown_content = parser_gai.to_markdown(current_intermediate_data)
                    try:
                        with open(md_out_path, 'w', encoding='utf-8') as f_md:
                            f_md.write(markdown_content)
                        print(f"  💾 Markdown for RAG saved to: {md_out_path}")
                    except Exception as e:
                        print(f"  ❌ Error saving Markdown for {filename}: {e}", file=sys.stderr)
                    processed_count += 1
                else:
                    print(f"  Could not parse file: {file_path}", file=sys.stderr)
        print(f"Processed {processed_count} file(s) from {args.input_dir}.")
    else:
        print("Error: Either --input_file or --input_dir must be specified for parse command.", file=sys.stderr)


def handle_reconstruct(args):
    """Handles the 'reconstruct' command."""
    if not os.path.isfile(args.input_json):
        print(f"Error: Input JSON file not found: {args.input_json}", file=sys.stderr)
        return

    if not os.path.isdir(args.template_dir):
        print(f"Error: Template directory not found: {args.template_dir}", file=sys.stderr)
        return

    # Load IntermediateChatData from the intermediate JSON file
    # This requires IntermediateChatData to be deserializable from dict,
    # or for the parser to be used to re-parse the intermediate JSON.
    # For now, let's use the parser to load the intermediate JSON, assuming it can handle its own output.
    # This is not ideal; a dedicated IntermediateChatData.from_dict() would be better.

    print(f"Loading intermediate data from: {args.input_json}...")
    # The intermediate JSON created by `handle_parse` is simplified.
    # A full `IntermediateChatData` cannot be reconstructed from it without proper serialization/deserialization.
    # We will proceed assuming the user provides an intermediate JSON that *can* be parsed by GAIParser
    # or we use a placeholder for now.
    # This highlights the need for robust serialization/deserialization for IntermediateChatData.

    # TEMPORARY: Create a dummy IntermediateChatData object for reconstructor to work
    # In a real scenario, this would be loaded and parsed properly.
    raw_intermediate_json_data = load_json_file(args.input_json)
    if not raw_intermediate_json_data:
        print(f"Error: Could not load or parse the intermediate JSON file: {args.input_json}", file=sys.stderr)
        return

    # Attempt to re-parse if it's in a format our parser can handle (e.g. original AI Studio format)
    # This is a workaround. Ideally, the intermediate JSON has a defined schema and from_dict method.
    # For now, we'll assume the reconstructor needs an IntermediateChatData object, however it's obtained.
    # If the input_json is the one from *this* script's parse command, it's simplified and won't fully re-parse.
    # We need a proper way to instantiate IntermediateChatData from the intermediate JSON.
    # Let's assume the GoogleAIStudioJSONParser can parse its own simplified output for now,
    # or that the user provides a richer JSON.

    # This is a critical point: The simplified JSON from handle_parse won't create a full IntermediateChatData.
    # For the CLI to be truly useful, IntermediateChatData needs to_dict and from_dict methods.
    # For now, we'll just pass the raw dict to a modified reconstructor or make reconstructor fail gracefully.
    # Or, for testing CLI flow, we can use the parser directly if it's an AI Studio file.

    # This CLI is designed to work with the *output* of the parse command.
    # That output is a simplified JSON. The Reconstructor expects a full IntermediateChatData object.
    # This mismatch needs to be resolved by:
    # 1. Making IntermediateChatData serializable to/from a rich JSON.
    # 2. Or, the reconstructor learns to work with the simplified JSON (less ideal).

    # For the purpose of this CLI subtask, we'll assume the reconstructor can work with what the parser produces.
    # This means the intermediate JSON should be loadable into an IntermediateChatData object.
    # The current simplified JSON from handle_parse is NOT sufficient.
    # We will proceed with a placeholder error message here until proper serialization is in place.

    # --- THIS IS THE POINT OF MISMATCH ---
    # The `parser.parse()` method expects the Google AI Studio format, not our intermediate format.
    # We need a new method in `IntermediateChatData` like `from_dict` or a loader function.

    # For CLI structure, let's assume such a loader exists or the reconstructor can handle a dict.
    # For now, we will just create a placeholder object and print a warning.
    print(f"WARNING: Proper deserialization of IntermediateChatData from JSON is not yet implemented.", file=sys.stderr)
    print(f"The reconstruct command will likely not work correctly with JSON from the 'parse' command yet.", file=sys.stderr)

    # Create a dummy/placeholder IntermediateChatData for CLI flow testing
    # In a real scenario, this would be properly loaded from args.input_json
    try:
        # Attempt to use the parser to see if it can load the intermediate format
        # This is not its intended use for the _intermediate_ format.
        parser_gai_for_reconstruct = GoogleAIStudioJSONParser()
        intermediate_data_for_reconstruct = parser_gai_for_reconstruct.parse(args.input_json) # This will fail if it's not studio fmt
        if not intermediate_data_for_reconstruct:
             print(f"Error: Could not parse the provided JSON into IntermediateChatData: {args.input_json}. Make sure it's a valid Google AI Studio export or a compatible format.", file=sys.stderr)
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
            intermediate_data=intermediate_data_for_reconstruct, # This is the placeholder
            template_name=args.template_name,
            api_key_var_name=args.api_key_var_name
        )

        # Ensure output directory for the script exists
        output_py_dir = os.path.dirname(args.output_py)
        if output_py_dir: # If output_py includes a path
            os.makedirs(output_py_dir, exist_ok=True)

        with open(args.output_py, 'w', encoding='utf-8') as f:
            f.write(python_script)
        print(f"💾 Python script saved to: {args.output_py}")

    except FileNotFoundError as e: # Specifically for template not found inside reconstructor
        print(f"Error during reconstruction: {e}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred during reconstruction: {e}", file=sys.stderr)


def main():
    """Main function for the CLI."""
    # Main parser
    parser = argparse.ArgumentParser(description="Google Chat Utils v3 CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # --- Parser for the 'parse' command ---
    parse_parser = subparsers.add_parser("parse", help="Parse Google AI Studio JSON export files.")
    input_group = parse_parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input_file", "-i", help="Path to a single input JSON file.")
    input_group.add_argument("--input_dir", "-d", help="Directory containing input JSON files.")
    parse_parser.add_argument("--output_dir", "-o", default="output_v3", help="Directory to save output (intermediate JSON and Markdown). Default: output_v3")
    parse_parser.set_defaults(func=handle_parse)

    # --- Parser for the 'reconstruct' command ---
    reconstruct_parser = subparsers.add_parser("reconstruct", help="Reconstruct Python script from intermediate JSON.")
    reconstruct_parser.add_argument("--input_json", "-ij", required=True, help="Path to the intermediate JSON file (output of 'parse' command).")
    reconstruct_parser.add_argument("--output_py", "-op", required=True, help="Path to save the reconstructed Python script.")
    reconstruct_parser.add_argument("--template_dir", "-td", required=True, help="Path to the directory containing .py.tpl template files.")
    reconstruct_parser.add_argument("--template_name", "-tn", required=True, help="Name of the template file within the template directory (e.g., gemini_studio_default.py.tpl).")
    reconstruct_parser.add_argument("--api_key_var_name", "-ak", default="YOUR_API_KEY", help="Name of the API key variable in the generated script. Default: YOUR_API_KEY")
    reconstruct_parser.set_defaults(func=handle_reconstruct)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()

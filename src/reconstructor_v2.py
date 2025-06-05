import json
import argparse
import datetime
import os
import base64 # For decoding in generated script
from typing import Dict, Any, List, Optional, Union
import sys

# Attempt to import google.generativeai and its types
# This is for type hinting and direct use in this script if necessary
# The generated script will have its own imports.
try:
    import google.generativeai as genai
    from google.generativeai.types import (
        HarmCategory, HarmBlockThreshold, 
        Tool, FunctionDeclaration, Schema, Types, # Assuming Types has STRING, NUMBER etc.
        CodeExecution, Part, Content, 
        FunctionCall, FunctionResponse, ExecutableCode, CodeExecutionResult, # For constructing parts
        # New imports for Code Execution Language and Outcome
        # Check if these are directly available as enums under CodeExecution/CodeExecutionResult
    )
    # Assuming Language and Outcome are nested classes/enums within CodeExecution/CodeExecutionResult
    _ = genai.types.CodeExecution.Language.PYTHON # Test if it's there
    _ = genai.types.CodeExecutionResult.Outcome.OK # Test if it's there
    # If genai.types.Type is the actual enum, then Schema would use it.
    # Let's assume schema_dict_to_python_code correctly uses genai.types.Type.XXX
except ImportError:
    # This allows the script to be parsed even if genai is not installed here,
    # as the main job is to generate code that *will* use genai.
    print("Warning: google.generativeai library not found. This script generates code requiring it.")
    # Define dummy types for type hinting to avoid runtime errors if genai is not present
    class DummyTypes:
        STRING = None; NUMBER = None; INTEGER = None; BOOLEAN = None; OBJECT = None; ARRAY = None # For PYTHON_TYPE_MAP
    class DummyGenaiTypes:
        Type = DummyTypes() # For PYTHON_TYPE_MAP referencing genai.types.Type
        Schema = dict # Placeholder for Schema type hint
        Tool = dict
        FunctionDeclaration = dict
        CodeExecution = dict
        Part = dict
        Content = dict
        FunctionCall = dict
        FunctionResponse = dict
        ExecutableCode = dict
        CodeExecutionResult = dict
        HarmCategory = None
        HarmBlockThreshold = None

        # Dummy classes for nested enums
        class _CodeExecution:
            class Language:
                PYTHON = "PYTHON"
        class _CodeExecutionResult:
            class Outcome:
                OK = "OK"
                # Add other outcomes if they might appear in data
                ERROR = "ERROR"

        CodeExecution = _CodeExecution()
        CodeExecutionResult = _CodeExecutionResult()

    class Genai:
        types = DummyGenaiTypes()
        def __getattr__(self, name): # To mock genai.GenerativeModel etc. if ever called directly
            print(f"Warning: Attempted to access genai.{name} but library not loaded.")
            return lambda *args, **kwargs: None 
            
    genai = Genai()
    # This setup helps the reconstructor script itself to run without genai,
    # but the generated code will definitely need it.

PYTHON_TYPE_MAP = {
    "STRING": "genai.types.Type.STRING",
    "NUMBER": "genai.types.Type.NUMBER",
    "INTEGER": "genai.types.Type.INTEGER", # Assuming genai.types.Type.INTEGER exists
    "BOOLEAN": "genai.types.Type.BOOLEAN",
    "OBJECT": "genai.types.Type.OBJECT",
    "ARRAY": "genai.types.Type.ARRAY" # Common JSON schema type
}

# Mapping for Code Execution Language
PYTHON_EXEC_LANG_MAP = {
    "PYTHON": "genai.types.CodeExecution.Language.PYTHON"
    # Add other languages if they appear in exports
}

# Mapping for Code Execution Outcome
CODE_EXEC_OUTCOME_MAP = {
    "OUTCOME_OK": "genai.types.CodeExecutionResult.Outcome.OK",
    "OUTCOME_CANCELLED": "genai.types.CodeExecutionResult.Outcome.CANCELLED",
    "OUTCOME_ERROR": "genai.types.CodeExecutionResult.Outcome.ERROR",
    # Add other outcomes if they appear in exports
}

def schema_dict_to_python_code(schema_dict: Dict[str, Any], current_indent: str = "") -> str:
    """
    Recursively converts a Python dictionary (from JSON schema) into a Python code string
    representing a genai.types.Schema object.

    Args:
        schema_dict: The dictionary representing the schema for a field.
        current_indent: The current indentation level string.

    Returns:
        A string of Python code for genai.types.Schema.
    """
    # DEBUG: Print input for this call
    # print(f"[DEBUG schema_dict_to_python_code] Input keys: {list(schema_dict.keys()) if isinstance(schema_dict, dict) else 'Not a dict'}, Indent: '{current_indent}'")

    if not isinstance(schema_dict, dict):
        return repr(schema_dict) 

    schema_type_str = schema_dict.get("type")
    py_type_const = PYTHON_TYPE_MAP.get(str(schema_type_str).upper(), "None") # Ensure type is string and upper for map lookup

    if py_type_const == "None" and schema_type_str is not None:
        # Handle unknown type explicitly to make it visible in output
        # print(f"[WARNING schema_dict_to_python_code] Unknown schema type: {schema_type_str}. Original dict: {schema_dict}")
        return f"genai.types.Schema(description={repr(f'UNKNOWN_SCHEMA_TYPE: {schema_type_str}. Original: {schema_dict}')})"
    elif schema_type_str is None:
        # print(f"[WARNING schema_dict_to_python_code] Schema type is None. Original dict: {schema_dict}")
        return f"genai.types.Schema(description={repr(f'SCHEMA_TYPE_IS_NONE. Original: {schema_dict}')})"

    args = [f"type={py_type_const}"]
    next_indent = current_indent + "    " # 4 spaces for nesting

    if "description" in schema_dict:
        args.append(f"description={repr(schema_dict['description'])}")

    if schema_type_str == "OBJECT":
        properties = schema_dict.get("properties")
        if isinstance(properties, dict) and properties:
            props_code_list = []
            for key, value in properties.items():
                # Indent for value part of the property
                prop_code = schema_dict_to_python_code(value, next_indent + "    ")
                props_code_list.append(f"{repr(key)}: {prop_code}") # Store as "key: value_code"
            
            # Join the "key: value_code" strings with comma, newline and proper indent
            # Add the initial indent for the first property manually
            if props_code_list:
                properties_body = (f",\n{next_indent}    ").join(props_code_list)
                args.append(f"properties={{\n{next_indent}    {properties_body}\n{next_indent}}}")
            else: # Should not happen if properties is not empty, but as a safeguard
                args.append("properties={}")
        else:
            args.append("properties={}") # Empty object
            
    elif schema_type_str == "ARRAY":
        items_schema = schema_dict.get("items")
        if isinstance(items_schema, dict):
            items_code = schema_dict_to_python_code(items_schema, next_indent)
            args.append(f"items={items_code}")
        # Else: array without items schema - less common but genai.types.Schema might support it

    if "enum" in schema_dict and schema_type_str == "STRING": # Enum usually for strings
        enum_values = schema_dict["enum"]
        if isinstance(enum_values, list):
            args.append(f"enum={repr(enum_values)}")
            
    if "required" in schema_dict and isinstance(schema_dict["required"], list):
        args.append(f"required={repr(schema_dict['required'])}")

    # Format arguments for multiline if many, or single line if few.
    if len(args) > 2 or "properties=" in args[-1] or "items=" in args[-1]:
        return f"genai.types.Schema(\n{next_indent}" + f",\n{next_indent}".join(args) + f"\n{current_indent})"
    else:
        return f"genai.types.Schema({', '.join(args)})"

def dict_to_pretty_code(d: Dict[str, Any], indent_level: int = 1, sort_keys: bool = False) -> str:
    """Converts a dictionary to a pretty, indented Python code string (for dict literals)."""
    items_str = []
    base_indent = "    " * indent_level
    next_indent = "    " * (indent_level + 1)
    iterable = sorted(d.items()) if sort_keys else d.items()
    for key, value in iterable:
        value_repr = repr(value)
        if isinstance(value, dict):
            value_repr = dict_to_pretty_code(value, indent_level + 1, sort_keys)
        elif isinstance(value, list):
            # Basic list representation, can be enhanced for nested lists/dicts
            value_repr = repr(value) 
        items_str.append(f"\n{next_indent}{repr(key)}: {value_repr},")
    if not items_str:
        return "{}"
    return f"{{\n{base_indent}{''.join(items_str).strip(',')}\n{base_indent}}}"

def reconstruct_tools_code_string(run_settings: Dict[str, Any], tools_info: Optional[list]) -> str:
    tool_code_objects = []
    if tools_info:
        for tool in tools_info:
            if tool.get("type") == "function_declaration":
                functions = tool.get("functions", [])
                func_decl_codes = []
                for func in functions:
                    name = func.get("name", "")
                    description = func.get("description", "")
                    parameters_schema_dict = func.get("parameters_schema", {})
                    params_code = schema_dict_to_python_code(parameters_schema_dict, current_indent="            ")
                    func_decl_codes.append(
                        f"genai.types.FunctionDeclaration(\n"
                        f"                name={repr(name)},\n"
                        f"                description={repr(description)},\n"
                        f"                parameters={params_code}\n"
                        f"            )"
                    )
                if func_decl_codes:
                    tool_code_objects.append(f"genai.types.Tool(function_declarations=[{', '.join(func_decl_codes)}])")
            elif tool.get("type") == "code_execution":
                tool_code_objects.append("genai.types.Tool(code_execution=genai.types.CodeExecution())")
            elif tool.get("type") == "google_search_enabled":
                tool_code_objects.append("genai.types.Tool(google_search=genai.types.GoogleSearch())")
            elif tool.get("type") == "browse_enabled":
                tool_code_objects.append("genai.types.Tool(url_context=genai.types.UrlContext())")
    if not tool_code_objects:
        return "None"
    return f"[{', '.join(tool_code_objects)}]"

def reconstruct_contents_code_string(dialogue_history: List[Dict[str, Any]]) -> str:
    """
    Reconstructs the 'contents' list for the history part of the genai.ChatSession or model.generate_content call.
    Handles various part types including text, thoughts, function calls/responses, and code execution.
    """
    history_entries = []
    for turn in dialogue_history:
        role = turn.get("role")
        parts_data = turn.get("parts", [])
        
        if not parts_data:
            continue

        part_code_strings = []
        for part in parts_data:
            part_type = part.get("type")
            if part_type == "text_response" or part_type == "thoughts" or (role == "user" and part_type == "text"):
                # Thoughts are not directly part of genai.Content history in the same way,
                # but if they were stored as simple text from the user's perspective of what model generated,
                # they are treated like text here.
                # For model, 'text_response' is the primary textual output.
                # For user, simple 'text' is used.
                content = part.get("content", "")
                part_code_strings.append(f"genai.types.Part(text={repr(content)})")
            elif part_type == "function_call":
                name = part.get("name")
                args = part.get("args", {}) # args should be a dict
                if name: # Ensure name is present
                    # Args are passed directly as a dictionary
                    part_code_strings.append(f"genai.types.Part.from_function_call(name={repr(name)}, args={args})")
            elif part_type == "function_response":
                name = part.get("name")
                response_content = part.get("response_content", {}) # response_content should be a dict
                if name: # Ensure name is present
                    # response is passed directly as a dictionary
                    part_code_strings.append(f"genai.types.Part.from_function_response(name={repr(name)}, response={response_content})")
            elif part_type == "executable_code":
                code = part.get("code_content", "")
                # language = part.get("language", "PYTHON") # language is not a direct param of ExecutableCode part
                part_code_strings.append(f"genai.types.Part(executable_code=genai.types.ExecutableCode(code={repr(code)}))")
            elif part_type == "code_execution_result":
                output = part.get("output_content", "")
                outcome_str = part.get("outcome", "OUTCOME_OK").upper() # from parser
                py_outcome_const = CODE_EXEC_OUTCOME_MAP.get(outcome_str, "genai.types.CodeExecutionResult.Outcome.OK")
                part_code_strings.append(
                    f"genai.types.Part(code_execution_result=genai.types.CodeExecutionResult(outcome={py_outcome_const}, output={repr(output)}))"
                )
            # Add other part types like multimodal if they become part of 'contents' reconstruction
            # For now, focusing on text, tools, and code execution as per typical chat history.

        if part_code_strings:
            parts_joined = f",\n            ".join(part_code_strings)
            history_entries.append(
                f"    genai.types.Content(\n"
                f"        parts=[\\n            {parts_joined}\\n        ],\\n"
                f"        role='{role}\\n"
                f"    )"
            )
            
    if not history_entries:
        return "[]" # Empty history list
    
    return f"[\n" + ",\n".join(history_entries) + "\n]"

def generate_python_chat_code(
    template_path: str,
    timestamp_str: str,
    source_file_name_str: str,
    model_name_repr: str,
    generation_config_code_str: str, 
    system_instruction_repr: str,
    history_code_str: str,
    response_mime_type_repr: str,
    response_schema_code_str: Optional[str],
    tools_code_str: Optional[str], # Added tools_code_str
    tool_config_code_str: Optional[str] = "None" # Retained tool_config_code_str for now
) -> str:
    """Generates the Python script content from the template and provided data."""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
    except FileNotFoundError:
        return f"Error: Template file not found at {template_path}"

    response_schema_entry_str = ""
    if response_mime_type_repr == repr("application/json") and response_schema_code_str and response_schema_code_str != "None":
        response_schema_entry_str = f",\n    response_schema={response_schema_code_str}"
        
    generation_config_code_str = generation_config_code_str if generation_config_code_str else "None"
    # Ensure tools_code_str defaults to the string "None" if it's None or empty for template replacement purity
    processed_tools_code_str = tools_code_str if tools_code_str and tools_code_str.strip() and tools_code_str.lower() != "none" else "None"
    tool_config_code_str = tool_config_code_str if tool_config_code_str else "None"
    system_instruction_repr = system_instruction_repr if system_instruction_repr else "None"
    model_name_repr = model_name_repr if model_name_repr else "None"
    response_mime_type_repr = response_mime_type_repr if response_mime_type_repr else "None"

    replacements = {
        "timestamp": timestamp_str,
        "source_file_name": source_file_name_str,
        "model_name_repr": model_name_repr,
        "generation_config_code_str": generation_config_code_str,
        "system_instruction_repr": system_instruction_repr,
        "history_code_str": history_code_str, # This will be from reconstruct_contents_code_string
        "response_mime_type_repr": response_mime_type_repr,
        "response_schema_entry_str": response_schema_entry_str, # For GenerationConfig
        # Use processed_tools_code_str for the 'tools' parameter of GenerativeModel
        "tools_code_str": processed_tools_code_str, 
        # tool_config_code_str is for the 'tool_config' parameter of GenerativeModel (if needed)
        "tool_config_code_str": tool_config_code_str 
    }

    # print(f"[DEBUG generate_python_chat_code] Replacements prepared: {list(replacements.keys())}")
    # print(f"[DEBUG generate_python_chat_code] tools_code_str to be used: {processed_tools_code_str}")

    generated_code = template_content
    for placeholder, value in replacements.items():
        generated_code = generated_code.replace(f"{{{placeholder}}}", str(value))

    return generated_code

def main_reconstruct(intermediate_json_path: str, output_py_file: str, template_path: str):
    """Главная функция: загружает промежуточный JSON и генерирует Python-скрипт."""
    print("\n🚀 Запуск reconstructor_v2.py 🚀")
    print(f"ℹ️  Входной JSON: {intermediate_json_path}")
    print(f"ℹ️  Шаблон: {template_path}")
    print("----------------------------------------------------")
    try:
        print("⚙️  Загрузка промежуточного JSON...", end=" ")
        with open(intermediate_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("✔️")

        print("⚙️  Воссоздание списка contents...", end=" ")
        dialogue_history = data.get("dialogue_history", [])
        history_code_str = reconstruct_contents_code_string(dialogue_history)
        print("✔️")

        print("⚙️  Воссоздание конфигурации инструментов (tools)...", end=" ")
        run_settings = data.get("run_settings", {})
        tools_info = run_settings.get("tools_info")
        tools_code_str = reconstruct_tools_code_string(run_settings, tools_info)
        print("✔️")

        print("⚙️  Воссоздание схемы ответа (response_schema)...", end=" ")
        response_schema_dict = run_settings.get("response_schema_configured")
        response_schema_code_str = "None"
        if isinstance(response_schema_dict, dict) and response_schema_dict:
            response_schema_code_str = schema_dict_to_python_code(response_schema_dict, current_indent="    ")
        print("✔️")

        print("🐍 Генерация Python-кода по шаблону...", end=" ")
        source_file_name = data.get("source_file_name", "Unknown Source File")
        parsed_at_timestamp = data.get("parsed_at_timestamp", datetime.datetime.utcnow().isoformat() + "Z")
        system_instruction = data.get("system_instruction", "")
        model_name_repr = repr(run_settings.get("model"))
        response_mime_type_repr = repr(run_settings.get("responseMimeType"))
        gen_config_args = []
        if "temperature" in run_settings: gen_config_args.append(f"temperature={run_settings['temperature']}")
        if "topP" in run_settings: gen_config_args.append(f"top_p={run_settings['topP']}")
        if "topK" in run_settings: gen_config_args.append(f"top_k={run_settings['topK']}")
        if "maxOutputTokens" in run_settings: gen_config_args.append(f"max_output_tokens={run_settings['maxOutputTokens']}")
        generation_config_code_str = f"genai.types.GenerationConfig({', '.join(gen_config_args)})" if gen_config_args else "None"
        system_instruction_repr = repr(system_instruction)
        output_code = generate_python_chat_code(
            template_path=template_path,
            timestamp_str=parsed_at_timestamp,
            source_file_name_str=source_file_name,
            model_name_repr=model_name_repr,
            generation_config_code_str=generation_config_code_str,
            system_instruction_repr=system_instruction_repr,
            history_code_str=history_code_str,
            response_mime_type_repr=response_mime_type_repr,
            response_schema_code_str=response_schema_code_str,
            tools_code_str=tools_code_str,
            tool_config_code_str="None"
        )
        print("✔️")

        print(f"💾 Сохранение Python-файла в: {output_py_file}...", end=" ")
        os.makedirs(os.path.dirname(output_py_file), exist_ok=True)
        with open(output_py_file, 'w', encoding='utf-8') as f:
            f.write(output_code)
        print("✔️")
        print("----------------------------------------------------")
        print("✨ Реконструкция Python-кода успешно завершена! ✨")
        print(f"   Выходной файл: {output_py_file}\n")
    except Exception as e:
        print("❌ Произошла ошибка при реконструкции!")
        print(e)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconstruct Python chat script from intermediate JSON.")
    parser.add_argument("--input_json", required=True, help="Path to the intermediate JSON file (output of parser_v2.py).")
    parser.add_argument("--output_py", required=True, help="Path to save the reconstructed Python script.")
    parser.add_argument("--template_path", "-tp", required=True, help="Path to the Python template file (.tpl) to use for code generation.")
    args = parser.parse_args()
    main_reconstruct(args.input_json, args.output_py, args.template_path) 
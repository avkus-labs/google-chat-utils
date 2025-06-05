# -*- coding: utf-8 -*-
"""This script was generated from a Google AI Studio chat export.

Timestamp: {timestamp}
Source File: {source_file_name}
"""

import google.generativeai as genai
from google.generativeai.types import content_types, GenerateContentResponse
import base64
import os

# --- API Key Configuration ---
# IMPORTANT: Set your API_KEY here or via the GOOGLE_API_KEY environment variable.
# genai.configure(api_key="YOUR_API_KEY")

# --- Model Configuration ---
MODEL_NAME = {model_name_repr}

# --- Generation Configuration ---
# These settings were extracted from the AI Studio session.
generation_config = {generation_config_code_str}

# --- Safety Settings ---
# safety_settings = [] # Add safety settings if needed, e.g., generation_config.safety_settings

# --- Tools Configuration (if any) ---
# Define your tools here if they were used in the session.
# Example:
# my_tool = genai.protos.Tool(
#     function_declarations=[
#         genai.protos.FunctionDeclaration(
#             name='my_function_name',
#             description='My function description.',
#             parameters=genai.protos.Schema(
#                 type=genai.protos.Type.OBJECT,
#                 properties={
#                     'param1': genai.protos.Schema(type=genai.protos.Type.STRING, description='Description for param1')
#                 },
#                 required=['param1']
#             )
#         )
#     ]
# )
# tools = [my_tool]
tools = {tools_code_str} # Will be None or list of tools

# --- Tool Configuration (if any) ---
# tool_config = {{ "function_calling_config": {{"mode": "ANY"}} }} # Example
tool_config = {tool_config_code_str} # Will be None or a dict

# --- System Instruction ---
# _DEFAULT_SYSTEM_INSTRUCTION_TEXT формируется напрямую из промежуточного JSON
_DEFAULT_SYSTEM_INSTRUCTION_TEXT = {system_instruction_repr}
_effective_si_text = None

# Механизм поиска .si-файла
try:
    import sys
    _script_path = os.path.abspath(sys.argv[0])
    _script_dir = os.path.dirname(_script_path)
    _script_base = os.path.splitext(os.path.basename(_script_path))[0]
    _si_filename = _script_base + ".si"
    _si_path_1 = os.path.join(_script_dir, _si_filename)
    _si_path_2 = os.path.abspath(os.path.join(_script_dir, "..", "input_data", "{source_file_name}".rsplit(".", 1)[0] + ".si"))
    if os.path.isfile(_si_path_1):
        with open(_si_path_1, "r", encoding="utf-8") as f:
            _effective_si_text = f.read()
        print(f"[INFO] Используется системная инструкция из файла: {_si_path_1}")
    elif os.path.isfile(_si_path_2):
        with open(_si_path_2, "r", encoding="utf-8") as f:
            _effective_si_text = f.read()
        print(f"[INFO] Используется системная инструкция из файла: {_si_path_2}")
    else:
        _effective_si_text = _DEFAULT_SYSTEM_INSTRUCTION_TEXT
except Exception as _si_exc:
    print(f"[WARNING] Ошибка при поиске/чтении .si-файла: {_si_exc}. Используется инструкция из JSON.")
    _effective_si_text = _DEFAULT_SYSTEM_INSTRUCTION_TEXT

# Преобразуем строку в Part только если не пусто и не None
system_instruction_for_api = None
if _effective_si_text and _effective_si_text != "None":
    # Убираем кавычки, если они есть (например, если строка пришла как 'text')
    _si_val = _effective_si_text
    if (_si_val.startswith("'") and _si_val.endswith("'")) or (_si_val.startswith('"') and _si_val.endswith('"')):
        _si_val = _si_val[1:-1]
    _si_val = _si_val.strip()
    if _si_val:
        system_instruction_for_api = [content_types.Part.from_text(text=_si_val)]

# --- Combined Generation Setup for send_message ---
generate_content_settings = {{
    "generation_config": generation_config,
    # "safety_settings": safety_settings, # Uncomment and define if used
    "tools": tools,
    "tool_config": tool_config,
    "system_instruction": system_instruction_for_api, # Use the processed Content object or None
    "response_mime_type": {response_mime_type_repr}{response_schema_entry_str} # response_schema_entry_str includes comma if schema is present
}}

# Filter out None values from the settings dictionary passed to send_message
final_send_message_settings = {{k: v for k, v in generate_content_settings.items() if v is not None}}

# --- Chat History ---
# History reconstructed from the AI Studio session.
history = {history_code_str}

def run_chat(model_name: str, chat_history: list, send_message_settings: dict):
    """Initializes and runs the chat session."""
    print(f"Initializing model: {{model_name}}")
    model = genai.GenerativeModel(
        model_name
        # System instruction is passed via send_message_settings if defined there
        # Tools are also passed via send_message_settings
    )
    chat = model.start_chat(history=chat_history)
    print("Chat session started. Type 'exit' or 'quit' to end.")

    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ['exit', 'quit']:
                print("Exiting chat.")
                break
            if not user_input:
                continue

            print("Gemini: Thinking...")
            # Use final_send_message_settings which has None values filtered out
            response = chat.send_message(user_input, **send_message_settings)
            
            # Process and print response parts
            all_text_parts = []
            function_calls_found = []
            executable_codes_found = []

            for part in response.parts: # response.parts is available on GenerateContentResponse
                if part.text:
                    all_text_parts.append(part.text)
                
                if hasattr(part, 'function_call') and part.function_call:
                    fc = part.function_call
                    function_calls_found.append(fc) # Store for later summary if needed
                    print(f"\n>> Function Call Request: {{fc.name}}")
                    print(f"   Arguments: {{fc.args}}")
                    print(f"   (To respond, call your function and then use: chat.send_message(content_types.Part.from_function_response(name='{fc.name}', response={{...}}))) ")
                
                if hasattr(part, 'executable_code') and part.executable_code:
                    ec = part.executable_code
                    executable_codes_found.append(ec)
                    print(f"\n>> Executable Code Provided by Model:")
                    print("```python")
                    print(ec.code)
                    print("```")
                    print(f"   (To respond with execution result, use: chat.send_message(content_types.Part.from_code_execution_result(output='...')))")

            if all_text_parts:
                print("Gemini:", "".join(all_text_parts))
            
            # If no text was printed, but tools were called, this indicates a tool-only turn clearly.
            # If nothing at all was found (no text, no fc, no ec), then print a generic no content message.
            if not all_text_parts and not function_calls_found and not executable_codes_found:
                print("Gemini: (No text, function call, or executable code in response)")

        except Exception as e:
            print(f"Error during chat: {{e}}")
            # break # Optionally break on error

if __name__ == '__main__':
    # Configure API key if not set via environment variable
    # import os
    # if not os.getenv('GOOGLE_API_KEY'):
    #     genai.configure(api_key="YOUR_API_KEY_HERE") # Prompt user or hardcode carefully
    #     if not os.getenv('GOOGLE_API_KEY') and not genai.API_KEY:
    #          print("Please set your GOOGLE_API_KEY environment variable or configure it in the script.")
    #          exit()

    run_chat(
        model_name=MODEL_NAME, 
        chat_history=history, 
        send_message_settings=final_send_message_settings
    ) 
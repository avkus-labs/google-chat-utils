# -*- coding: utf-8 -*-
"""Этот скрипт сгенерирован из Google AI Studio.

Timestamp: {timestamp}
Source File: {source_file_name}
"""

# To run this code you need to install the following dependencies:
# pip install google-genai

import base64
import os
from google import genai
from google.genai import types

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
# Системная инструкция только из промежуточного JSON
system_instruction_for_api = None
_si_val = {system_instruction_repr}
if _si_val and _si_val != "None":
    # Убираем кавычки, если они есть (например, если строка пришла как 'text')
    if (_si_val.startswith("'") and _si_val.endswith("'")) or (_si_val.startswith('"') and _si_val.endswith('"')):
        _si_val = _si_val[1:-1]
    _si_val = _si_val.strip()
    if _si_val:
        system_instruction_for_api = [types.Content.from_text(text=_si_val)]

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

def generate():
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    model = {model_name_repr}
    contents = {contents_code_str}
    tools = {tools_code_str}
    system_instruction = {system_instruction_repr}
    generation_config = {generation_config_code_str}
    response_mime_type = {response_mime_type_repr}
    response_schema = {response_schema_code_str}

    config_params = {{}}
    if generation_config is not None and generation_config != "None":
        config_params['generation_config'] = generation_config
    if tools is not None and tools != "None":
        config_params['tools'] = tools
    if system_instruction is not None and system_instruction != "None":
        config_params['system_instruction'] = system_instruction
    if response_mime_type is not None and response_mime_type != "None":
        config_params['response_mime_type'] = response_mime_type
    if response_schema is not None and response_schema != "None" and response_mime_type == 'application/json':
        config_params['response_schema'] = response_schema

    generate_content_config = types.GenerateContentConfig(**config_params)

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        # Логика вывода максимально похожа на Studio
        if hasattr(chunk, 'text') and chunk.text:
            print(chunk.text, end="")
        if hasattr(chunk, 'function_calls') and chunk.function_calls:
            for fc in chunk.function_calls:
                print(f"\nFunction call: {{fc.name}}({fc.args})")
        if hasattr(chunk, 'executable_code') and chunk.executable_code:
            print(f"\n[Executable code]: {chunk.executable_code}")
        if hasattr(chunk, 'code_execution_result') and chunk.code_execution_result:
            print(f"\n[Code execution result]: {chunk.code_execution_result}")

if __name__ == "__main__":
    generate() 
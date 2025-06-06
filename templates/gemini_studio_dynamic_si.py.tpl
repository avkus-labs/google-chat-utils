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

def generate():
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    model = {model_name_repr}
    contents = {contents_code_str}
    tools = {tools_code_str}
    system_instruction = {system_instruction_code_str}
generation_config = {generation_config_code_str}
    response_mime_type = {response_mime_type_code_str}
    response_schema = {response_schema_code_str}

    config_params = {}
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
                print(f"\nFunction call: {fc.name}({fc.args})")
        if hasattr(chunk, 'executable_code') and chunk.executable_code:
            print(f"\n[Executable code]: {chunk.executable_code}")
        if hasattr(chunk, 'code_execution_result') and chunk.code_execution_result:
            print(f"\n[Code execution result]: {chunk.code_execution_result}")

if __name__ == "__main__":
    generate() 
# -*- coding: utf-8 -*-
"""Этот скрипт сгенерирован из Google AI Studio.

Timestamp: 2025-06-08T22:53:29.110937Z
Source File: Example_overridden.json
"""

# To run this code you need to install the following dependencies:
# pip install google-genai

import base64
import os
from google import genai
from google.genai import types

def generate():
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    model = 'gemini-pro'
    contents = [
    types.Content(
        parts=[
                types.Part.from_text(text='Это первое пользовательское сообщение, добавленное через override.')
        ],
        role='user'
    ),
    types.Content(
        parts=[
                types.Part.from_function_call(name='someFunction', args={"Boolean": false, "Integer": 26.0, "String": "Hi"}),
                types.Part.from_function_response(name='someFunction', response={"String_output": "Это строка, сгенерированная someFunction", "Number_output": 10.5, "Integer_output": 100, "Boolean_output": false, "Object_output": {"String": "Вложенная строка ответа", "Number": 20.2, "Integer": 200, "Bollean": true}, "Enum_output": "value_1"})
        ],
        role='model'
    ),
    types.Content(
        parts=[
                types.Part.from_text(text='Я вызвал функцию `someFunction` со следующими параметрами: строка "Hi", число 26 и логическое значение "ложь". Вот ответ от функции:\n```json\n{"someFunction_response": {"Boolean_output": False, "Enum_output": "value_1", "Integer_output": 100, "Number_output": 10.5, "Object_output": {"Bollean": True, "Integer": 200, "Number": 20.2, "String": "Вложенная строка ответа"}, "String_output": "Это строка, сгенерированная someFunction"}}\n```')
        ],
        role='model'
    ),
    types.Content(
        parts=[
                types.Part.from_text(text='Тест Grounding with  Google Search.  Gemini, ответ просто "Ok"')
        ],
        role='user'
    ),
    types.Content(
        parts=[
                types.Part.from_text(text='Ok.')
        ],
        role='model'
    ),
    types.Content(
        parts=[
                types.Part.from_text(text='Тест Structured output.  Gemini, ответ просто "Ok"')
        ],
        role='user'
    ),
    types.Content(
        parts=[
                types.Part.from_text(text='{"String": "Ok"}')
        ],
        role='model'
    )
]
    tools = None
    system_instruction = [types.Part.from_text(text="""Новая системная инструкция для теста с оверрайдом.""")]
generation_config = types.GenerationConfig(
        temperature=1.0,
        top_p=0.95,
        top_k=64,
        max_output_tokens=65536,
        response_mime_type='text/plain'
    )
    response_mime_type = 'text/plain'
    response_schema = None

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
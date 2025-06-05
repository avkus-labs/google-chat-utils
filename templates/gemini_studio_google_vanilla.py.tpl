# To run this code you need to install the following dependencies:
# pip install google-genai

import base64
import os
from google import genai
from google.genai import types

def generate():
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = {model_name_repr}
    contents = {history_code_str}
    tools = {tools_code_str}
    system_instruction = [
        types.Part.from_text(text={system_instruction_repr}),
    ]
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type={response_mime_type_repr},
        tools=tools,
        generation_config={generation_config_code_str},
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config,
    ):
        print(chunk.text, end="")

if __name__ == "__main__":
    generate() 
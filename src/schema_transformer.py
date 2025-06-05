import google.generativeai.types as genai_types
from typing import Any, Dict, List, Union
import json

def openai_to_gemini_schema_code(openai_schema: dict, base_indent: str = "    ", _level: int = 1) -> str:
    """
    Рекурсивно преобразует словарь openai_schema (JSON Schema в стиле OpenAI)
    в строку Python-кода, создающую объект genai_types.Schema для Gemini API.
    """
    type_mapping = {
        "object": "genai_types.Type.OBJECT",
        "string": "genai_types.Type.STRING",
        "number": "genai_types.Type.NUMBER",
        "integer": "genai_types.Type.INTEGER",
        "boolean": "genai_types.Type.BOOLEAN",
        "array": "genai_types.Type.ARRAY",
    }

    indent = base_indent * _level
    next_indent = base_indent * (_level + 1)
    args = []

    # Обработка nullable (OpenAI 3.1+)
    nullable = False
    schema_type = openai_schema.get("type")
    if isinstance(schema_type, list):
        if "null" in schema_type:
            nullable = True
            schema_type = [t for t in schema_type if t != "null"]
            schema_type = schema_type[0] if schema_type else "string"
        else:
            schema_type = schema_type[0]
    if schema_type is None:
        schema_type = "object"  # fallback

    # type
    args.append(f"type={type_mapping.get(schema_type, repr(schema_type))}")

    # description
    if "description" in openai_schema:
        desc = openai_schema["description"].replace('"', '\"')
        args.append(f'description="{desc}"')

    # enum
    if "enum" in openai_schema:
        args.append(f"enum={json.dumps(openai_schema['enum'], ensure_ascii=False)}")

    # required
    if "required" in openai_schema:
        args.append(f"required={json.dumps(openai_schema['required'], ensure_ascii=False)}")

    # nullable
    if nullable:
        args.append("nullable=True")

    # properties (object)
    if schema_type == "object" and "properties" in openai_schema:
        props = openai_schema["properties"]
        prop_lines = []
        for k, v in props.items():
            code = openai_to_gemini_schema_code(v, base_indent, _level + 2)
            prop_lines.append(f'{next_indent}"{k}": {code}')
        props_code = "{\n" + ",\n".join(prop_lines) + f"\n{indent}}}"
        args.append(f"properties={props_code}")

    # items (array)
    if schema_type == "array" and "items" in openai_schema:
        items_code = openai_to_gemini_schema_code(openai_schema["items"], base_indent, _level + 1)
        args.append(f"items={items_code}")

    # Собираем итоговую строку
    code = f"genai_types.Schema(\n{indent}" + f",\n{indent}".join(args) + ")"
    return code


def gemini_schema_to_openai_json(gemini_schema_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Рекурсивно преобразует словарь gemini_schema_dict (схема Gemini с типами в верхнем регистре)
    в JSON Schema в стиле OpenAI.
    """
    type_mapping = {
        "OBJECT": "object",
        "STRING": "string",
        "NUMBER": "number",
        "INTEGER": "integer",
        "BOOLEAN": "boolean",
        "ARRAY": "array",
    }
    result = {}
    gemini_type = gemini_schema_dict.get("type")
    openai_type = type_mapping.get(gemini_type, gemini_type.lower() if isinstance(gemini_type, str) else gemini_type)
    nullable = gemini_schema_dict.get("nullable", False)

    # nullable: если тип не object/array, то type -> [type, "null"]
    if nullable and openai_type not in ("object", "array"):
        result["type"] = [openai_type, "null"]
    else:
        result["type"] = openai_type

    # description
    if "description" in gemini_schema_dict:
        result["description"] = gemini_schema_dict["description"]

    # enum
    if "enum" in gemini_schema_dict:
        result["enum"] = gemini_schema_dict["enum"]

    # required
    if "required" in gemini_schema_dict:
        result["required"] = gemini_schema_dict["required"]

    # properties (object)
    if openai_type == "object" and "properties" in gemini_schema_dict:
        result["properties"] = {}
        for k, v in gemini_schema_dict["properties"].items():
            result["properties"][k] = gemini_schema_to_openai_json(v)

    # items (array)
    if openai_type == "array" and "items" in gemini_schema_dict:
        result["items"] = gemini_schema_to_openai_json(gemini_schema_dict["items"])

    return result


if __name__ == "__main__":
    # Пример 1: простой объект
    openai_schema1 = {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "The city and state, e.g. San Francisco, CA"},
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
        },
        "required": ["location"]
    }
    print("Пример 1:\n" + openai_to_gemini_schema_code(openai_schema1))

    # Пример 2: вложенные объекты и массивы
    openai_schema2 = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer", "description": "Возраст пользователя"}
                },
                "required": ["name"]
            },
            "scores": {
                "type": "array",
                "items": {"type": "number"}
            },
            "active": {"type": ["boolean", "null"]}
        },
        "required": ["user", "scores"]
    }
    print("\nПример 2:\n" + openai_to_gemini_schema_code(openai_schema2))

    import copy
    import pprint

    # Gemini-стиль словаря для openai_schema1
    gemini_schema1 = {
        "type": "OBJECT",
        "properties": {
            "location": {"type": "STRING", "description": "The city and state, e.g. San Francisco, CA"},
            "unit": {"type": "STRING", "enum": ["celsius", "fahrenheit"]}
        },
        "required": ["location"]
    }
    # Gemini-стиль словаря для openai_schema2
    gemini_schema2 = {
        "type": "OBJECT",
        "properties": {
            "user": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "age": {"type": "INTEGER", "description": "Возраст пользователя"}
                },
                "required": ["name"]
            },
            "scores": {
                "type": "ARRAY",
                "items": {"type": "NUMBER"}
            },
            "active": {"type": "BOOLEAN", "nullable": True}
        },
        "required": ["user", "scores"]
    }
    print("\nОбратное преобразование Gemini -> OpenAI (пример 1):")
    pprint.pprint(gemini_schema_to_openai_json(gemini_schema1))
    print("\nОжидается:")
    pprint.pprint(openai_schema1)

    print("\nОбратное преобразование Gemini -> OpenAI (пример 2):")
    pprint.pprint(gemini_schema_to_openai_json(gemini_schema2))
    print("\nОжидается:")
    pprint.pprint(openai_schema2) 
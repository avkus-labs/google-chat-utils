import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.transformation.schema_transformer import SchemaTransformer
from utils.core.schema_elements import SchemaData


def test_openai_to_gemini_transformation():
    transformer = SchemaTransformer()
    with open('data/example_openai_schema.json', encoding='utf-8') as f:
        openai_schema = json.load(f)

    gemini_obj = transformer.openai_to_gemini_schema(openai_schema)
    assert isinstance(gemini_obj, SchemaData)
    assert gemini_obj.type == 'OBJECT'
    assert 'orderId' in gemini_obj.properties
    assert gemini_obj.properties['orderId'].type == 'STRING'


def test_gemini_to_openai_transformation():
    transformer = SchemaTransformer()
    with open('data/example_gemini_schema.json', encoding='utf-8') as f:
        gemini_dict = json.load(f)

    gemini_obj = SchemaData.from_dict(gemini_dict)
    openai_dict = transformer.gemini_schema_to_openai_dict(gemini_obj)
    assert openai_dict.get('type') == 'object'
    assert 'properties' in openai_dict
    assert 'orderId' in openai_dict['properties']
    assert openai_dict['properties']['orderId']['type'] == 'string'


def test_gemini_to_python_code():
    transformer = SchemaTransformer()
    with open('data/example_gemini_schema.json', encoding='utf-8') as f:
        gemini_dict = json.load(f)

    gemini_obj = SchemaData.from_dict(gemini_dict)
    code = transformer.gemini_schema_obj_to_python_code(gemini_obj)
    assert 'genai.types.Schema' in code
    assert 'genai.types.Type.OBJECT' in code

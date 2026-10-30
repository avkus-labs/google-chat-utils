import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.parsing.google_studio_parser import GoogleAIStudioJSONParser
from utils.reconstruction.gemini_code_reconstructor import GeminiAPICodeReconstructor


def test_reconstruct_vanilla_python_code():
    parser = GoogleAIStudioJSONParser()
    intermediate = parser.parse('data/Example')
    assert intermediate is not None
    intermediate.run_settings.model = 'gemini-2.5-flash'

    reconstructor = GeminiAPICodeReconstructor(template_dir='templates')
    code = reconstructor.reconstruct(
        intermediate_data=intermediate,
        template_name='gemini_studio_vanilla.py.tpl',
        api_key_var_name='MY_API_KEY'
    )
    assert 'from google import genai' in code
    assert 'MODEL_NAME = ' in code
    assert 'client = genai.Client' in code
    assert 'gemini-2.5-flash' in code


def test_reconstruct_dynamic_si_code():
    parser = GoogleAIStudioJSONParser()
    intermediate = parser.parse('data/Example')
    assert intermediate is not None
    intermediate.run_settings.model = 'gemini-2.5-pro'

    reconstructor = GeminiAPICodeReconstructor(template_dir='templates')
    code = reconstructor.reconstruct(
        intermediate_data=intermediate,
        template_name='gemini_studio_dynamic_si.py.tpl',
        api_key_var_name='MY_API_KEY'
    )
    assert 'from google import genai' in code
    assert 'def generate():' in code
    assert 'client.models.generate_content_stream' in code
    assert 'gemini-2.5-pro' in code

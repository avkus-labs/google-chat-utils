import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
from utils.reconstruction.gemini_code_reconstructor import GeminiAPICodeReconstructor
from utils.core.chat_elements import IntermediateChatData

def test_reconstruct_python_code():
    with open('output_data/Example6_intermediate.json', encoding='utf-8') as f:
        data = json.load(f)
    intermediate = IntermediateChatData.from_dict(data)
    reconstructor = GeminiAPICodeReconstructor(template_dir='utils/templates')
    code = reconstructor.reconstruct(intermediate, 'gemini_studio_default.py.tpl')
    assert 'def generate(' in code 
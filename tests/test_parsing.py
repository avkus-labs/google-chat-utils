import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.parsing.google_studio_parser import GoogleAIStudioJSONParser

def test_parse_example1():
    parser = GoogleAIStudioJSONParser()
    data = parser.parse('data/Example1')
    assert data is not None
    assert hasattr(data, 'dialogue_history')
    assert len(data.dialogue_history) > 0

def test_parse_with_si_fi():
    parser = GoogleAIStudioJSONParser()
    data = parser.parse('data/Example6')
    with open('data/Example6.si', encoding='utf-8') as f:
        si = f.read().strip()
    with open('data/Example6.fi', encoding='utf-8') as f:
        fi = f.read().strip()
    assert data.system_instruction.text == si
    assert data.dialogue_history[0].parts[0].content == fi 
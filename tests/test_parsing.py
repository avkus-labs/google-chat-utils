import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.parsing.google_studio_parser import GoogleAIStudioJSONParser


def test_parse_example():
    parser = GoogleAIStudioJSONParser()
    data = parser.parse('data/Example')
    assert data is not None
    assert hasattr(data, 'dialogue_history')
    assert len(data.dialogue_history) > 0
    assert data.system_instruction is not None
    assert data.system_instruction.text == "Системная инструкция"


def test_parse_dialogue_turns():
    parser = GoogleAIStudioJSONParser()
    data = parser.parse('data/Example')
    assert data is not None
    first_turn = data.dialogue_history[0]
    assert first_turn.role == 'user'
    assert len(first_turn.parts) > 0


def test_markdown_generation():
    parser = GoogleAIStudioJSONParser()
    data = parser.parse('data/Example')
    assert data is not None

    raw_rag = parser.to_markdown(data)
    assert "<system_instruction>" in raw_rag
    assert "role='user'" in raw_rag

    human_md = parser.to_human_markdown(data)
    assert "### System Instruction" in human_md
    assert "### **User**" in human_md

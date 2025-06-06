import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
from utils.reconstruction.studio_json_reconstructor import GoogleAIStudioJSONReconstructor
from utils.core.chat_elements import IntermediateChatData

def test_reconstruct_studio_json():
    with open('output_data/Example6_intermediate.json', encoding='utf-8') as f:
        data = json.load(f)
    intermediate = IntermediateChatData.from_dict(data)
    reconstructor = GoogleAIStudioJSONReconstructor()
    studio_json = reconstructor.reconstruct_studio_json(intermediate)
    assert 'runSettings' in studio_json
    assert 'chunkedPrompt' in studio_json
    assert 'chunks' in studio_json['chunkedPrompt'] 
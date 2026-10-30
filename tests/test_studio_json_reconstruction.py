import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.studio_json_modifier import apply_overrides


def test_apply_overrides_to_studio_json():
    with open('data/Example', encoding='utf-8') as f:
        raw_json = json.load(f)

    custom_si = "Custom System Instruction Override"
    custom_fi = "Custom First User Message"
    custom_li = "Custom Last User Message"

    modified = apply_overrides(
        raw_json=raw_json,
        si_text=custom_si,
        fi_text=custom_fi,
        li_text=custom_li,
        fi_mode='replace',
        li_mode='append'
    )

    assert modified['systemInstruction']['text'] == custom_si
    history = modified['chunkedPrompt']['chunks']
    assert history[0]['parts'][0]['text'] == custom_fi
    assert history[-1]['parts'][0]['text'] == custom_li

"""
Утилита для применения оверрайдов (.si, .fi, .li) к "сырым" JSON-файлам Google AI Studio.

- Заменяет systemInstruction, первое и/или последнее сообщение пользователя в истории.
- Поддерживает режимы: fi_mode (replace/prepend), li_mode (replace/append).
- Используется как отдельный скрипт или через команду apply_overrides_to_studio_json в cli_v3.py.

Пример:
python utils/studio_json_modifier.py --input_studio_json data/Example --output_studio_json data/Example_overridden.json --si_file data/Example.si --fi_file data/Example.fi --li_file data/Example.li --fi_mode replace --li_mode append
"""
import argparse
import json
from typing import Optional, Dict, Any, List

def load_text_file(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return None

def find_first_user_idx(history: List[Dict[str, Any]]) -> Optional[int]:
    for idx, msg in enumerate(history):
        if msg.get('role') == 'user' or msg.get('author') == 'user':
            return idx
    return None

def find_last_user_idx(history: List[Dict[str, Any]]) -> Optional[int]:
    for idx in range(len(history)-1, -1, -1):
        msg = history[idx]
        if msg.get('role') == 'user' or msg.get('author') == 'user':
            return idx
    return None

def make_user_message(text: str) -> Dict[str, Any]:
    return {
        'author': 'user',
        'role': 'user',
        'parts': [{'text': text}]
    }

def get_history_ref(raw_json: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    if 'chunkedPrompt' in raw_json and 'chunks' in raw_json['chunkedPrompt']:
        return raw_json['chunkedPrompt']['chunks']
    if 'pendingInputs' in raw_json:
        return raw_json['pendingInputs']
    if 'history' in raw_json:
        return raw_json['history']
    return None

def apply_overrides(
    raw_json: Dict[str, Any],
    si_text: Optional[str],
    fi_text: Optional[str],
    li_text: Optional[str],
    fi_mode: str = 'replace',
    li_mode: str = 'replace'
) -> Dict[str, Any]:
    # System instruction
    if si_text is not None:
        if isinstance(raw_json.get('systemInstruction'), dict):
            raw_json['systemInstruction']['text'] = si_text
        else:
            raw_json['systemInstruction'] = {'text': si_text}
    # Dialogue history
    history = get_history_ref(raw_json)
    if history is not None:
        # First user message
        if fi_text is not None:
            user_msg = make_user_message(fi_text)
            if fi_mode == 'replace':
                idx = find_first_user_idx(history)
                if idx is not None:
                    history[idx] = user_msg
                else:
                    history.insert(0, user_msg)
            elif fi_mode == 'prepend':
                history.insert(0, user_msg)
        # Last user message
        if li_text is not None:
            user_msg = make_user_message(li_text)
            if li_mode == 'replace':
                idx = find_last_user_idx(history)
                if idx is not None:
                    history[idx] = user_msg
                else:
                    history.append(user_msg)
            elif li_mode == 'append':
                history.append(user_msg)
    return raw_json

def main():
    parser = argparse.ArgumentParser(description="Apply .si/.fi/.li overrides to Google AI Studio raw JSON.")
    parser.add_argument('--input_studio_json', required=True, help='Path to input raw Studio JSON')
    parser.add_argument('--output_studio_json', required=True, help='Path to output modified Studio JSON')
    parser.add_argument('--si_file', required=False, help='Path to .si file (system instruction)')
    parser.add_argument('--fi_file', required=False, help='Path to .fi file (first user message)')
    parser.add_argument('--li_file', required=False, help='Path to .li file (last user message)')
    parser.add_argument('--fi_mode', choices=['replace', 'prepend'], default='replace', help='Mode for .fi: replace or prepend (default: replace)')
    parser.add_argument('--li_mode', choices=['replace', 'append'], default='replace', help='Mode for .li: replace or append (default: replace)')
    args = parser.parse_args()

    with open(args.input_studio_json, 'r', encoding='utf-8') as f:
        raw_json = json.load(f)
    si_text = load_text_file(args.si_file)
    fi_text = load_text_file(args.fi_file)
    li_text = load_text_file(args.li_file)
    modified = apply_overrides(
        raw_json,
        si_text=si_text,
        fi_text=fi_text,
        li_text=li_text,
        fi_mode=args.fi_mode,
        li_mode=args.li_mode
    )
    with open(args.output_studio_json, 'w', encoding='utf-8') as f:
        json.dump(modified, f, ensure_ascii=False, indent=2)
    print(f"Overrides applied. Output saved to {args.output_studio_json}")

if __name__ == '__main__':
    main() 
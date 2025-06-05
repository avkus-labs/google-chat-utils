import json
import argparse
import datetime
import os
import base64
from typing import List, Dict, Any, Optional, Union
import sys

def load_json_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Reads a JSON-file from the specified path (regardless of its extension).
    Returns the content as a Python dictionary or None if error.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from file {file_path}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading {file_path}: {e}")
        return None

def extract_run_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts run settings from the Google AI Studio JSON data.
    Includes model, temp, topP, topK, maxTokens, mimeType, tool flags,
    responseSchema, and functionDeclarations.
    """
    run_settings_data = data.get('runSettings', {})
    if not isinstance(run_settings_data, dict):
        return {}

    extracted_settings = {}
    fields_to_extract = [
        'model', 'temperature', 'topP', 'topK', 'maxOutputTokens',
        'responseMimeType', 'responseSchema' 
    ]
    # Extract standard fields
    for field in fields_to_extract:
        if field in run_settings_data:
            extracted_settings[field] = run_settings_data[field]
    
    # Handle functionDeclarations specifically to ensure it's present if provided, even empty
    if 'functionDeclarations' in run_settings_data:
        extracted_settings['functionDeclarations'] = run_settings_data['functionDeclarations']

    # Extract boolean tool flags - ensure they are present if explicitly set to False
    tool_flags = ['enableCodeExecution', 'enableSearchAsATool', 'enableBrowseAsATool']
    for flag in tool_flags:
        if flag in run_settings_data:
            extracted_settings[flag] = run_settings_data[flag]
        else:
            extracted_settings[flag] = False

    return extracted_settings

def extract_system_instruction(data: Dict[str, Any]) -> str:
    """Extracts the system instruction text."""
    system_instruction = data.get('systemInstruction', {})
    if isinstance(system_instruction, dict):
        return system_instruction.get('text', '')
    return ''

def parse_part(part_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parses a single part from a chunk into our intermediate format."""
    if not isinstance(part_data, dict):
        return None

    if 'text' in part_data:
        # This could be a simple text. Specific typing like 'thoughts' or 'text_response'
        # will be handled by the caller (extract_dialogue_history_v2) based on chunk properties (e.g., isThought, role).
        return {"type": "text", "content": part_data['text']}
    
    # Multimodal inputs from User (or potentially model in future API versions)
    if 'driveImage' in part_data and isinstance(part_data['driveImage'], dict):
        return {"type": "uri_reference", "source_type": "google_drive_image", "identifier": part_data['driveImage'].get('id')}
    if 'driveDocument' in part_data and isinstance(part_data['driveDocument'], dict):
        return {"type": "uri_reference", "source_type": "google_drive_document", "identifier": part_data['driveDocument'].get('id')}
    if 'sampleImageId' in part_data: # Typically a string ID
        return {"type": "uri_reference", "source_type": "sample_image", "identifier": part_data['sampleImageId']}
    if 'youtubeVideo' in part_data and isinstance(part_data['youtubeVideo'], dict):
        return {"type": "uri_reference", "source_type": "youtube_video", "identifier": part_data['youtubeVideo'].get('id')}
    if 'driveVideo' in part_data and isinstance(part_data['driveVideo'], dict):
        return {"type": "uri_reference", "source_type": "google_drive_video", "identifier": part_data['driveVideo'].get('id')}
    
    # Bytes data (inlineData in Google's format)
    if 'inlineData' in part_data and isinstance(part_data['inlineData'], dict):
        inline_data = part_data['inlineData']
        return {
            "type": "bytes_data", 
            "mime_type": inline_data.get('mimeType'), 
            "base64_data": inline_data.get('data') # Already base64 encoded by AI Studio
        }
    # File data (fileData in Google's format - typically a URI that might point to various sources)
    if 'fileData' in part_data and isinstance(part_data['fileData'], dict):
        file_data = part_data['fileData']
        if 'fileUri' in file_data:
             return {"type": "uri_reference", 
                     "source_type": "file_uri", # Generic file URI
                     "identifier": file_data['fileUri'], 
                     "mime_type": file_data.get('mimeType')}

    # Model response parts (tool related)
    if 'executableCode' in part_data and isinstance(part_data['executableCode'], dict):
        return {"type": "executable_code", "language": "PYTHON", "code_content": part_data['executableCode'].get('code', '')}
    
    if 'codeExecutionResult' in part_data and isinstance(part_data['codeExecutionResult'], dict):
        cer = part_data['codeExecutionResult']
        return {"type": "code_execution_result", "outcome": cer.get('outcome', 'OUTCOME_OK'), "output_content": cer.get('output', '')}

    # Note: 'functionCall' and 'functionResponse' parsing here is for standalone parts that might appear
    # directly in the 'parts' array of a chunk. 
    # 'resolvedFunctionCall' in a chunk (which contains both call and response) 
    # is handled by extract_dialogue_history_v2 directly.
    if 'functionCall' in part_data and isinstance(part_data['functionCall'], dict):
        fc = part_data['functionCall']
        return {"type": "function_call", "name": fc.get('name'), "args": fc.get('args', {})}

    if 'functionResponse' in part_data and isinstance(part_data['functionResponse'], dict):
        fr = part_data['functionResponse']
        # The 'response' field in a standalone functionResponse part (not from resolvedFunctionCall)
        # is typically already a dictionary/object, not a JSON string.
        return {"type": "function_response", "name": fr.get('name'), "response_content": fr.get('response', {})}

    # print(f"Warning: Unknown part structure encountered in parse_part: {part_data}")
    return None # Or consider: {"type": "unknown", "data": part_data}

def extract_tools_info(run_settings: dict) -> list:
    """
    Extracts and formats information about configured tools based on run_settings.
    This includes code execution, function declarations, Google Search, and browsing.
    """
    tools = []
    if run_settings.get('enableCodeExecution'):
        tools.append({'type': 'code_execution'})
    
    # Handle function declarations
    if 'functionDeclarations' in run_settings and run_settings['functionDeclarations']:
        functions_extracted = []
        if isinstance(run_settings['functionDeclarations'], list):
            for f_decl in run_settings['functionDeclarations']:
                if isinstance(f_decl, dict): # Ensure each declaration is a dict
                    functions_extracted.append({
                        'name': f_decl.get('name', ''),
                        'description': f_decl.get('description', ''),
                        'parameters_schema': f_decl.get('parameters', {}) # 'parameters' holds the JSON schema
                    })
        if functions_extracted: # Only add the tool type if there are valid functions
            tools.append({'type': 'function_declaration', 'functions': functions_extracted})

    if run_settings.get('enableSearchAsATool'): 
        tools.append({'type': 'google_search_enabled'})
    if run_settings.get('enableBrowseAsATool'): 
        tools.append({'type': 'browse_enabled'}) 
        
    return tools

def extract_dialogue_history_v2(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extracts and transforms dialogue history, handling multimodal parts,
    code execution, and function calling, including resolvedFunctionCall.
    """
    processed_history: List[Dict[str, Any]] = []
    
    source_chunks = data.get('chunkedPrompt', {}).get('chunks', [])
    if not source_chunks and 'pendingInputs' in data:
        source_chunks = data.get('pendingInputs', []) 
        if not isinstance(source_chunks, list):
            source_chunks = []

    current_model_turn_parts: List[Dict[str, Any]] = []
    current_model_turn_meta: Dict[str, Any] = {}

    def finalize_model_turn():
        nonlocal current_model_turn_parts, current_model_turn_meta
        if current_model_turn_parts:
            turn_to_add: Dict[str, Any] = {"role": "model", "parts": list(current_model_turn_parts)}
            if current_model_turn_meta.get('finish_reason'):
                turn_to_add['finish_reason'] = current_model_turn_meta['finish_reason']
            if current_model_turn_meta.get('token_count'):
                turn_to_add['token_count'] = current_model_turn_meta['token_count']
            if current_model_turn_meta.get('citations'):
                 turn_to_add['citations'] = current_model_turn_meta['citations']
            processed_history.append(turn_to_add)
            current_model_turn_parts.clear()
            current_model_turn_meta.clear()

    for chunk_index, chunk in enumerate(source_chunks):
        if not isinstance(chunk, dict):
            continue

        role = chunk.get('role')
        
        # This list will accumulate parts for the current chunk before deciding role-specific processing
        current_chunk_extracted_parts: List[Dict[str, Any]] = [] 
        
        # Handle resolvedFunctionCall first if present in a model chunk
        # This structure contains both the call and the response from the tool.
        if role == "model" and 'resolvedFunctionCall' in chunk and isinstance(chunk['resolvedFunctionCall'], dict):
            rfc = chunk['resolvedFunctionCall']
            fc_data = rfc.get('functionCall')
            fr_json_string = rfc.get('response') # This is a JSON string

            if isinstance(fc_data, dict) and 'name' in fc_data:
                # Add the function call part
                current_chunk_extracted_parts.append({
                    "type": "function_call",
                    "name": fc_data.get('name'),
                    "args": fc_data.get('args', {})
                })

                # Parse and add the function response part
                if isinstance(fr_json_string, str):
                    try:
                        response_content_dict = json.loads(fr_json_string)
                        current_chunk_extracted_parts.append({
                            "type": "function_response",
                            "name": fc_data.get('name'), # Use the same name as the call
                            "response_content": response_content_dict
                        })
                    except json.JSONDecodeError as e:
                        # print(f"Warning: Could not decode function response JSON in resolvedFunctionCall: {fr_json_string}. Error: {e}")
                        current_chunk_extracted_parts.append({
                            "type": "function_response",
                            "name": fc_data.get('name'),
                            "response_content": {"error": "Failed to parse response JSON", "raw_response": fr_json_string}
                        })
                else:
                    # This case should ideally not happen if 'response' in rFC is always a string.
                    # print(f"Warning: 'response' in resolvedFunctionCall for {fc_data.get('name')} is not a string: {fr_json_string}")
                    current_chunk_extracted_parts.append({
                        "type": "function_response",
                        "name": fc_data.get('name'),
                        "response_content": {"error": "Response was not a JSON string", "raw_response": fr_json_string}
                    })
            # After processing resolvedFunctionCall, we might still have other parts in the 'parts' array
            # of the same chunk, e.g., a thought or a textual summary of the tool interaction.
            # These will be processed by the loop below.

        # Process parts from the 'parts' array of the chunk
        chunk_parts_data_raw = chunk.get('parts', [])
        list_of_part_dicts = []
        if isinstance(chunk_parts_data_raw, list):
            list_of_part_dicts = chunk_parts_data_raw
        elif isinstance(chunk_parts_data_raw, dict):
            list_of_part_dicts = [chunk_parts_data_raw]
        elif 'text' in chunk and not chunk_parts_data_raw: # Simple text directly in chunk (no 'parts' or empty 'parts')
             list_of_part_dicts = [{'text': chunk['text']}]

        for part_dict_from_chunk in list_of_part_dicts:
            if not isinstance(part_dict_from_chunk, dict):
                 continue
            
            parsed_part = parse_part(part_dict_from_chunk)
            if parsed_part:
                # Avoid duplicating function_call or function_response if they were ALREADY processed
                # from a 'resolvedFunctionCall' structure within THIS SAME CHUNK.
                # This check is a bit tricky because parse_part itself creates these types.
                # We rely on the fact that parts from resolvedFunctionCall are added to current_chunk_extracted_parts first.
                # If a part from the 'parts' array is identical to one from resolvedFunctionCall, it would be a duplicate.
                # However, usually, the 'parts' array in a chunk with resolvedFunctionCall might contain thoughts or other related data,
                # not the call/response itself again. If it does, it implies source data redundancy.
                # For now, we add all parsed parts. If duplication becomes an issue, a more sophisticated check is needed.
                current_chunk_extracted_parts.append(parsed_part)
        
        # Fallback: if no parts extracted from 'parts' array or resolvedFunctionCall, but chunk has top-level 'text'.
        if not current_chunk_extracted_parts and 'text' in chunk and not list_of_part_dicts:
            text_part_fallback = parse_part({'text': chunk['text']})
            if text_part_fallback:
                 current_chunk_extracted_parts.append(text_part_fallback)

        # Apply role-specific type adjustments (e.g., 'thoughts', 'text_response') to generic 'text' parts
        is_thought_chunk = chunk.get('isThought', False)
        if role == "model": # This applies to all parts collected for this model chunk
            for p in current_chunk_extracted_parts:
                if p.get('type') == 'text': 
                    p['type'] = 'thoughts' if is_thought_chunk else 'text_response'
        
        # Now, based on role, add to history or current model turn accumulator
        if role == "user":
            finalize_model_turn() 
            if current_chunk_extracted_parts:
                user_turn: Dict[str, Any] = {"role": "user", "parts": current_chunk_extracted_parts}
                if 'tokenCount' in chunk: user_turn['token_count'] = chunk['tokenCount']
                if 'citations' in chunk: user_turn['citations'] = chunk['citations'] 
                processed_history.append(user_turn)
        elif role == "model":
            current_model_turn_parts.extend(current_chunk_extracted_parts)
            
            # Collect metadata for the model turn from the current chunk
            if 'finishReason' in chunk:
                current_model_turn_meta['finish_reason'] = chunk['finishReason']
            if 'tokenCount' in chunk: # This might be intermediate or final for the turn
                current_model_turn_meta['token_count'] = chunk['tokenCount'] 
            if 'citations' in chunk: # Citations are often associated with the chunk containing the text they refer to
                # We can merge citations. Example: list of dicts
                if 'citations' not in current_model_turn_meta:
                    current_model_turn_meta['citations'] = []
                if isinstance(chunk['citations'], list):
                    current_model_turn_meta['citations'].extend(chunk['citations'])
                else: # If it's not a list, wrap it or log warning
                    current_model_turn_meta['citations'].append(chunk['citations'])
            
            is_last_chunk = (chunk_index + 1 == len(source_chunks))
            next_chunk_is_user = False
            if not is_last_chunk:
                next_chunk = source_chunks[chunk_index + 1]
                if isinstance(next_chunk, dict) and next_chunk.get('role') == 'user':
                    next_chunk_is_user = True
            
            if chunk.get('finishReason') or is_last_chunk or next_chunk_is_user:
                finalize_model_turn()
        else: # Unknown or system-like roles (if any appear in chunks)
            finalize_model_turn() 
            if current_chunk_extracted_parts:
                # print(f"Warning: Chunk with role '{role}' found at index {chunk_index}. Storing as is.")
                processed_history.append({
                    "role": role or "unknown", 
                    "parts": current_chunk_extracted_parts
                })

    finalize_model_turn() # Finalize any last pending model turn
    return processed_history

def format_intermediate_json(
    source_file_name: str,
    run_settings: Dict[str, Any],
    system_instruction: str,
    dialogue_history: List[Dict[str, Any]]
) -> str:
    """Formats data into our standardized intermediate JSON string."""
    formatted_run_settings = run_settings.copy()
    if "responseSchema" in formatted_run_settings: # From original parser
        formatted_run_settings["response_schema_configured"] = formatted_run_settings.pop("responseSchema")
    
    tools_info_list = extract_tools_info(formatted_run_settings)
    if tools_info_list:
        formatted_run_settings["tools_info"] = tools_info_list

    intermediate_data = {
        "source_platform": "Google AI Studio",
        "source_file_name": source_file_name,
        "parsed_at_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "run_settings": formatted_run_settings,
        "system_instruction": system_instruction,
        "dialogue_history": dialogue_history
    }
    return json.dumps(intermediate_data, indent=2, ensure_ascii=False)

def format_markdown_for_rag(intermediate_json_data: Dict[str, Any]) -> str:
    markdown_parts = []
    md_add = markdown_parts.append

    md_add(f"# Chat Parse: {intermediate_json_data.get('source_file_name', 'N/A')}")
    md_add(f"Parsed at: {intermediate_json_data.get('parsed_at_timestamp', 'N/A')}")
    md_add(f"Source Platform: {intermediate_json_data.get('source_platform', 'N/A')}\\n")

    run_settings = intermediate_json_data.get('run_settings', {})
    md_add("<generation_settings>")
    for key, value in run_settings.items():
        if key == 'responseSchema' and value: # Already handled by response_schema_configured
            continue 
        if key == 'functionDeclarations' and value: # This is part of run_settings from source, but not directly in intermediate's run_settings.
                                                 # It's processed into tools_info.
            continue
        if key == 'tools_info': # tools_info is handled by the <configured_tools> section
            continue
        if key == 'response_schema_configured' and value:
            md_add(f"  <response_schema_definition name=\"configuredResponseSchema\">")
            md_add(f"    ```json\n{json.dumps(value, indent=2, ensure_ascii=False)}\n    ```")
            md_add(f"  </response_schema_definition>")
        else:
            # Avoid printing raw functionDeclarations here if it somehow slipped through
            if key != 'functionDeclarations': # Explicitly skip if it was not caught above
                 md_add(f"  <{key}>{value}</{key}>")
    md_add("</generation_settings>\\n")

    # Display Configured Tools
    tools_info = intermediate_json_data.get('tools_info', [])
    if tools_info:
        md_add("<configured_tools>")
        for tool_config in tools_info:
            tool_type = tool_config.get('type')
            if tool_type == "code_execution":
                md_add("  <tool type=\"code_execution_enabled\" />")
            elif tool_type == "google_search_enabled":
                md_add("  <tool type=\"google_search_enabled\" />")
            elif tool_type == "browse_enabled":
                md_add("  <tool type=\"browse_enabled\" />")
            elif tool_type == "function_declaration" and 'functions' in tool_config:
                md_add("  <tool type=\"function_declarations\">")
                for func_decl in tool_config.get('functions', []):
                    md_add(f"    <function name=\"{func_decl.get('name', 'N/A')}\">")
                    # Using CDATA for description to handle special characters safely
                    description_text = func_decl.get('description', '')
                    md_add(f"      <description><![CDATA[{description_text}]]></description>")
                    md_add(f"      <parameters_schema name=\"{func_decl.get('name', 'N/A')}_parameters\">")
                    md_add(f"        ```json\n{json.dumps(func_decl.get('parameters_schema', {}), indent=2, ensure_ascii=False)}\n        ```")
                    md_add(f"      </parameters_schema>")
                    md_add(f"    </function>")
                md_add("  </tool>")
        md_add("</configured_tools>\\n")

    system_instruction = intermediate_json_data.get('system_instruction')
    md_add("<system_instruction>")
    md_add(system_instruction.strip() if system_instruction.strip() else "<!-- No system instruction provided -->")
    md_add("</system_instruction>")

    # Dialogue History
    md_add("<dialogue_history>")
    dialogue_history = intermediate_json_data.get("dialogue_history", [])
    if not dialogue_history:
        md_add("  <!-- No dialogue history available -->")
    else:
        for turn_idx, turn in enumerate(dialogue_history):
            role = turn.get("role", "unknown")
            md_add(f'  <turn role="{role}" id="{turn_idx+1}">')
            parts = turn.get("parts", [])
            if not parts:
                # Add a placeholder for empty turns based on role
                if role == "user":
                    md_add(f'    <message_text><!-- Empty user message --></message_text>')
                elif role == "model":
                    md_add(f'    <response_text><!-- Empty model response --></response_text>')
                else:
                    md_add(f'    <!-- Empty turn for role {role} -->')
            else:
                for part_idx, part in enumerate(parts):
                    part_type = part.get("type")
                    
                    if part_type == "text": # User's text or unclassified text
                        content = part.get("content", "")
                        md_add(f'    <message_text>{content if content is not None else ""}</message_text>')
                    elif part_type == "thoughts":
                        content = part.get("content", "")
                        md_add(f'    <thoughts>{content if content is not None else ""}</thoughts>')
                    elif part_type == "text_response": # Model's primary text response
                        content = part.get("content", "")
                        md_add(f'    <response_text><![CDATA[{content if content is not None else ""}]]></response_text>')
                    elif part_type == "uri_reference":
                        source_type = part.get("source_type", "unknown_uri")
                        identifier = part.get("identifier", "unknown_id")
                        mime_type_attr = f' mime_type="{part["mime_type"]}"' if "mime_type" in part else ""
                        md_add(f'    <media_attachment type="{source_type}" identifier="{identifier}"{mime_type_attr}/>')
                    elif part_type == "bytes_data":
                        mime_type = part.get("mime_type", "application/octet-stream")
                        md_add(f'    <media_attachment type="bytes_data" mime_type="{mime_type}" data_preview="{part.get("base64_data", "")[:50]}..."/>')
                    elif part_type == "executable_code":
                        code_content = part.get("code_content", "")
                        language = part.get("language", "UNKNOWN")
                        md_add(f'    <executable_code language="{language}">')
                        md_add(f"      <![CDATA[{code_content}]]>")
                        md_add(f"    </executable_code>")
                    elif part_type == "code_execution_result":
                        output_content = part.get("output_content", "")
                        outcome = part.get("outcome", "UNKNOWN")
                        md_add(f'    <code_execution_result outcome="{outcome}">')
                        md_add(f"      <output><![CDATA[{output_content}]]></output>")
                        md_add(f"    </code_execution_result>")
                    elif part_type == "function_call":
                        fc_name = part.get('name', 'N/A')
                        fc_args = part.get('args', {})
                        md_add(f'    <function_call name="{fc_name}\">')
                        md_add(f"      <arguments>")
                        # ensure_ascii=False to allow non-ASCII characters in arguments JSON
                        md_add(f"        ```json\n{json.dumps(fc_args, indent=2, ensure_ascii=False)}\n        ```")
                        md_add(f"      </arguments>")
                        md_add(f"    </function_call>")
                    elif part_type == "function_response":
                        fr_name = part.get('name', 'N/A') # Name should match the corresponding call
                        response_content = part.get('response_content', {})
                        md_add(f"    <function_response name=\"{fr_name}\">")
                        md_add(f"      <response_data>")
                        # ensure_ascii=False for response data as well
                        md_add(f"        ```json\n{json.dumps(response_content, indent=2, ensure_ascii=False)}\n        ```")
                        md_add(f"      </response_data>")
                        md_add(f"    </function_response>")
                    elif part_type == "uri_reference":
                        # Adding mime_type to the output for uri_reference if available
                        mime_type_str = part.get('mime_type', 'N/A')
                        if mime_type_str is None: mime_type_str = 'N/A' # Ensure it's a string
                        md_add(f"    <uri_reference source_type=\"{part.get('source_type', 'unknown')}\" identifier=\"{part.get('identifier', 'N/A')}\" mime_type=\"{mime_type_str}\"/>")
                    else:
                        # Fallback for unknown part types, try to dump its content safely
                        unknown_part_content = {k: v for k, v in part.items() if k != 'type'}
                        md_add(f"    <unknown_part type=\"{part_type}\"><![CDATA[{str(part.get('content', part))}]]></unknown_part>")
            md_add(f"  </turn>")
    md_add("</dialogue_history>")
    return "\n".join(markdown_parts)

def save_output_file(output_path: str, content: str, description: str = ""):
    """Сохраняет контент в файл и выводит красивое сообщение."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"💾 {description} в: {output_path}... ✔️")
    except Exception as e:
        print(f"❌ Ошибка при сохранении файла {output_path}: {e}")
        # raise

def process_single_file(input_file_path: str, output_dir: str):
    """Processes a single input JSON file."""    
    print(f"\nStarting parsing for input file: {input_file_path}")
    base_name_from_input = os.path.splitext(os.path.basename(input_file_path))[0]
    # Ensure output_file_base_name is just the base, without extension, joined with output_dir
    output_file_base_name = os.path.join(output_dir, base_name_from_input)

    raw_data = load_json_file(input_file_path)
    if raw_data is None:
        print(f"Skipping file {input_file_path} due to loading error.")
        return

    run_settings = extract_run_settings(raw_data)
    system_instruction = extract_system_instruction(raw_data)
    dialogue_history = extract_dialogue_history_v2(raw_data)
    
    intermediate_json_str = format_intermediate_json(
        source_file_name=os.path.basename(input_file_path),
        run_settings=run_settings,
        system_instruction=system_instruction,
        dialogue_history=dialogue_history
    )

    json_output_path = output_file_base_name + '.json'
    # save_output_file already creates parent directory of the file if it doesn't exist.
    save_output_file(json_output_path, intermediate_json_str, "Промежуточный JSON")

    try:
        intermediate_json_data = json.loads(intermediate_json_str)
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode intermediate JSON for Markdown generation: {e}. Skipping Markdown for {input_file_path}")
        return
        
    markdown_output_str = format_markdown_for_rag(intermediate_json_data)
    md_output_path = output_file_base_name + '.md'
    save_output_file(md_output_path, markdown_output_str, "Markdown для RAG")
    print(f"Processing complete for {input_file_path}. Outputs saved to {json_output_path} and {md_output_path}")

def main():
    """
    Main function to load, parse, format, and save chat data.
    Handles single file or all files in a specified input directory.
    """
    print("\n🚀 Запуск parser_v2.py 🚀")
    parser = argparse.ArgumentParser(
        description="Parse Google AI Studio JSON chat files into intermediate JSON and Markdown for RAG."
    )
    parser.add_argument(
        "--input_file", "-i", 
        help="Path to a single input JSON file from Google AI Studio. If not provided, processes all files in --input_dir.", 
        required=False, 
        default=None # Explicitly default to None
    )
    parser.add_argument(
        "--input_dir", "-d", 
        default="input_data", 
        help="Directory containing input JSON files (default: input_data). Used if --input_file is not specified."
    )
    parser.add_argument(
        "--output_dir", "-o", 
        default="output_data", 
        help="Directory to save the output files (default: output_data). Ensure this path is writable."
    )
    
    args = parser.parse_args()

    # Ensure the main output directory exists
    if not os.path.exists(args.output_dir):
        try:
            os.makedirs(args.output_dir)
            print(f"Created output directory: {args.output_dir}")
        except OSError as e:
            print(f"Error: Could not create output directory {args.output_dir}: {e}")
            return # Exit if output directory cannot be created

    if args.input_file:
        if not os.path.isfile(args.input_file):
            print(f"Error: Specified input file not found: {args.input_file}")
            return
        print(f"Processing single input file: {args.input_file}")
        process_single_file(args.input_file, args.output_dir)
        print("\nSingle file processing complete.")
    else:
        print(f"No specific input file provided. Attempting to process all files in directory: {args.input_dir}")
        if not os.path.isdir(args.input_dir):
            print(f"Error: Input directory not found: {args.input_dir}")
            print("Please create it or specify a valid directory with --input_dir.")
            return
        
        processed_count = 0
        files_in_input_dir = os.listdir(args.input_dir)
        if not files_in_input_dir:
            print(f"No files found in the input directory: {args.input_dir}")
            return
            
        print(f"Found {len(files_in_input_dir)} entries in {args.input_dir}. Processing files...")
        for filename in files_in_input_dir:
            file_path = os.path.join(args.input_dir, filename)
            # Process only if it's a file (not a subdirectory)
            if os.path.isfile(file_path):
                process_single_file(file_path, args.output_dir)
                processed_count += 1
            else:
                print(f"Skipping non-file entry: {filename}")
        
        if processed_count == 0:
            print(f"No processable files found directly in {args.input_dir}. Subdirectories are not processed by default.")
        else:
            print(f"\nFinished processing {processed_count} file(s) from {args.input_dir}.")

if __name__ == "__main__":
    main() 
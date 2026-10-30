import json
import datetime
import os
from typing import List, Dict, Any, Optional, Union

# Import necessary classes from core modules
from utils.core.schema_elements import SchemaData, FunctionDefinition
from utils.core.chat_elements import (
    RunSettingsData, SystemInstruction, ChatMessagePart, TextPart, ThoughtsPart, # Basic parts for now
    ExecutableCodePart, CodeExecutionResultPart, FunctionCallPart, FunctionResponsePart,
    InlineDataPart, UriReferencePart, DialogueTurn, ToolConfiguration, IntermediateChatData
)
# SchemaTransformer might be needed if we decide to convert OpenAI-like schemas from export to SchemaData
# from utils.transformation.schema_transformer import SchemaTransformer


def load_json_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Reads a JSON-file from the specified path.
    Returns the content as a Python dictionary or None if error.
    (Adapted from parser_v2.py)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        # print(f"Error: File not found at {file_path}") # Consider logging instead of printing
        return None
    except json.JSONDecodeError:
        # print(f"Error: Could not decode JSON from file {file_path}")
        return None
    except Exception:
        # print(f"An unexpected error occurred while loading {file_path}: {e}")
        return None

class GoogleAIStudioJSONParser:
    """
    Parses Google AI Studio JSON chat exports into an IntermediateChatData object.
    """
    def __init__(self):
        """
        Initializes the parser.
        # self.schema_transformer = SchemaTransformer() # If needed for schema conversion
        """
        pass

    def _parse_schema_data(self, schema_dict: Dict[str, Any]) -> SchemaData:
        """
        Converts a JSON schema dictionary (from Google AI Studio export, assumed to be Gemini-like)
        into a SchemaData object.
        Google AI Studio's function parameter schemas and response schemas are already
        in a format that is quite close to Gemini API's schema structure.
        Types are typically uppercase (e.g., "STRING", "OBJECT").
        """
        if not isinstance(schema_dict, dict):
            # This is an error condition, schema_dict should always be a dictionary.
            # print(f"Warning: _parse_schema_data expected a dict, got {type(schema_dict)}. Returning default schema.")
            return SchemaData(type="STRING", description="Error: Invalid schema format.")

        # Directly map Google AI Studio schema to SchemaData fields.
        # Ensure type is uppercase as per SchemaData expectation if source varies.
        schema_type = str(schema_dict.get("type", "STRING")).upper() # Default to STRING

        properties = None
        if "properties" in schema_dict and isinstance(schema_dict["properties"], dict):
            properties = {
                key: self._parse_schema_data(value)
                for key, value in schema_dict["properties"].items()
            }

        items_schema = None
        if "items" in schema_dict and isinstance(schema_dict["items"], dict):
            items_schema = self._parse_schema_data(schema_dict["items"])

        return SchemaData(
            type=schema_type,
            description=schema_dict.get("description"),
            nullable=schema_dict.get("nullable", False), # Default nullable to False
            properties=properties,
            items=items_schema,
            enum=schema_dict.get("enum"),
            required=schema_dict.get("required")
        )

    def _parse_function_definition(self, func_decl_dict: Dict[str, Any]) -> FunctionDefinition:
        """
        Parses a function declaration dictionary into a FunctionDefinition object.
        """
        name = func_decl_dict.get("name", "")
        description = func_decl_dict.get("description", "")

        # 'parameters' in Google AI Studio's export holds the JSON schema for parameters
        parameters_json_schema = func_decl_dict.get("parameters", {"type": "OBJECT", "properties": {}}) # Default to empty object schema

        # Ensure parameters_json_schema is a dict before parsing
        if not isinstance(parameters_json_schema, dict):
            # print(f"Warning: 'parameters' for function {name} is not a dict. Using default empty schema.")
            parameters_json_schema = {"type": "OBJECT", "properties": {}}

        parameters_schema_data = self._parse_schema_data(parameters_json_schema)

        return FunctionDefinition(
            name=name,
            description=description,
            parameters_schema=parameters_schema_data
        )

    def _parse_run_settings(self, raw_data: Dict[str, Any]) -> RunSettingsData:
        """
        Extracts and transforms run settings from the raw JSON data into RunSettingsData.
        (Adapted from extract_run_settings in parser_v2.py)
        """
        run_settings_source = raw_data.get('runSettings', {})
        if not isinstance(run_settings_source, dict):
            run_settings_source = {}

        response_schema_obj: Optional[SchemaData] = None
        if 'responseSchema' in run_settings_source and isinstance(run_settings_source['responseSchema'], dict):
            response_schema_obj = self._parse_schema_data(run_settings_source['responseSchema'])

        func_declarations: Optional[List[FunctionDefinition]] = None
        if 'functionDeclarations' in run_settings_source and isinstance(run_settings_source['functionDeclarations'], list):
            func_declarations = [
                self._parse_function_definition(f_decl)
                for f_decl in run_settings_source['functionDeclarations']
                if isinstance(f_decl, dict)
            ]

        return RunSettingsData(
            model=run_settings_source.get('model'),
            temperature=run_settings_source.get('temperature'),
            top_p=run_settings_source.get('topP'),
            top_k=run_settings_source.get('topK'),
            max_output_tokens=run_settings_source.get('maxOutputTokens'),
            response_mime_type=run_settings_source.get('responseMimeType'),
            response_schema=response_schema_obj,
            function_declarations=func_declarations,
            enable_code_execution=run_settings_source.get('enableCodeExecution', False),
            enable_search_as_tool=run_settings_source.get('enableSearchAsATool', False),
            enable_browse_as_tool=run_settings_source.get('enableBrowseAsATool', False),
            enable_auto_function_response=run_settings_source.get('enableAutoFunctionResponse', False),
            raw_settings=run_settings_source
        )

    def _parse_system_instruction(self, raw_data: Dict[str, Any]) -> Optional[SystemInstruction]:
        """
        Extracts system instruction from the raw JSON data.
        (Adapted from extract_system_instruction in parser_v2.py)
        """
        system_instruction_data = raw_data.get('systemInstruction')
        if isinstance(system_instruction_data, dict) and 'text' in system_instruction_data:
            # Assuming 'text' field contains the instruction.
            # If source or other fields are present, they can be added to SystemInstruction class.
            return SystemInstruction(text=system_instruction_data['text'])
        elif isinstance(system_instruction_data, str): # Handle plain string if that's possible
             return SystemInstruction(text=system_instruction_data)
        return None


    def _parse_tool_configuration(self, run_settings: RunSettingsData) -> List[ToolConfiguration]:
        """
        Creates a list of ToolConfiguration objects based on RunSettingsData.
        (Adapted from extract_tools_info in parser_v2.py)
        """
        configs = []
        if getattr(run_settings, 'enable_code_execution', False) is True:
            configs.append(ToolConfiguration(type="code_execution"))
        if getattr(run_settings, 'function_declarations', None):
            if run_settings.function_declarations:
                configs.append(ToolConfiguration(type="function_declaration", functions=run_settings.function_declarations))
        if getattr(run_settings, 'enable_search_as_tool', False) is True:
            configs.append(ToolConfiguration(type="google_search_enabled"))
        if getattr(run_settings, 'enable_browse_as_tool', False) is True:
            configs.append(ToolConfiguration(type="browse_enabled"))
        print(f'DEBUG _parse_tool_configuration: {configs}')
        return configs

    def _parse_chat_message_part(self, part_data: Dict[str, Any], owner_role: str = "unknown", is_thought_chunk: bool = False) -> Optional[ChatMessagePart]:
        """
        Parses a single part from a chunk into a ChatMessagePart object.
        Adapted from parser_v2.py's parse_part.
        The 'owner_role' and 'is_thought_chunk' are contextual hints from the parent chunk.
        """
        if not isinstance(part_data, dict):
            return None

        if 'text' in part_data:
            # Context (role, isThought) determines if it's TextPart, ThoughtsPart, or (model's) TextPart.
            # This method creates a generic TextPart; _parse_dialogue_history will refine it.
            # Or, we can pass context here. Let's pass context.
            if owner_role == "model" and is_thought_chunk:
                 return ThoughtsPart(content=part_data['text'])
            # In parser_v2, 'text_response' was a type applied later. Here, TextPart can cover model's textual response.
            return TextPart(content=part_data['text'])

        # Multimodal inputs
        if 'driveImage' in part_data and isinstance(part_data['driveImage'], dict):
            return UriReferencePart(source_type="google_drive_image", identifier=part_data['driveImage'].get('id'))
        if 'driveDocument' in part_data and isinstance(part_data['driveDocument'], dict):
            return UriReferencePart(source_type="google_drive_document", identifier=part_data['driveDocument'].get('id'))
        if 'sampleImageId' in part_data:
            return UriReferencePart(source_type="sample_image", identifier=part_data['sampleImageId'])
        if 'youtubeVideo' in part_data and isinstance(part_data['youtubeVideo'], dict):
            return UriReferencePart(source_type="youtube_video", identifier=part_data['youtubeVideo'].get('id'))
        if 'driveVideo' in part_data and isinstance(part_data['driveVideo'], dict):
            return UriReferencePart(source_type="google_drive_video", identifier=part_data['driveVideo'].get('id'))

        if 'inlineData' in part_data and isinstance(part_data['inlineData'], dict):
            inline_data = part_data['inlineData']
            return InlineDataPart(mime_type=inline_data.get('mimeType'), base64_data=inline_data.get('data'))

        if 'fileData' in part_data and isinstance(part_data['fileData'], dict):
            file_data = part_data['fileData']
            if 'fileUri' in file_data:
                 return UriReferencePart(
                     source_type="file_uri",
                     identifier=file_data['fileUri'],
                     mime_type=file_data.get('mimeType')
                 )

        # Model response parts (tool related)
        if 'executableCode' in part_data and isinstance(part_data['executableCode'], dict):
            ec = part_data['executableCode']
            # Language is not directly in 'executableCode' part in Studio JSON, assume PYTHON or allow override
            return ExecutableCodePart(code_content=ec.get('code', ''), language=ec.get('language', 'PYTHON'))

        if 'codeExecutionResult' in part_data and isinstance(part_data['codeExecutionResult'], dict):
            cer = part_data['codeExecutionResult']
            return CodeExecutionResultPart(outcome=cer.get('outcome', 'OUTCOME_OK'), output_content=cer.get('output', ''))

        if 'functionCall' in part_data and isinstance(part_data['functionCall'], dict):
            fc = part_data['functionCall']
            return FunctionCallPart(name=fc.get('name'), args=fc.get('args', {}))

        if 'functionResponse' in part_data and isinstance(part_data['functionResponse'], dict):
            fr_part = part_data['functionResponse']
            # 'response' field in a standalone functionResponse part (not from resolvedFunctionCall)
            # is typically already a dictionary/object.
            return FunctionResponsePart(name=fr_part.get('name'), response_content=fr_part.get('response', {}))

        # print(f"Warning: Unknown part structure encountered in _parse_chat_message_part: {part_data}")
        return None

    def _parse_dialogue_history(self, raw_data: Dict[str, Any]) -> List[DialogueTurn]:
        """
        Extracts and transforms dialogue history into a list of DialogueTurn objects.
        Adapted from extract_dialogue_history_v2 in parser_v2.py.
        """
        processed_history: List[DialogueTurn] = []

        source_chunks = raw_data.get('chunkedPrompt', {}).get('chunks', [])
        if not source_chunks and 'pendingInputs' in raw_data: # Check pendingInputs as alternative source
            source_chunks = raw_data.get('pendingInputs', [])
            if not isinstance(source_chunks, list): # Ensure it's a list
                source_chunks = []

        current_model_turn_parts: List[ChatMessagePart] = []
        current_model_turn_meta: Dict[str, Any] = {}
        turn_counter = 1  # Для уникальных turn_id

        def finalize_model_turn():
            nonlocal current_model_turn_parts, current_model_turn_meta, turn_counter
            if current_model_turn_parts:
                turn_to_add = DialogueTurn(
                    role="model",
                    parts=list(current_model_turn_parts), # Take a copy
                    finish_reason=current_model_turn_meta.get('finish_reason'),
                    token_count=current_model_turn_meta.get('token_count'),
                    citations=current_model_turn_meta.get('citations'),
                    turn_id=turn_counter
                )
                processed_history.append(turn_to_add)
                current_model_turn_parts.clear()
                current_model_turn_meta.clear()
                turn_counter += 1

        for chunk_index, chunk in enumerate(source_chunks):
            if not isinstance(chunk, dict):
                continue

            role = chunk.get('role')
            is_thought_chunk = chunk.get('isThought', False)
            chunk_token_count = chunk.get('tokenCount')
            chunk_citations = chunk.get('citations') # List of dicts
            chunk_finish_reason = chunk.get('finishReason')

            current_chunk_extracted_parts: List[ChatMessagePart] = []

            # Handle resolvedFunctionCall first (contains both call and response)
            if role == "model" and 'resolvedFunctionCall' in chunk and isinstance(chunk['resolvedFunctionCall'], dict):
                rfc = chunk['resolvedFunctionCall']
                fc_data_from_rfc = rfc.get('functionCall')
                fr_json_string = rfc.get('response')

                if isinstance(fc_data_from_rfc, dict) and 'name' in fc_data_from_rfc:
                    # Attempt to remove a pre-existing FunctionCallPart from current_model_turn_parts
                    # if this resolvedFunctionCall corresponds to it, to avoid duplication.
                    call_name_from_rfc = fc_data_from_rfc.get('name')
                    for i, part_in_model_turn in reversed(list(enumerate(current_model_turn_parts))):
                        if isinstance(part_in_model_turn, FunctionCallPart) and part_in_model_turn.name == call_name_from_rfc:
                            # To be more precise, one might also compare args if available and simple enough.
                            # For now, matching by name is the primary heuristic used in parser_v2.
                            current_model_turn_parts.pop(i)
                            break

                    # Add the FunctionCall from resolvedFunctionCall itself
                    current_chunk_extracted_parts.append(FunctionCallPart(name=call_name_from_rfc, args=fc_data_from_rfc.get('args', {})))

                    response_content_dict = {}
                    if isinstance(fr_json_string, str):
                        try:
                            response_content_dict = json.loads(fr_json_string)
                        except json.JSONDecodeError:
                            response_content_dict = {"error": "Failed to parse response JSON", "raw_response": fr_json_string}
                    else:
                         response_content_dict = {"error": "Response was not a JSON string", "raw_response": fr_json_string}

                    current_chunk_extracted_parts.append(FunctionResponsePart(name=call_name_from_rfc, response_content=response_content_dict))

            # Process parts from the 'parts' array of the chunk
            # Ensure not to re-process a functionCall if it was part of resolvedFunctionCall handled above for THIS chunk.
            # However, the main duplication is from previous chunks being merged.
            chunk_parts_data_raw = chunk.get('parts', [])
            list_of_part_dicts = []
            if isinstance(chunk_parts_data_raw, list):
                list_of_part_dicts = chunk_parts_data_raw
            elif isinstance(chunk_parts_data_raw, dict): # Single part dict
                list_of_part_dicts = [chunk_parts_data_raw]
            elif 'text' in chunk and not chunk_parts_data_raw: # Simple text directly in chunk
                 list_of_part_dicts = [{'text': chunk['text']}]

            for part_dict_from_chunk in list_of_part_dicts:
                if not isinstance(part_dict_from_chunk, dict):
                    continue

                # Pass role and is_thought_chunk for context to _parse_chat_message_part
                parsed_part = self._parse_chat_message_part(part_dict_from_chunk, owner_role=role, is_thought_chunk=is_thought_chunk)
                if parsed_part:
                    current_chunk_extracted_parts.append(parsed_part)

            # Fallback if no parts extracted but chunk has top-level 'text'
            if not current_chunk_extracted_parts and 'text' in chunk and not list_of_part_dicts:
                # Role context is important here too
                text_part_fallback = self._parse_chat_message_part({'text': chunk['text']}, owner_role=role, is_thought_chunk=is_thought_chunk)
                if text_part_fallback:
                    current_chunk_extracted_parts.append(text_part_fallback)

            # Refine TextPart for model to ThoughtsPart if it's a thought chunk
            # This was partially handled in _parse_chat_message_part, but double-check or make logic exclusive.
            # The current _parse_chat_message_part already creates ThoughtsPart if context is right.

            if role == "user":
                finalize_model_turn() # Finalize any pending model turn before a user turn
                if current_chunk_extracted_parts:
                    user_turn = DialogueTurn(
                        role="user",
                        parts=current_chunk_extracted_parts,
                        token_count=chunk_token_count,
                        citations=chunk_citations,
                        turn_id=turn_counter
                    )
                    processed_history.append(user_turn)
            elif role == "model":
                current_model_turn_parts.extend(current_chunk_extracted_parts)
                if chunk_finish_reason:
                    current_model_turn_meta['finish_reason'] = chunk_finish_reason
                if chunk_token_count: # Accumulate or update token count for the turn
                    current_model_turn_meta['token_count'] = current_model_turn_meta.get('token_count', 0) + chunk_token_count
                if chunk_citations:
                    if 'citations' not in current_model_turn_meta: current_model_turn_meta['citations'] = []
                    current_model_turn_meta['citations'].extend(chunk_citations if isinstance(chunk_citations, list) else [chunk_citations])

                # Determine if model turn should be finalized
                is_last_chunk = (chunk_index + 1 == len(source_chunks))
                next_chunk_is_user = False
                if not is_last_chunk:
                    next_chunk = source_chunks[chunk_index + 1]
                    if isinstance(next_chunk, dict) and next_chunk.get('role') == 'user':
                        next_chunk_is_user = True

                if chunk_finish_reason or is_last_chunk or next_chunk_is_user:
                    finalize_model_turn()
            else: # Unknown or other roles
                finalize_model_turn()
                if current_chunk_extracted_parts:
                    # print(f"Warning: Chunk with role '{role}' found. Storing as is.")
                    processed_history.append(DialogueTurn(role=role or "unknown", parts=current_chunk_extracted_parts, turn_id=turn_counter))

        finalize_model_turn() # Finalize any last pending model turn
        print(f'DEBUG _parse_dialogue_history: {processed_history}')

        # Присваиваем turn_id всем ходам, если не был установлен
        for idx, turn in enumerate(processed_history, 1):
            if not getattr(turn, 'turn_id', None):
                turn.turn_id = idx
        return processed_history

    def to_markdown(self, intermediate_data: IntermediateChatData) -> str:
        """
        Generates a Markdown string with custom XML-like tags from IntermediateChatData.
        Adapted from format_markdown_for_rag in parser_v2.py.
        """
        markdown_parts = []
        md_add = markdown_parts.append

        md_add(f"# Chat Parse: {intermediate_data.source_file_name}")
        md_add(f"Parsed at: {intermediate_data.parsed_at_timestamp}")
        md_add(f"Source Platform: {intermediate_data.source_platform}\n")

        # Generation Settings from RunSettingsData
        rs = intermediate_data.run_settings
        md_add("<generation_settings>")
        if rs.model: md_add(f"  <model>{rs.model}</model>")
        if rs.temperature is not None: md_add(f"  <temperature>{rs.temperature}</temperature>")
        if rs.top_p is not None: md_add(f"  <topP>{rs.top_p}</topP>") # Note: key is topP in XML
        if rs.top_k is not None: md_add(f"  <topK>{rs.top_k}</topK>")   # Note: key is topK in XML
        if rs.max_output_tokens is not None: md_add(f"  <maxOutputTokens>{rs.max_output_tokens}</maxOutputTokens>")
        if rs.response_mime_type: md_add(f"  <responseMimeType>{rs.response_mime_type}</responseMimeType>")

        if rs.response_schema:
            # Assuming SchemaData doesn't have a direct to_json_string method,
            # we might need SchemaTransformer or a local helper to serialize it for display if needed.
            # The original parser_v2 used json.dumps on the schema dict.
            # For now, let's represent its presence or a summary.
            # If direct JSON representation is needed, SchemaData would need a method,
            # or we'd use SchemaTransformer here (gemini_schema_to_openai_dict then json.dumps).
            # For simplicity, using __repr__ or a summary:
            schema_for_md = intermediate_data.run_settings.raw_settings.get('responseSchema', {})
            md_add("  <response_schema_definition name='configuredResponseSchema'>")
            md_add("    ```json")
            md_add(json.dumps(schema_for_md, indent=2, ensure_ascii=False))
            md_add("    ```")
            md_add("  </response_schema_definition>")
        md_add("</generation_settings>\n")

        # Configured Tools from ToolConfiguration list
        if intermediate_data.tool_configurations:
            md_add("<configured_tools>")
            for tool_config in intermediate_data.tool_configurations:
                if tool_config.type == "code_execution":
                    md_add("  <tool type='code_execution_enabled' />")
                elif tool_config.type == "google_search_enabled":
                    md_add("  <tool type='google_search_enabled' />")
                elif tool_config.type == "browse_enabled":
                    md_add("  <tool type='browse_enabled' />")
                elif tool_config.type == "function_declaration" and tool_config.functions:
                    md_add("  <tool type='function_declarations'>")
                    for func_def in tool_config.functions:
                        # Use raw_settings for original schema representation for now
                        original_func_decl = next((item for item in rs.raw_settings.get('functionDeclarations', []) if item["name"] == func_def.name), None)
                        params_schema_for_md = {}
                        if original_func_decl and 'parameters' in original_func_decl:
                            params_schema_for_md = original_func_decl['parameters']

                        md_add(f"    <function name='{func_def.name}'>")
                        md_add(f"      <description><![CDATA[{func_def.description}]]></description>")
                        md_add(f"      <parameters_schema name='{func_def.name}_parameters'>")
                        md_add("        ```json")
                        md_add(json.dumps(params_schema_for_md, indent=2, ensure_ascii=False))
                        md_add("        ```")
                        md_add("      </parameters_schema>")
                        md_add("    </function>")
                    md_add("  </tool>")
            md_add("</configured_tools>\n")
        else:
            md_add("<tools_placeholder>В этом чате не было активных инструментов (function calling, code execution, search, browse). Для подробностей см. исходный код чата или JSON-представление.</tools_placeholder>\n")

        # System Instruction
        md_add("<system_instruction>")
        if intermediate_data.system_instruction and intermediate_data.system_instruction.text.strip():
            md_add(intermediate_data.system_instruction.text.strip())
        else:
            md_add("<!-- No system instruction provided -->")
        md_add("</system_instruction>")

        # Dialogue History
        md_add("<dialogue_history>")
        if not intermediate_data.dialogue_history:
            md_add("  <!-- No dialogue history available -->")
        else:
            for turn_idx, turn in enumerate(intermediate_data.dialogue_history):
                turn_id_val = turn.turn_id if turn.turn_id else turn_idx+1
                md_add(f"  <turn role='{turn.role}' id='{turn_id_val}'>")
                if not turn.parts:
                    placeholder = "<!-- Empty turn -->"
                    if turn.role == "user": placeholder = '    <message_text><!-- Empty user message --></message_text>'
                    elif turn.role == "model": placeholder = '    <response_text><!-- Empty model response --></response_text>'
                    md_add(placeholder)
                else:
                    for part_idx, part in enumerate(turn.parts):
                        if isinstance(part, TextPart):
                            tag = "message_text" if turn.role == "user" else "response_text"
                            content_escaped = f"<![CDATA[{part.content}]]>" if tag == "response_text" else part.content
                            md_add(f'    <{tag}>{content_escaped}</{tag}>')
                        elif isinstance(part, ThoughtsPart):
                            md_add(f'    <thoughts><![CDATA[{part.content}]]></thoughts>')
                        elif isinstance(part, UriReferencePart):
                            mime_attr = f" mime_type='{part.mime_type}'" if part.mime_type else ""
                            md_add(f"    <media_attachment type='{part.source_type}' identifier='{part.identifier}'{mime_attr}/>")
                        elif isinstance(part, InlineDataPart):
                            md_add(f"    <media_attachment type='bytes_data' mime_type='{part.mime_type}' data_preview='{part.base64_data[:50]}...'/>")
                        elif isinstance(part, ExecutableCodePart):
                            md_add(f"    <executable_code language='{part.language}'>")
                            md_add(f"      <![CDATA[{part.code_content}]]>")
                            md_add("    </executable_code>")
                        elif isinstance(part, CodeExecutionResultPart):
                            md_add(f"    <code_execution_result outcome='{part.outcome}'>")
                            md_add(f"      <output><![CDATA[{part.output_content}]]></output>")
                            md_add("    </code_execution_result>")
                        elif isinstance(part, FunctionCallPart):
                            md_add(f"    <function_call name='{part.name}'>")
                            md_add("      <arguments>")
                            md_add("        ```json")
                            md_add(json.dumps(part.args, indent=2, ensure_ascii=False))
                            md_add("        ```")
                            md_add("      </arguments>")
                            md_add("    </function_call>")
                        elif isinstance(part, FunctionResponsePart):
                            md_add(f"    <function_response name='{part.name}'>")
                            md_add("      <response_data>")
                            md_add("        ```json")
                            md_add(json.dumps(part.response_content, indent=2, ensure_ascii=False))
                            md_add("        ```")
                            md_add("      </response_data>")
                            md_add("    </function_response>")
                        else:
                            md_add(f"    <unknown_part type='{type(part).__name__}'><![CDATA[{str(part)}]]></unknown_part>")
                md_add("  </turn>")
        md_add("</dialogue_history>")
        return "\n".join(markdown_parts)

    def to_human_markdown(self, intermediate_data: IntermediateChatData) -> str:
        """
        Generates a clean, human-readable Markdown string representing the chat dialogue.
        Suitable for reading in Obsidian, GitHub, or any standard Markdown viewer.
        """
        markdown_parts = []
        md_add = markdown_parts.append

        md_add(f"# Chat: {intermediate_data.source_file_name}\n")
        
        if intermediate_data.system_instruction and intermediate_data.system_instruction.text.strip():
            md_add("### System Instruction")
            si_body = intermediate_data.system_instruction.text.strip().replace('\n', '\n> ')
            md_add(f"> {si_body}\n")

        if not intermediate_data.dialogue_history:
            md_add("*No dialogue history available.*")
            return "\n".join(markdown_parts)

        for turn in intermediate_data.dialogue_history:
            role_header = "**User**" if turn.role == "user" else "**Model**"
            md_add(f"### {role_header}")
            
            if not turn.parts:
                md_add("*Empty message*\n")
                continue

            current_text = []
            for part in turn.parts:
                if isinstance(part, TextPart):
                    current_text.append(part.content)
                else:
                    if current_text:
                        md_add("".join(current_text) + "\n")
                        current_text = []
                        
                    if isinstance(part, ThoughtsPart):
                        md_add(f"<details><summary>🧠 Model Thoughts</summary>\n\n{part.content}\n\n</details>\n")
                    elif isinstance(part, ExecutableCodePart):
                        lang = part.language.lower() if part.language else "python"
                        md_add(f"**Code Execution ({part.language})**:\n```{lang}\n{part.code_content}\n```\n")
                    elif isinstance(part, CodeExecutionResultPart):
                        md_add(f"**Execution Result ({part.outcome})**:\n```\n{part.output_content}\n```\n")
                    elif isinstance(part, FunctionCallPart):
                        md_add(f"**Function Call**: `{part.name}`\n```json\n{json.dumps(part.args, indent=2, ensure_ascii=False)}\n```\n")
                    elif isinstance(part, FunctionResponsePart):
                        md_add(f"**Function Response**: `{part.name}`\n```json\n{json.dumps(part.response_content, indent=2, ensure_ascii=False)}\n```\n")
                    elif isinstance(part, UriReferencePart):
                        md_add(f"*[Media Attachment: {part.source_type} - {part.identifier}]*\n")
                    elif isinstance(part, InlineDataPart):
                        md_add(f"*[Inline Data: {part.mime_type}]*\n")
                    else:
                        md_add(f"*[Unknown Part: {type(part).__name__}]*\n")
            
            if current_text:
                md_add("".join(current_text) + "\n")
                    
            md_add("---")

        return "\n".join(markdown_parts)

    # --- Main parse method ---
    def parse(self, file_path_or_data: Union[str, Dict[str, Any]]) -> Optional[IntermediateChatData]:
        """
        Parses a Google AI Studio JSON file or loaded dictionary into an IntermediateChatData object.
        """
        raw_data: Optional[Dict[str, Any]]
        source_file_name = "loaded_dict_data"

        if isinstance(file_path_or_data, str):
            source_file_name = os.path.basename(file_path_or_data)
            raw_data = load_json_file(file_path_or_data)
            if raw_data is None:
                return None
        elif isinstance(file_path_or_data, dict):
            raw_data = file_path_or_data
        else:
            return None

        # Если это промежуточный JSON — используем from_dict
        if 'dialogue_history' in raw_data and 'tool_configurations' in raw_data:
            try:
                return IntermediateChatData.from_dict(raw_data)
            except Exception as e:
                print(f"[parse] Ошибка десериализации промежуточного JSON: {e}")
                return None

        # Core parsing steps для сырого экспорта Studio
        run_settings = self._parse_run_settings(raw_data)
        system_instruction = self._parse_system_instruction(raw_data)
        tool_configurations = self._parse_tool_configuration(run_settings)
        dialogue_history = self._parse_dialogue_history(raw_data)
        parsed_at_ts = datetime.datetime.utcnow().isoformat() + "Z"
        intermediate_data = IntermediateChatData(
            source_file_name=source_file_name,
            parsed_at_timestamp=parsed_at_ts,
            run_settings=run_settings,
            dialogue_history=dialogue_history,
            source_platform="Google AI Studio",
            system_instruction=system_instruction,
            tool_configurations=tool_configurations
        )
        return intermediate_data

if __name__ == '__main__':
    # (Keep the existing complex JSON and parser tests)
    # ... existing sample_google_ai_studio_json_complex and parser instantiation ...
    # Re-run parsing or use existing intermediate_result if available in scope
    parser = GoogleAIStudioJSONParser() # Assuming definition is in current scope

    # Sample JSON from previous subtask, ensure it is defined here for the test
    sample_google_ai_studio_json_complex = {
        "runSettings": {
            "model": "gemini-pro-dialogue-test",
            "temperature": 0.7,
            "enableCodeExecution": True,
            "functionDeclarations": [{
                "name": "get_stock_price",
                "description": "Gets stock price for a ticker.",
                "parameters": {"type": "OBJECT", "properties": {"ticker": {"type": "STRING", "description": "The stock ticker symbol."}}}
            }],
            "responseSchema": {"type": "OBJECT", "properties": {"quote": {"type": "STRING"}}}
        },
        "systemInstruction": {"text": "You are a very helpful financial assistant."},
        "chunkedPrompt": {
            "chunks": [
                {"role": "user", "parts": [{"text": "Hi there!"}]},
                {"role": "model", "isThought": True, "parts": [{"text": "User said hi. I should respond politely."}]},
                {"role": "model", "parts": [{"text": "Hello! How can I help you with finances today?"}]},
                {"role": "user", "parts": [{"text": "What's the price of GOOG?"}]},
                {"role": "model",
                 "resolvedFunctionCall": { # This structure contains both call and response
                     "functionCall": {"name": "get_stock_price", "args": {"ticker": "GOOG"}},
                     "response": "{\"price\": 150.0, \"currency\": \"USD\"}"
                 },
                 "parts": [{"text": "The price for GOOG is $150.00 USD."}], # Model's textual summary after tool use
                 "finishReason": "COMPLETED"
                }
            ]
        }
    }
    # Create intermediate_result again for the markdown test
    intermediate_result_for_md = parser.parse(sample_google_ai_studio_json_complex)

    if intermediate_result_for_md:
        # This part of the test for dialogue history can be removed or simplified
        # as it's covered by the previous subtask's tests.
        # For brevity, let's assume the previous tests for dialogue parsing are sufficient.
        # print(f"Successfully parsed for MD. Source: {intermediate_result_for_md.source_file_name}")
        # print(f"Model: {intermediate_result_for_md.run_settings.model}")
        # print(f"Dialogue History Turns for MD: {len(intermediate_result_for_md.dialogue_history)}")

        print("\n--- Testing Markdown Generation ---")
        markdown_output = parser.to_markdown(intermediate_result_for_md)
        print(markdown_output)

        # Basic checks for markdown content
        assert "# Chat Parse:" in markdown_output
        assert "<generation_settings>" in markdown_output
        assert f"<model>{intermediate_result_for_md.run_settings.model}</model>" in markdown_output
        assert "<response_schema_definition name='configuredResponseSchema'>" in markdown_output
        assert "<configured_tools>" in markdown_output
        assert "<tool type='function_declarations'>" in markdown_output
        assert "<function name='get_stock_price'>" in markdown_output
        assert "<system_instruction>" in markdown_output
        assert intermediate_result_for_md.system_instruction.text in markdown_output
        assert "<dialogue_history>" in markdown_output
        assert "<turn role='user'" in markdown_output
        assert "<turn role='model'" in markdown_output
        assert "<message_text>Hi there!</message_text>" in markdown_output
        assert "<thoughts><![CDATA[User said hi. I should respond politely.]]></thoughts>" in markdown_output
        assert "<response_text><![CDATA[Hello! How can I help you with finances today?]]></response_text>" in markdown_output
        assert "<function_call name='get_stock_price'>" in markdown_output
        assert "<function_response name='get_stock_price'>" in markdown_output
        # Check for the model's textual summary part after function call/response
        assert "<response_text><![CDATA[The price for GOOG is $150.00 USD.]]></response_text>" in markdown_output

        print("\n--- Markdown generation test successful (basic checks) ---")
    else:
        print("\n--- Markdown generation test skipped due to parsing failure in __main__ ---")

import os
import json
import datetime # For __main__ block
from typing import List, Optional

# Core data models
from utils.core.chat_elements import (
    IntermediateChatData, RunSettingsData, SystemInstruction, DialogueTurn,
    ChatMessagePart, TextPart, ThoughtsPart, FunctionCallPart, FunctionResponsePart,
    InlineDataPart, UriReferencePart, ExecutableCodePart, CodeExecutionResultPart,
    ToolConfiguration
)
from utils.core.schema_elements import SchemaData, FunctionDefinition

# SchemaTransformer for converting SchemaData to genai.types.Schema Python code
from utils.transformation.schema_transformer import SchemaTransformer

# Constants adapted from reconstructor_v2.py
PYTHON_EXEC_LANG_MAP = {
    "PYTHON": "genai.types.CodeExecution.Language.PYTHON"
}
CODE_EXEC_OUTCOME_MAP = {
    "OUTCOME_OK": "genai.types.CodeExecutionResult.Outcome.OK",
    "OUTCOME_ERROR": "genai.types.CodeExecutionResult.Outcome.ERROR",
    "OUTCOME_DEADLINE_EXCEEDED": "genai.types.CodeExecutionResult.Outcome.DEADLINE_EXCEEDED",
    "OUTCOME_CANCELLED": "genai.types.CodeExecutionResult.Outcome.CANCELLED",
    "OK": "genai.types.CodeExecutionResult.Outcome.OK",
    "ERROR": "genai.types.CodeExecutionResult.Outcome.ERROR",
}

class GeminiAPICodeReconstructor:
    def __init__(self, template_dir: str):
        if not os.path.isdir(template_dir):
            raise FileNotFoundError(f"Template directory not found: {template_dir}")
        self.template_dir: str = template_dir
        self.schema_transformer: SchemaTransformer = SchemaTransformer()

    def _generate_parts_code(self, parts: List[ChatMessagePart]) -> List[str]:
        part_code_strings = []
        for part in parts:
            if isinstance(part, TextPart):
                part_code_strings.append(f"types.Part.from_text(text={repr(part.content)})")
            elif isinstance(part, ThoughtsPart):
                continue
            elif isinstance(part, FunctionCallPart):
                part_code_strings.append(f"types.Part.from_function_call(name={repr(part.name)}, args={json.dumps(part.args, ensure_ascii=False)})")
            elif isinstance(part, FunctionResponsePart):
                part_code_strings.append(f"types.Part.from_function_response(name={repr(part.name)}, response={json.dumps(part.response_content, ensure_ascii=False)})")
            elif isinstance(part, ExecutableCodePart):
                part_code_strings.append(f"types.Part.from_executable_code(language={repr(part.language)}, code={repr(part.code_content)})")
            elif isinstance(part, CodeExecutionResultPart):
                outcome_enum = CODE_EXEC_OUTCOME_MAP.get(part.outcome.upper(), "types.CodeExecutionResult.Outcome.OK")
                part_code_strings.append(
                    f"types.Part.from_code_execution_result(outcome={outcome_enum}, output={repr(part.output_content)})"
                )
            elif isinstance(part, InlineDataPart):
                part_code_strings.append(f"types.Part.from_bytes(mime_type={repr(part.mime_type)}, data=base64.b64decode({repr(part.base64_data)}))")
            elif isinstance(part, UriReferencePart):
                part_code_strings.append(f"types.Part(text=f'[URI Reference: Type={part.source_type}, ID={part.identifier}, MIME={part.mime_type}]')")
        return part_code_strings

    def _generate_contents_code(self, dialogue_turns: List[DialogueTurn]) -> str:
        history_entries_code = []
        for turn in dialogue_turns:
            if not turn.parts:
                continue
            part_code_strings = self._generate_parts_code(turn.parts)
            if part_code_strings:
                parts_joined_str = ",\n                ".join(part_code_strings)
                api_role = turn.role
                if api_role not in ["user", "model"]:
                    api_role = "user"
                history_entries_code.append(
                    f"    types.Content(\n"
                    f"        parts=[\n                {parts_joined_str}\n        ],\n"
                    f"        role='{api_role}'\n"
                    f"    )"
                )
        if not history_entries_code:
            return "[]"
        return "[\n" + ",\n".join(history_entries_code) + "\n]"

    def _generate_tools_code(self, tool_configurations: Optional[List[ToolConfiguration]]) -> str:
        if not tool_configurations:
            return "None"
        tool_code_objects_str = []
        for tool_config in tool_configurations:
            if tool_config.type == "function_declaration" and tool_config.functions:
                func_decl_codes = []
                for func_def in tool_config.functions:
                    params_schema_code = self.schema_transformer.gemini_schema_obj_to_python_code(
                        func_def.parameters_schema, current_indent="                "
                    )
                    func_decl_codes.append(
                        f"types.FunctionDeclaration(\n"
                        f"    name={repr(func_def.name)},\n"
                        f"    description={repr(func_def.description)},\n"
                        f"    parameters={params_schema_code}\n"
                        f")"
                    )
                if func_decl_codes:
                    joined_func_decls = ",\n                ".join(func_decl_codes)
                    tool_code_objects_str.append(
                        f"types.Tool(\n"
                        f"    function_declarations=[\n                {joined_func_decls}\n    ]\n"
                        f")"
                    )
            elif tool_config.type == "code_execution":
                tool_code_objects_str.append("types.Tool(code_execution=types.CodeExecution())")
            elif tool_config.type == "google_search_enabled":
                tool_code_objects_str.append("types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())")
            elif tool_config.type == "browse_enabled":
                tool_code_objects_str.append("types.Tool(browse=types.Browse())")
        if not tool_code_objects_str:
            return "None"
        return f"[{', '.join(tool_code_objects_str)}]"

    def _generate_tool_config_code(self, tool_configurations: Optional[List[ToolConfiguration]]) -> str:
        has_functions = any(tc.type == "function_declaration" and tc.functions for tc in tool_configurations or [])
        if has_functions:
            return "genai.types.ToolConfig(function_calling_config=genai.types.FunctionCallingConfig(mode=genai.types.FunctionCallingConfig.Mode.AUTO))"
        return "None"

    def _generate_generation_config_code(self, run_settings: RunSettingsData) -> str:
        gen_config_args = []
        if run_settings.temperature is not None:
            gen_config_args.append(f"temperature={run_settings.temperature}")
        if run_settings.top_p is not None:
            gen_config_args.append(f"top_p={run_settings.top_p}")
        if run_settings.top_k is not None:
            gen_config_args.append(f"top_k={run_settings.top_k}")
        if run_settings.max_output_tokens is not None:
            gen_config_args.append(f"max_output_tokens={run_settings.max_output_tokens}")
        if run_settings.response_mime_type:
            gen_config_args.append(f"response_mime_type={repr(run_settings.response_mime_type)}")
        if run_settings.response_mime_type == "application/json" and run_settings.response_schema:
            schema_code = self.schema_transformer.gemini_schema_obj_to_python_code(
                run_settings.response_schema, current_indent="        "
            )
            gen_config_args.append(f"response_schema={schema_code}")
        if not gen_config_args:
            return "None"
        args_joined_str = ",\n        ".join(gen_config_args)
        return f"types.GenerationConfig(\n        {args_joined_str}\n    )"

    def _generate_response_schema_code(self, run_settings: RunSettingsData) -> str:
        if run_settings.response_schema and run_settings.response_mime_type == "application/json":
            return self.schema_transformer.gemini_schema_obj_to_python_code(
                run_settings.response_schema, current_indent="    "
            )
        return "None"

    def reconstruct(self, intermediate_data: IntermediateChatData,
                    template_name: str,
                    api_key_var_name: str = "YOUR_API_KEY"
                   ) -> str:
        print('START RECONSTRUCT')
        print('DEBUG: dialogue_history:')
        for i, turn in enumerate(intermediate_data.dialogue_history):
            print(f'  Turn {i}: role={turn.role}, parts={[getattr(p, "content", str(p)) for p in turn.parts]}')
        print('DEBUG: tool_configurations:')
        for tool in intermediate_data.tool_configurations:
            print(f'  Tool type={tool.type}, functions={getattr(tool, "functions", None)}')
        template_path = os.path.join(self.template_dir, template_name)
        if not os.path.isfile(template_path):
            return f"# Error: Template file not found at {template_path}"
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        except Exception as e:
            return f"# Error reading template file: {e}"

        rs = intermediate_data.run_settings
        model_name_repr = repr(rs.model if rs.model else "gemini-pro")
        timestamp_str = intermediate_data.parsed_at_timestamp
        source_file_name_str = intermediate_data.source_file_name
        api_key_repr = 'os.environ.get("GEMINI_API_KEY")'

        contents_code_str = self._generate_contents_code(intermediate_data.dialogue_history)
        tools_code_str = self._generate_tools_code(intermediate_data.tool_configurations)
        if intermediate_data.system_instruction and intermediate_data.system_instruction.text:
            si_text = intermediate_data.system_instruction.text.replace('"""', '"')
            system_instruction_code_str = f'[types.Part.from_text(text="""{si_text}""")]'
        else:
            system_instruction_code_str = "None"
        generation_config_code_str = self._generate_generation_config_code(rs)
        response_mime_type_code_str = repr(rs.response_mime_type) if rs.response_mime_type else "None"
        response_schema_code_str = self._generate_response_schema_code(rs)

        replacements = {
            "timestamp": timestamp_str,
            "source_file_name": source_file_name_str,
            "model_name_repr": model_name_repr,
            "contents_code_str": contents_code_str,
            "tools_code_str": tools_code_str,
            "system_instruction_code_str": system_instruction_code_str,
            "generation_config_code_str": generation_config_code_str,
            "response_mime_type_code_str": response_mime_type_code_str,
            "response_schema_code_str": response_schema_code_str,
        }

        generated_code = template_content
        for placeholder, value in replacements.items():
            generated_code = generated_code.replace(f"{{{placeholder}}}", str(value))
        return generated_code

if __name__ == '__main__':
    import datetime # Ensure datetime is imported for __main__
    temp_template_dir = "temp_templates_reconstructor_full"
    os.makedirs(temp_template_dir, exist_ok=True)
    dummy_template_name = "test_template_full.py.tpl"
    # Updated template to use generation_config_code_str for all gen config aspects
    dummy_template_content = """
# Generated by Reconstructor at: {timestamp}
# Source file: {source_file_name}
import google.generativeai as genai
import base64

API_KEY = "{api_key_var_name}"
genai.configure(api_key=API_KEY)

# GenerationConfig will now include response_mime_type and response_schema
generation_config = {generation_config_code_str}

model = genai.GenerativeModel(
    model_name={model_name_repr},
    system_instruction={system_instruction_block},
    tools={tools_block},
    tool_config={tool_config_code_str},
    generation_config=generation_config
)

history = {history_code_str}

print(f"Script generated for model: {model_name_repr}")
if history:
    print(f"History contains {len(history)} turns (if history is a list).")
if generation_config != "None":
    print(f"Generation Config: {generation_config}")
"""
    with open(os.path.join(temp_template_dir, dummy_template_name), 'w') as f:
        f.write(dummy_template_content)

    sample_rs_data = RunSettingsData(
        model="gemini-1.5-pro-latest",
        temperature=0.6,
        top_p=0.9,
        top_k=30,
        max_output_tokens=4096,
        response_mime_type="application/json",
        response_schema=SchemaData(
            type="OBJECT",
            properties={"message": SchemaData(type="STRING", description="A short message.")},
            required=["message"]
        ),
        enable_code_execution=True,
        function_declarations=[
            FunctionDefinition(
                name="get_user_details",
                description="Fetches details for a given user ID.",
                parameters_schema=SchemaData(type="OBJECT", properties={"user_id": SchemaData(type="STRING")}, required=["user_id"])
            )
        ]
    )
    sample_sys_instruction = SystemInstruction(text="You are a test bot for code generation.")
    sample_dialogue = [
        DialogueTurn(role="user", parts=[TextPart(content="Hi Gemini!")]),
        DialogueTurn(role="model", parts=[TextPart(content="Hello there! How can I assist?")]),
    ]
    sample_tool_configs = [
        ToolConfiguration(type="code_execution"),
        ToolConfiguration(type="function_declaration", functions=sample_rs_data.function_declarations)
    ]

    intermediate_data_sample = IntermediateChatData(
        source_file_name="full_test.json",
        parsed_at_timestamp=datetime.datetime.utcnow().isoformat() + "Z",
        run_settings=sample_rs_data,
        system_instruction=sample_sys_instruction,
        dialogue_history=sample_dialogue,
        tool_configurations=sample_tool_configs
    )

    reconstructor = GeminiAPICodeReconstructor(template_dir=temp_template_dir)
    generated_script = reconstructor.reconstruct(intermediate_data_sample, dummy_template_name, api_key_var_name="MY_API_KEY_FULL")

    print("\n--- Fully Generated Python Script ---")
    print(generated_script)

    assert "API_KEY = \"MY_API_KEY_FULL\"" in generated_script # Check variable assignment
    assert "genai.configure(api_key=API_KEY)" in generated_script # Check configure call uses the variable
    assert "model_name='gemini-1.5-pro-latest'" in generated_script
    assert "system_instruction='You are a test bot for code generation.'" in generated_script
    assert "genai.types.Tool(code_execution=genai.types.CodeExecution())" in generated_script
    assert "name='get_user_details'" in generated_script
    assert "role='user'" in generated_script and "role='model'" in generated_script
    assert "genai.types.Part(text='Hi Gemini!')" in generated_script
    assert "tool_config=genai.types.ToolConfig(function_calling_config=genai.types.FunctionCallingConfig(mode=genai.types.FunctionCallingConfig.Mode.AUTO))" in generated_script
    # Check for GenerationConfig content
    assert "generation_config = genai.types.GenerationConfig(" in generated_script # Added space
    assert "temperature=0.6" in generated_script
    assert "top_p=0.9" in generated_script
    assert "top_k=30" in generated_script
    assert "max_output_tokens=4096" in generated_script
    assert "response_mime_type='application/json'" in generated_script
    assert "response_schema=genai.types.Schema(" in generated_script
    assert "type=genai.types.Type.OBJECT" in generated_script # For the main response_schema

    # Check for the 'message' property within the response_schema
    message_prop_start_index = generated_script.find("'message': genai.types.Schema(")
    assert message_prop_start_index != -1
    # Search for type and description within a reasonable range after the start of 'message' property
    # Increased search window to be safe with formatting.
    search_substring_for_message_prop = generated_script[message_prop_start_index : message_prop_start_index + 250]
    assert "type=genai.types.Type.STRING" in search_substring_for_message_prop
    assert "description='A short message.'" in search_substring_for_message_prop

    print("\n--- GeminiAPICodeReconstructor full test completed ---")

    try:
        os.remove(os.path.join(temp_template_dir, dummy_template_name))
        os.rmdir(temp_template_dir)
        print(f"Cleaned up {temp_template_dir}")
    except OSError as e:
        print(f"Error cleaning up temp files: {e}")
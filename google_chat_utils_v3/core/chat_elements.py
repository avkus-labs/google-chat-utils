from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from google_chat_utils_v3.core.schema_elements import SchemaData, FunctionDefinition

class RunSettingsData:
    """
    Stores and provides access to data from 'runSettings' in Google AI Studio exports.
    """
    def __init__(self,
                 model: Optional[str] = None,
                 temperature: Optional[float] = None,
                 top_p: Optional[float] = None,
                 top_k: Optional[int] = None,
                 max_output_tokens: Optional[int] = None,
                 response_mime_type: Optional[str] = None,
                 response_schema: Optional[SchemaData] = None,
                 function_declarations: Optional[List[FunctionDefinition]] = None,
                 enable_code_execution: Optional[bool] = False,
                 enable_search_as_tool: Optional[bool] = False,
                 enable_browse_as_tool: Optional[bool] = False,
                 # Add any other relevant fields from runSettings
                 raw_settings: Optional[Dict[str, Any]] = None # To store original settings
                ):
        self.model: Optional[str] = model
        self.temperature: Optional[float] = temperature
        self.top_p: Optional[float] = top_p
        self.top_k: Optional[int] = top_k
        self.max_output_tokens: Optional[int] = max_output_tokens
        self.response_mime_type: Optional[str] = response_mime_type
        self.response_schema: Optional[SchemaData] = response_schema
        self.function_declarations: Optional[List[FunctionDefinition]] = function_declarations
        self.enable_code_execution: Optional[bool] = enable_code_execution
        self.enable_search_as_tool: Optional[bool] = enable_search_as_tool
        self.enable_browse_as_tool: Optional[bool] = enable_browse_as_tool
        self.raw_settings: Optional[Dict[str, Any]] = raw_settings if raw_settings else {}

    def __repr__(self) -> str:
        return (f"RunSettingsData(model='{self.model}', temperature={self.temperature}, "
                f"top_p={self.top_p}, top_k={self.top_k}, "
                f"max_output_tokens={self.max_output_tokens}, "
                f"response_mime_type='{self.response_mime_type}', "
                f"response_schema_present={self.response_schema is not None}, "
                f"function_declarations_count={len(self.function_declarations) if self.function_declarations else 0}, "
                f"enable_code_execution={self.enable_code_execution}, "
                f"enable_search_as_tool={self.enable_search_as_tool}, "
                f"enable_browse_as_tool={self.enable_browse_as_tool})")

class SystemInstruction:
    """
    Represents the system instruction for the model.
    """
    def __init__(self, text: str, source: Optional[str] = None):
        """
        Initializes a SystemInstruction object.

        Args:
            text: The content of the system instruction.
            source: Optional field to indicate the origin of the instruction, if applicable.
        """
        self.text: str = text
        self.source: Optional[str] = source

    def __repr__(self) -> str:
        return f"SystemInstruction(text='{self.text[:50]}...', source='{self.source}')"

class ChatMessagePart(ABC):
    """
    Abstract base class for a part of a chat message.
    A single chat message (turn) can consist of multiple parts of different types.
    """
    @abstractmethod
    def __repr__(self) -> str:
        pass

    # Potentially add a to_dict() or similar method if needed for serialization later
    # @abstractmethod
    # def to_dict(self) -> Dict[str, Any]:
    #     pass

class TextPart(ChatMessagePart):
    """Represents a simple text part of a message."""
    def __init__(self, content: str):
        self.content: str = content

    def __repr__(self) -> str:
        return f"TextPart(content='{self.content[:50]}...')"

    # def to_dict(self) -> Dict[str, Any]:
    #     return {"type": "text", "content": self.content}

class ThoughtsPart(ChatMessagePart):
    """Represents the 'thoughts' of the model during its generation process."""
    def __init__(self, content: str):
        self.content: str = content

    def __repr__(self) -> str:
        return f"ThoughtsPart(content='{self.content[:50]}...')"

    # def to_dict(self) -> Dict[str, Any]:
    #     return {"type": "thoughts", "content": self.content}

class ExecutableCodePart(ChatMessagePart):
    """Represents a block of code to be executed (e.g., by a code interpreter tool)."""
    def __init__(self, code_content: str, language: str = "PYTHON"): # Defaulting language to PYTHON
        self.code_content: str = code_content
        self.language: str = language

    def __repr__(self) -> str:
        return f"ExecutableCodePart(language='{self.language}', code_content='{self.code_content[:50]}...')"

class CodeExecutionResultPart(ChatMessagePart):
    """Represents the result of a code execution."""
    def __init__(self, output_content: str, outcome: str = "OK"): # Defaulting outcome
        self.output_content: str = output_content
        self.outcome: str = outcome # e.g., "OK", "ERROR", "TIMEOUT"

    def __repr__(self) -> str:
        return f"CodeExecutionResultPart(outcome='{self.outcome}', output_content='{self.output_content[:50]}...')"

class FunctionCallPart(ChatMessagePart):
    """Represents a function call made by the model."""
    def __init__(self, name: str, args: Dict[str, Any]):
        self.name: str = name
        self.args: Dict[str, Any] = args

    def __repr__(self) -> str:
        args_preview = str(self.args)[:50]
        return f"FunctionCallPart(name='{self.name}', args='{args_preview}...')"

class FunctionResponsePart(ChatMessagePart):
    """Represents the response from a function call."""
    def __init__(self, name: str, response_content: Dict[str, Any]):
        self.name: str = name # Should match the name of the function call it's responding to
        self.response_content: Dict[str, Any] = response_content

    def __repr__(self) -> str:
        response_preview = str(self.response_content)[:50]
        return f"FunctionResponsePart(name='{self.name}', response_content='{response_preview}...')"

class InlineDataPart(ChatMessagePart):
    """
    Represents inline data, typically for images or other media, encoded as base64.
    Corresponds to 'inlineData' in Google AI Studio format.
    """
    def __init__(self, mime_type: str, base64_data: str):
        self.mime_type: str = mime_type
        self.base64_data: str = base64_data # The actual base64 encoded string

    def __repr__(self) -> str:
        return f"InlineDataPart(mime_type='{self.mime_type}', base64_data_len={len(self.base64_data)})"

class UriReferencePart(ChatMessagePart):
    """
    Represents a reference to data via a URI.
    Covers various URI-based parts like 'driveImage', 'fileData', 'youtubeVideo', etc.
    """
    def __init__(self, source_type: str, identifier: str, mime_type: Optional[str] = None):
        """
        Initializes a UriReferencePart.

        Args:
            source_type: The type of the source (e.g., "google_drive_image", "file_uri", "youtube_video").
            identifier: The URI or ID that identifies the resource.
            mime_type: Optional MIME type of the referenced content.
        """
        self.source_type: str = source_type
        self.identifier: str = identifier
        self.mime_type: Optional[str] = mime_type

    def __repr__(self) -> str:
        return (f"UriReferencePart(source_type='{self.source_type}', "
                f"identifier='{self.identifier[:50]}...', mime_type='{self.mime_type}')")

class DialogueTurn:
    """
    Represents a single turn in the dialogue, containing one or more message parts.
    """
    def __init__(self,
                 role: str,
                 parts: List[ChatMessagePart],
                 turn_id: Optional[str] = None, # Optional ID for the turn
                 token_count: Optional[int] = None,
                 finish_reason: Optional[str] = None,
                 citations: Optional[List[Dict[str, Any]]] = None # For grounding/citations
                ):
        """
        Initializes a DialogueTurn.

        Args:
            role: The role of the entity making this turn (e.g., "user", "model").
            parts: A list of ChatMessagePart objects that make up this turn.
            turn_id: An optional identifier for this turn.
            token_count: Optional token count for this turn.
            finish_reason: Optional reason why the model finished generating this turn.
            citations: Optional list of citation metadata.
        """
        if not parts: # A turn should ideally have at least one part.
            # Consider if an empty turn is valid or should raise error/warning.
            # For now, allowing it but it's unusual.
            pass
        self.role: str = role
        self.parts: List[ChatMessagePart] = parts
        self.turn_id: Optional[str] = turn_id
        self.token_count: Optional[int] = token_count
        self.finish_reason: Optional[str] = finish_reason
        self.citations: Optional[List[Dict[str, Any]]] = citations if citations else []

    def __repr__(self) -> str:
        return (f"DialogueTurn(role='{self.role}', num_parts={len(self.parts)}, "
                f"turn_id='{self.turn_id}', finish_reason='{self.finish_reason}')")

class ToolConfiguration:
    """
    Represents information about configured tools for the model.
    Based on the 'tools_info' structure from the intermediate JSON.
    """
    def __init__(self,
                 type: str, # e.g., "code_execution", "function_declaration", "google_search", "browse"
                 functions: Optional[List[FunctionDefinition]] = None):
        """
        Initializes a ToolConfiguration.

        Args:
            type: The type of the tool.
            functions: A list of FunctionDefinition objects, if type is "function_declaration".
        """
        self.type: str = type
        self.functions: Optional[List[FunctionDefinition]] = functions

        if self.type == "function_declaration" and not self.functions:
            # print("Warning: ToolConfiguration type is 'function_declaration' but no functions provided.")
            pass # Allowing it, but it's unusual

    def __repr__(self) -> str:
        return (f"ToolConfiguration(type='{self.type}', "
                f"num_functions={len(self.functions) if self.functions else 0})")

class IntermediateChatData:
    """
    Root data object that aggregates all parsed chat information.
    This object is the primary output of the parser and input for the reconstructor.
    """
    def __init__(self,
                 source_file_name: str,
                 parsed_at_timestamp: str,
                 run_settings: RunSettingsData,
                 dialogue_history: List[DialogueTurn],
                 source_platform: str = "Google AI Studio",
                 system_instruction: Optional[SystemInstruction] = None,
                 tool_configurations: Optional[List[ToolConfiguration]] = None):
        self.source_file_name: str = source_file_name
        self.parsed_at_timestamp: str = parsed_at_timestamp
        self.run_settings: RunSettingsData = run_settings
        self.dialogue_history: List[DialogueTurn] = dialogue_history
        self.source_platform: str = source_platform
        self.system_instruction: Optional[SystemInstruction] = system_instruction
        self.tool_configurations: Optional[List[ToolConfiguration]] = tool_configurations if tool_configurations else []

    def __repr__(self) -> str:
        return (f"IntermediateChatData(source_file_name='{self.source_file_name}', "
                f"platform='{self.source_platform}', num_turns={len(self.dialogue_history)}, "
                f"num_tool_configs={len(self.tool_configurations) if self.tool_configurations else 0}, "
                f"has_system_instruction={self.system_instruction is not None})")


# Update the __main__ block to test new aggregate classes
if __name__ == '__main__':
    # (Keep existing tests for RunSettingsData, SystemInstruction, and ChatMessagePart children)
    # Test RunSettingsData
    rs_data = RunSettingsData(model="gemini-pro", temperature=0.7, enable_code_execution=True)
    print("--- Example RunSettingsData ---")
    print(rs_data)

    # Test SystemInstruction
    sys_instruction = SystemInstruction(text="You are a helpful AI assistant.", source="user_prompt")
    print("\n--- Example SystemInstruction ---")
    print(sys_instruction)

    # Test TextPart, ThoughtsPart, etc.
    text_part = TextPart(content="Hello, world! This is a test message.")
    thoughts_part = ThoughtsPart(content="The user is asking a question. I should try to answer it.")
    exec_code_part = ExecutableCodePart(code_content="print('Hello from executed code!')", language="PYTHON")
    code_res_part = CodeExecutionResultPart(output_content="Hello from executed code!", outcome="OK")
    func_call_part = FunctionCallPart(name="get_weather", args={"location": "London", "unit": "celsius"})
    func_resp_part = FunctionResponsePart(name="get_weather", response_content={"weather": "sunny", "temp": 25})
    b64_image_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    inline_data_part = InlineDataPart(mime_type="image/png", base64_data=b64_image_data)
    uri_ref_part = UriReferencePart(source_type="google_drive_image", identifier="12345abcdef", mime_type="image/jpeg")

    print("\n--- Example Individual ChatMessageParts ---")
    print(text_part)
    print(thoughts_part)
    print(exec_code_part)
    print(code_res_part)
    print(func_call_part)
    print(func_resp_part)
    print(inline_data_part)
    print(uri_ref_part)

    # Test DialogueTurn
    user_turn = DialogueTurn(
        role="user",
        parts=[TextPart(content="What's the weather like in London?"), uri_ref_part],
        turn_id="user_turn_001"
    )
    model_parts = [
        ThoughtsPart(content="User is asking for weather. I have the get_weather tool."),
        FunctionCallPart(name="get_weather", args={"location": "London", "unit": "celsius"})
    ]
    model_turn_tool_call = DialogueTurn(
        role="model",
        parts=model_parts,
        turn_id="model_turn_001a",
        finish_reason="TOOL_CODE_NOT_EXECUTED" # Example, or FUNCTION_CALL
    )
    tool_response_turn = DialogueTurn( # This would typically be a 'tool' or 'user' role in some systems, or part of model turn
        role="model", # Or "tool" - needs clarification based on how parser_v2 structures this for resolvedFunctionCall
        parts=[
            FunctionResponsePart(name="get_weather", response_content={"weather": "sunny", "temperature": "15 C"}),
            # Potentially followed by a text part from the model summarizing this
            TextPart(content="The weather in London is sunny, 15°C.")
        ],
        turn_id="model_turn_001b",
        finish_reason="COMPLETED"
    )
    print("\n--- Example DialogueTurns ---")
    print(user_turn)
    print(model_turn_tool_call)
    print(tool_response_turn)

    # Test ToolConfiguration
    # First, create a sample FunctionDefinition (requires SchemaData)
    param_schema = SchemaData(type="OBJECT", properties={"location": SchemaData(type="STRING")})
    func_def1 = FunctionDefinition(name="get_weather", description="Gets weather", parameters_schema=param_schema)

    tool_config_fc = ToolConfiguration(type="function_declaration", functions=[func_def1])
    tool_config_ce = ToolConfiguration(type="code_execution")
    print("\n--- Example ToolConfigurations ---")
    print(tool_config_fc)
    print(tool_config_ce)

    # Test IntermediateChatData
    chat_data = IntermediateChatData(
        source_file_name="my_chat_export.json",
        parsed_at_timestamp="2023-10-27T10:00:00Z",
        run_settings=rs_data,
        dialogue_history=[user_turn, model_turn_tool_call, tool_response_turn],
        system_instruction=sys_instruction,
        tool_configurations=[tool_config_fc, tool_config_ce]
        # source_platform will use its default
    )
    print("\n--- Example IntermediateChatData ---")
    print(chat_data)
    print(f"Chat Data RS Model: {chat_data.run_settings.model}")
    print(f"Chat Data SI Text: {chat_data.system_instruction.text if chat_data.system_instruction else 'None'}")
    print(f"Chat Data History Turn 1 Role: {chat_data.dialogue_history[0].role}")
    print(f"Chat Data Tool Config 1 Type: {chat_data.tool_configurations[0].type if chat_data.tool_configurations else 'None'}")

    print("\n--- All Class Tests in chat_elements.py Passed ---")

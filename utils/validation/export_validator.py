"""
Pydantic validation models and validator functions for Google AI Studio exports.

Supports validating:
1. Raw Google AI Studio JSON exports (runSettings, chunkedPrompt, systemInstruction)
2. Intermediate JSON files (IntermediateChatData format)
"""

import json
import os
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class StudioValidationError(Exception):
    """Raised when JSON data fails validation against expected schemas."""
    pass


# --- Pydantic Models for Raw Google AI Studio Export ---

class SafetySettingModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    category: Optional[str] = None
    threshold: Optional[str] = None


class FunctionDeclarationModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class StudioRunSettingsModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    topP: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    topK: Optional[int] = Field(default=None, ge=1)
    maxOutputTokens: Optional[int] = Field(default=None, ge=1)
    responseMimeType: Optional[str] = None
    responseSchema: Optional[Dict[str, Any]] = None
    safetySettings: Optional[List[SafetySettingModel]] = None
    functionDeclarations: Optional[List[FunctionDeclarationModel]] = None
    enableCodeExecution: Optional[bool] = None
    enableSearchAsATool: Optional[bool] = None
    enableBrowseAsATool: Optional[bool] = None
    enableAutoFunctionResponse: Optional[bool] = None


class StudioSystemInstructionModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    text: Optional[str] = None
    parts: Optional[List[Any]] = None


class ResolvedFunctionCall(BaseModel):
    model_config = ConfigDict(extra="allow")
    functionCall: Optional[Dict[str, Any]] = None
    response: Optional[Any] = None


class StudioChunkModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    text: Optional[str] = None
    role: Optional[str] = None
    tokenCount: Optional[int] = None
    isThought: Optional[bool] = None
    thoughtSignatures: Optional[List[Any]] = None
    finishReason: Optional[str] = None
    resolvedFunctionCall: Optional[ResolvedFunctionCall] = None


class StudioChunkedPromptModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    chunks: List[StudioChunkModel] = Field(default_factory=list)


class GoogleStudioExportModel(BaseModel):
    """
    Schema for raw Google AI Studio JSON exports.
    Requires at least chunkedPrompt or runSettings.
    """
    model_config = ConfigDict(extra="allow")
    runSettings: Optional[StudioRunSettingsModel] = None
    systemInstruction: Optional[Union[StudioSystemInstructionModel, str]] = None
    chunkedPrompt: Optional[StudioChunkedPromptModel] = None

    @model_validator(mode="after")
    def check_has_content(self) -> "GoogleStudioExportModel":
        if self.runSettings is None and self.chunkedPrompt is None:
            raise ValueError("Google AI Studio export must contain at least 'runSettings' or 'chunkedPrompt'.")
        return self


# --- Pydantic Models for Intermediate Chat Data ---

class DialogueTurnModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: str
    parts: List[Dict[str, Any]] = Field(default_factory=list)
    turn_id: Optional[Union[str, int]] = None
    token_count: Optional[int] = None
    finish_reason: Optional[str] = None


class ToolConfigModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    functions: Optional[List[Dict[str, Any]]] = None


class IntermediateChatDataModel(BaseModel):
    """
    Schema for intermediate JSON files produced by Google Chat Utils.
    """
    model_config = ConfigDict(extra="allow")
    source_file_name: Optional[str] = None
    parsed_at_timestamp: Optional[str] = None
    run_settings: Optional[Dict[str, Any]] = None
    dialogue_history: List[DialogueTurnModel]
    source_platform: Optional[str] = None
    system_instruction: Optional[Union[str, Dict[str, Any]]] = None
    tool_configurations: Optional[List[ToolConfigModel]] = None


# --- Validation Output and Helper Functions ---

class ValidationResult(BaseModel):
    """Result of validation check with details on format, errors, and warnings."""
    is_valid: bool
    format_type: str  # "studio_raw", "intermediate", "unknown"
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validated_model: Optional[Any] = None


def validate_studio_export(data: Union[Dict[str, Any], str]) -> ValidationResult:
    """
    Validates dictionary or JSON string against expected Studio or Intermediate schemas.

    Args:
        data: Python dictionary or JSON string.

    Returns:
        ValidationResult object.
    """
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                format_type="unknown",
                errors=[f"Invalid JSON syntax: {e}"]
            )

    if not isinstance(data, dict):
        return ValidationResult(
            is_valid=False,
            format_type="unknown",
            errors=[f"Expected a JSON object (dict), got {type(data).__name__}"]
        )

    # Check if this is IntermediateChatData format
    if "dialogue_history" in data and "tool_configurations" in data:
        try:
            model = IntermediateChatDataModel.model_validate(data)
            warnings = []
            if not model.dialogue_history:
                warnings.append("Dialogue history is empty.")
            return ValidationResult(
                is_valid=True,
                format_type="intermediate",
                warnings=warnings,
                validated_model=model
            )
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return ValidationResult(
                is_valid=False,
                format_type="intermediate",
                errors=errors
            )

    # Check if this is Raw Google AI Studio Export
    if "chunkedPrompt" in data or "runSettings" in data or "systemInstruction" in data:
        try:
            model = GoogleStudioExportModel.model_validate(data)
            warnings = []
            if model.chunkedPrompt and not model.chunkedPrompt.chunks:
                warnings.append("Chunked prompt has no message chunks.")
            return ValidationResult(
                is_valid=True,
                format_type="studio_raw",
                warnings=warnings,
                validated_model=model
            )
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return ValidationResult(
                is_valid=False,
                format_type="studio_raw",
                errors=errors
            )

    return ValidationResult(
        is_valid=False,
        format_type="unknown",
        errors=["Unrecognized JSON structure: does not match Studio export or IntermediateChatData format."]
    )


def validate_json_file(file_path: str) -> ValidationResult:
    """
    Validates a JSON file on disk.

    Args:
        file_path: Path to the JSON file.

    Returns:
        ValidationResult object.
    """
    if not os.path.isfile(file_path):
        return ValidationResult(
            is_valid=False,
            format_type="unknown",
            errors=[f"File not found: {file_path}"]
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except UnicodeDecodeError as e:
        return ValidationResult(
            is_valid=False,
            format_type="unknown",
            errors=[f"File encoding error (expected UTF-8): {e}"]
        )
    except json.JSONDecodeError as e:
        return ValidationResult(
            is_valid=False,
            format_type="unknown",
            errors=[f"JSON syntax error: {e}"]
        )
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            format_type="unknown",
            errors=[f"Could not read file: {e}"]
        )

    return validate_studio_export(data)


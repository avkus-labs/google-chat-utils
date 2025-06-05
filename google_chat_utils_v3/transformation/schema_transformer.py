from typing import Any, Dict, List, Optional, Union
import json # For openai_to_gemini_schema's enum representation if needed by genai_types.Schema
from google_chat_utils_v3.core.schema_elements import SchemaData

# This map is similar to the one in reconstructor_v2.py
# It maps our SchemaData.type (which should be upper case like Gemini's API)
# to the genai.types.Type enum strings.
GEMINI_PYTHON_TYPE_MAP = {
    "STRING": "genai.types.Type.STRING",
    "NUMBER": "genai.types.Type.NUMBER",
    "INTEGER": "genai.types.Type.INTEGER",
    "BOOLEAN": "genai.types.Type.BOOLEAN",
    "OBJECT": "genai.types.Type.OBJECT",
    "ARRAY": "genai.types.Type.ARRAY",
    # Add other types if SchemaData supports them and they map directly
}

class SchemaTransformer:
    """
    Handles transformations related to JSON Schemas:
    1. Converting SchemaData object to Python code for genai.types.Schema.
    2. Converting OpenAI JSON schema (dict) to SchemaData object.
    3. Converting SchemaData object to OpenAI JSON schema (dict).
    """

    def gemini_schema_obj_to_python_code(self, schema_obj: SchemaData, current_indent: str = "    ") -> str:
        """
        Recursively converts a SchemaData object into a Python code string
        representing a genai.types.Schema object.

        Args:
            schema_obj: The SchemaData object to convert.
            current_indent: The current indentation level string for pretty printing.

        Returns:
            A string of Python code for initializing a genai.types.Schema.
        """
        if not isinstance(schema_obj, SchemaData):
            # This case should ideally not be hit if called correctly
            return repr(schema_obj)

        py_type_const = GEMINI_PYTHON_TYPE_MAP.get(schema_obj.type.upper())

        if py_type_const is None:
            # Fallback for unknown types or if schema_obj.type is None/empty
            error_msg = f"UNKNOWN_SCHEMA_TYPE: {schema_obj.type}. Original: {schema_obj!r}"
            # Consider logging a warning here
            # print(f"Warning: Unknown schema type '{schema_obj.type}' in gemini_schema_obj_to_python_code.")
            # Return a Schema init with the error message in description for visibility
            return f"genai.types.Schema(description={repr(error_msg)})"

        args = [f"type={py_type_const}"]
        next_indent = current_indent + "    "  # 4 spaces for nesting

        if schema_obj.description:
            args.append(f"description={repr(schema_obj.description)}")

        if schema_obj.nullable is True: # Explicitly check for True
            args.append("nullable=True")

        if schema_obj.type.upper() == "OBJECT":
            if schema_obj.properties:
                props_code_list = []
                for key, value_schema_obj in schema_obj.properties.items():
                    prop_code = self.gemini_schema_obj_to_python_code(value_schema_obj, next_indent + "    ") # Indent for value
                    props_code_list.append(f"{repr(key)}: {prop_code}")

                if props_code_list:
                    properties_body = (f",\n{next_indent}    ").join(props_code_list)
                    args.append(f"properties={{\n{next_indent}    {properties_body}\n{next_indent}}}")
                else:
                    args.append("properties={}") # Empty object
            else:
                args.append("properties={}") # No properties defined

            if schema_obj.required: # Should be a list of strings
                args.append(f"required={repr(schema_obj.required)}")

        elif schema_obj.type.upper() == "ARRAY":
            if schema_obj.items:
                items_code = self.gemini_schema_obj_to_python_code(schema_obj.items, next_indent)
                args.append(f"items={items_code}")
            # Else: array without items schema - genai.types.Schema might support it or default

        if schema_obj.enum: # Assuming enum is relevant for types like STRING
            args.append(f"enum={repr(schema_obj.enum)}")


        # Format arguments for multiline if many, or single line if few.
        if len(args) > 2 or "properties={" in args[-1] or "items=" in args[-1]:
            return f"genai.types.Schema(\n{next_indent}" + f",\n{next_indent}".join(args) + f"\n{current_indent})"
        else:
            return f"genai.types.Schema({', '.join(args)})"

    def openai_to_gemini_schema(self, openai_schema_dict: Dict[str, Any]) -> SchemaData:
        """
        Recursively converts an OpenAI JSON schema (dict) to a SchemaData object.
        The 'type' in SchemaData will be stored in UPPERCASE (e.g., "STRING", "OBJECT").
        """
        if not isinstance(openai_schema_dict, dict):
            # This might happen if a sub-schema is not a dict. Handle gracefully.
            # print(f"Warning: Expected dict for OpenAI schema, got {type(openai_schema_dict)}. Value: {openai_schema_dict}")
            # Depending on policy, could raise error or return a default/error SchemaData.
            # For now, creating a "default" or "error" schema.
            return SchemaData(type="STRING", description=f"Error: Invalid OpenAI schema part: {openai_schema_dict!r}")

        # Handle 'type' potentially being a list (e.g., ["string", "null"])
        oai_type = openai_schema_dict.get("type")
        nullable = False
        final_type_str = "STRING" # Default type if parsing fails

        if isinstance(oai_type, list):
            if "null" in oai_type:
                nullable = True
            # Get the first non-"null" type from the list
            actual_types = [t for t in oai_type if t != "null"]
            if actual_types:
                final_type_str = actual_types[0].upper()
            # If only "null" was in list or list was empty, it defaults to STRING. Could be refined.
        elif isinstance(oai_type, str):
            final_type_str = oai_type.upper()
        elif oai_type is None and "properties" in openai_schema_dict : # Implicit object type
             final_type_str = "OBJECT"
        elif oai_type is None and "items" in openai_schema_dict: # Implicit array type
            final_type_str = "ARRAY"
        # else: final_type_str remains "STRING" or could be error/None

        # Map common OpenAI types to SchemaData types (ensure uppercase)
        # This mapping is mostly direct, just ensuring uppercase.
        type_mapping_upper = {
            "STRING": "STRING", "NUMBER": "NUMBER", "INTEGER": "INTEGER",
            "BOOLEAN": "BOOLEAN", "OBJECT": "OBJECT", "ARRAY": "ARRAY"
        }
        schema_data_type = type_mapping_upper.get(final_type_str, "STRING") # Default to STRING if type unknown

        description = openai_schema_dict.get("description")
        enum = openai_schema_dict.get("enum")
        required = openai_schema_dict.get("required")

        properties: Optional[Dict[str, SchemaData]] = None
        if schema_data_type == "OBJECT" and "properties" in openai_schema_dict:
            properties = {}
            for key, value_dict in openai_schema_dict["properties"].items():
                properties[key] = self.openai_to_gemini_schema(value_dict)

        items_schema: Optional[SchemaData] = None
        if schema_data_type == "ARRAY" and "items" in openai_schema_dict:
            items_schema = self.openai_to_gemini_schema(openai_schema_dict["items"])

        # Handle 'format' from OpenAI schema - genai doesn't directly use it in Schema,
        # but it can be stored in description if needed.
        # For now, ignoring 'format' unless it's critical.

        return SchemaData(
            type=schema_data_type,
            description=description,
            nullable=nullable,
            properties=properties,
            items=items_schema,
            enum=enum,
            required=required
        )

    def gemini_schema_to_openai_dict(self, schema_obj: SchemaData) -> Dict[str, Any]:
        """
        Recursively converts a SchemaData object to an OpenAI JSON schema (dict).
        The 'type' in OpenAI schema will be lowercase.
        """
        if not isinstance(schema_obj, SchemaData):
            # Should not happen with correct usage
            return {"description": f"Error: Invalid SchemaData object: {schema_obj!r}"}

        # Map SchemaData types (UPPERCASE) to OpenAI types (lowercase)
        type_mapping_lower = {
            "STRING": "string", "NUMBER": "number", "INTEGER": "integer",
            "BOOLEAN": "boolean", "OBJECT": "object", "ARRAY": "array"
        }
        oai_type_str = type_mapping_lower.get(schema_obj.type, schema_obj.type.lower() if schema_obj.type else "string")

        result_dict: Dict[str, Any] = {}

        if schema_obj.nullable and oai_type_str not in ("object", "array"): # Per OpenAI spec for nullable
            result_dict["type"] = [oai_type_str, "null"]
        else:
            result_dict["type"] = oai_type_str
            if schema_obj.nullable and oai_type_str in ("object", "array"): # OpenAPI 3.0.x 'nullable: true'
                 result_dict["nullable"] = True


        if schema_obj.description:
            result_dict["description"] = schema_obj.description
        if schema_obj.enum:
            result_dict["enum"] = schema_obj.enum

        if schema_obj.type.upper() == "OBJECT":
            if schema_obj.properties:
                result_dict["properties"] = {}
                for key, value_schema_obj in schema_obj.properties.items():
                    result_dict["properties"][key] = self.gemini_schema_to_openai_dict(value_schema_obj)
            if schema_obj.required:
                result_dict["required"] = schema_obj.required

        elif schema_obj.type.upper() == "ARRAY":
            if schema_obj.items:
                result_dict["items"] = self.gemini_schema_to_openai_dict(schema_obj.items)

        return result_dict

if __name__ == '__main__':
    transformer = SchemaTransformer()

    # 1. Test gemini_schema_obj_to_python_code
    print("--- Test: SchemaData to Python Code ---")
    complex_schema_obj = SchemaData(
        type="OBJECT",
        description="User details",
        nullable=True,
        properties={
            "name": SchemaData(type="STRING", description="Full name of the user"),
            "age": SchemaData(type="INTEGER", description="Age in years", nullable=True),
            "address": SchemaData(
                type="OBJECT",
                properties={
                    "street": SchemaData(type="STRING"),
                    "city": SchemaData(type="STRING")
                },
                required=["street", "city"]
            ),
            "scores": SchemaData(type="ARRAY", items=SchemaData(type="NUMBER"))
        },
        required=["name", "address"]
    )
    python_code = transformer.gemini_schema_obj_to_python_code(complex_schema_obj, current_indent="    ")
    print(python_code)
    # A simple visual check is needed here, or exec(generated_code) in a context with genai.types mock/real
    assert "genai.types.Type.OBJECT" in python_code
    assert "properties={" in python_code
    assert "name" in python_code
    assert "nullable=True" in python_code # For 'age' and top-level 'User details'

    # 2. Test openai_to_gemini_schema
    print("\n--- Test: OpenAI Dict to SchemaData Object ---")
    openai_schema_example = {
        "type": "object",
        "description": "Product information",
        "properties": {
            "productId": {"type": "string", "description": "Unique product identifier"},
            "price": {"type": "number"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "status": {"type": ["string", "null"], "enum": ["available", "out_of_stock"]}
        },
        "required": ["productId", "price"]
    }
    gemini_schema_data_obj = transformer.openai_to_gemini_schema(openai_schema_example)
    print(gemini_schema_data_obj)
    assert gemini_schema_data_obj.type == "OBJECT"
    assert gemini_schema_data_obj.description == "Product information"
    assert gemini_schema_data_obj.properties is not None
    assert "productId" in gemini_schema_data_obj.properties
    assert gemini_schema_data_obj.properties["productId"].type == "STRING"
    assert gemini_schema_data_obj.properties["tags"].type == "ARRAY"
    assert gemini_schema_data_obj.properties["tags"].items.type == "STRING"
    assert gemini_schema_data_obj.properties["status"].type == "STRING" # Type is string
    assert gemini_schema_data_obj.properties["status"].nullable is True # Nullable from list
    assert gemini_schema_data_obj.properties["status"].enum == ["available", "out_of_stock"]
    assert gemini_schema_data_obj.required == ["productId", "price"]


    # 3. Test gemini_schema_to_openai_dict
    print("\n--- Test: SchemaData Object to OpenAI Dict ---")
    # Use the object created from the previous test
    reverted_openai_dict = transformer.gemini_schema_to_openai_dict(gemini_schema_data_obj)
    print(json.dumps(reverted_openai_dict, indent=2))

    # Check some key aspects of the conversion
    assert reverted_openai_dict["type"] == "object"
    assert reverted_openai_dict["properties"]["productId"]["type"] == "string"
    assert reverted_openai_dict["properties"]["tags"]["type"] == "array"
    assert reverted_openai_dict["properties"]["tags"]["items"]["type"] == "string"
    # For "status", which was type: ["string", "null"] in OAI, and became SchemaData(type="STRING", nullable=True)
    # it should revert to type: ["string", "null"] if not object/array.
    assert reverted_openai_dict["properties"]["status"]["type"] == ["string", "null"]
    assert reverted_openai_dict["properties"]["status"]["enum"] == ["available", "out_of_stock"]
    assert "nullable" not in reverted_openai_dict["properties"]["status"] # because type is a list with "null"

    # Test nullable for object/array in gemini_schema_to_openai_dict
    nullable_object_schema = SchemaData(type="OBJECT", nullable=True, properties={"key": SchemaData(type="STRING")})
    reverted_nullable_object = transformer.gemini_schema_to_openai_dict(nullable_object_schema)
    print(json.dumps(reverted_nullable_object, indent=2))
    assert reverted_nullable_object["type"] == "object"
    assert reverted_nullable_object["nullable"] is True


    print("\n--- SchemaTransformer tests completed ---")

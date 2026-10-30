from typing import List, Dict, Any, Optional

class SchemaData:
    """
    Represents a JSON Schema definition.

    This class is used to recursively define the structure of data,
    especially for function parameters and response schemas.
    """
    def __init__(self,
                 type: str,
                 description: Optional[str] = None,
                 nullable: Optional[bool] = False, # Changed default to False as per common practice
                 properties: Optional[Dict[str, 'SchemaData']] = None,
                 items: Optional['SchemaData'] = None,
                 enum: Optional[List[Any]] = None,
                 required: Optional[List[str]] = None):
        """
        Initializes a SchemaData object.

        Args:
            type: The type of the schema element (e.g., "OBJECT", "STRING", "ARRAY").
            description: A description of the schema element.
            nullable: Whether the schema element can be null.
            properties: A dictionary of child SchemaData objects for "OBJECT" type.
                        Keys are property names.
            items: A SchemaData object describing the items for "ARRAY" type.
            enum: A list of possible values for the schema element.
            required: A list of required property names for "OBJECT" type.
        """
        self.type: str = type
        self.description: Optional[str] = description
        self.nullable: Optional[bool] = nullable
        self.properties: Optional[Dict[str, 'SchemaData']] = properties
        self.items: Optional['SchemaData'] = items
        self.enum: Optional[List[Any]] = enum
        self.required: Optional[List[str]] = required

    def __repr__(self) -> str:
        return (f"SchemaData(type='{self.type}', "
                f"description='{self.description}', "
                f"nullable={self.nullable}, "
                f"properties={self.properties is not None}, " # Just indicate presence
                f"items={self.items is not None}, "       # Just indicate presence
                f"enum={self.enum}, "
                f"required={self.required})")

    def to_dict(self) -> dict:
        result = {
            "type": self.type,
        }
        if self.description is not None:
            result["description"] = self.description
        if self.nullable is not None:
            result["nullable"] = self.nullable
        if self.properties is not None:
            result["properties"] = {k: v.to_dict() for k, v in self.properties.items()}
        if self.items is not None:
            result["items"] = self.items.to_dict()
        if self.enum is not None:
            result["enum"] = self.enum
        if self.required is not None:
            result["required"] = self.required
        return result

    @staticmethod
    def from_dict(data: dict):
        if data is None:
            return None
        type_ = data.get('type')
        description = data.get('description')
        nullable = data.get('nullable', False)
        properties = None
        if 'properties' in data and data['properties'] is not None:
            properties = {k: SchemaData.from_dict(v) for k, v in data['properties'].items()}
        items = SchemaData.from_dict(data['items']) if 'items' in data and data['items'] is not None else None
        enum = data.get('enum')
        required = data.get('required')
        return SchemaData(
            type=type_,
            description=description,
            nullable=nullable,
            properties=properties,
            items=items,
            enum=enum,
            required=required
        )

# Type alias for function parameters, as they are defined by a SchemaData
FunctionParameter = SchemaData

class FunctionDefinition:
    """
    Represents the definition of a function that can be called by the model.
    """
    def __init__(self,
                 name: str,
                 description: str,
                 parameters_schema: SchemaData):
        """
        Initializes a FunctionDefinition object.

        Args:
            name: The name of the function.
            description: A description of what the function does.
            parameters_schema: A SchemaData object defining the parameters of the function.
                               This schema should be of type "OBJECT".
        """
        if not name:
            raise ValueError("Function name cannot be empty.")
        if parameters_schema.type != "OBJECT":
            # While technically any schema could be here, function parameters are typically an object.
            # Consider if this restriction is always desired or if a warning is better.
            # For now, enforcing OBJECT type for clarity of typical usage.
            pass # Relaxing this to allow any schema, though OBJECT is typical.

        self.name: str = name
        self.description: str = description
        self.parameters_schema: SchemaData = parameters_schema

    def __repr__(self) -> str:
        return (f"FunctionDefinition(name='{self.name}', "
                f"description='{self.description}', "
                f"parameters_schema={self.parameters_schema})")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters_schema": self.parameters_schema.to_dict() if self.parameters_schema else None
        }

    @staticmethod
    def from_dict(data: dict):
        return FunctionDefinition(
            name=data['name'],
            description=data['description'],
            parameters_schema=SchemaData.from_dict(data['parameters_schema'])
        )

if __name__ == '__main__':
    # Example Usage:
    # Define a schema for the parameters of a "get_weather" function
    weather_params_schema = SchemaData(
        type="OBJECT",
        description="Parameters for get_weather function",
        properties={
            "location": SchemaData(type="STRING", description="The city and state, e.g., San Francisco, CA"),
            "unit": SchemaData(type="STRING", description="Temperature unit", enum=["celsius", "fahrenheit"], nullable=True)
        },
        required=["location"]
    )

    get_weather_function_def = FunctionDefinition(
        name="get_weather",
        description="Get the current weather in a given location",
        parameters_schema=weather_params_schema
    )

    print("--- Example FunctionDefinition ---")
    print(get_weather_function_def)
    print(f"Function Name: {get_weather_function_def.name}")
    print(f"Function Description: {get_weather_function_def.description}")
    print(f"Parameters Schema Type: {get_weather_function_def.parameters_schema.type}")
    if get_weather_function_def.parameters_schema.properties:
        print("Parameters Properties:")
        for name, prop_schema in get_weather_function_def.parameters_schema.properties.items():
            print(f"  - {name}: {prop_schema}")

    # Example of a simple schema (not for function parameters directly, but valid SchemaData)
    simple_string_schema = SchemaData(type="STRING", description="A simple string.")
    print("\n--- Example Simple Schema ---")
    print(simple_string_schema)

    # Example of an array schema
    array_schema = SchemaData(
        type="ARRAY",
        description="A list of numbers",
        items=SchemaData(type="NUMBER")
    )
    print("\n--- Example Array Schema ---")
    print(array_schema)
    if array_schema.items:
        print(f"Array items type: {array_schema.items.type}")

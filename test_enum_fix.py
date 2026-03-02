"""
Quick test to verify enum conversion fix in bedrock_client.py
"""
import sys
import json
sys.path.insert(0, 'backend')

from core.bedrock_client import BedrockInstructorClient
from models.legal import LegalAgentState, WorkflowStatus
from pydantic import BaseModel

# Test the enum conversion logic directly
def test_enum_conversion():
    """Test that uppercase enum names are converted to lowercase values"""
    
    # Simulate what Bedrock returns (uppercase enum names)
    bedrock_response = {
        "workflow_status": "AWAITING_USER_INFO",  # UPPERCASE (wrong)
        "extracted_doc_data": "30-Day Eviction Notice",
        "next_question_for_user": "What is your name?",
        "user_consent_police": None,
        "drafts_to_generate": []
    }
    
    # Get the schema to understand enum values
    schema = LegalAgentState.model_json_schema()
    properties = schema.get("properties", {})
    defs = schema.get("$defs", {})
    
    # Function to get enum values, handling both inline and reference definitions
    def get_enum_values(field_schema):
        if "enum" in field_schema:
            return field_schema["enum"]
        if "$ref" in field_schema:
            ref_name = field_schema["$ref"].split("/")[-1]
            ref_schema = defs.get(ref_name, {})
            return ref_schema.get("enum", [])
        return []
    
    print(f"   Schema properties keys: {list(properties.keys())}")
    workflow_enum = get_enum_values(properties.get('workflow_status', {}))
    print(f"   workflow_status enum values: {workflow_enum}")
    
    print("✅ Testing enum conversion...")
    print(f"   Input enum value: {bedrock_response['workflow_status']} (uppercase)")
    
    # Simulate the conversion logic
    parsed_data = bedrock_response.copy()
    
    for field_name, field_value in list(parsed_data.items()):
        if isinstance(field_value, str) and field_name in properties:
            enum_values = get_enum_values(properties[field_name])
            if enum_values:
                if field_value not in enum_values:
                    matching_values = [e for e in enum_values if e.lower() == field_value.lower()]
                    if matching_values:
                        original = field_value
                        parsed_data[field_name] = matching_values[0]
                        print(f"   ✅ Converted '{field_name}': '{original}' -> '{matching_values[0]}'")
    
    # Try to create the model instance
    try:
        result = LegalAgentState(**parsed_data)
        print(f"\n✅ SUCCESS! Model created successfully")
        print(f"   workflow_status = {result.workflow_status}")
        print(f"   Type: {type(result.workflow_status)}")
        return True
    except ValueError as e:
        print(f"\n❌ FAILED! Validation error: {e}")
        return False

if __name__ == "__main__":
    # Change to backend directory for imports
    import os
    os.chdir('backend')
    
    success = test_enum_conversion()
    sys.exit(0 if success else 1)

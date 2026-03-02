"""
AWS Bedrock Client Wrapper for Instructor
------------------------------------------
Provides an instructor-compatible interface for AWS Bedrock LLMs.
"""

import boto3
import json
import instructor
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class BedrockInstructorClient:
    """
    Wrapper around AWS Bedrock that provides instructor-like structured output capability.
    Works with Llama and other Bedrock models.
    """
    
    def __init__(
        self,
        model_id: str,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        self.model_id = model_id
        
        # Initialize Bedrock Runtime client
        boto_kwargs = {"region_name": region_name}
        if aws_access_key_id and aws_secret_access_key:
            boto_kwargs["aws_access_key_id"] = aws_access_key_id
            boto_kwargs["aws_secret_access_key"] = aws_secret_access_key
        
        self.bedrock_runtime = boto3.client("bedrock-runtime", **boto_kwargs)
    
    async def chat_completions_create(
        self,
        response_model: Type[T],
        messages: list[Dict[str, str]],
        **kwargs
    ) -> T:
        """
        Instructor-compatible method that returns structured output.
        
        Args:
            response_model: Pydantic model to parse response into
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters (ignored for now)
        
        Returns:
            Instance of response_model with parsed data
        """
        
        # Convert messages to Bedrock Converse API format
        bedrock_messages = []
        system_prompt = None
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                system_prompt = content
            elif role == "user":
                bedrock_messages.append({
                    "role": "user",
                    "content": [{"text": content}]
                })
            elif role == "assistant":
                bedrock_messages.append({
                    "role": "assistant",
                    "content": [{"text": content}]
                })
        
        # Add instruction for JSON output
        schema = response_model.model_json_schema()
        
        # Extract required fields from schema
        required_fields = schema.get("required", [])
        required_info = f"\n\nREQUIRED FIELDS (must include all of these):\n" + ", ".join(required_fields) if required_fields else ""
        
        json_instruction = f"""
You must respond with ONLY valid JSON that matches this exact schema:
{json.dumps(schema, indent=2)}
{required_info}

CRITICAL INSTRUCTIONS:
1. Include ALL required fields in your JSON response. Do not omit any fields marked as required.
2. For enum fields (fields with "enum" list), use the EXACT values from the enum list in lowercase.
3. Do not use UPPERCASE names like AWAITING_USER_INFO; use the lowercase values like awaiting_user_info.
4. Do not include any explanatory text before or after the JSON. Output pure JSON only.
"""
        
        # Append JSON instruction to last user message or create new one
        if bedrock_messages:
            last_msg = bedrock_messages[-1]
            if last_msg["role"] == "user":
                last_msg["content"][0]["text"] += "\n\n" + json_instruction
            else:
                bedrock_messages.append({
                    "role": "user",
                    "content": [{"text": json_instruction}]
                })
        else:
            bedrock_messages.append({
                "role": "user",
                "content": [{"text": json_instruction}]
            })
        
        # Build Converse API request
        request_body = {
            "modelId": self.model_id,
            "messages": bedrock_messages,
            "inferenceConfig": {
                "maxTokens": 4096,
                "temperature": 0.7,
                "topP": 0.9,
            }
        }
        
        if system_prompt:
            request_body["system"] = [{"text": system_prompt}]
        
        # Call Bedrock
        try:
            response = self.bedrock_runtime.converse(**request_body)
            
            # Extract response text
            output_message = response['output']['message']
            response_text = output_message['content'][0]['text']
            
            # Parse JSON and create Pydantic model
            # Handle potential markdown code blocks
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            try:
                parsed_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"❌ JSON Parse Error: {e}")
                print(f"   Response was: {response_text[:500]}")
                raise ValueError(f"Model did not return valid JSON: {e}")
            
            # Get schema for enum conversion and field validation
            schema = response_model.model_json_schema()
            properties = schema.get("properties", {})
            defs = schema.get("$defs", {})
            
            # Helper function to get enum values (handles both inline and $ref formats)
            def get_enum_values(field_schema):
                """Extract enum values from field schema, handling $ref references."""
                if "enum" in field_schema:
                    return field_schema["enum"]
                if "$ref" in field_schema:
                    ref_name = field_schema["$ref"].split("/")[-1]
                    ref_schema = defs.get(ref_name, {})
                    return ref_schema.get("enum", [])
                return []
            
            # Convert uppercase enum names to lowercase enum values
            # (e.g., "AWAITING_USER_INFO" -> "awaiting_user_info")
            for field_name, field_value in list(parsed_data.items()):
                if isinstance(field_value, str) and field_name in properties:
                    enum_values = get_enum_values(properties[field_name])
                    if enum_values:
                        # Check if value is in enum (correct format)
                        if field_value not in enum_values:
                            # Try to find matching enum value with case-insensitive comparison
                            matching_values = [e for e in enum_values if e.lower() == field_value.lower()]
                            if matching_values:
                                original = field_value
                                parsed_data[field_name] = matching_values[0]
                                print(f"  🔄 Converting enum '{field_name}': '{original}' -> '{matching_values[0]}'")
            
            # Fill in any missing required fields with defaults
            required_fields = schema.get("required", [])
            for field in required_fields:
                if field not in parsed_data or parsed_data[field] is None:
                    print(f"⚠️  Missing required field '{field}' in response - using default")
                    # Try to infer a sensible default
                    field_schema = properties.get(field, {})
                    enum_values = get_enum_values(field_schema)
                    if enum_values:
                        parsed_data[field] = enum_values[0]
                    elif field_schema.get("type") == "string":
                        parsed_data[field] = "unknown"
                    elif "default" in field_schema:
                        parsed_data[field] = field_schema["default"]
            
            try:
                return response_model(**parsed_data)
            except ValueError as e:
                # Pydantic validation error
                print(f"❌ Validation Error: {e}")
                print(f"   Response data: {json.dumps(parsed_data, indent=2)}")
                required = schema.get("required", [])
                print(f"   Required fields: {required}")
                print(f"   Missing fields: {[f for f in required if f not in parsed_data or parsed_data[f] is None]}")
                raise
            
        except Exception as e:
            print(f"❌ Bedrock API Error: {e}")
            raise


class BedrockChatCompletions:
    """
    Mimics OpenAI's chat.completions interface for simple text generation.
    """
    
    def __init__(self, bedrock_runtime, model_id: str):
        self.bedrock_runtime = bedrock_runtime
        self.model_id = model_id
    
    async def create(
        self,
        model: str = None,  # Ignored, uses self.model_id
        messages: list[Dict[str, str]] = None,
        **kwargs
    ) -> Any:
        """
        Simple text completion (non-structured) for memory summarization.
        """
        bedrock_messages = []
        system_prompt = None
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                system_prompt = content
            elif role == "user":
                bedrock_messages.append({
                    "role": "user",
                    "content": [{"text": content}]
                })
            elif role == "assistant":
                bedrock_messages.append({
                    "role": "assistant",
                    "content": [{"text": content}]
                })
        
        request_body = {
            "modelId": self.model_id,
            "messages": bedrock_messages,
            "inferenceConfig": {
                "maxTokens": 2048,
                "temperature": 0.5,
            }
        }
        
        if system_prompt:
            request_body["system"] = [{"text": system_prompt}]
        
        response = self.bedrock_runtime.converse(**request_body)
        output_text = response['output']['message']['content'][0]['text']
        
        # Return OpenAI-like response structure
        class Choice:
            def __init__(self, text):
                self.message = type('Message', (), {'content': text})()
        
        class Response:
            def __init__(self, text):
                self.choices = [Choice(text)]
        
        return Response(output_text)


class BedrockAsyncClient:
    """
    Mimics AsyncOpenAI interface for compatibility with existing code.
    """
    
    def __init__(self, bedrock_runtime, model_id: str):
        self.bedrock_runtime = bedrock_runtime
        self.model_id = model_id
        self.chat = type('Chat', (), {
            'completions': BedrockChatCompletions(bedrock_runtime, model_id)
        })()

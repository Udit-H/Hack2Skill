from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv
import os
from typing import List, Optional

load_dotenv()

class DocumentIntelligenceSettings(BaseSettings):
    api_key: Optional[str] = os.getenv("DOCUMENT_INTELLIGENCE_API_KEY", "")
    endpoint: Optional[str] = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT", "")

class LLMSettings(BaseSettings):
    provider: str = os.getenv("LLM_PROVIDER", "bedrock")  # "bedrock" or "openai"
    model_id: str = os.getenv("LLM_MODEL_ID", "us.meta.llama3-2-90b-instruct-v1:0")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    # Legacy OpenAI/Gemini support
    api_key: Optional[str] = os.getenv("GEMINI_API_KEY", "")
    base_url: Optional[str] = os.getenv("GEMINI_BASE_URL", "")

class RedisDbSettings(BaseSettings):
    host: Optional[str] = os.getenv("REDIS_HOST", "localhost")
    password: Optional[str] = os.getenv("REDIS_PASSWORD", "")
    db_name: Optional[str] = os.getenv("REDIS_DB_NAME", "0")

class Settings(BaseSettings):
    document_intelligence: DocumentIntelligenceSettings = DocumentIntelligenceSettings()
    llm: LLMSettings = LLMSettings()
    redisdb: RedisDbSettings = RedisDbSettings()


@lru_cache
def get_settings():
    return Settings()

# Create global settings instance
settings = Settings()
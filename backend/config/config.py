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
    api_key: str = os.getenv("GEMINI_API_KEY", "")
    base_url: str = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")

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
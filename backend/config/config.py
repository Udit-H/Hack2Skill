from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv
import os
from typing import List

load_dotenv()

class DocumentIntelligenceSettings(BaseSettings):
    api_key: str = os.getenv("DOCUMENT_INTELLIGENCE_API_KEY")
    endpoint: str = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT")

class LLMSettings(BaseSettings):
    api_key: str = os.getenv("GEMINI_API_KEY")
    base_url: str = os.getenv("GEMINI_BASE_URL")

class RedisDbSettings(BaseSettings):
    host: str = os.getenv("REDIS_HOST")
    password: str = os.getenv("REDIS_PASSWORD")
    db_name: str = os.getenv("REDIS_DB_NAME")

# class LangSmithSettings(BaseSettings):
#     tracing: str = os.getenv("LANGSMITH_TRACING", "false")
#     endpoint: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
#     api_key: str = os.getenv("LANGSMITH_API_KEY")
#     project: str = os.getenv("LANGSMITH_PROJECT")

class Settings(BaseSettings):
    document_intelligence: DocumentIntelligenceSettings = DocumentIntelligenceSettings()
    llm: LLMSettings = LLMSettings()
    redisdb: RedisDbSettings = RedisDbSettings()


@lru_cache
def get_settings():
    return Settings()

# Create global settings instance
settings = Settings()
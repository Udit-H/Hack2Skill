from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv
import os
from typing import List, Optional

load_dotenv()


def _clean_env_str(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().strip('"').strip("'")


def _clean_env_int(name: str, default: int) -> int:
    value = _clean_env_str(name, "")
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _clean_env_bool(name: str, default: bool = False) -> bool:
    value = _clean_env_str(name, "")
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}

class DocumentIntelligenceSettings(BaseSettings):
    api_key: Optional[str] = os.getenv("DOCUMENT_INTELLIGENCE_API_KEY", "")
    endpoint: Optional[str] = os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT", "")

class LLMSettings(BaseSettings):
    # AWS Bedrock (Primary LLM)
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    bedrock_model_id: str = os.getenv("BEDROCK_MODEL_ID", "us.meta.llama3-2-90b-instruct-v1:0")
    # Groq (Fallback LLM)
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model_id: str = os.getenv("GROQ_MODEL_ID", "llama-3.3-70b-versatile")

class RedisDbSettings(BaseSettings):
    url: Optional[str] = _clean_env_str("REDIS_URL", "")
    host: Optional[str] = _clean_env_str("REDIS_HOST", "localhost")
    password: Optional[str] = _clean_env_str("REDIS_PASSWORD", "")
    db_name: Optional[str] = _clean_env_str("REDIS_DB_NAME", "0")
    port: Optional[int] = _clean_env_int("REDIS_PORT", 6379)
    username: Optional[str] = _clean_env_str("REDIS_USERNAME", "default")
    ssl: bool = _clean_env_bool("REDIS_SSL", False)

class SupabaseDbSettings(BaseSettings):
    url: Optional[str] = os.getenv("SUPABASE_URL", "")
    pub_key: Optional[str] = os.getenv("SUPABASE_PUB_KEY", "")
    service_key: Optional[str] = os.getenv("SUPABASE_ANON_KEY", "")

class CohereSettings(BaseSettings):
    api_key: Optional[str] = os.getenv("COHERE_API_KEY", "")
    base_url: str = "https://api.cohere.ai/v2"
    client_name: str = "Development_Phase"
    timeout: float = 4.0

class ChromaDbSettings(BaseSettings):
    tenant: Optional[str] = os.getenv("CHROMA_TENANT", "")
    database: Optional[str] = os.getenv("CHROMA_DATABASE", "")
    token: Optional[str] = os.getenv("CHROMA_TOKEN", "")

class Settings(BaseSettings):
    document_intelligence: DocumentIntelligenceSettings = DocumentIntelligenceSettings()
    llm: LLMSettings = LLMSettings()
    redisdb: RedisDbSettings = RedisDbSettings()
    supabase: SupabaseDbSettings = SupabaseDbSettings()
    cohere: CohereSettings = CohereSettings()
    chromadb: ChromaDbSettings = ChromaDbSettings()


@lru_cache
def get_settings():
    return Settings()

# Create global settings instance
settings = Settings()
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


def _parse_redis_host_port(default_host: str = "localhost", default_port: int = 6379) -> tuple[str, int]:
    raw_host = _clean_env_str("REDIS_HOST", default_host)
    raw_port = _clean_env_str("REDIS_PORT", "")

    host = raw_host
    parsed_port = default_port

    # Support REDIS_HOST values like "redis.example.com:12908"
    if raw_host and ":" in raw_host and not raw_host.startswith("redis://"):
        host_parts = raw_host.rsplit(":", 1)
        if len(host_parts) == 2 and host_parts[1].isdigit():
            host = host_parts[0]
            parsed_port = int(host_parts[1])

    if raw_port:
        try:
            parsed_port = int(raw_port)
        except ValueError:
            pass

    return host, parsed_port

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
    _parsed_host, _parsed_port = _parse_redis_host_port()

    url: Optional[str] = _clean_env_str("REDIS_URL", "")
    host: Optional[str] = _parsed_host
    password: Optional[str] = _clean_env_str("REDIS_PASSWORD", "")
    db_name: Optional[str] = _clean_env_str("REDIS_DB_NAME", "0")
    port: Optional[int] = _parsed_port
    username: Optional[str] = _clean_env_str("REDIS_USERNAME", "")
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
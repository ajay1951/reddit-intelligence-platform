from typing import Any, Optional

from pydantic import PostgresDsn, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int
    database_url: Optional[PostgresDsn] = None

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: Any) -> Any:
        if isinstance(v, str):
            return v
        return str(PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=info.data.get("postgres_user"),
            password=info.data.get("postgres_password"),
            host=info.data.get("postgres_host"),
            port=info.data.get("postgres_port"),
            path=f"/{info.data.get('postgres_db') or ''}",
        ))

    # App
    app_host: str
    app_port: int
    log_level: str
    scheduler_enabled: bool = True
    scheduler_job_store_url: Optional[str] = None

    # Scraper
    scraper_concurrency: int
    scraper_rate_limit_per_sec: int

    # ChromaDB
    chroma_persist_directory: str = "./chroma_data"
    chroma_tenant: str = "default_tenant"
    chroma_database: str = "default_database"
    chroma_collection_name: str = "reddit_collection"

    # AI & Search
    ollama_base_url: Optional[str] = None
    ollama_embedding_model: Optional[str] = None
    ollama_rag_model: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    openrouter_api_keys: str = ""
    openrouter_embedding_model: str = "nvidia/llama-nemotron-embed-vl-1b-v2:free"
    openrouter_rag_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    openrouter_fallback_rag_models: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
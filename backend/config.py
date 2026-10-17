from typing import Any, List, Optional
import os
import warnings

from pydantic import AliasChoices, PostgresDsn, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Environment
    app_env: str = Field("development", validation_alias=AliasChoices("APP_ENV", "app_env"))


    # Database
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int
    database_url: Optional[PostgresDsn] = None
    db_pool_size: int = 10
    db_max_overflow: int = 5

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

    # Security & Auth
    jwt_secret_key: str = "dev-insecure-secret-key-change-in-production-min-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    admin_api_key: Optional[str] = None
    admin_username: str = Field("admin", validation_alias=AliasChoices("ADMIN_USERNAME", "admin_username"))
    admin_password: str = Field("admin123", validation_alias=AliasChoices("ADMIN_PASSWORD", "admin_password"))
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,https://34.100.209.41.sslip.io"

    # Scraper & Ingestion Engine
    scraper_concurrency: int
    scraper_rate_limit_per_sec: int
    apify_api_token: Optional[str] = None
    ingestion_provider: str = Field("auto", validation_alias=AliasChoices("INGESTION_PROVIDER", "ingestion_provider"))

    # ChromaDB
    chroma_persist_directory: str = "./chroma_data"
    chroma_tenant: str = "default_tenant"
    chroma_database: str = "default_database"
    chroma_collection_name: str = "reddit_collection"

    # AI & Search
    ollama_base_url: Optional[str] = None
    ollama_embedding_model: Optional[str] = None
    ollama_rag_model: Optional[str] = None
    groq_api_key: Optional[str] = None
    groq_model: str = "llama3-8b-8192"
    hf_api_key: Optional[str] = None
    hf_embedding_model: str = "BAAI/bge-small-en-v1.5"

    # OpenRouter compatibility / rotation support
    openrouter_api_key: Optional[str] = None
    openrouter_api_keys: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        env = (self.app_env or "development").strip().lower()
        if env == "production":
            # 1. JWT secret key validation
            insecure_placeholders = {
                "super-secret-enterprise-key-do-not-use-in-prod",
                "dev-insecure-secret-key-change-in-production-min-32-chars",
                "change-me",
                "secret",
                "jwt-secret",
                "replace-with-a-secure-random-secret-key",
            }
            if not self.jwt_secret_key or len(self.jwt_secret_key) < 32 or self.jwt_secret_key.lower() in insecure_placeholders:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: "
                    "JWT_SECRET_KEY must be configured in production with a strong random secret of at least 32 characters. "
                    "Do not use default or placeholder keys."
                )

            # 2. Database credentials validation
            if self.postgres_password in {"reddit", "postgres", "password", "root", "123456"}:
                warnings.warn(
                    "SECURITY WARNING: Production database password is using a common default dictionary password.",
                    UserWarning,
                    stacklevel=2,
                )

            # 3. Wildcard CORS with credentials validation
            origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
            if "*" in origins:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: "
                    "CORS_ORIGINS cannot contain wildcard '*' in production when credentials are enabled."
                )

            # 4. Admin credentials validation
            insecure_admin_passwords = {"admin123", "admin", "password", "123456", "secret", "root"}
            if not self.admin_password or self.admin_password.lower() in insecure_admin_passwords:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: "
                    "ADMIN_PASSWORD must be configured in production with a strong unique password. "
                    "Do not use default or placeholder credentials."
                )
        return self


settings = Settings()
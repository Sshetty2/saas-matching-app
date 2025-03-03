from functools import lru_cache
from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = os.path.join(BASE_DIR, ".env")

COMMON_SETTINGS_CONFIG = SettingsConfigDict(
    env_file=ENV_FILE,
    case_sensitive=True,
    extra="allow",
)


class LLMConfig(BaseSettings):
    """Configuration for Language Model settings"""

    openai_api_key: Optional[SecretStr] = Field(
        default=None, validation_alias="OPENAI_API_KEY"
    )
    openai_model: Optional[str] = Field(
        default="gpt-4o-mini", validation_alias="OPENAI_MODEL"
    )
    parser_model: Optional[str] = Field(
        default="gpt-4o-mini", validation_alias="PARSER_MODEL"
    )
    local_analysis_model: Optional[str] = Field(
        default="qwen2.5:14b", validation_alias="LOCAL_ANALYSIS_MODEL"
    )
    local_parse_model: Optional[str] = Field(
        default="llama3.1", validation_alias="LOCAL_PARSE_MODEL"
    )
    embedding_model: Optional[str] = Field(
        default="all-MiniLM-L6-v2", validation_alias="EMBEDDING_MODEL"
    )

    model_config = COMMON_SETTINGS_CONFIG


class ExecutionConfig(BaseSettings):
    """Configuration for execution settings"""

    use_local_model: Optional[bool] = Field(
        default=False, validation_alias="USE_LOCAL_MODEL"
    )
    use_vector_store: Optional[bool] = Field(
        default=False, validation_alias="USE_VECTOR_STORE"
    )

    model_config = COMMON_SETTINGS_CONFIG


class DBConfig(BaseSettings):
    """Configuration for database settings"""

    db_name: Optional[str] = Field(default=None, validation_alias="DB_NAME")
    db_server: Optional[str] = Field(default=None, validation_alias="DB_SERVER")
    db_table: Optional[str] = Field(default=None, validation_alias="DB_TABLE")
    db_user: Optional[str] = Field(default=None, validation_alias="DB_USER")
    db_password: Optional[SecretStr] = Field(
        default=None, validation_alias="DB_PASSWORD"
    )

    model_config = COMMON_SETTINGS_CONFIG


class LoggingConfig(BaseSettings):
    """Configuration for logging settings"""

    log_format: Optional[str] = Field(default="json", validation_alias="LOG_FORMAT")
    log_file: Optional[str] = Field(default="logs/app.log", validation_alias="LOG_FILE")

    model_config = COMMON_SETTINGS_CONFIG


class Settings(BaseSettings):
    """Global settings configuration"""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    db: DBConfig = Field(default_factory=DBConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        case_sensitive=True,
        extra="allow",
        env_nested_delimiter="__",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()

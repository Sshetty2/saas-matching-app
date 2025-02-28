from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class LLMConfig(BaseSettings):
    """Configuration for Language Model settings"""

    use_local_model: bool = Field(default=False, validation_alias="USE_LOCAL_MODEL")
    openai_api_key: SecretStr = Field(..., validation_alias="OPENAI_API_KEY")
    ai_online_model: str = Field(
        default="gpt-4o-mini", validation_alias="LLM_AGENT_MODEL"
    )
    parser_model: str = Field(
        default="gpt-4o-mini", validation_alias="LLM_PARSER_MODEL"
    )

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "allow",  # Allows extra env vars without validation error
    }


class LoggingConfig(BaseSettings):
    """Configuration for logging settings"""

    log_format: str = Field(default="json")
    log_file: str = Field(default="logs/app.log")

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "allow"}


class Settings(BaseSettings):
    """Global settings configuration"""

    llm: LLMConfig = LLMConfig()
    logging: LoggingConfig = LoggingConfig()

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "allow"}


from functools import lru_cache


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Create a global settings instance
settings = get_settings()

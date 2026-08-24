"""Application configuration settings for AI Universe."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application settings
    APP_NAME: str = "AI Universe"
    APP_ENV: str = "development"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "sqlite:///data/universe.db"

    # 10 Cloud Provider API Keys (Permanently Free Tier Providers)
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    GROQ_API_KEY: Optional[str] = Field(default=None)
    CEREBRAS_API_KEY: Optional[str] = Field(default=None)
    MISTRAL_API_KEY: Optional[str] = Field(default=None)
    OPENROUTER_API_KEY: Optional[str] = Field(default=None)
    COHERE_API_KEY: Optional[str] = Field(default=None)
    SAMBANOVA_API_KEY: Optional[str] = Field(default=None)
    HUGGINGFACE_API_KEY: Optional[str] = Field(default=None)
    CLOUDFLARE_API_KEY: Optional[str] = Field(default=None)
    CLOUDFLARE_ACCOUNT_ID: Optional[str] = Field(default=None)
    NVIDIA_API_KEY: Optional[str] = Field(default=None)

    # Integration Keys
    FRIDAY_API_KEY: Optional[str] = Field(default="dev_friday_key_secret_boundary")

    # Operational Budgets & Limits
    MAX_BUDGET: float = Field(default=10.0, description="Maximum budget per request in USD or compute credits")
    REQUEST_TIMEOUT: float = Field(default=60.0, description="Default timeout in seconds for provider calls")


settings = Settings()

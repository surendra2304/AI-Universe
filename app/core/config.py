"""Application configuration settings for AI Universe."""

from typing import Dict, List, Optional
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

    # 7 Active Cloud Provider API Keys (Supports single or comma-separated lists)
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    GEMINI_API_KEYS: Optional[str] = Field(default=None)

    GROQ_API_KEY: Optional[str] = Field(default=None)
    GROQ_API_KEYS: Optional[str] = Field(default=None)

    MISTRAL_API_KEY: Optional[str] = Field(default=None)
    MISTRAL_API_KEYS: Optional[str] = Field(default=None)

    OPENROUTER_API_KEY: Optional[str] = Field(default=None)
    OPENROUTER_API_KEYS: Optional[str] = Field(default=None)

    COHERE_API_KEY: Optional[str] = Field(default=None)
    COHERE_API_KEYS: Optional[str] = Field(default=None)

    HUGGINGFACE_API_KEY: Optional[str] = Field(default=None)
    HUGGINGFACE_API_KEYS: Optional[str] = Field(default=None)

    NVIDIA_API_KEY: Optional[str] = Field(default=None)
    NVIDIA_API_KEYS: Optional[str] = Field(default=None)

    # Integration Keys
    AI_UNIVERSE_API_KEY: Optional[str] = Field(default="ai_universe_api")
    FRIDAY_UNIVERSE_API_KEY: Optional[str] = Field(default=None)
    X_FRIDAY_API_KEY: Optional[str] = Field(default=None)
    FRIDAY_API_KEY: Optional[str] = Field(default=None)

    def get_friday_api_key(self) -> Optional[str]:
        return self.AI_UNIVERSE_API_KEY or self.FRIDAY_UNIVERSE_API_KEY or self.X_FRIDAY_API_KEY or self.FRIDAY_API_KEY

    # Operational Budgets & Limits (Unlimited Token Flow Mode)
    MAX_BUDGET: float = Field(default=999999.0, description="Unlimited budget - supplies all available tokens until provider quota exhausted")
    REQUEST_TIMEOUT: float = Field(default=60.0, description="Default timeout in seconds for provider calls")

    def get_provider_keys(self, provider_name: str) -> List[str]:
        """
        Returns a deduplicated list of non-empty API keys for the specified provider.
        Checks both plural (e.g. GEMINI_API_KEYS) and singular (e.g. GEMINI_API_KEY) variables.
        Supports comma-separated strings in both.
        """
        prov = provider_name.upper().strip()
        keys: List[str] = []

        singular_val = getattr(self, f"{prov}_API_KEY", None)
        plural_val = getattr(self, f"{prov}_API_KEYS", None)

        for raw_val in [plural_val, singular_val]:
            if raw_val:
                for k in raw_val.split(","):
                    cleaned = k.strip().strip("'\"")
                    if cleaned and cleaned not in keys:
                        keys.append(cleaned)

        return keys


settings = Settings()

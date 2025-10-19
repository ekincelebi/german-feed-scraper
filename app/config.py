from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    scrape_interval: int = Field(default=60, env="SCRAPE_INTERVAL")
    groq_api_key: str = Field(default="", env="GROQ_API_KEY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

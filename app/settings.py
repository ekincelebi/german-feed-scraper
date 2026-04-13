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

    @property
    def normalized_log_level(self) -> str:
        """Return a safe log level fallback for logger setup."""
        level = (self.log_level or "INFO").upper()
        valid_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        return level if level in valid_levels else "INFO"


# Global settings instance
settings = Settings()

from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/todo_ai_chatbot"

    # OpenAI settings
    OPENAI_API_KEY: str = ""

    # Better Auth settings
    BETTER_AUTH_SECRET: str = "your-super-secret-key-here-32+chars"

    # CORS settings
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # JWT settings (for fallback if needed)
    JWT_SECRET: str = "your-super-secret-jwt-key-here-32+chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 604800  # 7 days in seconds

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields in .env


settings = Settings()
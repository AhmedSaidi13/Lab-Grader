from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    APP_ENV:    str = "development"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM:  str = "HS256"

    DATABASE_URL:      str = "postgresql+asyncpg://grader:grader123@localhost:5432/graderdb"
    SYNC_DATABASE_URL: str = "postgresql://grader:grader123@localhost:5432/graderdb"
    REDIS_URL:         str = "redis://localhost:6379/0"
    SANDBOX_IMAGE:     str = "c-sandbox:latest"

    # This must match the Docker volume mount point
    UPLOAD_DIR:       str = "/app/uploads"
    MAX_FILE_SIZE_MB: int = 5

    ANTHROPIC_API_KEY: str  = ""
    USE_LLM_FEEDBACK:  bool = True

    class Config:
        env_file = ".env"
        extra    = "ignore"

    @property
    def upload_path(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def max_file_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    return Settings()
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "pointless"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite:///./pointless.db"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()

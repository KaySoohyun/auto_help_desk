from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Auto Help Desk API"
    api_v1_prefix: str = "/v1"

    secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "api.example.com"
    jwt_audience: str = "api.example.com"

    database_url: str = "sqlite:///./app.db"


settings = Settings()

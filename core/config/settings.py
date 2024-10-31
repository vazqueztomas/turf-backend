from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_NAME: str = Field(alias="DATABASE_NAME", env="DATABASE_NAME", default=None)
    DB_USER: str = Field(alias="DATABASE_USER", default=None)
    DB_PASSWORD: str = Field(alias="DATABASE_PASSWORD", default=None)
    DB_HOST: str = Field(alias="DATABASE_HOST", default=None)
    DB_PORT: int = Field(alias="DATABASE_PORT", default=None)
    DB_URI: str = Field(alias="DATABASE_URL", default=None)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

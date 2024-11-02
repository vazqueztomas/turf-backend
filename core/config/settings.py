from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Cargar las variables de entorno desde el archivo .env
load_dotenv()


class Settings(BaseSettings):
    db_name: str = Field(..., json_schema_extra={"env": "DB_NAME"})
    db_user: str = Field(..., json_schema_extra={"env": "DB_USER"})
    db_password: str = Field(..., json_schema_extra={"env": "DB_PASSWORD"})
    db_host: str = Field(..., json_schema_extra={"env": "DB_HOST"})
    db_port: int = Field(..., json_schema_extra={"env": "DB_PORT"})
    database_url: str = Field(..., json_schema_extra={"env": "DATABASE_URL"})

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()

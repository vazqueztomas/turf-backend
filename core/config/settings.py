from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Cargar las variables de entorno desde el archivo .env
load_dotenv()


class Settings(BaseSettings):
    environment: str = Field(..., json_schema_extra={"env": "ENVIRONMENT"})
    postgres_database: str = Field(..., json_schema_extra={"env": "POSTGRES_DATABASE"})
    postgres_user: str = Field(..., json_schema_extra={"env": "POSTGRES_USER"})
    postgres_password: str = Field(..., json_schema_extra={"env": "POSTGRES_PASSWORD"})
    postgres_host: str = Field(..., json_schema_extra={"env": "POSTGRES_HOST"})
    db_port: int = Field(
        5432, json_schema_extra={"env": "DB_PORT"}
    )  # Valor por defecto 5432
    postgres_url: str = Field(..., json_schema_extra={"env": "POSTGRES_URL"})

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()

# Configurar la URL de la base de datos basada en el entorno
if settings.environment == "DEVELOPMENT":
    settings.postgres_url = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.db_port}/{settings.postgres_database}"  # pylint: disable=line-too-long

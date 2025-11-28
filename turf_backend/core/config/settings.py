from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    environment: str = Field(..., json_schema_extra={"env": "ENVIRONMENT"})
    postgres_database: str = Field(..., json_schema_extra={"env": "POSTGRES_DATABASE"})
    postgres_user: str = Field(..., json_schema_extra={"env": "POSTGRES_USER"})
    postgres_password: str = Field(..., json_schema_extra={"env": "POSTGRES_PASSWORD"})
    postgres_host: str = Field(..., json_schema_extra={"env": "POSTGRES_HOST"})
    db_port: int = Field(5432, json_schema_extra={"env": "DB_PORT"})
    postgres_url: str = Field(..., json_schema_extra={"env": "POSTGRES_URL_NO_SSL"})

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    def get_database_url(self) -> str:
        if self.environment != "DEVELOPMENT" and self.postgres_url.startswith(
            "postgres://"
        ):
            return self.postgres_url.replace(
                "postgres://", "postgresql://", 1
            )  # pragma: no cover
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.db_port}/{self.postgres_database}"  # pylint: disable=line-too-long


settings = Settings()

database_url = settings.get_database_url()

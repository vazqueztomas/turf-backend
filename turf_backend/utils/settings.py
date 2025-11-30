from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class ApplicationSettings(BaseSettings):
    ENVIRONMENT: str = Field(..., json_schema_extra={"env": "ENVIRONMENT"})
    POSTGRES_DATABASE: str = Field(..., json_schema_extra={"env": "POSTGRES_DATABASE"})
    POSTGRES_USER: str = Field(..., json_schema_extra={"env": "POSTGRES_USER"})
    POSTGRES_PASSWORD: str = Field(..., json_schema_extra={"env": "POSTGRES_PASSWORD"})
    POSTGRES_HOST: str = Field(..., json_schema_extra={"env": "POSTGRES_HOST"})
    POSTGRES_PORT: int = Field(5432, json_schema_extra={"env": "POSTGRES_PORT"})
    POSTGRES_URL: str = Field(..., json_schema_extra={"env": "POSTGRES_URL_NO_SSL"})

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def PALERMO_DOWNLOAD_TEXT(self) -> str:
        return "Descargar VersiÃ³n PDF"

    @property
    def PALERMO_URL(self) -> str:
        return "https://www.palermo.com.ar/es/turf/programa-oficial"

    @property
    def DATABASE_URL(self) -> str:
        if self.ENVIRONMENT != "DEVELOPMENT" and self.POSTGRES_URL.startswith(
            "postgres://"
        ):
            return self.POSTGRES_URL.replace(
                "postgres://", "postgresql://", 1
            )  # pragma: no cover
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"  # pylint: disable=line-too-long


Settings = ApplicationSettings()  # type: ignore[call-arg]

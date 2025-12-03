from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class ApplicationSettings(BaseSettings):
    ENVIRONMENT: str
    POSTGRES_DATABASE: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_URL: str

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

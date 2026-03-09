from contextlib import contextmanager
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from turf_backend.core.config.settings import database_url, settings


class DatabaseConnection:
    def __init__(self, uri: str):
        is_dev = settings.environment == "DEVELOPMENT"
        self.engine = create_engine(
            uri,
            echo=is_dev,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        SQLModel.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        with Session(self.engine) as session:
            yield session


database = DatabaseConnection(database_url)


def get_connection() -> Generator[Session, None, None]:
    with database.get_session() as session:
        yield session

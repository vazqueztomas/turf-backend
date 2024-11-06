from contextlib import contextmanager
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from core.config.settings import settings


class DatabaseConnection:
    def __init__(self, uri: str):
        self.engine = create_engine(uri, echo=True)
        SQLModel.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        with Session(self.engine) as session:
            yield session


database_url = settings.postgres_url
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)


database = DatabaseConnection(database_url)


def get_connection() -> Generator[Session, None, None]:
    with database.get_session() as session:
        yield session

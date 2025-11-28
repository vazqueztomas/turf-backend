from collections.abc import Generator
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

from turf_backend.core.config.settings import database_url


class DatabaseConnection:
    def __init__(self, uri: str):
        self.engine = create_engine(uri, echo=True)
        SQLModel.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        with Session(self.engine) as session:
            yield session


database = DatabaseConnection(database_url)


def get_connection() -> Generator[Session, None, None]:
    with database.get_session() as session:
        yield session

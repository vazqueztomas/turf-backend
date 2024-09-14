from contextlib import contextmanager
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from core import settings


class DatabaseConnection:
    def __init__(self, uri):
        self.engine = create_engine(uri, echo=True)
        SQLModel.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        with Session(self.engine) as session:
            yield session


database = DatabaseConnection(settings.DB_URI)


def get_connection() -> Generator[Session, None, None]:
    with database.get_session() as session:
        yield session

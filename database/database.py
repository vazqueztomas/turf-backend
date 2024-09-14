
from contextlib import contextmanager
from typing import Generator
from core import settings
from sqlmodel import create_engine, Session, SQLModel


class DatabaseConnection:
    def __init__(self, uri):
        self.engine = create_engine(uri, echo=True)
        SQLModel.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        with Session(self.engine) as session:
            yield session


database = DatabaseConnection(settings.DB_URI)

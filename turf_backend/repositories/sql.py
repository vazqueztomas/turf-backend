from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlmodel import SQLModel, col, select

from turf_backend.database.database import get_connection

T = TypeVar("T", bound=SQLModel)


class SQLRepository(Generic[T]):
    """Generic SQL repository for CRUD operations on SQLModel models."""

    def __init__(self, model: type[T]):
        self.model = model

    def upsert(self, entity: T) -> T:
        """Insert or create a new record in the database."""
        with next(get_connection()) as session:
            session.add(entity)
            session.commit()
            session.refresh(entity)
            return entity

    def get_by_id(self, id: UUID) -> T | None:
        """Get a record by its primary key ID."""
        with next(get_connection()) as session:
            return session.get(self.model, id)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """Get all records with pagination."""
        with next(get_connection()) as session:
            statement = select(self.model).offset(skip).limit(limit)
            return list(session.exec(statement).all())

    def get_by_query(self, skip: int = 0, limit: int = 100, **filters: Any) -> list[T]:
        """Get records by filters with pagination. Supports ilike for string fields."""
        with next(get_connection()) as session:
            statement = select(self.model)

            for field_name, value in filters.items():
                if value is not None:
                    field = getattr(self.model, field_name)
                    if isinstance(value, str):
                        statement = statement.where(col(field).ilike(f"%{value}%"))  # type: ignore
                    else:
                        statement = statement.where(field == value)

            statement = statement.offset(skip).limit(limit)
            return list(session.exec(statement).all())

    def delete(self, entity: T) -> None:
        """Delete a record from the database."""
        with next(get_connection()) as session:
            session.delete(entity)
            session.commit()

    def delete_by_id(self, id: UUID) -> bool:
        """Delete a record by its primary key ID. Returns True if deleted, False if not found."""
        entity = self.get_by_id(id)
        if entity:
            self.delete(entity)
            return True
        return False

    def exists(self, id: UUID) -> bool:
        """Check if a record exists by its primary key ID."""
        return self.get_by_id(id) is not None

    def count(self) -> int:
        """Count total records."""
        with next(get_connection()) as session:
            statement = select(self.model)
            return len(list(session.exec(statement).all()))

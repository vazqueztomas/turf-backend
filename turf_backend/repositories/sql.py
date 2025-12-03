from typing import Any
from uuid import UUID

from sqlmodel import SQLModel, col, select

from turf_backend.database.database import get_connection


class SQLRepository[T: SQLModel]:
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

    def get_by_id(self, id_: UUID) -> T | None:
        """Get a record by its primary key ID."""
        with next(get_connection()) as session:
            return session.get(self.model, id_)

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

    def get_by_params(self, skip: int = 0, limit: int = 100, **params: Any) -> list[T]:
        """Get a list of records record matching the given parameters."""
        with next(get_connection()) as session:
            statement = select(self.model)

            for field_name, value in params.items():
                if value is not None:
                    field = getattr(self.model, field_name)
                    statement = statement.where(field == value)

            statement = statement.offset(skip).limit(limit)
            return list(session.exec(statement).all())

    def get_first_by_params(self, **params: Any) -> T | None:
        """Get the first record matching the given parameters."""
        result = self.get_by_params(skip=0, limit=1, **params)
        return result[0] if result else None

    def delete(self, entity: T) -> None:
        """Delete a record from the database."""
        with next(get_connection()) as session:
            session.delete(entity)
            session.commit()

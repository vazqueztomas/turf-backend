from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from .race import Race


class Horse(SQLModel, table=True):  # type: ignore[call-arg]
    __table_args__ = (
        UniqueConstraint("nombre", "numero", "page", name="uq_horse_unique"),
    )

    horse_id: UUID = Field(default_factory=uuid4, primary_key=True)
    race_id: UUID = Field(foreign_key="race.race_id")
    numero: str | None = Field(default=None, index=True)
    nombre: str | None = Field(default=None)
    peso: int | None = Field(default=None)
    jockey: str | None = Field(default=None)
    ultimas: str | None = Field(default=None)
    padre_madre: str | None = Field(default=None)
    entrenador: str | None = Field(default=None)
    raw_rest: str | None = Field(default=None)
    page: int | None = Field(default=None)
    line_index: int | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    caballeriza: str | None = Field(default=None)
    races: list["Race"] = Relationship(back_populates="horses")
    race: Optional["Race"] = Relationship(back_populates="horses")

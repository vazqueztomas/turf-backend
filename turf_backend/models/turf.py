from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


class AvailableLocations(str, Enum):
    PALERMO = "palermo"


class Horse(SQLModel, table=True):
    __tablename__ = "horses"
    __table_args__ = (
        UniqueConstraint("nombre", "numero", "page", name="uq_horse_unique"),
    )

    id: int | None = Field(default=None, primary_key=True)
    race_id: int | None = Field(default=None, foreign_key="races.id")
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

    race: Optional["Race"] = Relationship(back_populates="horses")


class Race(SQLModel, table=True):
    __tablename__ = "races"
    id: int | None = Field(default=None, primary_key=True)
    numero: int | None = Field(default=None, index=True)
    nombre: str | None = Field(default=None)
    distancia: int | None = Field(default=None)
    fecha: str | None = Field(default_factory=None)
    hipodromo: str | None = Field(default="Palermo")

    # relación inversa con Horse
    horses: list["Horse"] = Relationship(back_populates="race")

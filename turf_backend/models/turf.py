from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


class AvailableLocations(str, Enum):
    PALERMO = "palermo"


class Horse(SQLModel, table=True):
    __tablename__ = "horses"
    __table_args__ = (
        UniqueConstraint("nombre", "numero", "page", name="uq_horse_unique"),
    )

    id: int | None = Field(default=None, primary_key=True)
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

    race_links: list["RaceHorseLink"] = Relationship(back_populates="horse")


class Race(SQLModel, table=True):
    __tablename__ = "races"
    race_id: UUID = Field(default=uuid4(), primary_key=True, index=True)
    numero: int | None = Field(default=None, index=True)
    nombre: str | None = Field(default=None)
    distancia: int | None = Field(default=None)
    fecha: str | None = Field(default_factory=None)
    hipodromo: str | None = Field(default="Palermo")
    hour: str | None = Field(default=None)

    horse_links: list["RaceHorseLink"] = Relationship(back_populates="race")


class RaceHorseLink(SQLModel, table=True):
    __tablename__ = "race_horses"

    race_id: UUID = Field(foreign_key="races.race_id", primary_key=True)
    horse_id: int = Field(foreign_key="horses.id", primary_key=True)

    race: "Race" = Relationship(back_populates="horse_links")
    horse: "Horse" = Relationship(back_populates="race_links")

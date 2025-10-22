from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel, UniqueConstraint


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
    created_at: datetime = Field(default_factory=datetime.utcnow)

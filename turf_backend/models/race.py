from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


class Race(SQLModel, table=True):  # type: ignore[call-arg]
    race_id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    numero: int | None = Field(default=None, index=True)
    nombre: str | None = Field(default=None)
    distancia: int | None = Field(default=None)
    fecha: str | None = Field(default_factory=None)
    hipodromo: str | None = Field(default="Palermo")
    hour: str | None = Field(default=None)

    horses: list["Horse"] = Relationship(back_populates="race")  # type: ignore[name-defined] # noqa: F821

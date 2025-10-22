from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


class AvailableLocations(str, Enum):
    PALERMO = "palermo"


class Horse(SQLModel, table=True):
    __tablename__ = "horses"  # 👈 Asegurate de que diga "horses"

    id: int | None = Field(default=None, primary_key=True)
    numero: str | None = Field(
        default=None, index=True, description="Número en la carrera"
    )
    nombre: str | None = Field(default=None, description="Nombre del caballo")
    peso: int | None = Field(default=None, description="Peso asignado (kg)")
    jockey: str | None = Field(default=None, description="Nombre del jockey (limpio)")
    ultimas: str | None = Field(
        default=None, description="Resultados últimas 5 (texto)"
    )
    padre_madre: str | None = Field(
        default=None, description="Texto bruto padre - madre (heurístico)"
    )
    entrenador: str | None = Field(default=None, description="Entrenador (heurístico)")
    raw_rest: str | None = Field(
        default=None, description="Texto crudo a la derecha de 'peso' extraído del PDF"
    )
    page: int | None = Field(
        default=None, description="Página del PDF donde fue extraído"
    )
    line_index: int | None = Field(
        default=None, description="Índice de línea dentro de la página"
    )
    created_at: datetime = Field(default_factory=datetime.now)

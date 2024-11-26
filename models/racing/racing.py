import uuid

from pydantic import BaseModel


class Horse(BaseModel):
    id: uuid.UUID
    name: str
    jockey: str
    trainer: str
    parents: list[str]


class Racing(BaseModel):
    id: uuid.UUID
    number: int
    horses: list[Horse]
    distance: int
    date: str
    time: str

from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    email: EmailStr
    authorized: bool


class UserInDB(User):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    hashed_password: str
    authorized: bool = False  # Establecer un valor por defecto

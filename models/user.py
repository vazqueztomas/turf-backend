from typing import Optional

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(
        default=None, primary_key=True, description="Unique identifier for the user"
    )
    email: EmailStr = Field(description="User's email address")
    authorized: bool = Field(
        default=False, description="Whether the user is authorized"
    )
    hashed_password: str = Field(
        description="User's hashed password for authentication"
    )
    name: str = Field(description="User's full name")

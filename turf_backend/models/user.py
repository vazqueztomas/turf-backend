from uuid import UUID, uuid4

from pydantic import EmailStr
from sqlmodel import Field, SQLModel, UniqueConstraint


class User(SQLModel, table=True):  # type: ignore[call-arg]
    user_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        description="Unique identifier for the user",
    )
    email: EmailStr = Field(description="User's email address")
    authorized: bool = Field(
        default=False,
        description="Whether the user is authorized to access platform features",
    )
    hashed_password: str = Field(
        description="User's hashed password for authentication"
    )
    name: str = Field(description="User's full name")

    __table_args__ = (UniqueConstraint("email", name="uq_user_email"),)

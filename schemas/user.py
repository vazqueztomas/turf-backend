from pydantic import BaseModel, EmailStr, Field


class UserCreatePayload(BaseModel):
    email: EmailStr = Field(description="User's email address")
    password: str = Field(description="User's password")
    name: str = Field(description="User's full name")


class UserOut(BaseModel):
    email: EmailStr = Field(description="User's email address")
    name: str = Field(description="User's full name")
    authorized: bool = Field(description="Whether the user is authorized")

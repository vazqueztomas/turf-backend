from pydantic import BaseModel, EmailStr, Field


class UserCreatePayload(BaseModel):
    email: EmailStr = Field(description="User's email address")
    password: str = Field(description="User's password")


class UserOut(BaseModel):
    email: EmailStr = Field(description="User's email address")
    authorized: bool = Field(description="Whether the user is authorized")


class AccessToken(BaseModel):
    access_token: str
    token_type: str

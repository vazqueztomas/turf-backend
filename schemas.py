from typing import Optional
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    email: EmailStr
    disabled: Optional[bool] = False
    authorized: bool


class UserInDB(UserOut):
    _id: Optional[str]
    hashed_password: str

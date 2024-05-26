from typing import Optional
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    email: EmailStr
    disabled: Optional[bool] = None


class UserInDB(UserOut):
    hashed_password: str

from typing import Optional
from pydantic import BaseModel, EmailStr


class User(BaseModel):
    email: EmailStr
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str

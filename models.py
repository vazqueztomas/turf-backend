from pydantic import BaseModel, EmailStr


class User(BaseModel):
    email: EmailStr


class UserInDB(User):
    hashed_password: str

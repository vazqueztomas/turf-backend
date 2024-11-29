from datetime import timedelta
from typing import Any, Optional

from pydantic import BaseModel
from sqlmodel import Session, select

from turf_backend.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from turf_backend.models.user import User
from turf_backend.schemas.user import AccessToken, UserCreatePayload


class AuthorizationRequest(BaseModel):
    authorized: bool


class UserController:
    def __init__(self, session: Session):
        self.connection = session

    def get_user(self, email: str) -> Optional[User]:
        statement = select(User).where(User.email == email)
        return self.connection.exec(statement).one_or_none()

    def get_users(self) -> list[User]:
        statement = select(User)
        users = self.connection.exec(statement).fetchall()
        return list(users)

    def create_user(self, data: UserCreatePayload) -> Optional[User]:
        user = data.model_dump()

        email_already_used = self.get_user(user["email"])
        if email_already_used:
            return None

        user["hashed_password"] = get_password_hash(data.password).decode("utf-8")
        del user["password"]

        new_user = User(**user)
        self.connection.add(new_user)
        self.connection.commit()
        self.connection.refresh(new_user)
        return new_user

    def update_user(
        self, email: str, auth_request: AuthorizationRequest
    ) -> Optional[User]:
        user = self.get_user(email)

        if not user:
            return None

        user.email = email
        user.authorized = auth_request.authorized
        self.connection.add(user)
        self.connection.commit()

        return user

    def decode_access_token(self, token: str) -> Optional[Any]:
        return decode_access_token(token)

    def login(self, email: str, password: str) -> Optional[AccessToken]:
        user = self.get_user(email)
        if not user:
            return None

        valid_password = verify_password(password, user.hashed_password)

        if not valid_password:
            return None

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=access_token_expires,
        )

        return AccessToken(access_token=access_token, token_type="bearer")

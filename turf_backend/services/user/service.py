from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from jose import jwt
from passlib.context import CryptContext

from turf_backend.models import User
from turf_backend.repositories import SQLRepository
from turf_backend.utils import LogLevel, log

from .exceptions import EmailAlreadyRegistered, InvalidUserCredentials, UserNotFound

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class UserService:
    @property
    def user_repository(self) -> SQLRepository[User]:
        return SQLRepository[User](model=User)

    @property
    def password_context(self) -> CryptContext:
        return CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, password: str) -> str:
        return self.password_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.password_context.verify(plain_password, hashed_password)

    def create_access_token(
        self,
        data: dict[str, Any],
    ) -> str:
        to_encode = data.copy()
        expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def authorize_user(self, user_id: UUID) -> User:
        existing_user = self.user_repository.get_by_id(user_id)
        if not existing_user:
            message = f"User with id {user_id} not found."
            log(message, LogLevel.ERROR)
            raise UserNotFound(message)

        existing_user.authorized = True
        user = self.user_repository.upsert(existing_user)
        return user

    def register_user(self, email: str, name: str, password: str) -> User:
        existing_user = self.user_repository.get_first_by_params(email=email)
        if existing_user:
            message = f"Email {email} is already registered."
            log(message, LogLevel.ERROR)
            raise EmailAlreadyRegistered(message)

        hashed_password = self.hash_password(password)
        user = User(email=email, name=name, hashed_password=hashed_password)
        user = self.user_repository.upsert(user)
        return user

    def login_user(self, email: str, password: str) -> str:
        user = self.user_repository.get_first_by_params(email=email)
        if not user or not self.verify_password(password, user.hashed_password):
            message = "Invalid user credentials"
            log(message, LogLevel.ERROR)
            raise InvalidUserCredentials(message)

        token = self.create_access_token({"sub": user.email})
        return token

    def get_user_by_id(self, user_id: UUID) -> User:
        existing_user = self.user_repository.get_by_id(user_id)
        if not existing_user:
            message = f"User with id {user_id} not found."
            log(message, LogLevel.ERROR)
            raise UserNotFound(message)
        return existing_user

    def get_all_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        return self.user_repository.get_all(skip=skip, limit=limit)

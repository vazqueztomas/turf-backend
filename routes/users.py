from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlmodel import Session, select

from auth import (
    decode_access_token,
    get_password_hash,
)
from models.user import User
from routes.dependencies import DatabaseSession
from schemas.user import UserCreatePayload, UserOut

router = APIRouter(prefix="/users")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class AuthorizationRequest(BaseModel):
    authorized: bool


@router.get("/", response_model=List[UserOut])
def read_users(connection: Session = DatabaseSession):
    statement = select(User)
    return connection.exec(statement).fetchall()


@router.get("/me", response_model=UserOut)
def read_users_me(
    token: str = Depends(oauth2_scheme), connection: Session = DatabaseSession
):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email: str = payload.get("sub")
    statement = select(User).where(User.email == email)
    user = connection.exec(statement).one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.post("/", response_model=UserOut)
def create_user(
    user: UserCreatePayload, connection: Session = DatabaseSession
) -> UserOut:
    user_dict = user.model_dump()
    user_dict["hashed_password"] = get_password_hash(user.password).decode("utf-8")
    del user_dict["password"]

    statement = select(User).where(User.email == user_dict["email"])
    email_already_used = connection.exec(statement).one_or_none()

    if email_already_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(**user_dict)
    connection.add(new_user)
    connection.commit()
    return UserOut(
        email=new_user.email, name=new_user.name, authorized=new_user.authorized
    )


@router.put("/{email}/authorize", response_model=UserOut)
def authorize_user(
    email: str,
    auth_request: AuthorizationRequest,
    connection: Session = DatabaseSession,
) -> UserOut:
    statement = select(User).where(User.email == email)
    user = connection.exec(statement).one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.email = email
    user.authorized = auth_request.authorized
    connection.add(user)

    return UserOut(**user.model_dump())

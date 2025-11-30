from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from turf_backend.api.dependencies import DatabaseSession
from turf_backend.auth import (
    AccessToken,
    User,
    UserCreatePayload,
    UserLogin,
    UserOut,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/")
def get_all_users(session: DatabaseSession) -> Sequence[User]:
    statement = select(User)
    return session.exec(statement).all()


@router.get("/{user_id}")
def get_user_by_id(user_id: int, session: DatabaseSession) -> UserOut:
    existing_user = session.exec(select(User).where(User.id == user_id)).first()
    if not existing_user:
        raise HTTPException(status_code=400, detail="That user does not exists.")
    return UserOut(
        email=existing_user.email,
        name=existing_user.name,
        authorized=existing_user.authorized,
    )


@router.post("/register", response_model=UserOut)
def register_user(payload: UserCreatePayload, session: DatabaseSession):
    existing_user = session.exec(
        select(User).where(User.email == payload.email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(payload.password)
    user = User(email=payload.email, name=payload.name, hashed_password=hashed_pw)
    session.add(user)
    session.commit()
    session.refresh(user)
    return UserOut(email=user.email, name=user.name, authorized=user.authorized)


@router.post("/login", response_model=AccessToken)
def login_user(payload: UserLogin, session: DatabaseSession):
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    token = create_access_token({"sub": user.email})
    return AccessToken(access_token=token, token_type="bearer")


@router.post("/authorize/{user_id}")
def authorize_user(user_id: int, session: DatabaseSession) -> User:
    existing_user = session.exec(select(User).where(User.id == user_id)).first()
    if not existing_user:
        raise HTTPException(status_code=400, detail="That user does not exists.")

    if existing_user.authorized:
        raise HTTPException(status_code=400, detail="That user is already authorized.")

    existing_user.authorized = True
    session.add(existing_user)
    session.commit()
    session.refresh(existing_user)
    return existing_user

from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from turf_backend.auth import (
    AccessToken,
    User,
    UserCreatePayload,
    UserOut,
    create_access_token,
    hash_password,
    verify_password,
)
from turf_backend.database import get_connection

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/")
def get_all_users(db: Session = Depends(get_connection)) -> Sequence[User]:
    statement = select(User)
    return db.exec(statement).all()


@router.get("/{user_id}")
def get_user_by_id(user_id: int, db: Session = Depends(get_connection)) -> UserOut:
    existing_user = db.exec(select(User).where(User.id == user_id)).first()
    if not existing_user:
        raise HTTPException(status_code=400, detail="That user does not exists.")
    return UserOut(
        email=existing_user.email,
        name=existing_user.name,
        authorized=existing_user.authorized,
    )


@router.post("/register", response_model=UserOut)
def register_user(payload: UserCreatePayload, db: Session = Depends(get_connection)):
    existing_user = db.exec(select(User).where(User.email == payload.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(payload.password)
    user = User(email=payload.email, name=payload.name, hashed_password=hashed_pw)
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(email=user.email, name=user.name, authorized=user.authorized)


@router.post("/login", response_model=AccessToken)
def login_user(payload: UserCreatePayload, db: Session = Depends(get_connection)):
    user = db.exec(select(User).where(User.email == payload.email)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    token = create_access_token({"sub": user.email})
    return AccessToken(access_token=token, token_type="bearer")


@router.post("/authorize/{user_id}")
def authorize_user(user_id: int, db: Session = Depends(get_connection)) -> User:
    existing_user = db.exec(select(User).where(User.id == user_id)).first()
    if not existing_user:
        raise HTTPException(status_code=400, detail="That user does not exists.")

    if existing_user.authorized:
        raise HTTPException(status_code=400, detail="That user is already authorized.")

    existing_user.authorized = True
    db.add(existing_user)
    db.commit()
    db.refresh(existing_user)
    return existing_user

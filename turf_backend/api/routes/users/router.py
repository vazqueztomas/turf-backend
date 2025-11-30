from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from turf_backend.api.auth import create_access_token, hash_password, verify_password
from turf_backend.api.dependencies import UserRepository
from turf_backend.models import User

from .schemas import AccessToken, UserCreatePayload, UserLogin, UserOut

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("")
def get_all_users(user_repository: UserRepository) -> Sequence[User]:
    return user_repository.get_all()


@router.get("/{user_id}")
def get_user_by_id(user_id: UUID, user_repository: UserRepository) -> UserOut:
    existing_user = user_repository.get_by_id(user_id)

    if existing_user:
        return UserOut(
            email=existing_user.email,
            name=existing_user.name,
            authorized=existing_user.authorized,
        )

    raise HTTPException(
        status_code=404,
        detail=f"The user with id {user_id} user does not exists",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserCreatePayload, user_repository: UserRepository
) -> UserOut:
    existing_user = user_repository.get_first_by_params(email=payload.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(payload.password)
    user = User(email=payload.email, name=payload.name, hashed_password=hashed_pw)
    user = user_repository.upsert(user)
    return UserOut(email=user.email, name=user.name, authorized=user.authorized)


@router.post("/login")
def login(payload: UserLogin, user_repository: UserRepository) -> AccessToken:
    user = user_repository.get_first_by_params(email=payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    token = create_access_token({"sub": user.email})
    return AccessToken(access_token=token, token_type="bearer")


@router.post("/authorize/{user_id}")
def authorize(user_id: UUID, user_repository: UserRepository) -> UserOut:
    existing_user = user_repository.get_by_id(user_id)
    if not existing_user:
        raise HTTPException(status_code=400, detail="That user does not exists.")

    existing_user.authorized = True
    user = user_repository.upsert(existing_user)
    return UserOut(
        email=user.email,
        name=user.name,
        authorized=user.authorized,
    )

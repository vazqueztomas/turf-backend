from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from turf_backend.api.dependencies import UserServiceDependency, UserRepository
from turf_backend.models import User

from .schemas import AccessToken, UserCreatePayload, UserLogin, UserOut

router = APIRouter(prefix="/users", tags=["Users"])

# TODO: Add exception handlers

@router.get("")
def get_all_users(user_repository: UserRepository) -> Sequence[User]:
    return user_repository.get_all()


@router.get("/{user_id}")
def get_user_by_id(user_id: UUID, user_service: UserServiceDependency) -> UserOut:
    existing_user = user_service.get_user_by_id(user_id)

    return UserOut(
        email=existing_user.email,
        name=existing_user.name,
        authorized=existing_user.authorized,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserCreatePayload, user_service: UserServiceDependency
) -> UserOut:
    user = user_service.register_user(**payload.model_dump())
    return UserOut(email=user.email, name=user.name, authorized=user.authorized)


@router.post("/login")
def login(payload: UserLogin, user_service: UserServiceDependency) -> AccessToken:
    token = user_service.login_user(email=payload.email, password=payload.password)
    return AccessToken(access_token=token, token_type="bearer")


@router.post("/authorize/{user_id}")
def authorize(user_id: UUID, user_service: UserServiceDependency) -> UserOut:
    user = user_service.authorize_user(user_id)
    return UserOut(
        email=user.email,
        name=user.name,
        authorized=user.authorized,
    )

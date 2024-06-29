from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from database import users_collection
from models.models import UserInDB
from schemas.schemas import UserCreate, UserOut

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class AuthorizationRequest(BaseModel):
    authorized: bool


async def get_user(email: str) -> Optional[UserInDB]:
    user_data = await users_collection.find_one({"email": email})
    if user_data:
        return UserInDB(**user_data)
    return None


async def authenticate_user(email: str, password: str):
    user = await get_user(email)
    if user and verify_password(password, user.hashed_password):
        return user
    return False


@router.get("/users/", response_model=List[UserOut])
async def read_users():
    users = await users_collection.find().to_list(1000)
    cleaned_users = []
    for user in users:
        user.setdefault("authorized", False)
        user.setdefault("disabled", False)
        cleaned_user = {k: v for k, v in user.items() if k in UserOut.__fields__}
        cleaned_users.append(UserOut(**cleaned_user))
    return cleaned_users


@router.get("/users/me/", response_model=UserOut)
async def read_users_me(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email: str = payload.get("sub")
    user = await get_user(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.post("/token", response_model=dict)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):  # noqa: B008
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", response_model=dict)
def logout():
    return {"message": "Logout successful"}


@router.post("/users/", response_model=UserOut)
async def create_user(user: UserCreate):
    user_dict = user.model_dump()
    user_dict["hashed_password"] = get_password_hash(user.password)
    del user_dict["password"]
    try:
        new_user = await users_collection.insert_one(
            user_dict,
        )  # Motor is used for async
        return await users_collection.find_one(
            {"_id": new_user.inserted_id},
        )  # Motor is used for async
    except DuplicateKeyError:
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )


@router.put("/users/{email}/authorize", response_model=UserOut)
async def authorize_user(email: str, auth_request: AuthorizationRequest) -> UserOut:
    user = await get_user(email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    await users_collection.update_one(
        {"email": email},
        {"$set": {"authorized": auth_request.authorized}},
    )

    # recharge user from database
    user = await get_user(email)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return UserOut(**user.dict())

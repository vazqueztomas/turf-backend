from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pymongo.errors import DuplicateKeyError
from models import UserInDB
from schemas import UserCreate, UserOut
from database import users_collection
from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
)

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_user(email: str):
    user = await users_collection.find_one({"email": email})
    if user:
        return UserInDB(**user)


async def authenticate_user(email: str, password: str):
    user = await get_user(email)
    if user and verify_password(password, user.hashed_password):
        return user
    return False


@app.post("/users/", response_model=UserOut)
async def create_user(user: UserCreate):
    user_dict = user.dict()
    user_dict["hashed_password"] = get_password_hash(user.password)
    del user_dict["password"]

    try:
        new_user = await users_collection.insert_one(user_dict)
        created_user = await users_collection.find_one({"_id": new_user.inserted_id})
        return created_user
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )


@app.post("/token", response_model=dict)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me/", response_model=UserOut)
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

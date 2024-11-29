from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session

from turf_backend.controllers.user import AuthorizationRequest, UserController
from turf_backend.database.database import get_connection
from turf_backend.schemas.user import AccessToken, UserCreatePayload, UserOut

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router.get("/user", response_model=list[UserOut])
def read_users(session: Session = Depends(get_connection)) -> list[UserOut]:  # noqa: B008
    user_controller = UserController(session)
    users = user_controller.get_users()
    return [
        UserOut(email=user.email, name=user.name, authorized=user.authorized)
        for user in users
    ]


@router.get("/user/me", response_model=UserOut)
def read_users_me(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_connection),  # noqa: B008
):
    user_controller = UserController(session)
    payload = user_controller.decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email: str = payload.get("sub")
    user = user_controller.get_user(email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.post("/create-user", response_model=UserOut)
def create_user(
    user: UserCreatePayload,
    session: Session = Depends(get_connection),  # noqa: B008
) -> UserOut:
    user_controller = UserController(session)
    new_user = user_controller.create_user(user)

    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    return UserOut(**new_user.model_dump())


@router.put("/user/{email}/authorize", response_model=UserOut)
def authorize_user(
    email: str,
    auth_request: AuthorizationRequest,
    session: Session = Depends(get_connection),  # noqa: B008
) -> UserOut:
    user_controller = UserController(session)
    user = user_controller.update_user(email, auth_request)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserOut(**user.model_dump())


@router.post("/token", response_model=AccessToken)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),  # noqa: B008
    session: Session = Depends(get_connection),  # noqa: B008
) -> AccessToken:
    user_controller = UserController(session)
    access_token = user_controller.login(form_data.username, form_data.password)

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return access_token


@router.post("/logout", response_model=dict)
def logout():
    return {"message": "Logout successful"}

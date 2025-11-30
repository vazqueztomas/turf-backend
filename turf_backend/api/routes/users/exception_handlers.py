from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from turf_backend.services import (
    EmailAlreadyRegistered,
    InvalidUserCredentials,
    UserNotFound,
)


def user_not_found_handler(_: Request, exc: UserNotFound) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"message": str(exc)},
    )


def invalid_credentials_handler(
    _: Request, exc: InvalidUserCredentials
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"message": str(exc)},
    )


def email_already_registered_handler(
    _: Request, exc: EmailAlreadyRegistered
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"message": str(exc)},
    )


def register_user_exception_handlers(app: FastAPI) -> None:
    app.exception_handlers = {
        **app.exception_handlers,
        UserNotFound: user_not_found_handler,
        InvalidUserCredentials: invalid_credentials_handler,
        EmailAlreadyRegistered: email_already_registered_handler,
    }

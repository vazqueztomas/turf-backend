from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlmodel import text

from turf_backend.api.dependencies import DatabaseSession

router = APIRouter(prefix="", tags=["Base"])


@router.get("/healthcheck")
def healtcheck() -> JSONResponse:
    return JSONResponse(
        content={"status": "ok"},
        status_code=status.HTTP_200_OK,
    )


@router.delete("/database/reset")
def reset_database(session: DatabaseSession) -> JSONResponse:
    session.exec(text("DELETE FROM horses;"))
    session.exec(text("DELETE FROM races;"))
    session.commit()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"detail": "Database reset successful"},
    )

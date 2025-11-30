from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from turf_backend.api import (
    base_router,
    horses_router,
    palermo_router,
    races_router,
    users_router,
)

app = FastAPI(redoc_url="/swagger")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(base_router)
app.include_router(palermo_router)
app.include_router(users_router)
app.include_router(races_router)
app.include_router(horses_router)


@app.exception_handler(HTTPException)
def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


@app.exception_handler(Exception)
def global_exception_handler(_: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected error occurred.", "detail": str(exc)},
    )


@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse(url="/docs")

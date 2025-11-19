from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from turf_backend.routes import palermo, san_isidro, temp_pdf_downloader, users

app = FastAPI(redoc_url="/swagger")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(palermo.router)
app.include_router(san_isidro.router)
app.include_router(users.router)
app.include_router(temp_pdf_downloader.router)


@app.get("/")
def healtcheck():
    return {"status": "ok"}  # pragma: no cover


@app.exception_handler(HTTPException)
def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):  # noqa: ARG001
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected error occurred.", "detail": str(exc)},
    )

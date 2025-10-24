from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from turf_backend.routes import horses, pdf_file, users

app = FastAPI(redoc_url="/swagger")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",  # Agregar este origen adicional
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pdf_file.router)
app.include_router(users.router)
app.include_router(horses.router)


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

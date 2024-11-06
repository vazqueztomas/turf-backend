from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routes import pdf_reader, users

app = FastAPI()

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

app.include_router(pdf_reader.router)
app.include_router(users.router)


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.exception_handler(HTTPException)
def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


@app.exception_handler(Exception)
def global_exception_handler():
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error"},
    )

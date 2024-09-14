from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import ASCENDING
from database import database

from database import database
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

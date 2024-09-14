
from typing import Annotated
from fastapi import Depends
from sqlmodel import Session
from database import database

DatabaseSession = Annotated[Session, Depends(database.get_session)]

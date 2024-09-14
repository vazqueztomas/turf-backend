
from typing import Annotated
from fastapi import Depends
from sqlmodel import Session
from database import get_connection

DatabaseSession = Annotated[Session, Depends(get_connection)]

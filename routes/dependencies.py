from fastapi import Depends
from sqlmodel import Session

from database import get_connection

DatabaseSession: Session = Depends(get_connection)

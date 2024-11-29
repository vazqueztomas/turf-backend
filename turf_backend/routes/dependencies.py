from fastapi import Depends
from sqlmodel import Session

from turf_backend.database import get_connection

DatabaseSession: Session = Depends(get_connection)

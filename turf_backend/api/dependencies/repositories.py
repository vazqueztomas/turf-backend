from typing import Annotated

from fastapi import Depends

from turf_backend.models import Horse, Race, User
from turf_backend.repositories import SQLRepository

UserRepository = Annotated[
    SQLRepository[User], Depends(lambda: SQLRepository[User](model=User))
]
HorseRepository = Annotated[
    SQLRepository[Horse], Depends(lambda: SQLRepository[Horse](model=Horse))
]
RaceRepository = Annotated[
    SQLRepository[Race], Depends(lambda: SQLRepository[Race](model=Race))
]

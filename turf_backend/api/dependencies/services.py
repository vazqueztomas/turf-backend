from typing import Annotated

from fastapi import Depends

from turf_backend.services import UserService

UserServiceDependency = Annotated[UserService, Depends(UserService)]

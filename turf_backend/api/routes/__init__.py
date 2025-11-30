from .base import router as base_router
from .horses import router as horses_router
from .palermo import router as palermo_router
from .races import router as races_router
from .san_isidro import san_isidro_router
from .users import router as users_router

__all__ = [
    "base_router",
    "horses_router",
    "palermo_router",
    "races_router",
    "san_isidro_router",
    "users_router",
]

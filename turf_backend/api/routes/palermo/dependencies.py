from typing import Annotated

from fastapi import Depends

from turf_backend.services import PalermoService

InjectedPalermoService = Annotated[PalermoService, Depends(PalermoService)]

from fastapi import APIRouter

from models.racing import Racing

router = APIRouter()


@router.get("/racings")
def get_all_racings() -> list[Racing]:
    return []


@router.get("/racings/{racing_id}")
def get_racing(racing_id: str) -> Racing:
    return Racing(
        id=racing_id,
        number=1,
        horses=[],
        distance=1000,
        date="2021-01-01",
        time="12:00",
    )

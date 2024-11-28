from models.racing import Racing


def test_get_racing(racing: Racing) -> None:
    assert racing.id == 1


def test_get_all_racings(racing: Racing) -> None:
    assert racing.name == "Racing 1"

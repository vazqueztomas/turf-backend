import pytest


@pytest.fixture()
def user_controller_mock(mocker) -> None:
    return mocker.patch("routes.users.UserController")

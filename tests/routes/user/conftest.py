import pytest


@pytest.fixture()
def user_controller_mock(mocker) -> None:
    return mocker.patch("turf_backend.routes.users.UserController")


@pytest.fixture()
def user_email() -> str:
    return "testuser@test.com"


@pytest.fixture()
def user_name() -> str:
    return "Test User"

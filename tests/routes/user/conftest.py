import pytest


@pytest.fixture()
def user_service_mock(mocker) -> None:
    return mocker.patch("turf_backend.routes.users.UserService")


@pytest.fixture()
def user_email() -> str:
    return "testuser@test.com"


@pytest.fixture()
def user_name() -> str:
    return "Test User"

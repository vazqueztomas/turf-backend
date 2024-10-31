from fastapi import status
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_login_success(user_controller_mock) -> None:
    # Mock the UserController and its login method
    user_controller_mock.return_value.login.return_value = {
        "access_token": "fake_token",
        "token_type": "bearer",
    }

    response = client.post(
        "/token", data={"username": "testuser", "password": "testpassword"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"access_token": "fake_token", "token_type": "bearer"}


def test_login_failed(user_controller_mock) -> None:
    user_controller_mock.return_value.login.return_value = None

    response = client.post(
        "/token", data={"username": "testuser", "password": "testpassword"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"message": "Email o contraseña incorrectos"}


def test_logout() -> None:
    response = client.post("/logout")
    assert response.status_code == 200
    assert response.json() == {"message": "Logout successful"}

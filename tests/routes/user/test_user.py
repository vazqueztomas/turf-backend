from unittest.mock import MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from main import app
from turf_backend.schemas.user import UserOut

client = TestClient(app)


def test_get_user(
    user_controller_mock: MagicMock, user_email: str, user_name: str
) -> None:
    user_controller_mock.return_value.get_users.return_value = [
        UserOut(email=user_email, name=user_name, authorized=True)
    ]

    response = client.get("/user")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "email": user_email,
            "name": user_name,
            "authorized": True,
        }
    ]


def test_authorize_user(
    user_controller_mock: MagicMock, user_email: str, user_name: str
) -> None:
    user_controller_mock.return_value.update_user.return_value = UserOut(
        email=user_email,
        name=user_name,
        authorized=True,
    )

    response = client.put("/user/testuser/authorize", json={"authorized": True})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "email": user_email,
        "name": user_name,
        "authorized": True,
    }


def test_authorize_user_not_found(user_controller_mock: MagicMock) -> None:
    user_controller_mock.return_value.update_user.return_value = None

    response = client.put("/user/testuser/authorize", json={"authorized": True})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"message": "User not found"}


def test_login_success(user_controller_mock: MagicMock, user_email: str) -> None:
    user_controller_mock.return_value.login.return_value = {
        "access_token": "fake_token",
        "token_type": "bearer",
    }

    response = client.post(
        "/token", data={"username": user_email, "password": "testpassword"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"access_token": "fake_token", "token_type": "bearer"}


def test_login_failed(user_controller_mock: MagicMock, user_email: str) -> None:
    user_controller_mock.return_value.login.return_value = None

    response = client.post(
        "/token", data={"username": user_email, "password": "testpassword"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"message": "Email o contraseña incorrectos"}


def test_logout() -> None:
    response = client.post("/logout")
    assert response.status_code == 200
    assert response.json() == {"message": "Logout successful"}

import pytest
from fastapi.testclient import TestClient

from turf_backend.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_get_horses(client: TestClient) -> None:
    response = client.get("/horses")

    assert response.status_code == 200

import pytest

from turf_backend.utils.http_requests import request_http


@pytest.fixture()
def invalid_url() -> str:
    return "asd://google.com"


@pytest.fixture()
def valid_url() -> str:
    return "https://google.com"


def test_request_http(valid_url: str) -> None:
    response = request_http(valid_url)
    assert response.get("status_code") == 200
    assert response.get("text") is not None


def test_request_http_error(invalid_url: str) -> None:
    response = request_http(invalid_url)
    assert response.get("status_code") == 500
    assert f"Error while making HTTP GET request to {invalid_url}" in response.get(
        "text"
    )

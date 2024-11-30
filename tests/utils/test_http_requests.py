from turf_backend.utils.http_requests import request_http


def test_request_http() -> None:
    response = request_http("https://www.google.com")
    assert response.get("status_code") == 200
    assert response.get("text") is not None


def test_request_http_error() -> None:
    response = request_http("https://www.google.com/404")
    assert response.get("status_code") == 404
    assert response.get("text") is not None

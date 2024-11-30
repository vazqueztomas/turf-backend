from enum import Enum
from typing import Optional, TypedDict

import requests


class HTTPMethods(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class HTTPResponse(TypedDict):
    status_code: int
    text: str


def request_http(
    url: str, method: Optional[HTTPMethods] = HTTPMethods.GET
) -> HTTPResponse:
    try:
        response = requests.request(method.value, url)  # type: ignore[attr-defined]
        return {"status_code": response.status_code, "text": response.text}  # noqa: TRY300
    except requests.exceptions.RequestException as error:
        print(f"Error while making HTTP {method} request to {url}: {error=}")  # noqa: T201
        return {
            "status_code": 500,
            "text": f"Error while making HTTP {method} request to {url}: {error=}",
        }

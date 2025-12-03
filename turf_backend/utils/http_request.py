from dataclasses import dataclass

import requests


@dataclass
class HTTPRequestException(Exception):
    status_code: int
    detail: str


def http_request(
    url: str, headers: dict[str, str] | None = None, method: str = "GET"
) -> requests.Response:
    response = requests.request(method, url, headers=headers)
    if not response.ok:
        raise HTTPRequestException(
            status_code=response.status_code,
            detail=response.text,
        )
    return response

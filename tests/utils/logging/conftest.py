from collections.abc import Generator

import pytest

from turf_backend.utils import LogLevel, get_logger


@pytest.fixture
def capture_logs() -> Generator[list[str]]:
    logger = get_logger()
    output: list[str] = []
    handler_id = logger.add(output.append)
    yield output
    logger.remove(handler_id)


@pytest.fixture(
    params=[LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL]
)
def log_level(request: pytest.FixtureRequest) -> LogLevel:
    return request.param  # type: ignore[no-any-return]


@pytest.fixture
def message() -> str:
    return "Test message"

# fmt:off
from enum import Enum
from pathlib import Path
from typing import Optional

from loguru import logger


class LogLevels(str, Enum):
    INFO = "INFO"
    DEBUG = "DEBUG"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


LOGS_DIRECTORY_PATH = Path("logs")
LOGS_FILE_PATH = Path(f"{LOGS_DIRECTORY_PATH}/turf_backend.log")


def log(message: str, level: Optional[LogLevels] = LogLevels.INFO) -> None:
    if not Path.exists(LOGS_DIRECTORY_PATH):
        LOGS_DIRECTORY_PATH.mkdir(parents=True, exist_ok=True)

    logger.add(LOGS_FILE_PATH, format="{time} {level} {message}", level=level.value)  # type: ignore[attr-defined]
    log_methods = {
        LogLevels.INFO: logger.info,
        LogLevels.DEBUG: logger.debug,
        LogLevels.WARNING: logger.warning,
        LogLevels.ERROR: logger.error,
        LogLevels.CRITICAL: logger.critical,
    }
    log_methods[level](message)  # type: ignore[attr-defined]

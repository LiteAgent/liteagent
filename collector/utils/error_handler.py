from typing import Any

from . import logger  # Import the global logger


class TimeoutException(Exception):
    pass


# TODO Make this error handling more concrete and specific
class AgentException(Exception):
    pass


stop_flag = [False]


def timeout_handler(signum: int, frame: Any) -> None:
    """Handle timeout by setting the stop_flag."""
    logger.debug("Timeout handler triggered, setting stop_flag.")
    stop_flag[0] = True

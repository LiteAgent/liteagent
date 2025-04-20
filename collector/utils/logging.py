import logging
import os
import sys
from datetime import datetime
from typing import Any

# Define a global logger
logger = logging.getLogger("liteagent") # TODO Have this be generic based on the name passed in


def get_logger_level():
    logger_level = os.environ.get("LOGGER_LEVEL")
    if logger_level:
        logger_level = logger_level.lower()
        if logger_level == "debug":
            return logging.DEBUG
        elif logger_level == "info":
            return logging.INFO
        elif logger_level == "warning":
            return logging.WARNING
        elif logger_level == "error":
            return logging.ERROR
        elif logger_level == "critical":
            return logging.CRITICAL
    return logging.INFO


def setup_logger(name: str, agent_method: str) -> None:
    """Configure the global logger with the specified name and agent_method."""
    logger.setLevel(get_logger_level())
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(funcName)s:%(lineno)d] - %(message)s"
    )

    # Clear existing handlers to prevent duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # StreamHandler for console output
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    try:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        logs_dir = os.path.join(
            root_dir, "logs", agent_method
        )  # Agent_method subfolder
        os.makedirs(logs_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file = os.path.join(logs_dir, f"liteagent-{timestamp}.log")
        fh = logging.FileHandler(log_file)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except FileNotFoundError as e:
        print(f"Log file path not found: {e}")
    except PermissionError as e:
        print(f"Permission denied when creating log file: {e}")
    except ValueError as e:
        print(f"Value issue in logger setup: {e}")
    except Exception as e:
        print(f"Logging setup error: {e}")


def print_browser_and_js_logs(driver: Any) -> None:
    logs = driver.get_log("browser")
    for entry in logs:
        logger.debug(f"[{entry['level']}] - {entry['message']}")

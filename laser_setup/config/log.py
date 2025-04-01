"""Logging configuration for the laser_setup package.
"""
import logging
import logging.config
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class Colors:
    RESET = "\033[0m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class ColoredFormatter(logging.Formatter):
    """Logging formatter with colored level names."""

    COLORS = {
        logging.DEBUG: Colors.BLUE,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.BOLD + Colors.RED,
    }
    NAME_COLOR = Colors.CYAN

    def format(self, record):
        """Format the log record with colored level name.

        :param record: Log record to format
        :return: Formatted log message with colored level name
        """
        levelname = record.levelname
        if record.levelno in self.COLORS:
            color = self.COLORS[record.levelno]
            record.levelname = f"{color}{levelname}{Colors.RESET}"

        name = record.name
        if self.NAME_COLOR:
            record.name = f"{self.NAME_COLOR}{record.name}{Colors.RESET}"

        result = super().format(record)
        record.levelname = levelname
        record.name = name
        return result


def setup_logging(config: Mapping[str, Any]) -> logging.Logger:
    """Set up logging from configuration dictionary.

    :param config: Dictionary containing logging configuration.
        Applies the config to `logging.config.dictConfig`.
    :return: Configured logger for the config module
    """
    filename = config.get('handlers', {}).get('file', {}).get('filename')
    if filename:
        Path(filename).parent.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(config=config)


default_log_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            '()': '${class:laser_setup.config.log.ColoredFormatter}',
            'format': '%(asctime)s: [%(levelname)s] %(message)s (%(name)s)',
            'datefmt': '%I:%M:%S %p'
        },
        'file': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'console',
        },
        'file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'file',
            'filename': 'log/laser_setup.log',
            'mode': 'a',
            'encoding': None,
        }
    },
    'loggers': {
        'root': {
            'level': 'INFO',
            'handlers': ['file'],
        },
        'laser_setup': {
            'level': 'INFO',
            'handlers': ['console'],
        },
        'laser_setup.display.widgets.log_widget': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
        'pymeasure.log': {
            'level': 'WARNING',
        }
    }
}

from typing import Optional, Union, ClassVar, List
import logging
from colorama import Fore, Style, init


class Data:
    """A class representing constants for the library.
    :ivar LOG_LEVEL ClassVar[int]: The default level of logging as an integer
    :ivar LOGGERS List[str]: A list of all loggers registered from this library
    """

    LOG_LEVEL: ClassVar[int] = logging.ERROR
    LOGGERS: List[str] = []


class CustomFormatter(logging.Formatter):
    """A class that allows for customized logged outputs from the library."""

    format_str: str = "%(levelname)s:%(name)s:(ln.%(lineno)d):%(message)s"
    formats: dict = {
        logging.DEBUG: Fore.CYAN + format_str + Fore.RESET,
        logging.INFO: Fore.GREEN + format_str + Fore.RESET,
        logging.WARNING: Fore.YELLOW + format_str + Fore.RESET,
        logging.ERROR: Fore.RED + format_str + Fore.RESET,
        logging.CRITICAL: Style.BRIGHT
        + Fore.RED
        + format_str
        + Fore.RESET
        + Style.NORMAL,
    }

    def __init__(self):
        super().__init__()
        init(autoreset=True)

    def format(self, record):
        log_format = self.formats.get(record.levelno)
        formatter = logging.Formatter(log_format)
        return formatter.format(record)


def get_logger(
    logger: Optional[Union[logging.Logger, str]] = None,
    handler: Optional[logging.Handler] = logging.StreamHandler(),
) -> logging.Logger:
    _logger = logging.getLogger(logger) if isinstance(logger, str) else logger
    _logger_name = logger if isinstance(logger, str) else logger.name
    if len(_logger.handlers) > 1:
        _logger.removeHandler(_logger.handlers[0])
    _handler = handler
    _handler.setFormatter(CustomFormatter)
    _handler.setLevel(Data.LOG_LEVEL)
    _logger.addHandler(_handler)
    _logger.propagate = True

    Data.LOGGERS.append(_logger_name)
    return _logger
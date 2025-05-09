import logging
import sys
from typing import Dict, Optional, Union

from .constants import MAGIC_STDOUT


def getLogger_res2csv(
    module_name: str = "res2df", args_dict: Optional[Dict[str, Union[str, bool]]] = None
) -> logging.Logger:
    # pylint: disable=invalid-name
    """Provide a custom logger for res2csv and csv2res

    Logging output is by default split by logging levels (split between WARNING and
    ERROR) to stdout and stderr, each log occurs in only one of the streams.
    This deviates from Unix standard, but is accepted here because the code
    often writes it main output to a dedicated filename.

    Args:
        module_name: A suggested name for the logger, usually
            __name__ should be supplied
        args_dict: Dictionary with contents from the argparse namespace object.
            Only keys "output", "verbose" and "debug" will be looked at.
            Use vars(args) in caller code to convert from argparse Namespace object.
    """
    logger = logging.getLogger(module_name)

    if args_dict is None:
        args_dict = {}

    formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")

    # In case this logger has been initialized earlier, clear it:
    logger.handlers.clear()

    if args_dict.get("output", "") == MAGIC_STDOUT:
        # If main output is to stdout, we must send all logs to stderr:
        default_handler = logging.StreamHandler(sys.stderr)
        default_handler.setFormatter(formatter)
        logger.addHandler(default_handler)
    else:
        # Split log messages to either stdout or stderr based on log level:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.addFilter(lambda record: record.levelno < logging.ERROR)
        stdout_handler.setFormatter(formatter)

        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.addFilter(lambda record: record.levelno >= logging.ERROR)
        stderr_handler.setFormatter(formatter)

        logger.addHandler(stdout_handler)
        logger.addHandler(stderr_handler)

    # --debug overrides --verbose
    if args_dict.get("debug", False):
        logger.setLevel(logging.DEBUG)
    elif args_dict.get("verbose", False):
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)

    return logger

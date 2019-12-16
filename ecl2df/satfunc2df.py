"""
This module is only for backwards compatibility and will be removed in future versions
"""
import logging

logging.warning(
    "satfunc2df has been renamed to satfunc, update your code before ecl2df 0.4.0"
)

from .satfunc import deck2satfuncdf, deck2df  # noqa

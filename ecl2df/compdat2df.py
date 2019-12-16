"""
This module is only for backwards compatibility and will be removed in future versions
"""
import logging

logging.warning(
    "compdat2df has been renamed to compdat, update your code before ecl2df 0.4.0"
)

from .compdat import deck2dfs

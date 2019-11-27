name = "ecl2df"

from .eclfiles import EclFiles

from . import (
    grid,
    ecl2csv,
    nnc,
    rft,
    summary,
    gruptree,
    equil,
    faults,
    pillars,
    wcon,
    satfunc,
    trans,
)

from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions

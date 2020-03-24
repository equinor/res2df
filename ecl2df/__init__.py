name = "ecl2df"

try:
    from .version import version
    __version__ = version
except ImportError:
    __version__ = "v0.0.0"

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


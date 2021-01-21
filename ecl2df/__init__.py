"""ecl2df"""

try:
    from .version import version

    __version__ = version
except ImportError:
    __version__ = "v0.0.0"

from .eclfiles import EclFiles

from . import (
    ecl2csv,
    equil,
    faults,
    grid,
    gruptree,
    nnc,
    pillars,
    pvt,
    rft,
    satfunc,
    summary,
    trans,
    wcon,
)

name = "ecl2df"

# List of submodules, at least in use by tests to loop over all.
SUBMODULES = [
    "grid",
    "summary",
    "nnc",
    "faults",
    "trans",
    "pillars",
    "pvt",
    "rft",
    "fipreports",
    "satfunc",
    "compdat",
    "equil",
    "gruptree",
    "wcon",
]

import importlib
from typing import List

try:
    from .version import version  # type: ignore

    __version__ = version
except ImportError:
    __version__ = "v0.0.0"

from .eclfiles import EclFiles

name: str = "ecl2df"

SUBMODULES: List[str] = [
    "compdat",
    "equil",
    "faults",
    "fipreports",
    "grid",
    "gruptree",
    "nnc",
    "pillars",
    "pvt",
    "rft",
    "satfunc",
    "summary",
    "trans",
    "wcon",
]

for submodule in SUBMODULES + ["ecl2csv", "csv2ecl"]:
    importlib.import_module("ecl2df." + submodule)

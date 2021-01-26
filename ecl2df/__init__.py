"""ecl2df"""
import importlib

try:
    from .version import version

    __version__ = version
except ImportError:
    __version__ = "v0.0.0"

from .eclfiles import EclFiles

name = "ecl2df"

SUBMODULES = [
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

import importlib
from typing import List

from .__version__ import __version__
from .res2csvlogger import getLogger_res2csv
from .resdatafiles import ResdataFiles

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
    "vfp",
    "wellcompletiondata",
    "wellconnstatus",
    "wcon",
]


for submodule in SUBMODULES + ["res2csv", "csv2res"]:
    importlib.import_module("res2df." + submodule)

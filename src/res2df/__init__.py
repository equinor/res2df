from . import compdat as compdat
from . import csv2res as csv2res
from . import equil as equil
from . import faults as faults
from . import fipreports as fipreports
from . import grid as grid
from . import gruptree as gruptree
from . import nnc as nnc
from . import pillars as pillars
from . import pvt as pvt
from . import res2csv as res2csv
from . import rft as rft
from . import satfunc as satfunc
from . import summary as summary
from . import trans as trans
from . import vfp as vfp
from . import wcon as wcon
from . import wellcompletiondata as wellcompletiondata
from . import wellconnstatus as wellconnstatus
from .__version__ import __version__ as __version__
from .res2csvlogger import getLogger_res2csv as getLogger_res2csv
from .resdatafiles import ResdataFiles as ResdataFiles

SUBMODULES: list[str] = [
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


__all__ = [
    "ResdataFiles",
    "__version__",
    "compdat",
    "csv2res",
    "equil",
    "faults",
    "fipreports",
    "getLogger_res2csv",
    "grid",
    "gruptree",
    "nnc",
    "pillars",
    "pvt",
    "res2csv",
    "rft",
    "satfunc",
    "summary",
    "trans",
    "vfp",
    "wcon",
    "wellcompletiondata",
    "wellconnstatus",
]

from .eclfiles import EclFiles

import grid2df
import compdat2df
import eclfiles
import equil2df
import faults2df
import gruptree2df
import nnc2df
import satfunc2df
import summary2df
import wcon2df

name = "ecl2df"

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

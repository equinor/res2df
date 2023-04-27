"""Constants for use in ecl2df."""
from typing import List

# This is a magic filename that means read/write from/to stdout
# This makes it impossible to write to a file called "-" on disk
# but that would anyway create a lot of other problems in the shell.
MAGIC_STDOUT: str = "-"

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
    "bulk"
]

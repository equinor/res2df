"""
Some definitions and parameters used to define VFPPROD and VFPINJ keywords in Eclipse.
This includes definitions of rates, thp, wfr (water fractions), gfr (gas fractions),
alq (artificial-lift-quantities), units and so on. Used for consistency check in IO
routines for VFPPROD and VFPINJ keywords in res2df.
"""

from enum import Enum
from typing import Dict, List, Union

# Supported types of VFP keywords
SUPPORTED_KEYWORDS: List[str] = [
    "VFPPROD",
    "VFPINJ",
]

# The renamers listed here map from opm-common json item names to
# desired column names in produced dataframes. They also to a certain
# extent determine the structure of the dataframe, in particular
# for keywords with arbitrary data amount pr. record (GAS, THP, WGR, GOR f.ex)
RENAMERS: Dict[str, Dict[str, Union[str, List[str]]]] = {}


# Type of VFP curve
class VFPTYPE(Enum):
    VFPPROD = "VFPPROD"
    VFPINJ = "VFPINJ"


# Flow rate variable types for VFPPROD
class VFPPROD_FLO(Enum):
    OIL = "OIL"
    LIQ = "LIQ"
    GAS = "GAS"
    WG = "WG"
    TM = "TM"


# Flow rate variable types for VFPINJ
class VFPINJ_FLO(Enum):
    OIL = "OIL"
    WAT = "WAT"
    GAS = "GAS"
    WG = "WG"
    TM = "TM"


# Water fraction types for VFPPROD
class WFR(Enum):
    WOR = "WOR"
    WCT = "WCT"
    WGR = "WGR"
    WWR = "WWR"
    WTF = "WTF"


# Gas fraction types for VFPPROD
class GFR(Enum):
    GOR = "GOR"
    GLR = "GLR"
    OGR = "OGR"
    MMW = "MMW"


# Artificial lift types for VFPPROD
class ALQ(Enum):
    GRAT = "GRAT"
    IGLR = "IGLR"
    TGLR = "TGLR"
    PUMP = "PUMP"
    COMP = "COMP"
    DENO = "DENO"
    DENG = "DENG"
    BEAN = "BEAN"
    UNDEFINED = "''"


# Unit types
class UNITTYPE(Enum):
    METRIC = "METRIC"
    FIELD = "FIELD"
    LAB = "LAB"
    PVTM = "PVT-M"
    DEFAULT = "DEFAULT"


# THP types supported
class THPTYPE(Enum):
    THP = "THP"


# Tabulated values types for VFPPROD
class VFPPROD_TABTYPE(Enum):
    BHP = "BHP"
    THT = "TEMP"


# Tabulated values types for VFPINJ
class VFPINJ_TABTYPE(Enum):
    BHP = "BHP"


# Unit definitions for VFPPROD
VFPPROD_UNITS = {
    "DEFAULT": {
        "FLO": {
            "OIL": "",
            "LIQ": "",
            "GAS": "",
            "WG": "",
            "TM": "",
        },
        "THP": {"THP": "barsa"},
        "WFR": {
            "WOR": "",
            "WCT": "",
            "WGR": "",
            "WWR": "",
            "WTF": "",
        },
        "GFR": {
            "GOR": "",
            "GLR": "",
            "OGR": "",
            "MMW": "",
        },
        "ALQ": {
            "GRAT": "",
            "IGLR": "",
            "TGLR": "",
            "DENO": "",
            "DENG": "",
            "BEAN": "",
            "''": "",
        },
    },
    "METRIC": {
        "FLO": {
            "OIL": "sm3/day",
            "LIQ": "sm3/day",
            "GAS": "sm3/day",
            "WG": "sm3/day",
            "TM": "kg-M/day",
        },
        "THP": {"THP": "barsa"},
        "WFR": {
            "WOR": "sm3/sm3",
            "WCT": "sm3/sm3",
            "WGR": "sm3/sm3",
            "WWR": "sm3/sm3",
            "WTF": "",
        },
        "GFR": {
            "GOR": "sm3/sm3",
            "GLR": "sm3/sm3",
            "OGR": "sm3/sm3",
            "MMW": "kg/kg-M",
        },
        "ALQ": {
            "GRAT": "sm3/day",
            "IGLR": "sm3/sm3",
            "TGLR": "sm3/sm3",
            "DENO": "kg/m3",
            "DENG": "kg/m3",
            "BEAN": "mm",
            "''": "",
        },
    },
    "FIELD": {
        "FLO": {
            "OIL": "stb/day",
            "LIQ": "stb/day",
            "GAS": "Mscf/day",
            "WG": "lb-M/day",
            "TM": "lb-M/day",
        },
        "THP": {"THP": "psia"},
        "WFR": {
            "WOR": "stb/stb",
            "WCT": "stb/stb",
            "WGR": "stb/Mscf",
            "WWR": "stb/Mscf",
            "WTF": "",
        },
        "GFR": {
            "GOR": "Mscf/stb",
            "GLR": "Mscf/stb",
            "OGR": "stb/Mscf",
            "MMW": "lb/lb-M",
        },
        "ALQ": {
            "GRAT": "Mscf/day",
            "IGLR": "Mscf/stb",
            "TGLR": "Mscf/stb",
            "DENO": "lb/ft3",
            "DENG": "lb/ft3",
            "BEAN": "1/64",
            "''": "",
        },
    },
    "LAB": {
        "FLO": {
            "OIL": "scc/hr",
            "LIQ": "scc/hr",
            "GAS": "scc/hr",
            "WG": "scc/hr",
            "TM": "lb-M/day",
        },
        "THP": {"THP": "atma"},
        "WFR": {
            "WOR": "scc/scc",
            "WCT": "scc/scc",
            "WGR": "scc/scc",
            "WWR": "scc/scc",
            "WTF": "",
        },
        "GFR": {
            "GOR": "scc/scc",
            "GLR": "scc/scc",
            "OGR": "scc/scc",
            "MMW": "lb/lb-M",
        },
        "ALQ": {
            "GRAT": "scc/hr",
            "IGLR": "scc/scc",
            "TGLR": "scc/scc",
            "DENO": "gm/cc",
            "DENG": "gm/cc",
            "BEAN": "mm",
            "''": "",
        },
    },
    "PVT-M": {
        "FLO": {
            "OIL": "sm3/day",
            "LIQ": "sm3/day",
            "GAS": "sm3/day",
            "WG": "sm3/day",
            "TM": "kg-M/day",
        },
        "THP": {"THP": "atma"},
        "WFR": {
            "WOR": "sm3/sm3",
            "WCT": "sm3/sm3",
            "WGR": "sm3/sm3",
            "WWR": "sm3/sm3",
            "WTF": "",
        },
        "GFR": {
            "GOR": "sm3/sm3",
            "GLR": "sm3/sm3",
            "OGR": "sm3/sm3",
            "MMW": "kg/kg-M",
        },
        "ALQ": {
            "GRAT": "sm3/day",
            "IGLR": "sm3/sm3",
            "TGLR": "sm3/sm3",
            "DENO": "kg/m3",
            "DENG": "kg/m3",
            "BEAN": "mm",
            "''": "",
        },
    },
}

# Unit definitions for VFPINJ
VFPINJ_UNITS = {
    "DEFAULT": {
        "FLO": {
            "OIL": "",
            "WAT": "",
            "GAS": "",
            "WG": "",
            "TM": "",
        },
        "THP": {"THP": ""},
    },
    "METRIC": {
        "FLO": {
            "OIL": "sm3/day",
            "WAT": "sm3/day",
            "GAS": "sm3/day",
            "WG": "sm3/day",
            "TM": "kg-M/day",
        },
        "THP": {"THP": "barsa"},
    },
    "FIELD": {
        "FLO": {
            "OIL": "stb/day",
            "WAT": "stb/day",
            "GAS": "Mscf/day",
            "WG": "Mscf/day",
            "TM": "lb-M/day",
        },
        "THP": {"THP": "psia"},
    },
    "LAB": {
        "FLO": {
            "OIL": "scc/hr",
            "WAT": "scc/hr",
            "GAS": "scc/hr",
            "WG": "scc/hr",
            "TM": "gm-M/hr",
        },
        "THP": {"THP": "atma"},
    },
    "PVT-M": {
        "FLO": {
            "OIL": "sm3/day",
            "WAT": "sm3/day",
            "GAS": "sm3/day",
            "WG": "sm3/day",
            "TM": "kg-M/day",
        },
        "THP": {"THP": "atma"},
    },
}

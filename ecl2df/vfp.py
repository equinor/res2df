"""
Extract the VFPPROD/VFPINJ data from an Eclipse (input) deck as Pandas Dataframes

Data can be extracted from a full Eclipse deck or from individual files.
"""

import argparse
import logging
import numbers
import sys
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

try:
    # Needed for mypy

    # pylint: disable=unused-import
    import opm.io

    # This import is seemingly not used, but necessary for some attributes
    # to be included in DeckItem objects.
    from opm.io.deck import DeckKeyword
except ImportError:
    pass

from ecl2df import EclFiles, common, getLogger_ecl2csv

logger = logging.getLogger(__name__)

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
    UNDEFINED = "UNDEFINED"


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
            "UNDEFINED": "",
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
            "UNDEFINED": "",
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
            "UNDEFINED": "",
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
            "UNDEFINED": "",
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
            "UNDEFINED": "",
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


# Dicitionaries for type definitions that are different for VFPPROD and VFPINJ
FLO = {VFPTYPE.VFPPROD: VFPPROD_FLO, VFPTYPE.VFPINJ: VFPINJ_FLO}
UNITS = {VFPTYPE.VFPPROD: VFPPROD_UNITS, VFPTYPE.VFPINJ: VFPINJ_UNITS}
TABTYPE = {VFPTYPE.VFPPROD: VFPPROD_TABTYPE, VFPTYPE.VFPINJ: VFPINJ_TABTYPE}


def vfpprod2df(keyword: DeckKeyword) -> pd.DataFrame:
    """Return a dataframes of a single VFPPROD table from an Eclipse deck.

    Data from the VFPPROD keyword are stacked into a Pandas Dataframe

     Args:
         deck:    Eclipse deck
    """

    # Number of records in keyword
    num_rec = len(keyword)

    # Parse records with basic information and interpolation ranges
    basic_record = common.parse_opmio_deckrecord(keyword[0], "VFPPROD", "records", 0)
    flow_record = common.parse_opmio_deckrecord(keyword[1], "VFPPROD", "records", 1)
    thp_record = common.parse_opmio_deckrecord(keyword[2], "VFPPROD", "records", 2)
    wfr_record = common.parse_opmio_deckrecord(keyword[3], "VFPPROD", "records", 3)
    gfr_record = common.parse_opmio_deckrecord(keyword[4], "VFPPROD", "records", 4)
    alq_record = common.parse_opmio_deckrecord(keyword[5], "VFPPROD", "records", 5)

    flow_values: Union[Any, List[float]]
    thp_values: Union[Any, List[float]]
    wfr_values: Union[Any, List[float]]
    gfr_values: Union[Any, List[float]]
    alq_values: Union[Any, List[float]]
    # Extract interpolation ranges into lists
    if isinstance(flow_record.get("FLOW_VALUES"), list):
        flow_values = flow_record.get("FLOW_VALUES")
    elif isinstance(flow_record.get("FLOW_VALUES"), numbers.Number):
        flow_values = [flow_record.get("FLOW_VALUES")]
    if isinstance(thp_record.get("THP_VALUES"), list):
        thp_values = thp_record.get("THP_VALUES")
    elif isinstance(thp_record.get("THP_VALUES"), numbers.Number):
        thp_values = [thp_record.get("THP_VALUES")]
    if isinstance(wfr_record.get("WFR_VALUES"), list):
        wfr_values = wfr_record.get("WFR_VALUES")
    elif isinstance(wfr_record.get("WFR_VALUES"), numbers.Number):
        wfr_values = [wfr_record.get("WFR_VALUES")]
    if isinstance(gfr_record.get("GFR_VALUES"), list):
        gfr_values = gfr_record.get("GFR_VALUES")
    elif isinstance(gfr_record.get("GFR_VALUES"), numbers.Number):
        gfr_values = [gfr_record.get("GFR_VALUES")]
    if isinstance(alq_record.get("ALQ_VALUES"), list):
        alq_values = alq_record.get("ALQ_VALUES")
    elif isinstance(alq_record.get("ALQ_VALUES"), numbers.Number):
        alq_values = [alq_record.get("ALQ_VALUES")]

    # Check of consistent dimensions
    no_flow_values = len(flow_values)
    no_thp_values = len(thp_values)
    no_wfr_values = len(wfr_values)
    no_gfr_values = len(gfr_values)
    no_alq_values = len(alq_values)
    no_interp_values = no_thp_values * no_wfr_values * no_gfr_values * no_alq_values
    no_tab_records = num_rec - 6
    if no_interp_values != no_tab_records:
        logger.error(
            "Dimensions of interpolation ranges "
            "does not match number of tabulated records"
        )
        return pd.DataFrame()

    # Extract basic table information
    table = int(basic_record["TABLE"])
    datum = float(basic_record["DATUM_DEPTH"])
    rate = VFPPROD_FLO.GAS
    if basic_record["RATE_TYPE"]:
        rate = VFPPROD_FLO[basic_record["RATE_TYPE"]]
    wfr = WFR.WCT
    if basic_record["WFR"]:
        wfr = WFR[basic_record["WFR"]]
    gfr = GFR.GOR
    if basic_record["GFR"]:
        gfr = GFR[basic_record["GFR"]]
    thp = THPTYPE.THP
    if basic_record["PRESSURE_DEF"]:
        thp = THPTYPE[basic_record["PRESSURE_DEF"]]
    alq = ALQ.UNDEFINED
    if basic_record["ALQ_DEF"]:
        if basic_record["ALQ_DEF"].strip():
            alq = ALQ[basic_record["ALQ_DEF"]]
    units = UNITTYPE.DEFAULT
    if basic_record["UNITS"]:
        units = UNITTYPE[basic_record["UNITS"]]
    tab = VFPPROD_TABTYPE.BHP
    if basic_record["BODY_DEF"]:
        tab = VFPPROD_TABTYPE[basic_record["BODY_DEF"]]

    # Extract tabulated values (BHP values)
    bhp_array_values: List[Any] = []
    for n in range(6, num_rec):
        bhp_record = common.parse_opmio_deckrecord(keyword[n], "VFPPROD", "records", 6)
        bhp_values: Union[Any, List[float]]
        if isinstance(bhp_record.get("VALUES"), list):
            bhp_values = bhp_record.get("VALUES")
        elif isinstance(bhp_record.get("VALUES"), numbers.Number):
            bhp_values = [bhp_record.get("VALUES")]

        thp_index = bhp_record["THP_INDEX"] - 1
        wfr_index = bhp_record["WFR_INDEX"] - 1
        gfr_index = bhp_record["GFR_INDEX"] - 1
        alq_index = bhp_record["ALQ_INDEX"] - 1

        thp_value = thp_values[thp_index]
        wfr_value = wfr_values[wfr_index]
        gfr_value = gfr_values[gfr_index]
        alq_value = alq_values[alq_index]

        bhp_record_values = (
            [thp_value] + [wfr_value] + [gfr_value] + [alq_value] + bhp_values
        )
        if len(bhp_values) != no_flow_values:
            logger.error(
                "Dimension of record of tabulated values "
                "does not match number of flow values"
            )
            return pd.DataFrame()
        bhp_array_values.append(bhp_record_values)

    df_bhp = pd.DataFrame(bhp_array_values)

    indextuples = [
        ("PRESSURE", "DELETE"),
        ("WFR", "DELETE"),
        ("GFR", "DELETE"),
        ("ALQ", "DELETE"),
    ]

    flow_vals: List[float] = [float(val) for val in flow_values]
    for flowvalue in flow_vals:
        indextuples.append(("TAB", str(flowvalue)))

    # Set the columns to a MultiIndex, to facilitate stacking
    df_bhp.columns = pd.MultiIndex.from_tuples(indextuples)

    # Now stack
    df_bhp_stacked = df_bhp.stack()

    # In order to propagate the gfr, thp, wct values after
    # stacking to the correct rows, we should either understand
    # how to do that properly using pandas, but for now, we try a
    # backwards fill, hopefully that is robust enough
    df_bhp_stacked.bfill(inplace=True)
    # Also reset the index:
    df_bhp_stacked.reset_index(inplace=True)
    df_bhp_stacked.drop("level_0", axis="columns", inplace=True)
    # This column is not meaningful (it is the old index)

    # Delete rows that does not belong to any flow rate (this is
    # possibly a by-product of not doing the stacking in an
    # optimal way)
    df_bhp_stacked = df_bhp_stacked[df_bhp_stacked["level_1"] != "DELETE"]

    # Add correct column name for the flow values that we have stacked
    cols = list(df_bhp_stacked.columns)
    cols[cols.index("level_1")] = "RATE"
    df_bhp_stacked.columns = cols
    df_bhp_stacked["RATE"] = df_bhp_stacked["RATE"].astype(float)

    # Add meta-data
    df_bhp_stacked["VFP_TYPE"] = "VFPPROD"
    df_bhp_stacked["TABLE_NUMBER"] = table
    df_bhp_stacked["DATUM"] = datum
    df_bhp_stacked["UNIT_TYPE"] = units.value
    df_bhp_stacked["RATE_TYPE"] = rate.value
    df_bhp_stacked["WFR_TYPE"] = wfr.value
    df_bhp_stacked["GFR_TYPE"] = gfr.value
    df_bhp_stacked["ALQ_TYPE"] = alq.value
    df_bhp_stacked["PRESSURE_TYPE"] = thp.value
    df_bhp_stacked["TAB_TYPE"] = tab.value

    # Sort the columns in wanted order
    df_bhp_stacked = df_bhp_stacked[
        [
            "RATE",
            "PRESSURE",
            "WFR",
            "GFR",
            "ALQ",
            "TAB",
            "VFP_TYPE",
            "TABLE_NUMBER",
            "DATUM",
            "RATE_TYPE",
            "WFR_TYPE",
            "GFR_TYPE",
            "ALQ_TYPE",
            "PRESSURE_TYPE",
            "TAB_TYPE",
            "UNIT_TYPE",
        ]
    ]

    return df_bhp_stacked


def vfpinj2df(keyword: DeckKeyword) -> pd.DataFrame:
    """Return a dataframes of a single VFPINJ table from an Eclipse deck

    Data from the VFPINJ keyword are stacked into a Pandas Dataframe

     Args:
         deck:    Eclipse deck
    """

    # Number of record in keyword
    num_rec = len(keyword)

    # Parse records with basic information and interpolation ranges
    basic_record = common.parse_opmio_deckrecord(keyword[0], "VFPINJ", "records", 0)
    flow_record = common.parse_opmio_deckrecord(keyword[1], "VFPINJ", "records", 1)
    thp_record = common.parse_opmio_deckrecord(keyword[2], "VFPINJ", "records", 2)

    # Extract interpolation ranges
    flow_values: Union[Any, List[float]]
    thp_values: Union[Any, List[float]]
    if isinstance(flow_record.get("FLOW_VALUES"), list):
        flow_values = flow_record.get("FLOW_VALUES")
    elif isinstance(flow_record.get("FLOW_VALUES"), numbers.Number):
        flow_values = [flow_record.get("flow_VALUES")]
    if isinstance(thp_record.get("THP_VALUES"), list):
        thp_values = thp_record.get("THP_VALUES")
    elif isinstance(thp_record.get("THP_VALUES"), numbers.Number):
        thp_values = [thp_record.get("THP_VALUES")]

    # Check of consistent dimensions
    no_flow_values = len(flow_values)
    no_thp_values = len(thp_values)
    no_interp_values = no_thp_values
    no_tab_records = num_rec - 3
    if no_interp_values != no_tab_records:
        logger.error(
            "Dimensions of interpolation ranges "
            "does not match number of tabulated records"
        )
        return pd.DataFrame()

    # Extract basic table information
    table = basic_record["TABLE"]
    datum = basic_record["DATUM_DEPTH"]
    rate = VFPINJ_FLO.GAS
    if basic_record["RATE_TYPE"]:
        rate = VFPINJ_FLO[basic_record["RATE_TYPE"]]
    thp = THPTYPE.THP
    if basic_record["PRESSURE_DEF"]:
        thp = THPTYPE[basic_record["PRESSURE_DEF"]]
    units = UNITTYPE.DEFAULT
    if basic_record["UNITS"]:
        units = UNITTYPE[basic_record["UNITS"]]
    tab = VFPINJ_TABTYPE.BHP
    if basic_record["BODY_DEF"]:
        tab = VFPINJ_TABTYPE[basic_record["BODY_DEF"]]

    # Extract tabulated values (BHP values)
    bhp_array_values = []
    for n in range(3, num_rec):
        bhp_record = common.parse_opmio_deckrecord(keyword[n], "VFPINJ", "records", 3)
        bhp_values: Union[Any, List[float]]
        if isinstance(bhp_record.get("VALUES"), list):
            bhp_values = bhp_record.get("VALUES")
        elif isinstance(bhp_record.get("VALUES"), numbers.Number):
            bhp_values = [bhp_record.get("VALUES")]

        thp_index = bhp_record["THP_INDEX"] - 1
        thp_value = thp_values[thp_index]

        bhp_record_values = [thp_value] + bhp_values
        if len(bhp_values) != no_flow_values:
            logger.error(
                "Dimension of record of tabulated values "
                "does not match number of flow values"
            )
            return pd.DataFrame()
        bhp_array_values.append(bhp_record_values)

    df_bhp = pd.DataFrame(bhp_array_values)

    indextuples = [("PRESSURE", "DELETE")]

    for flowvalue in flow_values:
        indextuples.append(("TAB", str(flowvalue)))

    # Set the columns to a MultiIndex, to facilitate stacking
    df_bhp.columns = pd.MultiIndex.from_tuples(indextuples)

    # Now stack
    df_bhp_stacked = df_bhp.stack()

    # In order to propagate the thp values after
    # stacking to the correct rows, we should either understand
    # how to do that properly using pandas, but for now, we try a
    # backwards fill, hopefully that is robust enough
    df_bhp_stacked.bfill(inplace=True)
    # Also reset the index:
    df_bhp_stacked.reset_index(inplace=True)
    df_bhp_stacked.drop("level_0", axis="columns", inplace=True)
    # This column is not meaningful (it is the old index)

    # Delete rows that does not belong to any flow rate (this is
    # possibly a by-product of not doing the stacking in an
    # optimal way)
    df_bhp_stacked = df_bhp_stacked[df_bhp_stacked["level_1"] != "DELETE"]

    # Add correct column name for the flow values that we have stacked
    cols = list(df_bhp_stacked.columns)
    cols[cols.index("level_1")] = "RATE"
    df_bhp_stacked.columns = cols
    df_bhp_stacked["RATE"] = df_bhp_stacked["RATE"].astype(float)

    # Add meta-data
    df_bhp_stacked["VFP_TYPE"] = "VFPINJ"
    df_bhp_stacked["TABLE_NUMBER"] = int(table)
    df_bhp_stacked["DATUM"] = float(datum)
    df_bhp_stacked["UNIT_TYPE"] = units.value
    df_bhp_stacked["RATE_TYPE"] = rate.value
    df_bhp_stacked["PRESSURE_TYPE"] = thp.value
    df_bhp_stacked["TAB_TYPE"] = tab.value

    # Sort the columns in wanted order
    df_bhp_stacked = df_bhp_stacked[
        [
            "RATE",
            "PRESSURE",
            "TAB",
            "VFP_TYPE",
            "TABLE_NUMBER",
            "DATUM",
            "RATE_TYPE",
            "PRESSURE_TYPE",
            "TAB_TYPE",
            "UNIT_TYPE",
        ]
    ]

    return df_bhp_stacked


def dfs(
    deck: Union[str, EclFiles, "opm.libopmcommon_python.Deck"],
    keywords: Optional[List[str]] = ["VFPROD"],
) -> List[pd.DataFrame]:
    """Produce a list of dataframes of vfp tables from a deck

    Data for the keywords VFPPROD/VFPINJ will be returned as separate item in list

    Args:
        deck:     Eclipse deck or string with deck
        keywords: VFP table type, i.e. ['VFPPROD'], ['VFPINJ'] or ['VFPPROD','VFPINJ']
    """
    if isinstance(deck, EclFiles):
        deck = deck.get_ecldeck()
    elif isinstance(deck, str):
        deck = EclFiles.str2deck(deck)

    if keywords:
        for keyword in keywords:
            if keyword not in SUPPORTED_KEYWORDS:
                logger.error(
                    "VFP type %s not supported by vfp.dfs, "
                    "choose 'VFPPROD', 'VFPINJ' or both" % keyword
                )

    dfs_vfp = []
    # The keywords VFPPROD/VFPINJ can be used many times in Eclipse and be introduced in
    # separate files or a common file. Need to loop to find all instances of keyword and
    # store separately
    for deck_keyword in deck:
        if keywords and deck_keyword.name in keywords:
            if deck_keyword.name == "VFPPROD":
                dfs_vfp.append(vfpprod2df(deck_keyword))
            elif deck_keyword.name == "VFPINJ":
                dfs_vfp.append(vfpinj2df(deck_keyword))

    return dfs_vfp


def write_eclipse_comment(comment: str, max_char_per_line: int = 72) -> str:
    """Produce a string representing comment in Eclipse file

    Args:
        comment:           comment to be included in Eclipse output
        max_char_per_line: max number of characters per line
    """

    max_char = max_char_per_line - 2
    comment_str = ""

    # Respect original line shifts, but add additional line shift
    # when line is longer than maximum number of characters allowed
    comment_lines = comment.split("\n")
    for line in comment_lines:
        words = line.split()
        while words:
            new_line = ""
            while words and len(new_line) + len(words[0]) <= max_char:
                if new_line:
                    new_line += " " + words[0]
                else:
                    new_line += words[0]
                words.pop(0)
            comment_str += new_line + "\n"

    return comment_str


def write_vfpprod_basic_record(
    tableno: int,
    datum: float,
    flo_type: str,
    wfr_type: str,
    gfr_type: str,
    alq_type: str,
    pressure_type: str,
    unit_type: str,
    tab_type: str,
) -> str:
    """Produce a string representing the first record for Eclipse  VFPPROD keyword

    Args:
        tableno:       VFPROD table number
        datum:         datum depth
        flo_type:      FLO type
        wfr_type       WFR type
        gfr_type       GFR type
        alq_type:      ALQ type
        pressure_type: THP type
        unit_type:     Unit type
        tab_type:      Table type (BHP/THT)
    """

    alq_type_str = "''"
    if alq_type != "UNDEFINED":
        alq_type_str = alq_type

    ecl_str = "-- Table  Datum Depth  Rate Type  WFR Type  "
    ecl_str += "GFR Type  THP Type  ALQ Type  UNITS   TAB Type\n"
    ecl_str += "-- -----  -----------  ---------  --------  "
    ecl_str += "--------  --------  --------  ------  --------\n"
    ecl_str += "   %5d  %11.1f   %8s  %8s  %8s  %8s  %8s  %6s  %8s /\n\n" % (
        tableno,
        datum,
        flo_type,
        wfr_type,
        gfr_type,
        pressure_type,
        alq_type_str,
        unit_type,
        tab_type,
    )
    return ecl_str


def write_vfpinj_basic_record(
    tableno: int,
    datum: float,
    flo_type: str,
    pressure_type: str,
    unit_type: str,
    tab_type: str,
) -> str:
    """Produce a string representing the first record for Eclipse  VFPINJ keyword

    Args:
        tableno:       VFPROD table number
        datum:         datum depth
        pressure_type: THP type
        unit_type:     Unit type
        tab_type:      Table type (BHP)
    """

    unit_type_str = "1*"
    if unit_type != "DEFAULT":
        unit_type_str = unit_type

    ecl_str = "-- Table  Datum Depth  Rate Type  THP Type  UNITS     TAB Type\n"
    ecl_str += "-- -----  -----------  ---------  --------  --------  --------\n"
    ecl_str += "   %5d  %11.1f  %9s  %8s  %8s  %8s /\n\n" % (
        tableno,
        datum,
        flo_type,
        pressure_type,
        unit_type_str,
        tab_type,
    )

    return ecl_str


def write_vfp_range(
    values: List[float],
    var_type: str,
    unit_type: str,
    format: str = "%10.6g",
    values_per_line: int = 5,
) -> str:
    """Produce a string representing an Eclipse record for a given table range

    Args:
        values:          List/array with the range sorted
        var_type:        The Eclipse variable type defintion
        unit_type:       The unit type for the variable
        format:          Format string for values
        values_per_line: Number of values per line in output
    """

    var_type_str = "''"
    if var_type != "UNDEFINED":
        var_type_str = var_type

    ecl_str = "-- %s units - %s ( %d values )\n" % (
        var_type_str,
        unit_type,
        len(values),
    )
    for i, value in enumerate(values):
        ecl_str += format % value
        if (i + 1) % values_per_line == 0 and i < len(values) - 1:
            ecl_str += "\n"
    ecl_str += " /\n"
    ecl_str += "\n"

    return ecl_str


def write_vfpprod_table(
    table: pd.DataFrame,
    format: str = "%10.3",
    values_per_line: int = 5,
) -> str:
    """Produce a string representing an Eclipse record for a VFPPROD table (BHP part)

    Args:
        table: DataFrame with multiindex for table ranges and colums
               for tabulated values (BHP)
        format: Format string for values
        values_per_line: Number of values per line in output
    """

    ecl_str = ""
    for idx, row in table.iterrows():
        ecl_str += "%2d %2d %2d %2d" % (idx[0], idx[1], idx[2], idx[3])
        no_flo = len(table.loc[idx].to_list())
        for n, value in enumerate(table.loc[idx].to_list()):
            ecl_str += format % value
            if (n + 1) % values_per_line == 0:
                if n < no_flo - 1:
                    ecl_str += "\n"
                    ecl_str += " " * 11
                else:
                    ecl_str += "\n"
            elif n == no_flo - 1:
                ecl_str += "\n"
        ecl_str += "/\n"

    return ecl_str


def write_vfpinj_table(
    table: pd.DataFrame,
    format: str = "%10.6g",
    values_per_line: int = 5,
) -> str:
    """Produce a string representing an Eclipse record for a VFPINJ table (BHP part)

    Args:
        table: DataFrame with multiindex for table ranges and colums
               for tabulated values (BHP)
        format: Format string for values
        values_per_line: Number of values per line in output
    """

    ecl_str = ""
    for idx, row in table.iterrows():
        ecl_str += "%2d" % (idx)
        no_flo = len(table.loc[idx].to_list())
        for n, value in enumerate(table.loc[idx].to_list()):
            ecl_str += format % value
            if (n + 1) % values_per_line == 0:
                if n < no_flo - 1:
                    ecl_str += "\n"
                    ecl_str += " " * 2
                else:
                    ecl_str += "\n"
            elif n == no_flo - 1:
                ecl_str += "\n"
        ecl_str += "/\n"

    return ecl_str


def df2ecl_vfpprod(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Produce a string defining single VFPPROD Eclipse input from a dataframe

    All data for the keywords VFPPROD will be returned.

    Args:
        dframe:    Dataframe containing complete description of single VFPPROD input
        comment:   Text that will be included as comment
    """
    if dframe.empty:
        return "-- No data!"

    # Consistency checks of data type
    if len(dframe["RATE_TYPE"].unique()) == 1:
        rate = VFPPROD_FLO[dframe["RATE_TYPE"].unique()[0]]
    else:
        logger.error("Definition of FLO type is not unique")
        return ""
    if len(dframe["WFR_TYPE"].unique()) == 1:
        wfr = WFR[dframe["WFR_TYPE"].unique()[0]]
    else:
        logger.error("Definition of WFR type is not unique")
        return ""
    if len(dframe["GFR_TYPE"].unique()) == 1:
        gfr = GFR[dframe["GFR_TYPE"].unique()[0]]
    else:
        logger.error("Definition of GFR type is not unique")
        return ""
    if len(dframe["ALQ_TYPE"].unique()) == 1:
        alq = ALQ[dframe["ALQ_TYPE"].unique()[0]]
    else:
        logger.error("Definition of ALQ type is not unique")
        return ""
    if len(dframe["PRESSURE_TYPE"].unique()) == 1:
        thp = THPTYPE[dframe["PRESSURE_TYPE"].unique()[0]]
    else:
        logger.error("Definition of THP type is not unique")
        return ""
    if len(dframe["TAB_TYPE"].unique()) == 1:
        tab = VFPPROD_TABTYPE[dframe["TAB_TYPE"].unique()[0]]
    else:
        logger.error("Definition of TAB type is not unique")
        return ""
    if len(dframe["UNIT_TYPE"].unique()) == 1:
        unit = UNITTYPE[dframe["UNIT_TYPE"].unique()[0]]
    else:
        logger.error("Definition of UNIT type is not unique")
        return ""

    # Consistency check of basic data
    if len(dframe["TABLE_NUMBER"].unique()) == 1:
        vfpno = dframe["TABLE_NUMBER"].unique()[0]
    else:
        logger.error("Definition of TABLE_NUMBER is not unique")
        return ""
    if len(dframe["DATUM"].unique()) == 1:
        datum = dframe["DATUM"].unique()[0]
    else:
        logger.error("Definition of DATUM is not unique")
        return ""

    # Reading interpolation ranges
    flow_values = dframe["RATE"].unique().astype(float).tolist()
    no_flow_values = len(flow_values)
    wfr_values = dframe["WFR"].unique().astype(float).tolist()
    wfr_values.sort()
    no_wfr_values = len(wfr_values)
    gfr_values = dframe["GFR"].unique().astype(float).tolist()
    gfr_values.sort()
    no_gfr_values = len(gfr_values)
    alq_values = dframe["ALQ"].unique().astype(float).tolist()
    alq_values.sort()
    no_alq_values = len(alq_values)
    thp_values = dframe["PRESSURE"].unique().astype(float).tolist()
    thp_values.sort()
    no_thp_values = len(thp_values)
    no_interp_values = (
        no_thp_values * no_alq_values * no_gfr_values * no_wfr_values * no_flow_values
    )
    no_tab_values = len(dframe)

    # Wheck consistency of interpolation ranges and tabulated values
    if no_tab_values % no_flow_values != 0:
        logger.error(
            "Number of unique rate values %d not consistent "
            "with number of tabulated values %d" % (no_flow_values, no_tab_values)
        )
    if no_tab_values % no_wfr_values != 0:
        logger.error(
            "Number of unique wfr values %d not "
            "consistent with number of tabulated values %d"
            % (no_wfr_values, no_tab_values)
        )
    if no_tab_values % no_gfr_values != 0:
        logger.error(
            "Number of unique gfr values %d not consistent "
            "with number of tabulated values %d" % (no_gfr_values, no_tab_values)
        )
    if no_tab_values % no_alq_values != 0:
        logger.error(
            "Number of unique alq values %d not consistent "
            "with number of tabulated values %d" % (no_alq_values, no_tab_values)
        )
    if no_tab_values % no_thp_values != 0:
        logger.error(
            "Number of unique thp values %d not consistent "
            "with number of tabulated values %d" % (no_thp_values, no_tab_values)
        )
    if no_tab_values % no_interp_values != 0:
        logger.error(
            "Number of unique interpolation values %d not consistent "
            "with number of tabulated values %d" % (no_interp_values, no_tab_values)
        )

    # Replace interpolation values with index in dataframe
    df_tab = dframe[["PRESSURE", "WFR", "GFR", "ALQ", "RATE", "TAB"]].copy()
    wfr_indices = [float(val) for val in range(1, len(wfr_values) + 1)]
    wfr_replace_map = dict(zip(wfr_values, wfr_indices))
    df_tab["WFR"] = df_tab["WFR"].apply(lambda x: wfr_replace_map[x])
    df_tab.loc[:, "WFR"] = df_tab.loc[:, "WFR"].astype(int)
    gfr_indices = [float(val) for val in range(1, len(gfr_values) + 1)]
    gfr_replace_map = dict(zip(gfr_values, gfr_indices))
    df_tab["GFR"] = df_tab["GFR"].apply(lambda x: gfr_replace_map[x])
    df_tab.loc[:, "GFR"] = df_tab.loc[:, "GFR"].astype(int)
    alq_indices = [float(val) for val in range(1, len(alq_values) + 1)]
    alq_replace_map = dict(zip(alq_values, alq_indices))
    df_tab["ALQ"] = df_tab["ALQ"].apply(lambda x: alq_replace_map[x])
    df_tab.loc[:, "ALQ"] = df_tab.loc[:, "ALQ"].astype(int)
    thp_indices = [float(val) for val in range(1, len(thp_values) + 1)]
    thp_replace_map = dict(zip(thp_values, thp_indices))
    df_tab["PRESSURE"] = df_tab["PRESSURE"].apply(lambda x: thp_replace_map[x])
    df_tab.loc[:, "PRESSURE"] = df_tab.loc[:, "PRESSURE"].astype(int)

    # Make multiindex for interpolation index
    df_tab.set_index(["PRESSURE", "WFR", "GFR", "ALQ", "RATE"], inplace=True)

    # Unstack dataframe to get flow values (rate) into columns
    df_tab_unstack = df_tab.unstack(level=-1)
    # Sort multiindex
    df_tab_unstack.sort_index(inplace=True)

    # Write dataframe to string with Eclipse format for VFPPROD
    ecl_str = "VFPPROD\n"
    if comment:
        ecl_str += common.comment_formatter(comment)
    else:
        ecl_str += "\n"

    unit_value = unit.value
    if unit == UNITTYPE.DEFAULT:
        unit_value = "1*"
    ecl_str += write_vfpprod_basic_record(
        vfpno,
        datum,
        rate.value,
        wfr.value,
        gfr.value,
        alq.value,
        thp.value,
        unit_value,
        tab.value,
    )
    ecl_str += write_vfp_range(
        flow_values, rate.value, VFPPROD_UNITS[unit.value]["FLO"][rate.value], "%10.6g"
    )
    ecl_str += write_vfp_range(
        thp_values, thp.value, VFPPROD_UNITS[unit.value]["THP"][thp.value], "%10.6g"
    )
    ecl_str += write_vfp_range(
        wfr_values, wfr.value, VFPPROD_UNITS[unit.value]["WFR"][wfr.value], "%10.6g"
    )
    ecl_str += write_vfp_range(
        gfr_values, gfr.value, VFPPROD_UNITS[unit.value]["GFR"][gfr.value], "%10.6g"
    )
    ecl_str += write_vfp_range(
        alq_values, alq.value, VFPPROD_UNITS[unit.value]["ALQ"][alq.value], "%10.6g"
    )
    ecl_str += write_vfpprod_table(df_tab_unstack, "%10.6g")

    return ecl_str


def df2ecl_vfpinj(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Produce a string defining single VFPINJ Eclipse input from a dataframe

    All data for the keywords VFPINJ will be returned.

    Args:
        dframe:    Dataframe containing complete description of single VFPINJ input
        comment:   Text that will be included as comment
    """
    if dframe.empty:
        return "-- No data!"

    # Consistency checks of data type
    if len(dframe["RATE_TYPE"].unique()) == 1:
        rate = VFPINJ_FLO[dframe["RATE_TYPE"].unique()[0]]
    else:
        logger.error("Definition of FLO type is not unique")
    if len(dframe["PRESSURE_TYPE"].unique()) == 1:
        thp = THPTYPE[dframe["PRESSURE_TYPE"].unique()[0]]
    else:
        logger.error("Definition of THP type is not unique")
    if len(dframe["TAB_TYPE"].unique()) == 1:
        tab = VFPINJ_TABTYPE[dframe["TAB_TYPE"].unique()[0]]
    else:
        logger.error("Definition of TAB type is not unique")
    if len(dframe["UNIT_TYPE"].unique()) == 1:
        unit = UNITTYPE[dframe["UNIT_TYPE"].unique()[0]]
    else:
        logger.error("Definition of UNIT type is not unique")

    # Consistency check of basic data
    if len(dframe["TABLE_NUMBER"].unique()) == 1:
        vfpno = dframe["TABLE_NUMBER"].unique()[0]
    else:
        logger.error("Definition of TABLE_NUMBER is not unique")
    if len(dframe["DATUM"].unique()) == 1:
        datum = dframe["DATUM"].unique()[0]
    else:
        logger.error("Definition of DATUM is not unique")

    # Reading interpolation ranges
    flow_values = dframe["RATE"].unique().astype(float).tolist()
    no_flow_values = len(flow_values)
    thp_values = dframe["PRESSURE"].unique().astype(float).tolist()
    thp_values.sort()
    no_thp_values = len(thp_values)
    no_interp_values = no_thp_values * no_flow_values
    no_tab_values = len(dframe)

    # Wheck consistency of interpolation ranges and tabulated values
    if no_tab_values % no_flow_values != 0:
        logger.error(
            "Number of unique rate values %d"
            " not consistent with number of tabulated"
            " values %d" % (no_flow_values, no_tab_values)
        )
    if no_tab_values % no_thp_values != 0:
        logger.error(
            "Number of unique thp values %d not consistent "
            "with number of tabulated values %d" % (no_thp_values, no_tab_values)
        )
    if no_tab_values % no_interp_values != 0:
        logger.error(
            "Number of unique interpolation values %d not consistent "
            "with number of tabulated values %d" % (no_interp_values, no_tab_values)
        )

    # Replace interpolation values with index in dataframe
    df_tab = dframe[["PRESSURE", "RATE", "TAB"]].copy()
    thp_indices = [float(val) for val in range(1, len(thp_values) + 1)]
    thp_range_map = dict(zip(thp_values, thp_indices))
    df_tab["PRESSURE"] = df_tab["PRESSURE"].apply(lambda x: thp_range_map[x])
    df_tab["PRESSURE"] = df_tab["PRESSURE"].astype(int)
    df_tab["RATE"] = df_tab["RATE"].astype(int)

    # Make multiindex for interpolation index
    df_tab.set_index(["PRESSURE", "RATE"], inplace=True)

    # Unstack dataframe to get flow values (rate) into columns
    df_tab_unstack = df_tab.unstack(level=-1)
    # Sort multiindex
    df_tab_unstack.sort_index(inplace=True)

    # Write dataframe to string with Eclipse format for VFPINJ
    ecl_str = "VFPINJ\n"
    if comment:
        ecl_str += common.comment_formatter(comment)
    else:
        ecl_str += "\n"

    unit_value = unit.value
    if unit == UNITTYPE.DEFAULT:
        unit_value = "1*"
    ecl_str += write_vfpinj_basic_record(
        vfpno, datum, rate.value, thp.value, unit_value, tab.value
    )
    ecl_str += write_vfp_range(
        flow_values, rate.value, VFPINJ_UNITS[unit.value]["FLO"][rate.value], "%10.6g"
    )
    ecl_str += write_vfp_range(
        thp_values, thp.value, VFPINJ_UNITS[unit.value]["THP"][thp.value], "%10.6g"
    )
    ecl_str += write_vfpinj_table(df_tab_unstack, "%10.6g")

    return ecl_str


def df2ecls_vfp(
    dframe: pd.DataFrame,
    keywords: Optional[List[str]] = None,
    comments: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Produce a list of strings defining VFPPROD/VFPINJ Eclipse input from a dataframe

    All data for the keywords VFPPROD/VFPINJ will be returned.

    Args:
        dframe:    Dataframe containing complete description of VFPPROD/VFPINJ input
        keywords: List of keywords to include, ['VFPPROD'], ['VFPINJ']
                  or ['VFPPROD','VFPINJ']
        comments: Dictionary indexed by keyword with comments to be
            included pr. keyword.
    """

    if dframe.empty:
        return []

    vfp_keywords = []
    if keywords:
        for keyword in keywords:
            if keyword not in SUPPORTED_KEYWORDS:
                logger.warning(
                    "Given keyword %s is not in supported keywords" % (keyword)
                )
            else:
                vfp_keywords.append(keyword)

    vfp_strs = []
    vfp_numbers = dframe["TABLE_NUMBER"].unique()
    for vfpno in vfp_numbers:
        df_vfp = dframe[dframe["TABLE_NUMBER"] == vfpno]
        if np.all(df_vfp["VFP_TYPE"] == "VFPPROD") and "VFPPROD" in vfp_keywords:
            if comments and "VFPPROD" in comments.keys():
                vfp_strs.append(df2ecl_vfpprod(df_vfp, comments["VFPPROD"]))
            else:
                vfp_strs.append(df2ecl_vfpprod(df_vfp))
        elif np.all(df_vfp["VFP_TYPE"] == "VFPINJ") and "VFPINJ" in vfp_keywords:
            if comments and "VFPINJ" in comments.keys():
                vfp_strs.append(df2ecl_vfpinj(df_vfp, comments["VFPINJ"]))
            else:
                vfp_strs.append(df2ecl_vfpinj(df_vfp))
        else:
            logger.warning(
                "WARNING: VFP number {vfpno} does not have consistent "
                "type defintion in vfp.dfecls_vfp"
            )

    return vfp_strs


def df2ecl(
    dframe: pd.DataFrame,
    keywords: Optional[List[str]],
    comments: Optional[Dict[str, str]] = None,
    filename: Optional[str] = None,
) -> str:
    """Produce a string defining all VFPPROD/VFPINJ Eclipse input from a dataframe

    All data for the keywords VFPPROD/VFPINJ will be returned.

    Args:
        dframe:    Dataframe containing complete description of VFPPROD/VFPINJ input
        keywords:  List of keywords to include, ['VFPPROD'], ['VFPINJ']
                   or ['VFPPROD','VFPINJ']
        comments:  comments: Dictionary indexed by keyword with comments to be
                   included pr. keyword. If a key named "master" is present
                   it will be used as a master comment for the outputted file.
        filename:  If supplied, the generated text will also be dumped
                   to file.
    """

    strs_vfp = df2ecls_vfp(dframe, keywords=keywords, comments=comments)
    str_vfps = ""

    if comments and "master" in comments.keys():
        str_vfps += common.comment_formatter(comments["master"])
    for str_vfp in strs_vfp:
        str_vfps += str_vfp
        str_vfps += "\n"

    if filename:
        with open(filename, "r") as fout:
            fout.write(str_vfp)
    return str_vfps


def df(
    deck: Union[str, EclFiles, "opm.libopmcommon_python.Deck"],
    keywords: Optional[List[str]] = ["VFPPROD"],
) -> pd.DataFrame:
    """Produce a dataframes of all vfp tables from a deck

    All data for the keywords VFPPROD/VFPINJ will be returned.

    Args:
        deck:     Eclipse deck or string wit deck
        keywords: VFP table type, i.e. ['VFPPROD'], ['VFPINJ']
                  or ['VFPPROD','VFPINJ']
    """

    if not keywords:
        logger.warning("No keywords provided to vfp.df. Empty dataframe returned")
        return pd.DataFrame()

    if isinstance(deck, EclFiles):
        deck = deck.get_ecldeck()
    elif isinstance(deck, str):
        deck = EclFiles.str2deck(deck)

    # Extract all VFPROD/VFPINJ as separate dataframes
    dfs_vfp = dfs(deck, keywords)
    # Concat all dataframes into one dataframe
    if dfs_vfp:
        return pd.concat(dfs_vfp)


#    else:
#        logger.warning('Empty dataframe, input file does not contain keywords')


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parsers.

    Arguments:
        parser (argparse.ArgumentParser or argparse.subparser): parser
            to fill with arguments
    """
    parser.add_argument("DATAFILE", help="Name of Eclipse DATA file.")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file. No CSV dump if empty",
        default="",
    )
    parser.add_argument(
        "-k",
        "--keywords",
        nargs="+",
        help="List of VFP keywords to include, i.e. VFPPROD/VFPINJ",
        default=None,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def fill_reverse_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Fill a parser for the operation dataframe -> eclipse include file"""
    return common.fill_reverse_parser(parser, "VFPPROD, VFPINJ", "vfp.inc")


def vfp_main(args) -> None:
    """Entry-point for module, for command line utility."""
    logger = getLogger_ecl2csv(  # pylint: disable=redefined-outer-name
        __name__, vars(args)
    )
    if args.keywords:
        for keyword in args.keywords:
            if keyword not in SUPPORTED_KEYWORDS:
                logger.error("Keyword argument {keyword} not supported")
                sys.exit(0)
    if not args.output:
        logger.info("Nothing to do. Set --output")
        sys.exit(0)
    eclfiles = EclFiles(args.DATAFILE)
    dframe = df(eclfiles.get_ecldeck(), keywords=args.keywords)
    if args.output:
        common.write_dframe_stdout_file(
            dframe, args.output, index=False, caller_logger=logger
        )
    logger.info("Parsed file %s for vfp.df" % (args.DATAFILE))


def vfp_reverse_main(args) -> None:
    """Entry-point for module, for command line utility for CSV to Eclipse"""
    logger = getLogger_ecl2csv(  # pylint: disable=redefined-outer-name
        __name__, vars(args)
    )
    vfp_df = pd.read_csv(args.csvfile)
    logger.info("Parsed %s", args.csvfile)
    inc_string = df2ecl(vfp_df, args.keywords)
    if args.output:
        common.write_inc_stdout_file(inc_string, args.output)

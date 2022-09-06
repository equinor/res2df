"""
Extract the VFPPROD/VFPINJ data from an Eclipse (input) deck as Pandas Dataframes

Data can be extracted from a full Eclipse deck or from individual files. Supports
output both in csv format as a pandas DataFrame or in pyarrow and pyarrow.table
"""

import argparse
import logging
import numbers
import sys
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
import pyarrow as pa

try:
    # Needed for mypy

    # pylint: disable=unused-import
    import opm.io

    # This import is seemingly not used, but necessary for some attributes
    # to be included in DeckItem objects.
    from opm.io.deck import DeckKeyword  # noqa
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


def _string2intlist(list_def_str: str) -> List[int]:
    """Produce a list of int from input string

    Args:
        list_def_str: String defining list of int
                      Format "[1,2,6:9]" to define list [1,2,6,7,8,9]
    """
    list = []
    list_def = list_def_str.strip().strip("[").strip("]")
    if list_def.strip():
        list_items = []
        if "," in list_def:
            list_items = list_def.split(",")
        else:
            list_items = [list_def]
        for item in list_items:
            if ":" in item:
                item_split = item.split(":")
                for value in item_split:
                    list.append(int(value))
            else:
                list.append(int(item))

    return list


def deckrecord2list(
    record: "opm.libopmcommon_python.DeckRecord",
    keyword: str,
    recordindex: int,
    recordname: str,
) -> Union[Any, List[float]]:
    """
    Parse an opm.libopmcommon_python.DeckRecord belonging to a certain keyword
    and return as list of numbers

    Args:
        record:      Record be parsed
        keyword:     Which Eclipse keyword this belongs to
        recordindex: For keywords where itemlistname is 'records', this is a
                     list index to the "record".
        recordname:  Name of the record
    """
    record = common.parse_opmio_deckrecord(record, keyword, "records", recordindex)

    values: Union[Any, List[float]]
    # Extract interpolation ranges into lists
    if isinstance(record.get(recordname), list):
        values = record.get(recordname)
    elif isinstance(record.get(recordname), numbers.Number):
        values = [record.get(recordname)]
    else:
        raise ValueError(
            f"Keyword {keyword} and recordname {recordname} "
            "not match number of tabulated records"
        )

    return values


def _stack_vfptable2df(
    index_names_list: List[str],
    index_values_list: List[List[float]],
    flow_values_list: List[float],
    table_values_list: List[List[float]],
) -> pd.DataFrame:
    """Return a dataframe from a list of interpolation ranges and tabulated values

    Args:
        index_names_list:  List with name of each interpolated
                           quantity (i.e. THP, WFR, GFR, ALQ for VFPPROD
                           or THP for VFPINJ)
        index_values_list: List of list with values for
                           each interpolated quantity for
                           each row in vfp table (each record)
                           (dim (no index names) x (no records))
        flow_values_list:  List of flow values (dim = no flow_values)
        table_values_list: List of list with tabulated values
                           (dim = (no records) x  (no flow_values))
    """
    if len(index_names_list) != len(index_values_list):
        raise ValueError("Number of index names not equal to number of index lists")
    for index_values in index_values_list:
        if len(index_values) != len(table_values_list):
            raise ValueError(
                "Number of index values not equal to number of records in table"
            )
    for table_values in table_values_list:
        if len(table_values) != len(flow_values_list):
            raise ValueError(
                "Number of flow values not equal to number of tabulated values"
            )

    df_vfptable = pd.DataFrame(table_values_list)
    no_indices = len(index_names_list)

    # insert index values as first columns in dataframe
    for i in range(0, no_indices):
        df_vfptable.insert(i, index_names_list[i], index_values_list[i])

    #  create multi-index for columns
    indextuples = []
    for index_name in index_names_list:
        indextuples.append((index_name, "DELETE"))
    for flowvalue in flow_values_list:
        indextuples.append(("TAB", str(flowvalue)))

    # Set the columns to a MultiIndex, to facilitate stacking
    df_vfptable.columns = pd.MultiIndex.from_tuples(indextuples)

    # Now stack
    df_vfptable_stacked = df_vfptable.stack()

    # In order to propagate the gfr, thp, wct values after
    # stacking to the correct rows, we should either understand
    # how to do that properly using pandas, but for now, we try a
    # backwards fill, hopefully that is robust enough
    df_vfptable_stacked.bfill(inplace=True)
    # Also reset the index:
    df_vfptable_stacked.reset_index(inplace=True)
    df_vfptable_stacked.drop("level_0", axis="columns", inplace=True)
    # This column is not meaningful (it is the old index)

    # Delete rows that does not belong to any flow rate (this is
    # possibly a by-product of not doing the stacking in an
    # optimal way)
    df_vfptable_stacked = df_vfptable_stacked[
        df_vfptable_stacked["level_1"] != "DELETE"
    ]

    # Add correct column name for the flow values that we have stacked
    cols = list(df_vfptable_stacked.columns)
    cols[cols.index("level_1")] = "RATE"
    df_vfptable_stacked.columns = cols
    df_vfptable_stacked["RATE"] = df_vfptable_stacked["RATE"].astype(float)

    # Sort values in correct order
    df_vfptable_stacked.sort_values(
        by=index_names_list + ["RATE"], ascending=True, inplace=True, ignore_index=True
    )

    return df_vfptable_stacked


def basic_data_vfpprod2df(
    tableno: int,
    datum: float,
    rate_type: VFPPROD_FLO,
    wfr_type: WFR,
    gfr_type: GFR,
    alq_type: ALQ,
    thp_type: THPTYPE,
    unit_type: UNITTYPE,
    tab_type: VFPPROD_TABTYPE,
    flow_values: np.ndarray,
    thp_values: np.ndarray,
    wfr_values: np.ndarray,
    gfr_values: np.ndarray,
    alq_values: np.ndarray,
    thp_indices: np.ndarray,
    wfr_indices: np.ndarray,
    gfr_indices: np.ndarray,
    alq_indices: np.ndarray,
    tab_data: np.ndarray,
) -> pd.DataFrame:
    """Return a pandas DataFrame from VFPPROD liftcurve data
    Args:
        tableno     : table number
        datum       : datum depth
        rate_type   : rate type used for flow values
        wfr_type    : water fraction type
        gfr_type    : gas fraction type
        alq_type    : artificial lift type
        thp_type    : thp type
        unit_type   : unit type
        tab_type    : type for tabulated (record) values
        flow_values : rate values used to generate table
        thp_values  : THP values used to generate table
        wfr_values  : water fraction values used to generate table
        gfr_values  : gas fraction values used to generate table
        alq_values  : artificial lift values (if any) used to generate table
        thp_indices : which index in thp value table a given BHP value
                      corresponds to (1-base)
        wfr_indices : which index in wfr value table a given BHP value
                      corresponds to (1-base)
        gfr_indices : which index in gfr value table a given BHP value
                      corresponds to (1-base)
        alq_indices : which index in alq value table a given BHP value
                      corresponds to (1-base)
        tab_data    : tabulated (BHP) data
                      (ordered as thp-, wfr-, gfr-, alq- and flow-values)
    """

    # Generate list with values instead of indices
    thp_values_list = [thp_values[i - 1] for i in thp_indices]
    wfr_values_list = [wfr_values[i - 1] for i in wfr_indices]
    gfr_values_list = [gfr_values[i - 1] for i in gfr_indices]
    alq_values_list = [alq_values[i - 1] for i in alq_indices]

    # create stacked dataframe from VFP table values
    index_names = ["PRESSURE", "WFR", "GFR", "ALQ"]
    index_values = [thp_values_list, wfr_values_list, gfr_values_list, alq_values_list]
    df_bhp_stacked = _stack_vfptable2df(
        index_names, index_values, flow_values, tab_data
    )

    # Add meta-data
    df_bhp_stacked["VFP_TYPE"] = "VFPPROD"
    df_bhp_stacked["TABLE_NUMBER"] = tableno
    df_bhp_stacked["DATUM"] = datum
    df_bhp_stacked["UNIT_TYPE"] = unit_type.value
    df_bhp_stacked["RATE_TYPE"] = rate_type.value
    df_bhp_stacked["WFR_TYPE"] = wfr_type.value
    df_bhp_stacked["GFR_TYPE"] = gfr_type.value
    df_bhp_stacked["ALQ_TYPE"] = alq_type.value
    df_bhp_stacked["PRESSURE_TYPE"] = thp_type.value
    df_bhp_stacked["TAB_TYPE"] = tab_type.value

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

    # reset index (not used other than tests)
    return df_bhp_stacked.reset_index(drop=True)


def basic_data_vfpinj2df(
    tableno: int,
    datum: float,
    rate_type: VFPINJ_FLO,
    thp_type: THPTYPE,
    unit_type: UNITTYPE,
    tab_type: VFPINJ_TABTYPE,
    flow_values: np.ndarray,
    thp_values: np.ndarray,
    thp_indices: np.ndarray,
    tab_data: np.ndarray,
) -> pd.DataFrame:
    """Return a pandas DataFrame from VFPINJ liftcurve data
    Args:
        tableno     : table number
        datum       : datum depth
        rate_type   : rate type used for flow values
        thp_type    : thp type
        unit_type   : unit type
        tab_type    : tab type
        flow_values : rate values used to generate table
        thp_values  : THP values used to generate table
        thp_indices : which index in thp value table a given
                      BHP value corresponds to (1-base)
        tab_data    : tabulated (BHP) data
                      (ordered according to thp- and flow-values)
    """

    # Generate list with values instead of indices
    thp_values_list = [thp_values[i - 1] for i in thp_indices]

    # create stacked dataframe from VFP table values
    index_names = ["PRESSURE"]
    index_values = [thp_values_list]
    df_bhp_stacked = _stack_vfptable2df(
        index_names, index_values, flow_values, tab_data
    )

    # Add meta-data
    df_bhp_stacked["VFP_TYPE"] = "VFPINJ"
    df_bhp_stacked["TABLE_NUMBER"] = int(tableno)
    df_bhp_stacked["DATUM"] = float(datum)
    df_bhp_stacked["UNIT_TYPE"] = unit_type.value
    df_bhp_stacked["RATE_TYPE"] = rate_type.value
    df_bhp_stacked["PRESSURE_TYPE"] = thp_type.value
    df_bhp_stacked["TAB_TYPE"] = tab_type.value

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

    # reset index (not used other than tests)
    df_bhp_stacked.reset_index(inplace=True, drop=True)
    return df_bhp_stacked


def basic_data_vfpprod2pyarrow(
    tableno: int,
    datum: float,
    rate_type: VFPPROD_FLO,
    wfr_type: WFR,
    gfr_type: GFR,
    alq_type: ALQ,
    thp_type: THPTYPE,
    unit_type: UNITTYPE,
    tab_type: VFPPROD_TABTYPE,
    flow_values: np.ndarray,
    thp_values: np.ndarray,
    wfr_values: np.ndarray,
    gfr_values: np.ndarray,
    alq_values: np.ndarray,
    thp_indices: np.ndarray,
    wfr_indices: np.ndarray,
    gfr_indices: np.ndarray,
    alq_indices: np.ndarray,
    tab_data: np.ndarray,
) -> pa.Table:
    """Return a pyarrow Table from VFPPROD liftcurve data

    Args:
        tableno     : table number
        datum       : datum depth
        rate_type   : rate type used for flow values
        wfr_type    : water fraction type
        gfr_type    : gas fraction type
        alq_type    : artificial lift type
        thp_type    : thp type
        unit_type   : unit type
        tab_type    : type for tabulated (record) values
        flow_values : rate values used to generate table
        thp_values  : THP values used to generate table
        wfr_values  : water fraction values used to generate table
        gfr_values  : gas fraction values used to generate table
        alq_values  : artificial lift values (if any) used to generate table
        thp_indices : THP indices for each record in tabulated data
        wfr_indices : WFR indices for each record in tabulated data
        gfr_indices : GFR indices for each record in tabulated data
        alq_indices : ALQ indices for each record in tabulated data
        tab_data    : tabulated (BHP) data
                      (ordered according to thp-, wfr-, gfr-, alq- and flow-values)
    """

    # Add everything except tabulated BHP pressures as meta data
    table_metadata = {
        bytes("VFP_TYPE", encoding="ascii"): bytes(
            VFPTYPE.VFPPROD.value, encoding="ascii"
        ),
        bytes("TABLE_NUMBER", encoding="ascii"): bytes(str(tableno), encoding="ascii"),
        bytes("DATUM", encoding="ascii"): bytes(str(datum), encoding="ascii"),
        bytes("RATE_TYPE", encoding="ascii"): bytes(rate_type.value, encoding="ascii"),
        bytes("WFR_TYPE", encoding="ascii"): bytes(wfr_type.value, encoding="ascii"),
        bytes("GFR_TYPE", encoding="ascii"): bytes(gfr_type.value, encoding="ascii"),
        bytes("ALQ_TYPE", encoding="ascii"): bytes(alq_type.value, encoding="ascii"),
        bytes("THP_TYPE", encoding="ascii"): bytes(thp_type.value, encoding="ascii"),
        bytes("UNIT_TYPE", encoding="ascii"): bytes(unit_type.value, encoding="ascii"),
        bytes("TAB_TYPE", encoding="ascii"): bytes(tab_type.value, encoding="ascii"),
        bytes("THP_VALUES", encoding="ascii"): np.array(
            thp_values, dtype=float
        ).tobytes(),
        bytes("WFR_VALUES", encoding="ascii"): np.array(
            wfr_values, dtype=float
        ).tobytes(),
        bytes("GFR_VALUES", encoding="ascii"): np.array(
            gfr_values, dtype=float
        ).tobytes(),
        bytes("ALQ_VALUES", encoding="ascii"): np.array(
            alq_values, dtype=float
        ).tobytes(),
        bytes("FLOW_VALUES", encoding="ascii"): np.array(
            flow_values, dtype=float
        ).tobytes(),
    }

    # Column metadata is list of indices (THP,WFR,GFR,ALQ)
    col_metadata_list = []
    num_records = len(thp_values) * len(wfr_values) * len(gfr_values) * len(alq_values)
    for i in range(0, num_records):
        thp_idx = thp_indices[i]
        wfr_idx = wfr_indices[i]
        gfr_idx = gfr_indices[i]
        alq_idx = alq_indices[i]
        col_name = (
            str(thp_idx) + "_" + str(wfr_idx) + "_" + str(gfr_idx) + "_" + str(alq_idx)
        )
        col_dtype = pa.float64()
        col_metadata = {
            bytes("thp_idx", encoding="ascii"): bytes(str(thp_idx), encoding="ascii"),
            bytes("wfr_idx", encoding="ascii"): bytes(str(wfr_idx), encoding="ascii"),
            bytes("gfr_idx", encoding="ascii"): bytes(str(gfr_idx), encoding="ascii"),
            bytes("alq_idx", encoding="ascii"): bytes(str(alq_idx), encoding="ascii"),
            bytes("record", encoding="ascii"): bytes(str(i), encoding="ascii"),
        }
        col_metadata_list.append(pa.field(col_name, col_dtype, metadata=col_metadata))

    schema = pa.schema(col_metadata_list, table_metadata)
    no_thp_values = len(thp_values)
    no_wfr_values = len(wfr_values)
    no_gfr_values = len(gfr_values)
    no_alq_values = len(alq_values)
    no_flow_values = len(flow_values)
    no_records = no_thp_values * no_wfr_values * no_gfr_values * no_alq_values
    pa_table = pa.table(
        tab_data.reshape(no_records, no_flow_values).tolist(), schema=schema
    )

    return pa_table


def basic_data_vfpinj2pyarrow(
    tableno: int,
    datum: float,
    rate_type: VFPINJ_FLO,
    thp_type: THPTYPE,
    unit_type: UNITTYPE,
    tab_type: VFPINJ_TABTYPE,
    flow_values: np.ndarray,
    thp_values: np.ndarray,
    thp_indices: np.ndarray,
    tab_data: np.ndarray,
) -> pa.Table:
    """Return a pyarrow Table from a VFPINJ record data

    Args:
        tableno     : table number
        datum       : datum depth
        rate_type   : rate type used for flow values
        thp_type    : thp type
        unit_type   : unit type
        tab_type    : type for tabulated (record) values
        flow_values : rate values used to generate table
        thp_values  : THP values used to generate table
        thp_indices : THP indices for each record in tabulated data
        tab_data    : tabulated (BHP) data
                      (ordered according to thp- and flow-values)
    """

    # Add everything except tabulated BHP pressures as meta data
    table_metadata = {
        bytes("VFP_TYPE", encoding="ascii"): bytes(
            VFPTYPE.VFPINJ.value, encoding="ascii"
        ),
        bytes("TABLE_NUMBER", encoding="ascii"): bytes(str(tableno), encoding="ascii"),
        bytes("DATUM", encoding="ascii"): bytes(str(datum), encoding="ascii"),
        bytes("RATE_TYPE", encoding="ascii"): bytes(rate_type.value, encoding="ascii"),
        bytes("THP_TYPE", encoding="ascii"): bytes(thp_type.value, encoding="ascii"),
        bytes("UNIT_TYPE", encoding="ascii"): bytes(unit_type.value, encoding="ascii"),
        bytes("TAB_TYPE", encoding="ascii"): bytes(tab_type.value, encoding="ascii"),
        bytes("THP_VALUES", encoding="ascii"): np.array(
            thp_values, dtype=float
        ).tobytes(),
        bytes("FLOW_VALUES", encoding="ascii"): np.array(
            flow_values, dtype=float
        ).tobytes(),
    }

    # Column metadata is index in THP array
    col_metadata_list = []
    for i in range(0, len(thp_values)):
        col_name = str(i)
        col_dtype = pa.float64()
        col_metadata = {
            bytes("thp_idx", encoding="ascii"): bytes(str(i + 1), encoding="ascii")
        }
        col_metadata_list.append(pa.field(col_name, col_dtype, metadata=col_metadata))

    schema = pa.schema(col_metadata_list, table_metadata)
    no_thp_values = len(thp_values)
    no_flow_values = len(flow_values)
    pa_table = pa.table(
        tab_data.reshape(no_thp_values, no_flow_values).tolist(), schema=schema
    )

    return pa_table


def df2vfpprod_basic_data(dframe: pd.DataFrame) -> Dict[str, Any]:
    """Return basic data type for VFPPROD from a pandas dataframe.

    Return format is a dictionary all data in VFPPROD in basic data types
    (str, int, float, numpy.array)

    Args:
        dframe : pandas DataFrame for VFPPROD
    """

    if dframe.empty:
        return {}

    # Consistency checks of data type
    if len(dframe["RATE_TYPE"].unique()) == 1:
        rate_type = VFPPROD_FLO[dframe["RATE_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of FLO type is not unique")
    if len(dframe["WFR_TYPE"].unique()) == 1:
        wfr_type = WFR[dframe["WFR_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of WFR type is not unique")
    if len(dframe["GFR_TYPE"].unique()) == 1:
        gfr_type = GFR[dframe["GFR_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of GFR type is not unique")
    if len(dframe["ALQ_TYPE"].unique()) == 1:
        if not dframe["ALQ_TYPE"].unique()[0] or dframe["ALQ_TYPE"].unique()[0] == "''":
            alq_type = ALQ.UNDEFINED
        else:
            alq_type = ALQ[dframe["ALQ_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of ALQ type is not unique")
    if len(dframe["PRESSURE_TYPE"].unique()) == 1:
        thp_type = THPTYPE[dframe["PRESSURE_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of THP type is not unique")
    if len(dframe["TAB_TYPE"].unique()) == 1:
        tab_type = VFPPROD_TABTYPE[dframe["TAB_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of TAB type is not unique")
    if len(dframe["UNIT_TYPE"].unique()) == 1:
        unit_type = UNITTYPE[dframe["UNIT_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of UNIT type is not unique")

    # Consistency check of basic data
    if len(dframe["TABLE_NUMBER"].unique()) == 1:
        tableno = dframe["TABLE_NUMBER"].unique()[0]
    else:
        raise ValueError("Definition of TABLE_NUMBER is not unique")
    if len(dframe["DATUM"].unique()) == 1:
        datum = dframe["DATUM"].unique()[0]
    else:
        raise ValueError("Definition of DATUM is not unique")

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
        raise ValueError(
            f"Number of unique rate values {no_flow_values} not consistent "
            "with number of tabulated values {no_tab_values}"
        )
    if no_tab_values % no_wfr_values != 0:
        raise ValueError(
            f"Number of unique wfr values {no_wfr_values} not "
            "consistent with number of tabulated values {no_tab_values}"
        )
    if no_tab_values % no_gfr_values != 0:
        raise ValueError(
            f"Number of unique gfr values {no_gfr_values} not consistent "
            "with number of tabulated values {no_tab_values}"
        )
    if no_tab_values % no_alq_values != 0:
        raise ValueError(
            f"Number of unique alq values {no_alq_values} not consistent "
            "with number of tabulated values {no_tab_values}"
        )
    if no_tab_values % no_thp_values != 0:
        raise ValueError(
            f"Number of unique thp values {no_thp_values} not consistent "
            "with number of tabulated values {no_tab_values}"
        )
    if no_tab_values % no_interp_values != 0:
        raise ValueError(
            f"Number of unique interpolation values {no_interp_values} not consistent "
            "with number of tabulated values {no_tab_values}"
        )

    # Replace interpolation values with index in dataframe
    wfr_loc_indices = [float(val) for val in range(1, len(wfr_values) + 1)]
    wfr_replace_map = dict(zip(wfr_values, wfr_loc_indices))
    wfr_glob_indices = (
        dframe.loc[::no_flow_values, "WFR"]
        .apply(lambda x: wfr_replace_map[x])
        .astype(int)
    )

    gfr_loc_indices = [float(val) for val in range(1, len(gfr_values) + 1)]
    gfr_replace_map = dict(zip(gfr_values, gfr_loc_indices))
    gfr_glob_indices = (
        dframe.loc[::no_flow_values, "GFR"]
        .apply(lambda x: gfr_replace_map[x])
        .astype(int)
    )

    alq_loc_indices = [float(val) for val in range(1, len(alq_values) + 1)]
    alq_replace_map = dict(zip(alq_values, alq_loc_indices))
    alq_glob_indices = (
        dframe.loc[::no_flow_values, "ALQ"]
        .apply(lambda x: alq_replace_map[x])
        .astype(int)
    )

    thp_loc_indices = [float(val) for val in range(1, len(thp_values) + 1)]
    thp_replace_map = dict(zip(thp_values, thp_loc_indices))
    thp_glob_indices = (
        dframe.loc[::no_flow_values, "PRESSURE"]
        .apply(lambda x: thp_replace_map[x])
        .astype(int)
    )

    no_records = no_wfr_values * no_gfr_values * no_alq_values * no_thp_values
    bhp_table = np.array(dframe["TAB"].tolist()).reshape(no_records, no_flow_values)

    vfpprod_data = {
        "TABLE_NUMBER": tableno,
        "DATUM": datum,
        "RATE_TYPE": rate_type,
        "WFR_TYPE": wfr_type,
        "GFR_TYPE": gfr_type,
        "ALQ_TYPE": alq_type,
        "THP_TYPE": thp_type,
        "UNIT_TYPE": unit_type,
        "TAB_TYPE": tab_type,
        "THP_VALUES": np.array(thp_values),
        "WFR_VALUES": np.array(wfr_values),
        "GFR_VALUES": np.array(gfr_values),
        "ALQ_VALUES": np.array(alq_values),
        "FLOW_VALUES": np.array(flow_values),
        "THP_INDICES": np.array(thp_glob_indices),
        "WFR_INDICES": np.array(wfr_glob_indices),
        "GFR_INDICES": np.array(gfr_glob_indices),
        "ALQ_INDICES": np.array(alq_glob_indices),
        "BHP_TABLE": np.array(bhp_table),
    }

    return vfpprod_data


def df2vfpinj_basic_data(dframe: pd.DataFrame) -> Dict[str, Any]:
    """Return basic data type for VFPINJ from a pandas dataframe.

    Return format is a dictionary all data in VFPINJ in basic data types
    (str, int, float, numpy.array)

    Args:
        dframe : pandas DataFrame for VFPINJ
    """

    if dframe.empty:
        return {}

    # Consistency checks of data type
    if len(dframe["RATE_TYPE"].unique()) == 1:
        rate_type = VFPINJ_FLO[dframe["RATE_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of FLO type is not unique")
    if len(dframe["PRESSURE_TYPE"].unique()) == 1:
        thp_type = THPTYPE[dframe["PRESSURE_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of THP type is not unique")
    if len(dframe["TAB_TYPE"].unique()) == 1:
        tab_type = VFPINJ_TABTYPE[dframe["TAB_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of TAB type is not unique")
    if len(dframe["UNIT_TYPE"].unique()) == 1:
        unit_type = UNITTYPE[dframe["UNIT_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of UNIT type is not unique")

    # Consistency check of basic data
    if len(dframe["TABLE_NUMBER"].unique()) == 1:
        tableno = dframe["TABLE_NUMBER"].unique()[0]
    else:
        raise ValueError("Definition of TABLE_NUMBER is not unique")
    if len(dframe["DATUM"].unique()) == 1:
        datum = dframe["DATUM"].unique()[0]
    else:
        raise ValueError("Definition of DATUM is not unique")

    # Reading interpolation ranges
    flow_values = dframe["RATE"].unique().astype(float).tolist()
    no_flow_values = len(flow_values)
    thp_values = dframe["PRESSURE"].unique().astype(float).tolist()
    thp_values.sort()
    no_thp_values = len(thp_values)
    no_tab_values = len(dframe)

    # Wheck consistency of interpolation ranges and tabulated values
    if no_tab_values % no_flow_values != 0:
        raise ValueError(
            f"Number of unique rate values {no_flow_values} not consistent "
            "with number of tabulated values {no_tab_values}"
        )
    if no_tab_values % no_thp_values != 0:
        raise ValueError(
            f"Number of unique thp values {no_thp_values} not consistent "
            "with number of tabulated values {no_tab_values}"
        )

    # Replace interpolation values with index in dataframe
    thp_loc_indices = [float(val) for val in range(1, len(thp_values) + 1)]
    thp_replace_map = dict(zip(thp_values, thp_loc_indices))
    thp_glob_indices = (
        dframe.loc[::no_flow_values, "PRESSURE"]
        .apply(lambda x: thp_replace_map[x])
        .astype(int)
    )

    no_records = no_thp_values
    bhp_table = np.array(dframe["TAB"].tolist()).reshape(no_records, no_flow_values)

    vfpinj_data = {
        "TABLE_NUMBER": tableno,
        "DATUM": datum,
        "RATE_TYPE": rate_type,
        "THP_TYPE": thp_type,
        "UNIT_TYPE": unit_type,
        "TAB_TYPE": tab_type,
        "THP_VALUES": np.array(thp_values),
        "FLOW_VALUES": np.array(flow_values),
        "THP_INDICES": np.array(thp_glob_indices),
        "BHP_TABLE": np.array(bhp_table),
    }

    return vfpinj_data


def pyarrow2vfpprod_basic_data(pa_table: pa.Table) -> Dict[str, Any]:
    """Return basic data type for VFPPROD from a pyarrow.Table.

    Return format is a dictionary all data in VFPPROD in basic data types
    (str, int, float, numpy.array)

    Args:
        pa_table : pyarrow Table with data for VFPPROD
    """

    # Extract index data from colum metadata
    thp_indices = []
    wfr_indices = []
    gfr_indices = []
    alq_indices = []
    for i in range(0, pa_table.num_columns):
        thp_indices.append(int(pa_table.schema.field(i).metadata[b"thp_idx"]))
        wfr_indices.append(int(pa_table.schema.field(i).metadata[b"wfr_idx"]))
        gfr_indices.append(int(pa_table.schema.field(i).metadata[b"gfr_idx"]))
        alq_indices.append(int(pa_table.schema.field(i).metadata[b"alq_idx"]))

    # Extract table data as numpy.array
    bhp_data = np.array(pa_table.columns)

    alq_type = ALQ.UNDEFINED
    if pa_table.schema.metadata[b"ALQ_TYPE"].decode("utf-8") != "''":
        alq_type = ALQ[pa_table.schema.metadata[b"ALQ_TYPE"].decode("utf-8")]

    vfpprod_data = {
        "VFP_TYPE": VFPTYPE[pa_table.schema.metadata[b"VFP_TYPE"].decode("utf-8")],
        "TABLE_NUMBER": int(pa_table.schema.metadata[b"TABLE_NUMBER"].decode("utf-8")),
        "DATUM": float(pa_table.schema.metadata[b"DATUM"].decode("utf-8")),
        "RATE_TYPE": VFPPROD_FLO[
            pa_table.schema.metadata[b"RATE_TYPE"].decode("utf-8")
        ],
        "WFR_TYPE": WFR[pa_table.schema.metadata[b"WFR_TYPE"].decode("utf-8")],
        "GFR_TYPE": GFR[pa_table.schema.metadata[b"GFR_TYPE"].decode("utf-8")],
        "ALQ_TYPE": alq_type,
        "THP_TYPE": THPTYPE[pa_table.schema.metadata[b"THP_TYPE"].decode("utf-8")],
        "UNIT_TYPE": UNITTYPE[pa_table.schema.metadata[b"UNIT_TYPE"].decode("utf-8")],
        "TAB_TYPE": VFPPROD_TABTYPE[
            pa_table.schema.metadata[b"TAB_TYPE"].decode("utf-8")
        ],
        "THP_VALUES": np.frombuffer(
            pa_table.schema.metadata[b"THP_VALUES"], dtype=np.float64
        ),
        "WFR_VALUES": np.frombuffer(
            pa_table.schema.metadata[b"WFR_VALUES"], dtype=np.float64
        ),
        "GFR_VALUES": np.frombuffer(
            pa_table.schema.metadata[b"GFR_VALUES"], dtype=np.float64
        ),
        "ALQ_VALUES": np.frombuffer(
            pa_table.schema.metadata[b"ALQ_VALUES"], dtype=np.float64
        ),
        "FLOW_VALUES": np.frombuffer(
            pa_table.schema.metadata[b"FLOW_VALUES"], dtype=np.float64
        ),
        "THP_INDICES": np.array(thp_indices),
        "WFR_INDICES": np.array(wfr_indices),
        "GFR_INDICES": np.array(gfr_indices),
        "ALQ_INDICES": np.array(alq_indices),
        "BHP_TABLE": np.array(bhp_data),
    }

    return vfpprod_data


def pyarrow2vfpinj_basic_data(pa_table: pa.Table) -> Dict[str, Any]:
    """Return basic data type for VFPINJ from a pyarrow.Table.

    Return format is a dictionary all data in VFPINJ in basic data types
    (str, int, float, numpy.array)

    Args:
        pa_table : pyarrow Table with data for VFPINJ
    """

    # Extract index data from colum metadata
    thp_indices = []
    for i in range(0, pa_table.num_columns):
        thp_indices.append(int(pa_table.schema.field(i).metadata[b"thp_idx"]))

    # Extract table data as numpy.array
    bhp_data = np.array(pa_table.columns)

    vfpinj_data = {
        "VFP_TYPE": VFPTYPE[pa_table.schema.metadata[b"VFP_TYPE"].decode("utf-8")],
        "TABLE_NUMBER": int(pa_table.schema.metadata[b"TABLE_NUMBER"].decode("utf-8")),
        "DATUM": float(pa_table.schema.metadata[b"DATUM"].decode("utf-8")),
        "RATE_TYPE": VFPINJ_FLO[pa_table.schema.metadata[b"RATE_TYPE"].decode("utf-8")],
        "THP_TYPE": THPTYPE[pa_table.schema.metadata[b"THP_TYPE"].decode("utf-8")],
        "UNIT_TYPE": UNITTYPE[pa_table.schema.metadata[b"UNIT_TYPE"].decode("utf-8")],
        "TAB_TYPE": VFPINJ_TABTYPE[
            pa_table.schema.metadata[b"TAB_TYPE"].decode("utf-8")
        ],
        "THP_VALUES": np.frombuffer(pa_table.schema.metadata[b"THP_VALUES"]),
        "FLOW_VALUES": np.frombuffer(pa_table.schema.metadata[b"FLOW_VALUES"]),
        "THP_INDICES": np.array(thp_indices),
        "BHP_TABLE": np.array(bhp_data),
    }

    return vfpinj_data


def read_vfpprod_basic_data(
    keyword: "opm.libopmcommon_python.DeckKeyword",
    vfpnumbers_str: Optional[str] = None,
) -> Dict[str, Any]:
    """Read and return all data for Eclipse VFPPROD keyword as basic data types

    Empty string returned if vfp table number does not match any number in list

    Args:
        keyword:        Eclipse deck keyword
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds
    """
    # Number of records in keyword
    num_rec = len(keyword)

    # Parse records with basic information and interpolation ranges
    basic_record = common.parse_opmio_deckrecord(keyword[0], "VFPPROD", "records", 0)

    # Extract basic table information
    tableno = int(basic_record["TABLE"])
    if vfpnumbers_str:
        vfpnumbers = _string2intlist(vfpnumbers_str)
        if tableno not in vfpnumbers:
            return pd.DataFrame()
    datum = float(basic_record["DATUM_DEPTH"])
    rate_type = VFPPROD_FLO.GAS
    if basic_record["RATE_TYPE"]:
        rate_type = VFPPROD_FLO[basic_record["RATE_TYPE"]]
    wfr_type = WFR.WCT
    if basic_record["WFR"]:
        wfr_type = WFR[basic_record["WFR"]]
    gfr_type = GFR.GOR
    if basic_record["GFR"]:
        gfr_type = GFR[basic_record["GFR"]]
    thp_type = THPTYPE.THP
    if basic_record["PRESSURE_DEF"]:
        thp_type = THPTYPE[basic_record["PRESSURE_DEF"]]
    alq_type = ALQ.UNDEFINED
    if basic_record["ALQ_DEF"]:
        if basic_record["ALQ_DEF"].strip():
            alq_type = ALQ[basic_record["ALQ_DEF"]]
    unit_type = UNITTYPE.DEFAULT
    if basic_record["UNITS"]:
        unit_type = UNITTYPE[basic_record["UNITS"]]
    tab_type = VFPPROD_TABTYPE.BHP
    if basic_record["BODY_DEF"]:
        tab_type = VFPPROD_TABTYPE[basic_record["BODY_DEF"]]

    flow_values = deckrecord2list(keyword[1], "VFPPROD", 1, "FLOW_VALUES")
    thp_values = deckrecord2list(keyword[2], "VFPPROD", 2, "THP_VALUES")
    wfr_values = deckrecord2list(keyword[3], "VFPPROD", 3, "WFR_VALUES")
    gfr_values = deckrecord2list(keyword[4], "VFPPROD", 4, "GFR_VALUES")
    alq_values = deckrecord2list(keyword[5], "VFPPROD", 5, "ALQ_VALUES")

    # Check of consistent dimensions
    no_flow_values = len(flow_values)
    no_thp_values = len(thp_values)
    no_wfr_values = len(wfr_values)
    no_gfr_values = len(gfr_values)
    no_alq_values = len(alq_values)
    no_interp_values = no_thp_values * no_wfr_values * no_gfr_values * no_alq_values
    no_tab_records = num_rec - 6
    if no_interp_values != no_tab_records:
        raise ValueError(
            "Dimensions of interpolation ranges "
            "does not match number of tabulated records"
        )

    # Extract interpolation values and tabulated values (BHP values)
    bhp_table: List[List[float]] = []
    thp_indices: List[float] = []
    wfr_indices: List[float] = []
    gfr_indices: List[float] = []
    alq_indices: List[float] = []
    for n in range(6, num_rec):
        bhp_record = common.parse_opmio_deckrecord(keyword[n], "VFPPROD", "records", 6)
        bhp_values: Union[Any, List[float]]
        if isinstance(bhp_record.get("VALUES"), list):
            bhp_values = bhp_record.get("VALUES")
        elif isinstance(bhp_record.get("VALUES"), numbers.Number):
            bhp_values = [bhp_record.get("VALUES")]

        thp_index = bhp_record["THP_INDEX"]
        wfr_index = bhp_record["WFR_INDEX"]
        gfr_index = bhp_record["GFR_INDEX"]
        alq_index = bhp_record["ALQ_INDEX"]

        thp_indices.append(thp_index)
        wfr_indices.append(wfr_index)
        gfr_indices.append(gfr_index)
        alq_indices.append(alq_index)

        if len(bhp_values) != no_flow_values:
            raise ValueError(
                "Dimension of record of tabulated "
                "values does not match number of flow values"
            )
        bhp_table.append(bhp_values)

    vfpprod_data = {
        "TABLE_NUMBER": tableno,
        "DATUM": datum,
        "RATE_TYPE": rate_type,
        "WFR_TYPE": wfr_type,
        "GFR_TYPE": gfr_type,
        "ALQ_TYPE": alq_type,
        "THP_TYPE": thp_type,
        "UNIT_TYPE": unit_type,
        "TAB_TYPE": tab_type,
        "THP_VALUES": np.array(thp_values),
        "WFR_VALUES": np.array(wfr_values),
        "GFR_VALUES": np.array(gfr_values),
        "ALQ_VALUES": np.array(alq_values),
        "FLOW_VALUES": np.array(flow_values),
        "THP_INDICES": np.array(thp_indices),
        "WFR_INDICES": np.array(wfr_indices),
        "GFR_INDICES": np.array(gfr_indices),
        "ALQ_INDICES": np.array(alq_indices),
        "BHP_TABLE": np.array(bhp_table),
    }

    return vfpprod_data


def read_vfpinj_basic_data(
    keyword: "opm.libopmcommon_python.DeckKeyword",
    vfpnumbers_str: Optional[str] = None,
) -> Dict[str, Any]:
    """Read and return all data for Eclipse VFPINJ keyword as basic data types

    Empty string returned if vfp table number does not match any number in list

    Args:
        keyword:        Eclipse deck keyword
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds
    """

    # Number of record in keyword
    num_rec = len(keyword)

    # Parse records with basic information and interpolation ranges
    basic_record = common.parse_opmio_deckrecord(keyword[0], "VFPINJ", "records", 0)

    # Extract basic table information
    tableno = basic_record["TABLE"]
    if vfpnumbers_str:
        vfpnumbers = _string2intlist(vfpnumbers_str)
        if tableno not in vfpnumbers:
            return pd.DataFrame()
    datum = basic_record["DATUM_DEPTH"]
    rate_type = VFPINJ_FLO.GAS
    if basic_record["RATE_TYPE"]:
        rate_type = VFPINJ_FLO[basic_record["RATE_TYPE"]]
    thp_type = THPTYPE.THP
    if basic_record["PRESSURE_DEF"]:
        thp_type = THPTYPE[basic_record["PRESSURE_DEF"]]
    unit_type = UNITTYPE.DEFAULT
    if basic_record["UNITS"]:
        unit_type = UNITTYPE[basic_record["UNITS"]]
    tab_type = VFPINJ_TABTYPE.BHP
    if basic_record["BODY_DEF"]:
        tab_type = VFPINJ_TABTYPE[basic_record["BODY_DEF"]]

    # Extract interpolation ranges
    flow_values = deckrecord2list(keyword[1], "VFPPROD", 1, "FLOW_VALUES")
    thp_values = deckrecord2list(keyword[2], "VFPPROD", 2, "THP_VALUES")

    # Check of consistent dimensions
    no_flow_values = len(flow_values)
    no_thp_values = len(thp_values)
    no_interp_values = no_thp_values
    no_tab_records = num_rec - 3
    if no_interp_values != no_tab_records:
        raise ValueError(
            "Dimensions of interpolation ranges does "
            "not match number of tabulated records"
        )

    # Extract interpolation values and tabulated values (BHP values)
    bhp_table: List[List[float]] = []
    thp_indices: List[float] = []
    for n in range(3, num_rec):
        bhp_record = common.parse_opmio_deckrecord(keyword[n], "VFPINJ", "records", 3)
        bhp_values: Union[Any, List[float]]
        if isinstance(bhp_record.get("VALUES"), list):
            bhp_values = bhp_record.get("VALUES")
        elif isinstance(bhp_record.get("VALUES"), numbers.Number):
            bhp_values = [bhp_record.get("VALUES")]

        thp_index = bhp_record["THP_INDEX"]
        thp_indices.append(thp_index)

        if len(bhp_values) != no_flow_values:
            raise ValueError(
                "Dimension of record of tabulated values "
                "does not match number of flow values"
            )
        bhp_table.append(bhp_values)

    vfpinj_data = {
        "TABLE_NUMBER": tableno,
        "DATUM": datum,
        "RATE_TYPE": rate_type,
        "THP_TYPE": thp_type,
        "UNIT_TYPE": unit_type,
        "TAB_TYPE": tab_type,
        "THP_VALUES": np.array(thp_values),
        "FLOW_VALUES": np.array(flow_values),
        "THP_INDICES": np.array(thp_indices),
        "BHP_TABLE": np.array(bhp_table),
    }

    return vfpinj_data


def check_vfpprod_basic_data(vfp_data: Dict[str, Any]) -> bool:
    """Perform a check of the VFPPROD data contained in the dictionary.
    Checks if all data is present and if the dimensions of the arrays
    are consisitent.

    Args:
        vfp_data:   Dictionary containing all data for a VFPPROD keyword in Eclipse
    """

    # Check if all data is present
    if "VFP_NUMBER" not in vfp_data.keys():
        return False
    if "DATUM" not in vfp_data.keys():
        return False
    if "RATE_TYPE" not in vfp_data.keys():
        return False
    if "WFR_TYPE" not in vfp_data.keys():
        return False
    if "GFR_TYPE" not in vfp_data.keys():
        return False
    if "ALQ_TYPE" not in vfp_data.keys():
        return False
    if "THP_TYPE" not in vfp_data.keys():
        return False
    if "UNIT_TYPE" not in vfp_data.keys():
        return False
    if "TAB_TYPE" not in vfp_data.keys():
        return False
    if "THP_VALUES" not in vfp_data.keys():
        return False
    if "WFR_VALUES" not in vfp_data.keys():
        return False
    if "GFR_VALUES" not in vfp_data.keys():
        return False
    if "ALQ_VALUES" not in vfp_data.keys():
        return False
    if "FLOW_VALUES" not in vfp_data.keys():
        return False
    if "THP_INDICES" not in vfp_data.keys():
        return False
    if "WFR_INDICES" not in vfp_data.keys():
        return False
    if "GFR_INDICES" not in vfp_data.keys():
        return False
    if "ALQ_INDICES" not in vfp_data.keys():
        return False
    if "BHP_TABLE" not in vfp_data.keys():
        return False

    no_thp_indices = vfp_data["THP_INDICES"].size
    no_wfr_indices = vfp_data["WFR_INDICES"].size
    no_gfr_indices = vfp_data["GFR_INDICES"].size
    no_alq_indices = vfp_data["ALQ_INDICES"].size
    no_thp_values = vfp_data["THP_VALUES"].size
    no_wfr_values = vfp_data["WFR_VALUES"].size
    no_gfr_values = vfp_data["GFR_VALUES"].size
    no_alq_values = vfp_data["ALQ_VALUES"].size
    no_flow_values = vfp_data["FLOW_VALUES"].size
    no_tab_values = vfp_data["BHP_TABLE"].flatten().size

    if no_thp_indices != no_wfr_indices:
        return False
    if no_thp_indices != no_gfr_indices:
        return False
    if no_thp_indices != no_alq_indices:
        return False

    no_records = no_thp_values * no_wfr_values * no_gfr_values * no_alq_values
    if no_tab_values % no_flow_values > 0:
        return False
    elif no_tab_values // no_flow_values != no_records:
        return False

    return True


def check_vfpinj_basic_data(vfp_data: Dict[str, Any]) -> bool:
    """Perform a check of the VFPINJ data contained in the dictionary.
    Checks if all data is present and if the dimensions of the arrays
    are consisitent.

    Args:
        vfp_data:   Dictionary containing all data for a VFPPROD keyword in Eclipse
    """

    # Check if all data is present
    if "VFP_NUMBER" not in vfp_data.keys():
        return False
    if "DATUM" not in vfp_data.keys():
        return False
    if "RATE_TYPE" not in vfp_data.keys():
        return False

    if "THP_TYPE" not in vfp_data.keys():
        return False
    if "UNIT_TYPE" not in vfp_data.keys():
        return False
    if "TAB_TYPE" not in vfp_data.keys():
        return False
    if "THP_VALUES" not in vfp_data.keys():
        return False
    if "FLOW_VALUES" not in vfp_data.keys():
        return False
    if "THP_INDICES" not in vfp_data.keys():
        return False
    if "BHP_TABLE" not in vfp_data.keys():
        return False

    no_thp_indices = vfp_data["THP_INDICES"].size
    no_thp_values = vfp_data["THP_VALUES"].size
    no_flow_values = vfp_data["FLOW_VALUES"].size
    no_tab_values = vfp_data["BHP_TABLE"].flatten().size

    if no_thp_indices != no_thp_values:
        return False

    no_records = no_thp_indices
    if no_tab_values % no_flow_values > 0:
        return False
    elif no_tab_values // no_flow_values != no_records:
        return False

    return True


def vfpprod2df(
    keyword: "opm.libopmcommon_python.DeckKeyword",
    vfpnumbers_str: Optional[str] = None,
) -> Union[pd.DataFrame, None]:
    """Return a dataframe or pyarrow Table of a single VFPPROD table
    from an Eclipse deck.

    Args:
        keyword:        Eclipse deck keyword
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds to [0,1,8,9,10,11].
    """

    vfpprod_data = read_vfpprod_basic_data(keyword, vfpnumbers_str)

    # Check if vfp number exists. If not return empry DataFrame
    if len(vfpprod_data) == 0:
        return None

    # Put VFPPROD data into pandas DataFrame
    df_vfpprod = basic_data_vfpprod2df(
        tableno=vfpprod_data["TABLE_NUMBER"],
        datum=vfpprod_data["DATUM"],
        rate_type=vfpprod_data["RATE_TYPE"],
        wfr_type=vfpprod_data["WFR_TYPE"],
        gfr_type=vfpprod_data["GFR_TYPE"],
        alq_type=vfpprod_data["ALQ_TYPE"],
        thp_type=vfpprod_data["THP_TYPE"],
        unit_type=vfpprod_data["UNIT_TYPE"],
        tab_type=vfpprod_data["TAB_TYPE"],
        flow_values=vfpprod_data["FLOW_VALUES"],
        thp_values=vfpprod_data["THP_VALUES"],
        wfr_values=vfpprod_data["WFR_VALUES"],
        gfr_values=vfpprod_data["GFR_VALUES"],
        alq_values=vfpprod_data["ALQ_VALUES"],
        thp_indices=vfpprod_data["THP_INDICES"],
        wfr_indices=vfpprod_data["WFR_INDICES"],
        gfr_indices=vfpprod_data["GFR_INDICES"],
        alq_indices=vfpprod_data["ALQ_INDICES"],
        tab_data=vfpprod_data["BHP_TABLE"],
    )

    return df_vfpprod


def vfpinj2df(
    keyword: "opm.libopmcommon_python.DeckKeyword",
    vfpnumbers_str: Optional[str] = None,
) -> Union[pd.DataFrame, None]:
    """Return a dataframes of a single VFPINJ table from an Eclipse deck

    Data from the VFPINJ keyword are stacked into a Pandas Dataframe

    Args:
        keyword:        Eclipse deck keyword
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds to [0,1,8,9,10,11].
    """

    # Get basic data from VFPINJ tables
    vfpinj_data = read_vfpinj_basic_data(keyword, vfpnumbers_str)

    if len(vfpinj_data) == 0:
        return None

    # Put VFPPROD data into pandas DataFrame
    df_vfpinj = basic_data_vfpinj2df(
        tableno=vfpinj_data["TABLE_NUMBER"],
        datum=vfpinj_data["DATUM"],
        rate_type=vfpinj_data["RATE_TYPE"],
        thp_type=vfpinj_data["THP_TYPE"],
        unit_type=vfpinj_data["UNIT_TYPE"],
        tab_type=vfpinj_data["TAB_TYPE"],
        flow_values=vfpinj_data["FLOW_VALUES"],
        thp_values=vfpinj_data["THP_VALUES"],
        thp_indices=vfpinj_data["THP_INDICES"],
        tab_data=vfpinj_data["BHP_TABLE"],
    )

    return df_vfpinj


def vfpprod2pyarrow(
    keyword: "opm.libopmcommon_python.DeckKeyword",
    vfpnumbers_str: Optional[str] = None,
) -> Union[pa.Table, None]:
    """Return a pyarrow Table of a single VFPPROD table from an Eclipse deck.
       If no VFPPROD curve found, return None

    Args:
        keyword:        Eclipse deck keyword
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds to [0,1,8,9,10,11].
    """

    # Get basic data from VFPPROD tables
    vfpprod_data = read_vfpprod_basic_data(keyword, vfpnumbers_str)

    if len(vfpprod_data) == 0:
        return None

    # Put VFPPROD data into pandas DataFrame
    pa_vfpprod = basic_data_vfpprod2pyarrow(
        tableno=vfpprod_data["TABLE_NUMBER"],
        datum=vfpprod_data["DATUM"],
        rate_type=vfpprod_data["RATE_TYPE"],
        wfr_type=vfpprod_data["WFR_TYPE"],
        gfr_type=vfpprod_data["GFR_TYPE"],
        alq_type=vfpprod_data["ALQ_TYPE"],
        thp_type=vfpprod_data["THP_TYPE"],
        unit_type=vfpprod_data["UNIT_TYPE"],
        tab_type=vfpprod_data["TAB_TYPE"],
        flow_values=vfpprod_data["FLOW_VALUES"],
        thp_values=vfpprod_data["THP_VALUES"],
        wfr_values=vfpprod_data["WFR_VALUES"],
        gfr_values=vfpprod_data["GFR_VALUES"],
        alq_values=vfpprod_data["ALQ_VALUES"],
        thp_indices=vfpprod_data["THP_INDICES"],
        wfr_indices=vfpprod_data["WFR_INDICES"],
        gfr_indices=vfpprod_data["GFR_INDICES"],
        alq_indices=vfpprod_data["ALQ_INDICES"],
        tab_data=vfpprod_data["BHP_TABLE"],
    )

    return pa_vfpprod


def vfpinj2pyarrow(
    keyword: "opm.libopmcommon_python.DeckKeyword",
    vfpnumbers_str: Optional[str] = None,
) -> Union[pa.Table, None]:
    """Return a pyarrow Table of a single VFPINJ table from an Eclipse deck
       If no VFPINJ table found, return None

    Args:
        keyword:        Eclipse deck keyword
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds to [0,1,8,9,10,11].
    """

    # Get basic data from VFPINJ tables
    vfpinj_data = read_vfpinj_basic_data(keyword, vfpnumbers_str)

    if len(vfpinj_data) == 0:
        return None

    # Put VFPPROD data into pandas DataFrame
    pa_vfpinj = basic_data_vfpinj2pyarrow(
        tableno=vfpinj_data["TABLE_NUMBER"],
        datum=vfpinj_data["DATUM"],
        rate_type=vfpinj_data["RATE_TYPE"],
        thp_type=vfpinj_data["THP_TYPE"],
        unit_type=vfpinj_data["UNIT_TYPE"],
        tab_type=vfpinj_data["TAB_TYPE"],
        flow_values=vfpinj_data["FLOW_VALUES"],
        thp_values=vfpinj_data["THP_VALUES"],
        thp_indices=vfpinj_data["THP_INDICES"],
        tab_data=vfpinj_data["BHP_TABLE"],
    )

    return pa_vfpinj


def dfs(
    deck: Union[str, EclFiles, "opm.libopmcommon_python.Deck"],
    keyword: str = "VFPPROD",
    vfpnumbers_str: Optional[str] = None,
) -> List[pd.DataFrame]:
    """Produce a list of dataframes of vfp tables from a deck

    Data for the keyword VFPPROD or VFPINJ will be returned as separate item in list

    Args:
        deck:           Eclipse deck or string with deck
        keyword:        VFP table type, i.e. 'VFPPROD' or 'VFPINJ'
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds to [0,1,8,9,10,11].
    """
    if isinstance(deck, EclFiles):
        deck = deck.get_ecldeck()
    elif isinstance(deck, str):
        deck = EclFiles.str2deck(deck)

    if keyword not in SUPPORTED_KEYWORDS:
        raise ValueError(
            f"VFP type {keyword} not supported choose 'VFPPROD'or 'VFPINJ'"
        )

    dfs_vfp = []
    # The keywords VFPPROD/VFPINJ can be used many times in Eclipse and be introduced in
    # separate files or a common file. Need to loop to find all instances of keyword and
    # store separately
    for deck_keyword in deck:
        if deck_keyword.name == keyword:
            if deck_keyword.name == "VFPPROD":
                df_vfpprod = vfpprod2df(deck_keyword, vfpnumbers_str)
                if df_vfpprod is not None:
                    dfs_vfp.append(df_vfpprod)
            elif deck_keyword.name == "VFPINJ":
                df_vfpinj = vfpinj2df(deck_keyword, vfpnumbers_str)
                if df_vfpinj is not None:
                    dfs_vfp.append(df_vfpinj)

    return dfs_vfp


def pas(
    deck: Union[str, EclFiles, "opm.libopmcommon_python.Deck"],
    keyword: str = "VFPPROD",
    vfpnumbers_str: Optional[str] = None,
) -> List[pa.Table]:
    """Produce a list of pyarrow.Table of vfp tables from a deck

    Data for the keyword VFPPROD or VFPINJ will be returned as separate item in list

    Args:
        deck:           Eclipse deck or string with deck
        keyword:        VFP table type, i.e. 'VFPPROD' or 'VFPINJ'
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds to [0,1,8,9,10,11].
    """
    if isinstance(deck, EclFiles):
        deck = deck.get_ecldeck()
    elif isinstance(deck, str):
        deck = EclFiles.str2deck(deck)

    if keyword not in SUPPORTED_KEYWORDS:
        raise ValueError(
            f"VFP type {keyword} not supported choose 'VFPPROD'or 'VFPINJ'"
        )

    pyarrow_tables_vfp = []
    # The keywords VFPPROD/VFPINJ can be used many times in Eclipse and be introduced in
    # separate files or a common file. Need to loop to find all instances of keyword and
    # store separately
    for deck_keyword in deck:
        if deck_keyword.name == keyword:
            if deck_keyword.name == "VFPPROD":
                pa_table_vfpprod = vfpprod2pyarrow(deck_keyword, vfpnumbers_str)
                if pa_table_vfpprod is not None:
                    pyarrow_tables_vfp.append(pa_table_vfpprod)
            elif deck_keyword.name == "VFPINJ":
                pa_table_vfpinj = vfpinj2pyarrow(deck_keyword, vfpnumbers_str)
                if pa_table_vfpinj is not None:
                    pyarrow_tables_vfp.append(pa_table_vfpinj)

    return pyarrow_tables_vfp


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
    ecl_str += f"   {tableno:5d}"
    ecl_str += f"  {datum:11.1f}"
    ecl_str += f"   {flo_type:>8s}"
    ecl_str += f"  {wfr_type:>8s}"
    ecl_str += f"  {gfr_type:>8s}"
    ecl_str += f"  {pressure_type:>8s}"
    ecl_str += f"  {alq_type_str:>8s}"
    ecl_str += f"  {unit_type:>6s}"
    ecl_str += f"  {tab_type:>8s} /\n\n"
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
    ecl_str += f"   {tableno:5d}"
    ecl_str += f"  {datum:11.1f}"
    ecl_str += f"  {flo_type:>9s}"
    ecl_str += f"  {pressure_type:>8s}"
    ecl_str += f"  {unit_type_str:>8s}"
    ecl_str += f"  {tab_type:>8s} /\n\n"
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

    ecl_str = f"-- {var_type_str} units - {unit_type} ( {len(values)} values )\n"
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
        table:           DataFrame with multiindex for table ranges and colums
                         for tabulated values (BHP)
        format:          Format string for values
        values_per_line: Number of values per line in output
    """

    ecl_str = ""
    for idx, row in table.iterrows():
        ecl_str += f"{idx[0]:2d} {idx[1]:2d} {idx[2]:2d} {idx[3]:2d}"
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


def write_vfpprod_table_records(
    thp_indices: np.ndarray,
    wfr_indices: np.ndarray,
    gfr_indices: np.ndarray,
    alq_indices: np.ndarray,
    table: np.ndarray,
    format: str = "%10.3",
    values_per_line: int = 5,
) -> str:
    """Produce a string representing an Eclipse record for a VFPPROD table (BHP part)

    Args:
        thp_indices:     array of int representing index for THP value for record
        wfr_indices:     array of int representing index for WFR value for record
        gfr_indices:     array of int representing index for GFR value for record
        alq_indices:     array of int representing index for ALQ value for record
        table:           DataFrame with multiindex for table ranges and colums
                         for tabulated values (BHP)
        format:          Format string for values
        values_per_line: Number of values per line in output
    """

    ecl_str = ""
    no_records = len(thp_indices)
    no_flow_values = table.size // no_records
    if table.size % no_records > 0:
        raise ValueError("Incompatible BHP table size")
        return ecl_str
    else:
        table = table.reshape(no_records, no_flow_values)

    for row in range(0, no_records):
        thp = thp_indices[row]
        wfr = wfr_indices[row]
        gfr = gfr_indices[row]
        alq = alq_indices[row]
        ecl_str += f"{thp:2d} {wfr:2d} {gfr:2d} {alq:2d}"
        for n, value in enumerate(table[row, :]):
            ecl_str += format % value
            if (n + 1) % values_per_line == 0:
                if n < no_flow_values - 1:
                    ecl_str += "\n"
                    ecl_str += " " * 11
                else:
                    ecl_str += "\n"
            elif n == no_flow_values - 1:
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
        table:           DataFrame with multiindex for table ranges and colums
                         for tabulated values (BHP)
        format:          Format string for values
        values_per_line: Number of values per line in output
    """

    ecl_str = ""
    for idx, row in table.iterrows():
        ecl_str += f"{idx:2d}"
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


def write_vfpinj_table_records(
    thp_indices: np.ndarray,
    table: pd.DataFrame,
    format: str = "%10.6g",
    values_per_line: int = 5,
) -> str:
    """Produce a string representing an Eclipse record for a VFPINJ table (BHP part)

    Args:
        thp_indices:     array of int representing index for THP value for record
        table:           DataFrame with multiindex for table ranges and colums
                         for tabulated values (BHP)
        format:          Format string for values
        values_per_line: Number of values per line in output
    """

    ecl_str = ""
    no_records = len(thp_indices)
    no_flow_values = table.size // no_records
    if table.size % no_records > 0:
        raise ValueError("Incompatible BHP table size")
        return ecl_str
    else:
        table = table.reshape(no_records, no_flow_values)

    for row in range(0, no_records):
        thp = thp_indices[row]
        ecl_str += f"{thp:2d}"
        for n, value in enumerate(table[row, :]):
            ecl_str += format % value
            if (n + 1) % values_per_line == 0:
                if n < no_flow_values - 1:
                    ecl_str += "\n"
                    ecl_str += " " * 2
                else:
                    ecl_str += "\n"
            elif n == no_flow_values - 1:
                ecl_str += "\n"

        ecl_str += "/\n"

    return ecl_str


def df2ecl_vfpprod(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Produce a string defining single VFPPROD Eclipse input from a dataframe

    All data for the keywords VFPPROD will be returned.

    Args:
        dframe:  Dataframe containing complete description of single VFPPROD input
        comment: Text that will be included as comment
    """
    if dframe.empty:
        return "-- No data!"

    # Extract basic data structutes for VFPPROD
    vfpprod_data = df2vfpprod_basic_data(dframe)
    rate_type = vfpprod_data["RATE_TYPE"]
    wfr_type = vfpprod_data["WFR_TYPE"]
    gfr_type = vfpprod_data["GFR_TYPE"]
    alq_type = vfpprod_data["ALQ_TYPE"]
    thp_type = vfpprod_data["THP_TYPE"]
    unit_type = vfpprod_data["UNIT_TYPE"]

    # Write dataframe to string with Eclipse format for VFPPROD
    ecl_str = "VFPPROD\n"
    if comment:
        ecl_str += common.comment_formatter(comment)
    else:
        ecl_str += "\n"

    unit_value = vfpprod_data["UNIT_TYPE"].value
    if vfpprod_data["UNIT_TYPE"] == UNITTYPE.DEFAULT:
        unit_value = "1*"
    ecl_str += write_vfpprod_basic_record(
        vfpprod_data["TABLE_NUMBER"],
        vfpprod_data["DATUM"],
        vfpprod_data["RATE_TYPE"].value,
        vfpprod_data["WFR_TYPE"].value,
        vfpprod_data["GFR_TYPE"].value,
        vfpprod_data["ALQ_TYPE"].value,
        vfpprod_data["THP_TYPE"].value,
        vfpprod_data["UNIT_TYPE"].value,
        vfpprod_data["TAB_TYPE"].value,
    )
    ecl_str += write_vfp_range(
        vfpprod_data["FLOW_VALUES"],
        rate_type.value,
        VFPPROD_UNITS[unit_type.value]["FLO"][rate_type.value],
        "%10.6g",
    )
    ecl_str += write_vfp_range(
        vfpprod_data["THP_VALUES"],
        thp_type.value,
        VFPPROD_UNITS[unit_type.value]["THP"][thp_type.value],
        "%10.6g",
    )
    ecl_str += write_vfp_range(
        vfpprod_data["WFR_VALUES"],
        wfr_type.value,
        VFPPROD_UNITS[unit_type.value]["WFR"][wfr_type.value],
        "%10.6g",
    )
    ecl_str += write_vfp_range(
        vfpprod_data["GFR_VALUES"],
        gfr_type.value,
        VFPPROD_UNITS[unit_type.value]["GFR"][gfr_type.value],
        "%10.6g",
    )
    ecl_str += write_vfp_range(
        vfpprod_data["ALQ_VALUES"],
        alq_type.value,
        VFPPROD_UNITS[unit_type.value]["ALQ"][alq_type.value],
        "%10.6g",
    )
    ecl_str += write_vfpprod_table_records(
        vfpprod_data["THP_INDICES"],
        vfpprod_data["WFR_INDICES"],
        vfpprod_data["GFR_INDICES"],
        vfpprod_data["ALQ_INDICES"],
        vfpprod_data["BHP_TABLE"],
        "%10.6g",
    )

    return ecl_str

    # Consistency checks of data type
    if len(dframe["RATE_TYPE"].unique()) == 1:
        rate = VFPPROD_FLO[dframe["RATE_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of FLO type is not unique")
    if len(dframe["WFR_TYPE"].unique()) == 1:
        wfr = WFR[dframe["WFR_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of WFR type is not unique")
    if len(dframe["GFR_TYPE"].unique()) == 1:
        gfr = GFR[dframe["GFR_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of GFR type is not unique")
    if len(dframe["ALQ_TYPE"].unique()) == 1:
        if not dframe["ALQ_TYPE"].unique()[0] or dframe["ALQ_TYPE"].unique()[0] == "''":
            alq = ALQ.UNDEFINED
        else:
            alq = ALQ[dframe["ALQ_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of ALQ type is not unique")
    if len(dframe["PRESSURE_TYPE"].unique()) == 1:
        thp = THPTYPE[dframe["PRESSURE_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of THP type is not unique")
    if len(dframe["TAB_TYPE"].unique()) == 1:
        tab = VFPPROD_TABTYPE[dframe["TAB_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of TAB type is not unique")
    if len(dframe["UNIT_TYPE"].unique()) == 1:
        unit = UNITTYPE[dframe["UNIT_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of UNIT type is not unique")

    # Consistency check of basic data
    if len(dframe["TABLE_NUMBER"].unique()) == 1:
        vfpno = dframe["TABLE_NUMBER"].unique()[0]
    else:
        raise ValueError("Definition of TABLE_NUMBER is not unique")
    if len(dframe["DATUM"].unique()) == 1:
        datum = dframe["DATUM"].unique()[0]
    else:
        raise ValueError("Definition of DATUM is not unique")

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
        raise ValueError(
            f"Number of unique rate values {no_flow_values} not consistent "
            "with number of tabulated values {no_tab_values}"
        )
    if no_tab_values % no_wfr_values != 0:
        raise ValueError(
            f"Number of unique wfr values {no_wfr_values} not "
            "consistent with number of tabulated values {no_tab_values}"
        )
    if no_tab_values % no_gfr_values != 0:
        raise ValueError(
            f"Number of unique gfr values {no_gfr_values} not consistent "
            "with number of tabulated values {no_tab_values}"
        )
    if no_tab_values % no_alq_values != 0:
        raise ValueError(
            f"Number of unique alq values {no_alq_values} not consistent "
            "with number of tabulated values {no_tab_values}"
        )
    if no_tab_values % no_thp_values != 0:
        raise ValueError(
            f"Number of unique thp values {no_thp_values} not consistent "
            "with number of tabulated values {no_tab_values}"
        )
    if no_tab_values % no_interp_values != 0:
        raise ValueError(
            f"Number of unique interpolation values {no_interp_values} not consistent "
            "with number of tabulated values {no_tab_values}"
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
        raise ValueError("Definition of FLO type is not unique")
    if len(dframe["PRESSURE_TYPE"].unique()) == 1:
        thp = THPTYPE[dframe["PRESSURE_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of THP type is not unique")
    if len(dframe["TAB_TYPE"].unique()) == 1:
        tab = VFPINJ_TABTYPE[dframe["TAB_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of TAB type is not unique")
    if len(dframe["UNIT_TYPE"].unique()) == 1:
        unit = UNITTYPE[dframe["UNIT_TYPE"].unique()[0]]
    else:
        raise ValueError("Definition of UNIT type is not unique")

    # Consistency check of basic data
    if len(dframe["TABLE_NUMBER"].unique()) == 1:
        vfpno = dframe["TABLE_NUMBER"].unique()[0]
    else:
        raise ValueError("Definition of TABLE_NUMBER is not unique")
    if len(dframe["DATUM"].unique()) == 1:
        datum = dframe["DATUM"].unique()[0]
    else:
        raise ValueError("Definition of DATUM is not unique")

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
        raise ValueError(
            f"Number of unique rate values {no_flow_values}"
            " not consistent with number of tabulated"
            " values {no_tab_values}"
        )
    if no_tab_values % no_thp_values != 0:
        raise ValueError(
            f"Number of unique thp values {no_thp_values} not consistent "
            "with number of tabulated values {no_tab_values}"
        )
    if no_tab_values % no_interp_values != 0:
        raise ValueError(
            f"Number of unique interpolation values {no_interp_values} not consistent "
            "with number of tabulated values {no_tab_values}"
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
    keyword: str = "VFPPROD",
    comments: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Produce a list of strings defining VFPPROD/VFPINJ Eclipse input from a dataframe

    All data for the keyword VFPPROD or VFPINJ will be returned.

    Args:
        dframe:   Dataframe containing complete description of VFPPROD/VFPINJ input
        keywords: Keyword to include, 'VFPPROD' or 'VFPINJ'
        comments: Dictionary indexed by keyword with comments to be
                  included pr. keyword.
    """

    if dframe.empty:
        return []

    if keyword not in SUPPORTED_KEYWORDS:
        raise ValueError(f"Given keyword {keyword} is not in supported keywords")

    vfp_strs = []
    vfp_numbers = dframe["TABLE_NUMBER"].unique()
    for vfpno in vfp_numbers:
        df_vfp = dframe[dframe["TABLE_NUMBER"] == vfpno]
        if np.all(df_vfp["VFP_TYPE"] == keyword):
            if comments and keyword in comments.keys():
                if keyword == "VFPPROD":
                    vfp_strs.append(df2ecl_vfpprod(df_vfp, comments["VFPPROD"]))
                elif keyword == "VFPINJ":
                    vfp_strs.append(df2ecl_vfpinj(df_vfp, comments["VFPINJ"]))
            else:
                if keyword == "VFPPROD":
                    vfp_strs.append(df2ecl_vfpprod(df_vfp))
                elif keyword == "VFPINJ":
                    vfp_strs.append(df2ecl_vfpinj(df_vfp))
        else:
            raise ValueError(
                f"VFP number {vfpno} does not have consistent "
                "type defintion in vfp.dfecls_vfp"
            )

    return vfp_strs


def df2ecl(
    dframe: pd.DataFrame,
    keyword: str = "VFPPROD",
    comments: Optional[Dict[str, str]] = None,
    filename: Optional[str] = None,
) -> str:
    """Produce a string defining all VFPPROD/VFPINJ Eclipse input from a dataframe

    All data for the keywords VFPPROD/VFPINJ will be returned.

    Args:
        dframe:    Dataframe containing complete description of VFPPROD/VFPINJ input
        keyword:   Keywords to include, i.e. 'VFPPROD' or 'VFPINJ'
        comments:  comments: Dictionary indexed by keyword with comments to be
                   included pr. keyword. If a key named "master" is present
                   it will be used as a master comment for the outputted file.
        filename:  If supplied, the generated text will also be dumped
                   to file.
    """

    strs_vfp = df2ecls_vfp(dframe, keyword=keyword, comments=comments)
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
    keyword: str = "VFPPROD",
    vfpnumbers_str: Optional[str] = None,
) -> pd.DataFrame:
    """Produce a dataframes of all vfp tables from a deck

    All data for the keywords VFPPROD/VFPINJ will be returned.

    Args:
        deck:           Eclipse deck or string wit deck
        keyword:        VFP table type, i.e. 'VFPPROD' or 'VFPINJ'
        vfpnumbers_str: str with list of VFP table numbers to extract
    """

    if not keyword:
        logger.warning("No keywords provided to vfp.df. Empty dataframe returned")
        return pd.DataFrame()

    if isinstance(deck, EclFiles):
        deck = deck.get_ecldeck()
    elif isinstance(deck, str):
        deck = EclFiles.str2deck(deck)

    # Extract all VFPROD/VFPINJ as separate dataframes
    dfs_vfp = dfs(deck, keyword, vfpnumbers_str)
    # Concat all dataframes into one dataframe
    if dfs_vfp:
        return pd.concat(dfs_vfp)
    else:
        return pd.DataFrame()


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
        "--keyword",
        type=str,
        help="VFP keywords to include, i.e. VFPPROD or VFPINJ",
        default="",
    )
    parser.add_argument(
        "-n",
        "--vfpnumbers",
        type=str,
        help="List of VFP table numbers to include. Format [1,2,4:10]",
        default="",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument("--arrow", action="store_true", help="Write to pyarrow format")
    return parser


def fill_reverse_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Fill a parser for the operation dataframe -> eclipse include file"""
    return common.fill_reverse_parser(parser, "VFPPROD, VFPINJ", "vfp.inc")


def vfp_main(args) -> None:
    """Entry-point for module, for command line utility."""
    logger = getLogger_ecl2csv(  # pylint: disable=redefined-outer-name
        __name__, vars(args)
    )
    if args.keyword:
        if args.keyword not in SUPPORTED_KEYWORDS:
            raise ValueError(f"Keyword argument {args.keyword} not supported")
    if not args.output:
        logger.info("Nothing to do. Set --output")
        sys.exit(0)
    vfpnumbers = None
    if "vfpnumbers" in args:
        vfpnumbers = str(args.vfpnumbers)

    eclfiles = EclFiles(args.DATAFILE)
    if args.arrow:
        outputfile = args.output
        outputfile.replace(".arrow", "")
        vfp_arrow_tables = pas(
            eclfiles.get_ecldeck(), keyword=args.keyword, vfpnumbers_str=vfpnumbers
        )
        for vfp_table in vfp_arrow_tables:
            table_number = int(
                vfp_table.schema.metadata[b"TABLE_NUMBER"].decode("utf-8")
            )
            vfp_filename = outputfile + "_" + str(table_number) + ".arrow"
            common.write_dframe_stdout_file(
                vfp_table, vfp_filename, index=False, caller_logger=logger
            )
            logger.info(f"Parsed file {args.DATAFILE} for vfp.dfs_arrow")
    else:
        dframe = df(
            eclfiles.get_ecldeck(), keyword=args.keyword, vfpnumbers_str=vfpnumbers
        )
        if args.output:
            common.write_dframe_stdout_file(
                dframe, args.output, index=False, caller_logger=logger
            )
            logger.info(f"Parsed file {args.DATAFILE} for vfp.df")


def vfp_reverse_main(args) -> None:
    """Entry-point for module, for command line utility for CSV to Eclipse"""
    logger = getLogger_ecl2csv(  # pylint: disable=redefined-outer-name
        __name__, vars(args)
    )
    vfp_df = pd.read_csv(args.csvfile)
    logger.info("Parsed {args.csvfile}")
    inc_string = df2ecl(vfp_df, args.keyword)
    if args.output:
        common.write_inc_stdout_file(inc_string, args.output)

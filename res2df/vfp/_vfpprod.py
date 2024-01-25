"""Utilities to extract the VFPPROD data from an Eclipse (input) deck.
Data can be extracted from Eclipse (.Ecl format) in 3 different formats:
basic_data (dictionary with basic data types), df (pandas DataFrame) or
pyarrow_tables (pyarrow.Tables).

Data can be extracted from a complete deck or from individual files.
Supports output both in csv format as a pandas DataFrame or in pyarrow
as pyarrow.Table. Also functionality to write pandas DataFrame and
pyarrow.Table to file as Eclipse .Ecl format.
"""

import logging
import numbers
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

from ..common import comment_formatter, parse_opmio_deckrecord
from ._vfpcommon import (
    _deckrecord2list,
    _stack_vfptable2df,
    _string2intlist,
    _write_vfp_range,
)
from ._vfpdefs import (
    ALQ,
    GFR,
    THPTYPE,
    UNITTYPE,
    VFPPROD_FLO,
    VFPPROD_TABTYPE,
    VFPPROD_UNITS,
    VFPTYPE,
    WFR,
)

# Keys used for basic data dictionary representation of VFPPROD
BASIC_DATA_KEYS = [
    "VFP_TYPE",
    "TABLE_NUMBER",
    "DATUM",
    "RATE_TYPE",
    "WFR_TYPE",
    "GFR_TYPE",
    "ALQ_TYPE",
    "THP_TYPE",
    "UNIT_TYPE",
    "TAB_TYPE",
    "THP_VALUES",
    "WFR_VALUES",
    "GFR_VALUES",
    "ALQ_VALUES",
    "FLOW_VALUES",
    "THP_INDICES",
    "WFR_INDICES",
    "GFR_INDICES",
    "ALQ_INDICES",
    "BHP_TABLE",
]


logger = logging.getLogger(__name__)


def basic_data(
    keyword: "opm.libopmcommon_python.DeckKeyword",
    vfpnumbers_str: Optional[str] = None,
) -> Union[Dict[str, Any], None]:
    """Read and return all data for Eclipse VFPPROD keyword as basic data types

    Empty string returned if vfp table number does not match any number in list

    Args:
        keyword:        :term:`.DATA file` keyword
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds
    """
    # Number of records in keyword
    num_rec = len(keyword)

    # Parse records with basic information and interpolation ranges
    basic_record = parse_opmio_deckrecord(keyword[0], "VFPPROD", "records", 0)

    # Extract basic table information
    tableno = int(basic_record["TABLE"])
    if vfpnumbers_str:
        vfpnumbers = _string2intlist(vfpnumbers_str)
        if tableno not in vfpnumbers:
            return None
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

    flow_values = _deckrecord2list(keyword[1], "VFPPROD", 1, "FLOW_VALUES")
    thp_values = _deckrecord2list(keyword[2], "VFPPROD", 2, "THP_VALUES")
    wfr_values = _deckrecord2list(keyword[3], "VFPPROD", 3, "WFR_VALUES")
    gfr_values = _deckrecord2list(keyword[4], "VFPPROD", 4, "GFR_VALUES")
    alq_values = _deckrecord2list(keyword[5], "VFPPROD", 5, "ALQ_VALUES")

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
        bhp_record = parse_opmio_deckrecord(keyword[n], "VFPPROD", "records", 6)
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
        "VFP_TYPE": VFPTYPE.VFPPROD,
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


def basic_data2df(
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

    # Generate list with values instead of indices in index columns
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


def basic_data2pyarrow(
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
        col_name = str(thp_idx) + f"_{str(wfr_idx)}_{str(gfr_idx)}_{str(alq_idx)}"
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


def df2basic_data(dframe: pd.DataFrame) -> Dict[str, Any]:
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
        "VFP_TYPE": VFPTYPE.VFPPROD,
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


def pyarrow2basic_data(pa_table: pa.Table) -> Dict[str, Any]:
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


def _check_basic_data(vfp_data: Dict[str, Any]) -> bool:
    """Perform a check of the VFPPROD data contained in the dictionary.
    Checks if all data is present and if the dimensions of the arrays
    are consistent.

    Args:
        vfp_data:   Dictionary containing all data for a VFPPROD keyword in Eclipse
    """

    # Check if all data is present
    for key in BASIC_DATA_KEYS:
        if key not in vfp_data.keys():
            raise KeyError(f"{key} key is not in basic data dictionary VFPPROD")
    if vfp_data["VFP_TYPE"] is not VFPTYPE.VFPPROD:
        raise KeyError("VFPTYPE must be VFPPROD")

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
        raise ValueError(
            f"Number of THP_INDICES {no_thp_indices} does not match "
            f"number of WFR_INDICES {no_wfr_indices} in basic data dictionary "
            f"for VFPPROD"
        )
    if no_thp_indices != no_gfr_indices:
        raise ValueError(
            f"Number of THP_INDICES {no_thp_indices} does not match "
            f"number of GFR_INDICES {no_gfr_indices} in basic data dictionary "
            f"for VFPPROD"
        )
    if no_thp_indices != no_alq_indices:
        raise ValueError(
            f"Number of THP_INDICES {no_thp_indices} does not match "
            f"number of ALQ_INDICES {no_alq_indices} in basic data dictionary "
            f"for VFPPROD"
        )

    no_records = no_thp_values * no_wfr_values * no_gfr_values * no_alq_values
    if no_tab_values % no_flow_values > 0:
        raise ValueError(
            f"Number of BHP_TABLE values {no_tab_values} is not a multiplum "
            f"of number of THP_VALUES {no_thp_values} in basic data dictionary "
            f"for VFPPROD"
        )
    elif no_tab_values // no_flow_values != no_records:
        raise ValueError(
            f"Number of BHP_TABLE values {no_tab_values} is not a multiplum "
            f"of number of FLOW_VALUES {no_flow_values} in basic data dictionary "
            f"for VFPPROD"
        )

    return True


def df(
    keyword: "opm.libopmcommon_python.DeckKeyword",
    vfpnumbers_str: Optional[str] = None,
) -> Union[pd.DataFrame, None]:
    """Return a dataframe or pyarrow Table of a single VFPPROD table
    from a :term:`.DATA file`.

    Args:
        keyword:        :term:`.DATA file` keyword
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds to [0,1,8,9,10,11].
    """

    vfpprod_data = basic_data(keyword, vfpnumbers_str)

    # Check if vfp number exists. If not return empry DataFrame
    if vfpprod_data is None:
        return None

    # Put VFPPROD data into pandas DataFrame
    df_vfpprod = basic_data2df(
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


def pyarrow(
    keyword: "opm.libopmcommon_python.DeckKeyword",
    vfpnumbers_str: Optional[str] = None,
) -> Union[pa.Table, None]:
    """Return a pyarrow Table of a single VFPPROD table from a :term:`.DATA file`.
       If no VFPPROD curve found, return None

    Args:
        keyword:        :term:`.DATA file` keyword
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds to [0,1,8,9,10,11].
    """

    # Get basic data from VFPPROD tables
    vfpprod_data = basic_data(keyword, vfpnumbers_str)

    if vfpprod_data is None:
        return None

    # Put VFPPROD data into pandas DataFrame
    pa_vfpprod = basic_data2pyarrow(
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


def _write_basic_record(
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
    """Creates a :term:`include file` content string representing
    the first record for Eclipse VFPPROD keyword

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

    deck_str = "-- Table  Datum Depth  Rate Type  WFR Type  "
    deck_str += "GFR Type  THP Type  ALQ Type  UNITS   TAB Type\n"
    deck_str += "-- -----  -----------  ---------  --------  "
    deck_str += "--------  --------  --------  ------  --------\n"
    deck_str += f"   {tableno:5d}"
    deck_str += f"  {datum:11.1f}"
    deck_str += f"   {flo_type:>8s}"
    deck_str += f"  {wfr_type:>8s}"
    deck_str += f"  {gfr_type:>8s}"
    deck_str += f"  {pressure_type:>8s}"
    deck_str += f"  {alq_type_str:>8s}"
    deck_str += f"  {unit_type:>6s}"
    deck_str += f"  {tab_type:>8s} /\n\n"
    return deck_str


def _write_table(
    table: pd.DataFrame,
    format: str = "%10.3",
    values_per_line: int = 5,
) -> str:
    """Creates a :term:`include file` content string representing
    a resdata record for a VFPPROD table (BHP part)

    Args:
        table:           DataFrame with multiindex for table ranges and colums
                         for tabulated values (BHP)
        format:          Format string for values
        values_per_line: Number of values per line in output
    """

    deck_str = ""
    for idx, row in table.iterrows():
        deck_str += f"{idx[0]:2d} {idx[1]:2d} {idx[2]:2d} {idx[3]:2d}"
        no_flo = len(table.loc[idx].to_list())
        for n, value in enumerate(table.loc[idx].to_list()):
            deck_str += format % value
            if (n + 1) % values_per_line == 0:
                if n < no_flo - 1:
                    deck_str += "\n"
                    deck_str += " " * 11
                else:
                    deck_str += "\n"
            elif n == no_flo - 1:
                deck_str += "\n"
        deck_str += "/\n"

    return deck_str


def _write_table_records(
    thp_indices: np.ndarray,
    wfr_indices: np.ndarray,
    gfr_indices: np.ndarray,
    alq_indices: np.ndarray,
    table: np.ndarray,
    format: str = "%10.6g",
    values_per_line: int = 5,
) -> str:
    """Creates a :term:`include file` content string representing a
    resdata record for a VFPPROD table (BHP part)

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

    deck_str = ""
    no_records = len(thp_indices)
    no_flow_values = table.size // no_records
    if table.size % no_records > 0:
        raise ValueError("Incompatible BHP table size")
    else:
        table = table.reshape(no_records, no_flow_values)

    for row in range(0, no_records):
        thp = thp_indices[row]
        wfr = wfr_indices[row]
        gfr = gfr_indices[row]
        alq = alq_indices[row]
        deck_str += f"{thp:2d} {wfr:2d} {gfr:2d} {alq:2d}"
        for n, value in enumerate(table[row, :]):
            deck_str += format % value
            if (n + 1) % values_per_line == 0:
                if n < no_flow_values - 1:
                    deck_str += "\n"
                    deck_str += " " * 11
                else:
                    deck_str += "\n"
            elif n == no_flow_values - 1:
                deck_str += "\n"
            else:
                deck_str += " "

        deck_str += "/\n"

    return deck_str


def df2res(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Creates a :term:`include file` content string
    representing single VFPPROD Eclipse input from a dataframe

    All data for the keywords VFPPROD will be returned.

    Args:
        dframe:  Dataframe containing complete description of single VFPPROD input
        comment: Text that will be included as comment
    """
    if dframe.empty:
        return "-- No data!"

    # Extract basic data structutes for VFPPROD
    vfpprod_data = df2basic_data(dframe)
    rate_type = vfpprod_data["RATE_TYPE"]
    wfr_type = vfpprod_data["WFR_TYPE"]
    gfr_type = vfpprod_data["GFR_TYPE"]
    alq_type = vfpprod_data["ALQ_TYPE"]
    thp_type = vfpprod_data["THP_TYPE"]
    unit_type = vfpprod_data["UNIT_TYPE"]

    # Write dataframe to string with Eclipse format for VFPPROD
    deck_str = "VFPPROD\n"
    if comment:
        deck_str += comment_formatter(comment)
    else:
        deck_str += "\n"

    unit_value = vfpprod_data["UNIT_TYPE"].value
    if vfpprod_data["UNIT_TYPE"] == UNITTYPE.DEFAULT:
        unit_value = "1*"
    deck_str += _write_basic_record(
        vfpprod_data["TABLE_NUMBER"],
        vfpprod_data["DATUM"],
        vfpprod_data["RATE_TYPE"].value,
        vfpprod_data["WFR_TYPE"].value,
        vfpprod_data["GFR_TYPE"].value,
        vfpprod_data["ALQ_TYPE"].value,
        vfpprod_data["THP_TYPE"].value,
        unit_value,
        vfpprod_data["TAB_TYPE"].value,
    )
    deck_str += _write_vfp_range(
        vfpprod_data["FLOW_VALUES"],
        rate_type.value,
        VFPPROD_UNITS[unit_type.value]["FLO"][rate_type.value],
        "%10.6g",
    )
    deck_str += _write_vfp_range(
        vfpprod_data["THP_VALUES"],
        thp_type.value,
        VFPPROD_UNITS[unit_type.value]["THP"][thp_type.value],
        "%10.6g",
    )
    deck_str += _write_vfp_range(
        vfpprod_data["WFR_VALUES"],
        wfr_type.value,
        VFPPROD_UNITS[unit_type.value]["WFR"][wfr_type.value],
        "%10.6g",
    )
    deck_str += _write_vfp_range(
        vfpprod_data["GFR_VALUES"],
        gfr_type.value,
        VFPPROD_UNITS[unit_type.value]["GFR"][gfr_type.value],
        "%10.6g",
    )
    deck_str += _write_vfp_range(
        vfpprod_data["ALQ_VALUES"],
        alq_type.value,
        VFPPROD_UNITS[unit_type.value]["ALQ"][alq_type.value],
        "%10.6g",
    )
    deck_str += _write_table_records(
        vfpprod_data["THP_INDICES"],
        vfpprod_data["WFR_INDICES"],
        vfpprod_data["GFR_INDICES"],
        vfpprod_data["ALQ_INDICES"],
        vfpprod_data["BHP_TABLE"],
        "%10.6g",
    )

    return deck_str

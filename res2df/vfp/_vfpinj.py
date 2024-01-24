"""Utilities to extract the VFPINJ data from an Eclipse (input) deck.
Data can be extracted from Eclipse (.Ecl format) in 3 different formats:
basic_data (dictionary with basic data types), df (pandas DataFrame) or
pyarrow_tables (pyarrow.Tables).

Data can be extracted from a complete deck or from individual files.
Supports output both in csv format as a pandas DataFrame or in pyarrow
a pyarrow.Table. Also functionality to write pandas DataFrame and
pyarrow.Table to file as Eclipse .Ecl format
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
    THPTYPE,
    UNITTYPE,
    VFPINJ_FLO,
    VFPINJ_TABTYPE,
    VFPINJ_UNITS,
    VFPTYPE,
)

# Keys used for basic data dictionary representation of VFPINJ
BASIC_DATA_KEYS = [
    "VFP_TYPE",
    "TABLE_NUMBER",
    "DATUM",
    "RATE_TYPE",
    "THP_TYPE",
    "UNIT_TYPE",
    "TAB_TYPE",
    "THP_VALUES",
    "FLOW_VALUES",
    "THP_INDICES",
    "BHP_TABLE",
]


logger = logging.getLogger(__name__)


def basic_data(
    keyword: "opm.libopmcommon_python.DeckKeyword",
    vfpnumbers_str: Optional[str] = None,
) -> Dict[str, Any]:
    """Read and return all data for Eclipse VFPINJ keyword as basic data types

    Empty string returned if vfp table number does not match any number in list

    Args:
        keyword:        :term:`.DATA file` keyword
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds
    """

    # Number of record in keyword
    num_rec = len(keyword)

    # Parse records with basic information and interpolation ranges
    basic_record = parse_opmio_deckrecord(keyword[0], "VFPINJ", "records", 0)

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
    flow_values = _deckrecord2list(keyword[1], "VFPINJ", 1, "FLOW_VALUES")
    thp_values = _deckrecord2list(keyword[2], "VFPINJ", 2, "THP_VALUES")

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
        bhp_record = parse_opmio_deckrecord(keyword[n], "VFPINJ", "records", 3)
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
        "VFP_TYPE": VFPTYPE.VFPINJ,
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


def basic_data2df(
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
        thp_type    : thp type used for THP values
        unit_type   : unit type
        tab_type    : type for tabulated (record) values
        flow_values : rate values used to generate table
        thp_type    : thp type
        thp_indices : which index in thp value table a given BHP value
                      corresponds to (1-base)
        tab_data    : tabulated (BHP) data
                      (ordered as thp- and flow-values)
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


def basic_data2pyarrow(
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
    """Return a pyarrow Table from VFPINJ record data

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


def df2basic_data(dframe: pd.DataFrame) -> Dict[str, Any]:
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
        "VFP_TYPE": VFPTYPE.VFPINJ,
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


def pyarrow2basic_data(pa_table: pa.Table) -> Dict[str, Any]:
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


def _check_basic_data(vfp_data: Dict[str, Any]) -> bool:
    """Perform a check of the VFPINJ data contained in the dictionary.
    Checks if all data is present and if the dimensions of the arrays
    are consisitent.

    Args:
        vfp_data:   Dictionary containing all data for a VFPINJ keyword in Eclipse
    """

    # Check if all data is present
    for key in BASIC_DATA_KEYS:
        if key not in vfp_data.keys():
            raise KeyError(f"{key} key is not in basic data dictionary VFPINJ")
    if vfp_data["VFP_TYPE"] is not VFPTYPE.VFPINJ:
        raise KeyError("VFPTYPE must be VFPINJ")

    no_thp_indices = vfp_data["THP_INDICES"].size
    no_thp_values = vfp_data["THP_VALUES"].size
    no_flow_values = vfp_data["FLOW_VALUES"].size
    no_tab_values = vfp_data["BHP_TABLE"].flatten().size

    if no_tab_values % no_flow_values > 0:
        raise ValueError(
            f"Number of BHP_TABLE values {no_tab_values} is not a multiplum "
            f"of number of FLOW_VALUES {no_flow_values} in basic data dictionary "
            f"for VFPINJ "
        )
    if no_tab_values % no_thp_values > 0:
        raise ValueError(
            f"Number of BHP_TABLE values {no_tab_values} is not a multiplum "
            f"of number of THP_VALUES {no_thp_values} in basic data dictionary "
            f"for VFPINJ "
        )
    if no_thp_indices != no_thp_values:
        raise ValueError(
            f"Number of THP_VALUES values {no_thp_values} is not equal to "
            f"of number of THP_INDICES {no_thp_indices}"
        )
    if no_tab_values != no_flow_values * no_thp_indices:
        raise ValueError(
            f"Number of BHP_TABLE values {no_tab_values} is not equal to "
            f"of number of THP_VALUES {no_thp_values} times number of "
            f"FLOW_VALUES {no_flow_values} "
        )

    return True


def df(
    keyword: "opm.libopmcommon_python.DeckKeyword",
    vfpnumbers_str: Optional[str] = None,
) -> Union[pd.DataFrame, None]:
    """Return a dataframes of a single VFPINJ table from a :term:`.DATA file`

    Data from the VFPINJ keyword are stacked into a Pandas Dataframe

    Args:
        keyword:        :term:`.DATA file` keyword
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds to [0,1,8,9,10,11].
    """

    # Get basic data from VFPINJ tables
    vfpinj_data = basic_data(keyword, vfpnumbers_str)

    if len(vfpinj_data) == 0:
        return None

    # Put VFPINJ data into pandas DataFrame
    df_vfpinj = basic_data2df(
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


def pyarrow(
    keyword: "opm.libopmcommon_python.DeckKeyword",
    vfpnumbers_str: Optional[str] = None,
) -> Union[pa.Table, None]:
    """Return a pyarrow Table of a single VFPINJ table from a :term:`.DATA file`
       If no VFPINJ table found, return None

    Args:
        keyword:        :term:`.DATA file` keyword
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds to [0,1,8,9,10,11].
    """

    # Get basic data from VFPINJ tables
    vfpinj_data = basic_data(keyword, vfpnumbers_str)

    if len(vfpinj_data) == 0:
        return None

    # Put VFPINJ data into pandas DataFrame
    pa_vfpinj = basic_data2pyarrow(
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


def _write_basic_record(
    tableno: int,
    datum: float,
    flo_type: str,
    pressure_type: str,
    unit_type: str,
    tab_type: str,
) -> str:
    """Creates a :term:`include file` content string of the
    first record for the Eclipse VFPINJ keyword

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

    deck_str = "-- Table  Datum Depth  Rate Type  THP Type  UNITS     TAB Type\n"
    deck_str += "-- -----  -----------  ---------  --------  --------  --------\n"
    deck_str += f"   {tableno:5d}"
    deck_str += f"  {datum:11.1f}"
    deck_str += f"  {flo_type:>9s}"
    deck_str += f"  {pressure_type:>8s}"
    deck_str += f"  {unit_type_str:>8s}"
    deck_str += f"  {tab_type:>8s} /\n\n"
    return deck_str


def _write_table(
    table: pd.DataFrame,
    format: str = "%10.6g",
    values_per_line: int = 5,
) -> str:
    """Creates a :term:`include file` content string representing
    a resdata record for a VFPINJ table (BHP part)

    Args:
        table:           DataFrame with multiindex for table ranges and colums
                         for tabulated values (BHP)
        format:          Format string for values
        values_per_line: Number of values per line in output
    """

    deck_str = ""
    for idx, row in table.iterrows():
        deck_str += f"{idx:2d}"
        no_flo = len(table.loc[idx].to_list())
        for n, value in enumerate(table.loc[idx].to_list()):
            deck_str += format % value
            if (n + 1) % values_per_line == 0:
                if n < no_flo - 1:
                    deck_str += "\n"
                    deck_str += " " * 2
                else:
                    deck_str += "\n"
            elif n == no_flo - 1:
                deck_str += "\n"
        deck_str += "/\n"

    return deck_str


def _write_table_records(
    thp_indices: np.ndarray,
    table: pd.DataFrame,
    format: str = "%10.6g",
    values_per_line: int = 5,
) -> str:
    """Creates a :term:`include file` content string representing
    for a VFPINJ table (BHP part)

    Args:
        thp_indices:     array of int representing index for THP value for record
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
        deck_str += f"{thp:2d}"
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
    representing single VFPINJ Eclipse input from a dataframe

    All data for the keywords VFPINJ will be returned.

    Args:
        dframe:    Dataframe containing complete description of single VFPINJ input
        comment:   Text that will be included as comment
    """
    if dframe.empty:
        return "-- No data!"

    # Extract basic data structutes for VFPINJ
    vfpinj_data = df2basic_data(dframe)
    rate_type = vfpinj_data["RATE_TYPE"]
    thp_type = vfpinj_data["THP_TYPE"]
    unit_type = vfpinj_data["UNIT_TYPE"]

    # Write dataframe to string with Eclipse format for VFPINJ
    deck_str = "VFPINJ\n"
    if comment:
        deck_str += comment_formatter(comment)
    else:
        deck_str += "\n"

    unit_value = vfpinj_data["UNIT_TYPE"].value
    if vfpinj_data["UNIT_TYPE"] == UNITTYPE.DEFAULT:
        unit_value = "1*"
    deck_str += _write_basic_record(
        vfpinj_data["TABLE_NUMBER"],
        vfpinj_data["DATUM"],
        vfpinj_data["RATE_TYPE"].value,
        vfpinj_data["THP_TYPE"].value,
        unit_value,
        vfpinj_data["TAB_TYPE"].value,
    )
    deck_str += _write_vfp_range(
        vfpinj_data["FLOW_VALUES"],
        rate_type.value,
        VFPINJ_UNITS[unit_type.value]["FLO"][rate_type.value],
        "%10.6g",
    )
    deck_str += _write_vfp_range(
        vfpinj_data["THP_VALUES"],
        thp_type.value,
        VFPINJ_UNITS[unit_type.value]["THP"][thp_type.value],
        "%10.6g",
    )
    deck_str += _write_table_records(
        vfpinj_data["THP_INDICES"],
        vfpinj_data["BHP_TABLE"],
        "%10.6g",
    )

    return deck_str

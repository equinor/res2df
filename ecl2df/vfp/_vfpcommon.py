"""Common functionality for vfp module to extract VFPPROD/VFPINJ data from Eclipse
deck to extract the VFPPROD/VFPINJ data from an Eclipse (input) deck as Pandas
Dataframes

Data can be extracted from a full Eclipse deck or from individual files. Supports
output both in csv format as a pandas DataFrame or in pyarrow and pyarrow.table
"""

import logging
import numbers
from typing import Any, List, Union

import numpy as np
import pandas as pd
import pyarrow as pa

from ecl2df.vfp._vfpdefs import UNITTYPE

try:
    # Needed for mypy

    # pylint: disable=unused-import
    import opm.io

    # This import is seemingly not used, but necessary for some attributes
    # to be included in DeckItem objects.
    from opm.io.deck import DeckKeyword  # noqa
except ImportError:
    pass

from ecl2df import EclFiles, common

logger = logging.getLogger(__name__)


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


def _string2stringlist(list_def_str: str) -> List[str]:
    """Produce a list of string from input string

    Args:
        list_def_str: String defining list of string
                      Format "["str1","str2","str3"]"
                      to define list ["str1","str2","str3"]
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
            list.append(str(item))

    return list


def _deckrecord2list(
    record: "opm.libopmcommon_python.DeckRecord",
    keyword: str,
    recordindex: int,
    recordname: str,
) -> Union[Any, List[float]]:
    """
    Parse an opm.libopmcommon_python.DeckRecord belonging to a
    certain keyword and return as list of numbers

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
    index_values_list: Union[np.ndarray, List[List[float]]],
    flow_values_list: Union[np.ndarray, List[float]],
    table_values_list: Union[np.ndarray, List[List[float]]],
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


def _write_vfp_range(
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


def _ecl_unit_system(
    deck: Union[str, EclFiles, "opm.libopmcommon_python.Deck"]
) -> UNITTYPE:
    """Extract Eclipse unit system definition from Eclipse deck.
       The unit system in Eclipse should be one of
       "METRIC", "FIELD", "LAB" or "PVT-M" and the corresponding
       Enum type METRIC, FIELD, LAB or PVT-M is returned
       If unit system not found METRIC unit system is returned
       as default.

    Args:
        deck: Eclipse deck or string with deck
    """
    
    ecl_deck = deck
    if isinstance(deck, EclFiles):
        ecl_deck = deck.get_ecldeck()
    elif isinstance(deck, str):
        ecl_deck = EclFiles.str2deck(deck)

    for keyword in ecl_deck:
        if keyword.name in ["METRIC", "FIELD", "LAB", "PVT-M"]:
            return UNITTYPE[keyword.name]
    return UNITTYPE.DEFAULT


def _unique_vfps(
    vfps: Union[List[pd.DataFrame], List[pa.Table]]
) -> Union[List[pd.DataFrame], List[pa.Table]]:
    """Extract list of VFPs with unique VFP number from original list of VFPs.
    If same VFP number is used for several curves, the last curve is included
    in the list returned.

    Args:
        vfps: list of VFP curves as DataFrames of pyarrow.Table
    """

    vfp_numbers = []
    for vfp in vfps:
        if isinstance(vfp, pd.DataFrame):
            vfp_number = vfp["TABLE_NUMBER"].unique()
            vfp_numbers.append(vfp_number[0])
        elif isinstance(vfp, pa.Table):
            vfp_number = int(vfp.schema.metadata[b"TABLE_NUMBER"].decode("utf-8"))
            vfp_numbers.append(vfp_number)

    vfp_unique_numbers = []
    vfp_duplicate_numbers = []
    for n, vfp_number in enumerate(vfp_numbers):
        if vfp_number in vfp_numbers[(n + 1) :]:  # noqa: E203
            vfp_duplicate_numbers.append(vfp_number)
            vfp_unique_numbers.append(-1)
        else:
            vfp_unique_numbers.append(vfp_number)

    vfps_unique = []
    for n, vfp in enumerate(vfps):
        if vfp_unique_numbers[n] > -1:
            vfps_unique.append(vfp)

    if len(vfp_duplicate_numbers) > 0:
        logger.warning(
            (
                f"The following VFP numbers are used "
                f"for more than one VFP table: "
                f"{*vfp_duplicate_numbers,}"
            )
        )

    return vfps_unique

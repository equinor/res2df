"""Define table index from tagname"""
import logging
from typing import Union
from pandas import DataFrame
from pyarrow import Table


DEFINITIONS = {
    "summary": ["DATE"],
    "equil": ["EQLNUM"],
    "compdat": ["WELL", "DATE", "DIR"],
    "faults": ["NAME", "FACE"],
    "grid": ["GLOBAL_INDEX", "I", "J", "K"],
    "pillars": ["PILLAR"],
    "pvt": ["PVTNUM", "KEYWORD"],
    "rft": ["WELL", "DATE", "DEPTH"],
    "satfunc": ["SATNUM", "KEYWORD"],
    "wellcompletiondata": ["WELL", "DATE", "ZONE"],
}

logger = logging.getLogger(__name__)


def assign_table_index(tagname: str, table: Union[DataFrame, Table]):
    """Assign table index based on tagname

    Args:
        tagname (str): name of tagname (aka submodule name)
        table (Union[DataFrame, Table]): the table connected to table_index

    Returns:
        list: list of columns that are in table_index
    """
    if tagname not in DEFINITIONS:
        table_index = []
    else:
        table_index = DEFINITIONS[tagname]
    logger.debug("Submodule: %s, table_index: %s", tagname, table_index)

    try:
        # Some datatypes the index is
        available_columns = table.copy().reset_index().columns

    except AttributeError:
        available_columns = table.column_names

    for col_name in table_index:
        if col_name not in available_columns:
            table_index.remove(col_name)
    logger.debug("After removing table index is %s", table_index)
    return table_index

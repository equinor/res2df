"""
Common functions for ecl2df modules
"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
import pandas as pd

import logging
import pandas as pd


def parse_ecl_month(eclmonth):
    eclmonth2num = {
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "JLY": 7,
        "AUG": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DEC": 12,
    }
    return eclmonth2num[eclmonth]


def merge_zones(df, zonedict, zoneheader="ZONE", kname="K1"):
    """Merge in a column with zone names, from a dictionary mapping
    k-index to zone name

    Args:
        df (pd.DataFrame): Dataframe where we should augment a column
        zonedict (dict): Dictionary with integer keys pointing to strings
            with zone names.
        zoneheader (str): Name of the result column merged in,
            default: ZONE
        kname (str): Column header in your dataframe that maps to dictionary keys.
            default K1
    """
    assert isinstance(zonedict, dict)
    assert isinstance(zoneheader, str)
    assert isinstance(kname, str)
    assert isinstance(df, pd.DataFrame)
    if not zonedict:
        logging.warning("Can't merge in empty zone information")
        return df
    if zoneheader in df:
        logging.error(
            "Column name %s already exists, refusing to merge in any more", zoneheader
        )
        return df
    if kname not in df:
        logging.error("Can't merge on non-existing column %s", kname)
        return df
    zone_df = pd.DataFrame.from_dict(zonedict, orient="index", columns=[zoneheader])
    zone_df.index.name = "K"
    zone_df.reset_index(inplace=True)
    return pd.merge(df, zone_df, left_on=kname, right_on="K")

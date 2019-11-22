"""
Common functions for ecl2df modules
"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
import json
import logging
import datetime

import pandas as pd

# Parse named JSON files, this exposes a dict of dictionary describing the contents
# of supported Eclipse keyword data
OPMKEYWORDS = {}
for keyw in [
    "COMPDAT",
    "COMPSEGS",
    "EQUIL",
    "FAULTS",
    "WELSPECS",
    "WELSEGS",
    "WCONPROD",
    "WCONHIST",
    "WCONINJE",
    "WCONINJH",
    "GRUPTREE",
    "GRUPNET",
]:
    OPMKEYWORDS[keyw] = json.load(
        open(os.path.join(os.path.dirname(__file__), "opmkeywords", keyw))
    )


logging.basicConfig()
logger = logging.getLogger(__name__)


def parse_ecl_month(eclmonth):
    """Translate Eclipse month strings to integer months"""
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


def parse_opmio_deckrecord(
    record, keyword, itemlistname="items", recordindex=None, renamer=None
):
    """
    Parse an opm.io.DeckRecord belonging to a certain keyword

    Args:
        record (opm.libopmcommon_python.DeckRecord): Record be parsed
        keyword (string): Which Eclipse keyword this belongs to
        itemlistname (string): The key in the json dict that describes the items,
            typically 'items' or 'records'
        recordindex (int): For keywords where itemlistname is 'records', this is a
            list index to the "record"
            Beware, there are multiple concepts here for what we call a record.
        renamer (dict): If supplied, this dictionary will be used to remap
            the keys in returned dict
    Returns:
        dict
    """
    if keyword not in OPMKEYWORDS:
        logging.error("Keyword %s not supported by common.py", str(keyword))

    # opm.io deckitem access functions, depending on value_type in json data for item:
    deckitem_fn = {
        "STRING": "get_str",
        "INT": "get_int",
        "DOUBLE": "get_raw",
        "UDA": "get_raw",  # Does not work. Is UDA unsupported in opm.io??
    }
    rec_dict = {}

    if recordindex is None:  # Beware, 0 is different from None here.
        itemlist = OPMKEYWORDS[keyword][itemlistname]
    else:
        itemlist = OPMKEYWORDS[keyword][itemlistname][recordindex]

    for item_idx, jsonitem in enumerate(itemlist):
        item_name = jsonitem["name"]
        if not record[item_idx].defaulted(0):
            rec_dict[item_name] = getattr(
                record[item_idx], deckitem_fn[jsonitem["value_type"]]
            )(0)
        else:
            if "default" in jsonitem:
                rec_dict[item_name] = jsonitem["default"]
            else:
                rec_dict[item_name] = None
    if renamer:
        renamed_dict = {}
        for key in rec_dict:
            if key in renamer:
                renamed_dict[renamer[key]] = rec_dict[key]
            else:
                renamed_dict[key] = rec_dict[key]
        return renamed_dict
    return rec_dict


def parse_opmio_date_rec(record):
    """
    Parse a opm.io.DeckRecord under a DATES or START keyword in a deck.

    Return:
        datetime.date
    """
    day = record[0].get_int(0)
    month = record[1].get_str(0)
    year = record[2].get_int(0)
    return datetime.date(year=year, month=parse_ecl_month(month), day=day)


def parse_opmio_tstep_rec(record):
    """Parse a record with TSTEP data

    Return:
        list of floats or ints
    """
    return record[0].get_raw_data_list()


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
        logger.warning("Can't merge in empty zone information")
        return df
    if zoneheader in df:
        logger.error(
            "Column name %s already exists, refusing to merge in any more", zoneheader
        )
        return df
    if kname not in df:
        logger.error("Can't merge on non-existing column %s", kname)
        return df
    zone_df = pd.DataFrame.from_dict(zonedict, orient="index", columns=[zoneheader])
    zone_df.index.name = "K"
    zone_df.reset_index(inplace=True)
    return pd.merge(df, zone_df, left_on=kname, right_on="K")


def stack_on_colnames(dframe, sep="@", stackcolname="DATE", inplace=True):
    """For a dataframe where some columns are multilevel, but where
    the second level is encoded in the column name, this function
    will stack the dataframe by putting the second level of the column
    multiindex into its own column, best understood by this example:

    A dframe like this

       ===== =============== ==============
       PORV   OWC@2000-01-01 OWC@2020-01-01
       ===== =============== ==============
       100       1000          990
       ===== =============== ==============

    will be stacked to

       ====  ====  ==========
       PORV  OWC   DATE
       ====  ====  ==========
       100   1000  2000-01-01
       100   990   2020-01-01
       ====  ====  ==========

    (for the defaults values for *sep* and *stackcolname*)

    Column order is not guaranteed

    Args:
        dframe (pd.DataFrame): A dataframe to stack
        sep (str): The separator that is used in dframe.columns to define
            the multilevel column names.
        stackcolname (str): Used as column name for the second level
            of the column multiindex

    Returns:
        pd.DataFrame
    """
    if not inplace:
        dframe = pd.DataFrame(dframe)
    tuplecolumns = list(map(lambda x: tuple(x.split(sep)), dframe.columns))
    if max(map(len, tuplecolumns)) < 2:
        logger.info("No columns to stack")
        return dframe
    dframe.columns = pd.MultiIndex.from_tuples(
        tuplecolumns, names=["dummy", stackcolname]
    )
    dframe = dframe.stack()
    staticcols = [col[0] for col in tuplecolumns if len(col) == 1]
    dframe[staticcols] = dframe[staticcols].fillna(method="ffill")
    dframe.reset_index(inplace=True)
    # Drop rows stemming from the NaNs in the second tuple-element for
    # static columns:
    dframe.dropna(axis="index", subset=["DATE"], inplace=True)
    del dframe["level_0"]
    dframe.index.name = ""
    return dframe

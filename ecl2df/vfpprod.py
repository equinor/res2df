"""
Extract the VFPPROD data from an Eclipse (input) deck as Pandas Dataframes

Data can be extracted from a full Eclipse deck or from individual files.
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union
import pandas as pd
import numbers

try:
    # Needed for mypy

    # pylint: disable=unused-import
    import opm.io
except ImportError:
    pass

from ecl2df import EclFiles, common, getLogger_ecl2csv
from my_common import (
    parse_opmio_date_rec,
    parse_opmio_deckrecord,
    parse_opmio_tstep_rec,
    write_dframe_stdout_file,
)

from opm.io.deck import DeckKeyword

logger = logging.getLogger(__name__)

SUPPORTED_KEYWORDS: List[str] = [
    "VFPPROD",
]

# The renamers listed here map from opm-common json item names to
# desired column names in produced dataframes. They also to a certain
# extent determine the structure of the dataframe, in particular
# for keywords with arbitrary data amount pr. record (GAS, THP, WGR, GOR f.ex)
RENAMERS: Dict[str, Dict[str, Union[str, List[str]]]] = {}

def vfpprod2df(keyword: DeckKeyword)->pd.DataFrame:
    num_rec = len(keyword)

    basic_record = parse_opmio_deckrecord(keyword[0],'VFPPROD','records',0)
    flow_record  = parse_opmio_deckrecord(keyword[1],'VFPPROD','records',1)
    thp_record   = parse_opmio_deckrecord(keyword[2],'VFPPROD','records',2)
    wfr_record   = parse_opmio_deckrecord(keyword[3],'VFPPROD','records',3)
    gfr_record   = parse_opmio_deckrecord(keyword[4],'VFPPROD','records',4)
    alq_record   = parse_opmio_deckrecord(keyword[5],'VFPPROD','records',5)
    
    table = basic_record["TABLE"]
    datum = basic_record["DATUM_DEPTH"]
    rate  = basic_record["RATE_TYPE"]
    wfr = basic_record["WFR"]
    gfr = basic_record["GFR"]
    thp = basic_record["PRESSURE_DEF"]
    alq = basic_record["ALQ_DEF"]
    units = basic_record["UNITS"]
    tab  = basic_record["BODY_DEF"]

    bhp_array_values = []
    for n in range(6,num_rec):
        bhp_record = parse_opmio_deckrecord(keyword[n],'VFPPROD','records',6)
        bhp_record_values = [bhp_record["THP_INDEX"]] + [bhp_record["WFR_INDEX"]] + [bhp_record["GFR_INDEX"]] + [bhp_record["ALQ_INDEX"]] + bhp_record["VALUES"]
        bhp_array_values.append(bhp_record_values)

    bhp_values = pd.DataFrame(bhp_array_values)
    if isinstance(thp_record.get('THP_VALUES'),list):
        bhp_values[0] = [thp_record.get('THP_VALUES')[int(x) - 1] for x in bhp_values[0]]
    elif isinstance(thp_record.get('THP_VALUES'),numbers.Number):
        bhp_values[0] = [thp_record.get('THP_VALUES') for x in bhp_values[0]]
    if isinstance(wfr_record.get('WFR_VALUES'),list):
        bhp_values[1] = [wfr_record.get('WFR_VALUES')[int(x) - 1] for x in bhp_values[1]]
    elif isinstance(wfr_record.get('WFR_VALUES'),numbers.Number):
        bhp_values[1] = [wfr_record.get('WFR_VALUES') for x in bhp_values[1]]
    if isinstance(gfr_record.get('GFR_VALUES'),list):
        bhp_values[2] = [gfr_record.get('GFR_VALUES')[int(x) - 1] for x in bhp_values[2]]
    elif isinstance(gfr_record.get('GFR_VALUES'),numbers.Number):
        bhp_values[2] = [gfr_record.get('GFR_VALUES') for x in bhp_values[2]]
    if isinstance(alq_record.get('ALQ_VALUES'),list):
        bhp_values[3] = [alq_record.get('ALQ_VALUES')[int(x)-1] for x in bhp_values[3]]
    elif isinstance(alq_record.get('ALQ_VALUES'),numbers.Number):
        bhp_values[3] = [alq_record.get('ALQ_VALUES') for x in bhp_values[3]]

    if alq:
        alq = "-" + alq
    indextuples = [(thp, ""), (wfr, ""), (gfr, ""), ("ALQ" + alq, "")]

    for flowvalue in flow_record["FLOW_VALUES"]:
        indextuples.append(("BHP", flowvalue))

    # Set the columns to a MultiIndex, to facilitate stacking
    bhp_values.columns = pd.MultiIndex.from_tuples(indextuples)

    # Now stack
    bhp_values_stacked = bhp_values.stack()

    # In order to propagate the gfr, thp, wct values after
    # stacking to the correct rows, we should either understand
    # how to do that properly using pandas, but for now, we try a
    # backwards fill, hopefully that is robust enough
    bhp_values_stacked.bfill(inplace=True)
    # Also reset the index:
    bhp_values_stacked.reset_index(inplace=True)
    bhp_values_stacked.drop("level_0", axis="columns", inplace=True)
    # This column is not meaningful (it is the old index)

    # Delete rows that does not belong to any flow rate (this is
    # possibly a by-product of not doing the stacking in an
    # optimal way)
    bhp_values_stacked = bhp_values_stacked[bhp_values_stacked["level_1"] != ""]

    # Add correct column name for the flow values that we have stacked
    cols = list(bhp_values_stacked.columns)
    cols[0] = rate
    bhp_values_stacked.columns = cols

    # Add meta-data
    bhp_values_stacked["VFPTYPE"] = 'VFPPROD'
    bhp_values_stacked["TABLENUMBER"] = int(table)
    bhp_values_stacked["DATUM"] = float(datum)
    bhp_values_stacked["UNITS"] = units
    bhp_values_stacked["TABTYPE"] = tab

#    bhp_values_stacked["FILENAME"] = filename

    return bhp_values_stacked


def df(deck: Union[EclFiles, "opm.libopmcommon_python.Deck"]) -> pd.DataFrame:
    """Produce a dataframe of fault data from a deck

    All data for the keyword VFPPROD will be returned.

    Args:
        deck: Eclipse deck
    """
    if isinstance(deck, EclFiles):
        deck = deck.get_ecldeck()

    dfs_vfpprod = []
    # The keyword VFPPROD can be used many times in Eclipse and be introduced in 
    # separate files or a common file. Need to loop to find all instances of keyword
    for keyword in deck:
        if keyword.name in SUPPORTED_KEYWORDS:
            dfs_vfpprod.append(vfpprod2df(keyword))

    df_vfpprods = pd.concat(dfs_vfpprod)
    return df_vfpprods


def vfpprodfile2df(
        vfp_filename: str = "",
) -> pd.DataFrame:
    """Return a dataframe with vfp table by reading from file##

    The dataframe will have a indices corresponding to values that are interpolated
    (WGR, WCT, GOR, ...). Column correspond to different rates (GAS, OIL)

    """
    deck = EclFiles(vfp_filename)
    if isinstance(deck, EclFiles):
        deck = deck.get_ecldeck()
    if deck[0] in SUPPORTED_KEYWORDS:
        vfpprod = vfpprod2df(deck[0])
        return vfpprod
    else:
        return None


deck = EclFiles("/scratch/asg-ptc02/smb/rhold/smb_22.0.0_20220501_ahm/realization-0/iter-0/eclipse/model/SMB_HISTORY-0.DATA")
if isinstance(deck, EclFiles):
        deck = deck.get_ecldeck()

vfpprod_df = []
vfpinj_df = []
for keyword in deck:
    if keyword.name in SUPPORTED_KEYWORDS:
        vfpprod_df.append(vfpprod2df(keyword))
print(vfpprod_df[0])

                         
                   

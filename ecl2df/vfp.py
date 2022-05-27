"""
Extract the VFPPROD/VFPINJ data from an Eclipse (input) deck as Pandas Dataframes

Data can be extracted from a full Eclipse deck or from individual files.
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union
import pandas as pd
import numbers
from enum import Enum

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
    'VFPPROD',
    'VFPINJ',
]

# The renamers listed here map from opm-common json item names to
# desired column names in produced dataframes. They also to a certain
# extent determine the structure of the dataframe, in particular
# for keywords with arbitrary data amount pr. record (GAS, THP, WGR, GOR f.ex)
RENAMERS: Dict[str, Dict[str, Union[str, List[str]]]] = {}

# Type of VFP curve
class VFPTYPE(Enum):
    VFPPROD = 'VFPPROD'
    VFPINJ  = 'VFPINJ'

# Flow rate variable types for VFPPROD
class VFPPROD_FLO(Enum):
    OIL = 'OIL'
    LIQ = 'LIQ'
    GAS = 'GAS'
    WG  = 'WG'
    TM  = 'TM'

# Flow rate variable types for VFPINJ
class VFPINJ_FLO(Enum):
    OIL = 'OIL'
    WAT = 'WAT'
    GAS = 'GAS'
    WG  = 'WG'
    TM  = 'TM'

# Water fraction types for VFPPROD
class WFR(Enum):
    WOR = 'WOR'
    WCT = 'WCT'
    WGR = 'WGR'
    WWR = 'WWR'
    WTF = 'WTF'

# Gas fraction types for VFPPROD
class GFR(Enum):
    GOR = 'GOR'
    GLR = 'GLR'
    OGR = 'OGR'
    MMW = 'MMW'

# Artificial lift types for VFPPROD
class ALQ(Enum):
    GRAT = 'GRAT'
    IGLR = 'IGLR'
    TGLR = 'TGLR'
    PUMP = 'PUMP'
    COMP = 'COMP'
    DENO = 'DENO'
    DENG = 'DENG'
    BEAN = 'BEAN'
    UNDEFINED = 'UNDEFINED'

# Unit types
class UNITTYPE(Enum):
    METRIC  = 'METRIC'
    FIELD   = 'FIELD'
    LAB     = 'LAB'
    PVTM    = 'PVT-M'
    DEFAULT = 'DEFAULT'

# THP types supported
class THPTYPE(Enum):
    THP = 'THP'

# Tabulated values types for VFPPROD
class VFPPROD_TABTYPE(Enum):
    BHP  = 'BHP'
    THT  = 'THT'

# Tabulated values types for VFPINJ
class VFPINJ_TABTYPE(Enum):
    BHP  = 'BHP'

# Unit definitions for VFPPROD
VFPPROD_UNITS = { 'METRIC': { 'FLO': {'OIL': 'sm3/day',
                                      'LIQ': 'sm3/day',
                                      'GAS': 'sm3/day',
                                      'WG' : 'sm3/day',
                                      'TM' : 'kg-M/day'},
                              'THP': {'THP': 'barsa'},
                              'WFR': {'WOR': 'sm3/sm3',
                                      'WCT': 'sm3/sm3',
                                      'WGR': 'sm3/sm3',
                                      'WWR': 'sm3/sm3',
                                      'WTF': ''},
                              'GFR': {'GOR': 'sm3/sm3',
                                      'GLR': 'sm3/sm3',
                                      'OGR': 'sm3/sm3',
                                      'MMW': 'kg/kg-M'},
                              'ALQ': {'GRAT': 'sm3/day',
                                      'IGLR': 'sm3/sm3',
                                      'TGLR': 'sm3/sm3',
                                      'DENO': 'kg/m3',
                                      'DENG': 'kg/m3',
                                      'BEAN': 'mm',
                                      "''"  : ''}},
                  'FIELD': { 'FLO': {'OIL': 'stb/day',
                                     'LIQ': 'stb/day',
                                     'GAS': 'Mscf/day',
                                     'WG' : 'lb-M/day',
                                     'TM' : 'lb-M/day'},
                             'THP': {'THP': 'psia'},
                             'WFR': {'WOR': 'stb/stb',
                                     'WCT': 'stb/stb',
                                     'WGR': 'stb/Mscf',
                                     'WWR': 'stb/Mscf',
                                     'WTF': ''},
                             'GFR': {'GOR': 'Mscf/stb',
                                     'GLR': 'Mscf/stb',
                                     'OGR': 'stb/Mscf',
                                     'MMW': 'lb/lb-M'},
                             'ALQ': {'GRAT': 'Mscf/day',
                                     'IGLR': 'Mscf/stb',
                                     'TGLR': 'Mscf/stb',
                                     'DENO': 'lb/ft3',
                                     'DENG': 'lb/ft3',
                                     'BEAN': '1/64',
                                     "''"  : ''}},
                  'LAB':   { 'FLO': {'OIL': 'scc/hr',
                                     'LIQ': 'scc/hr',
                                     'GAS': 'scc/hr',
                                     'WG' : 'scc/hr',
                                     'TM' : 'lb-M/day'},
                             'THP': {'THP': 'atma'},
                             'WFR': {'WOR': 'scc/scc',
                                     'WCT': 'scc/scc',
                                     'WGR': 'scc/scc',
                                     'WWR': 'scc/scc',
                                     'WTF': ''},
                             'GFR': {'GOR': 'scc/scc',
                                     'GLR': 'scc/scc',
                                     'OGR': 'scc/scc',
                                     'MMW': 'lb/lb-M'},
                             'ALQ': {'GRAT': 'scc/hr',
                                     'IGLR': 'scc/scc',
                                     'TGLR': 'scc/scc',
                                     'DENO': 'gm/cc',
                                     'DENG': 'gm/cc',
                                     'BEAN': 'mm',
                                     "''"  : ''}},          
                  'PVT-M': { 'FLO': {'OIL': 'sm3/day',
                                     'LIQ': 'sm3/day',
                                     'GAS': 'sm3/day',
                                     'WG' : 'sm3/day',
                                     'TM' : 'kg-M/day'},
                             'THP': {'THP': 'atma'},
                             'WFR': {'WOR': 'sm3/sm3',
                                     'WCT': 'sm3/sm3',
                                     'WGR': 'sm3/sm3',
                                     'WWR': 'sm3/sm3',
                                     'WTF': ''},
                             'GFR': {'GOR': 'sm3/sm3',
                                     'GLR': 'sm3/sm3',
                                     'OGR': 'sm3/sm3',
                                     'MMW': 'kg/kg-M'},
                             'ALQ': {'GRAT': 'sm3/day',
                                     'IGLR': 'sm3/sm3',
                                     'TGLR': 'sm3/sm3',
                                     'DENO': 'kg/m3',
                                     'DENG': 'kg/m3',
                                     'BEAN': 'mm',
                                     "''"  : '',}}}                                       

# Unit definitions for VFPINJ
VFPINJ_UNITS = { 'METRIC': { 'FLO': {'OIL': 'sm3/day',
                                     'WAT': 'sm3/day',
                                     'GAS': 'sm3/day',
                                     'WG' : 'sm3/day',
                                     'TM' : 'kg-M/day'},
                             'THP': {'THP': 'barsa'}},
                 'FIELD':  { 'FLO': {'OIL': 'stb/day',
                                     'WAT': 'stb/day',
                                     'GAS': 'Mscf/day',
                                     'WG' : 'Mscf/day',
                                     'TM' : 'lb-M/day'},
                             'THP': {'THP': 'psia'}},
                 'LAB':    { 'FLO': {'OIL': 'scc/hr',
                                     'WAT': 'scc/hr',
                                     'GAS': 'scc/hr',
                                     'WG' : 'scc/hr',
                                     'TM' : 'gm-M/hr'},
                             'THP': {'THP': 'atma'}},
                 'PVT-M':  { 'FLO': {'OIL': 'sm3/day',
                                     'WAT': 'sm3/day',
                                     'GAS': 'sm3/day',
                                     'WG' : 'sm3/day',
                                     'TM' : 'kg-M/day'},
                             'THP': {'THP': 'atma'}}}
                 

# Dicitionaries for type definitions that are different for VFPPROD and VFPINJ
FLO = { VFPTYPE.VFPPROD: VFPPROD_FLO, VFPTYPE.VFPINJ : VFPINJ_FLO }
UNITS = { VFPTYPE.VFPPROD: VFPPROD_UNITS, VFPTYPE.VFPINJ : VFPINJ_UNITS }
TABTYPE = { VFPTYPE.VFPPROD: VFPPROD_TABTYPE, VFPTYPE.VFPINJ : VFPINJ_TABTYPE }

"""Return a dataframes of a single VFPPROD table from an Eclipse deck
   Data from the VFPPROD keyword are stacked into a Pandas Dataframe

    Args:
        deck:    Eclipse deck
    """
def vfpprod2df(keyword: DeckKeyword)->pd.DataFrame:
    num_rec = len(keyword)

    # Parse records with basic information and interpolation ranges
    basic_record = parse_opmio_deckrecord(keyword[0],'VFPPROD','records',0)
    flow_record  = parse_opmio_deckrecord(keyword[1],'VFPPROD','records',1)
    thp_record   = parse_opmio_deckrecord(keyword[2],'VFPPROD','records',2)
    wfr_record   = parse_opmio_deckrecord(keyword[3],'VFPPROD','records',3)
    gfr_record   = parse_opmio_deckrecord(keyword[4],'VFPPROD','records',4)
    alq_record   = parse_opmio_deckrecord(keyword[5],'VFPPROD','records',5)

    # Extract interpolation ranges
    flow_values = []
    if isinstance(flow_record.get('FLOW_VALUES'),list):
        flow_values = flow_record.get('FLOW_VALUES')
    elif isinstance(flow_record.get('FLOW_VALUES'),numbers.Number):
        flow_values = [flow_record.get('FLOW_VALUES')]
    thp_values = []
    if isinstance(thp_record.get('THP_VALUES'),list):
        thp_values = thp_record.get('THP_VALUES')
    elif isinstance(thp_record.get('THP_VALUES'),numbers.Number):
        thp_values = [thp_record.get('THP_VALUES')]
    wfr_values = []
    if isinstance(wfr_record.get('WFR_VALUES'),list):
        wfr_values = wfr_record.get('WFR_VALUES')
    elif isinstance(wfr_record.get('WFR_VALUES'),numbers.Number):
        wfr_values = [wfr_record.get('WFR_VALUES')]
    gfr_values = []
    if isinstance(gfr_record.get('GFR_VALUES'),list):
        gfr_values = gfr_record.get('GFR_VALUES')
    elif isinstance(gfr_record.get('GFR_VALUES'),numbers.Number):
        gfr_values = [gfr_record.get('GFR_VALUES')]
    alq_values = []
    if isinstance(alq_record.get('ALQ_VALUES'),list):
        alq_values = alq_record.get('ALQ_VALUES')
    elif isinstance(alq_record.get('ALQ_VALUES'),numbers.Number):
        alq_values = [alq_record.get('ALQ_VALUES')]

    # Extract basic table information
    table = int(basic_record['TABLE'])
    datum = float(basic_record['DATUM_DEPTH'])
    rate  = VFPPROD_FLO[basic_record['RATE_TYPE']]
    wfr = WFR[basic_record['WFR']]
    gfr = GFR[basic_record['GFR']]
    thp = THPTYPE[basic_record['PRESSURE_DEF']]
    alq = ALQ.UNDEFINED
    if  basic_record['ALQ_DEF'].strip():
        alq = ALQ[basic_record['ALQ_DEF']]
    units = UNITTYPE[basic_record['UNITS']]
    tab  = VFPPROD_TABTYPE[basic_record['BODY_DEF']]

    # Extract tabulated values (BHP values)
    bhp_array_values = []
    for n in range(6,num_rec):
        bhp_record = parse_opmio_deckrecord(keyword[n],'VFPPROD','records',6)
        bhp_values = []
        if isinstance(bhp_record.get('VALUES'),list):
            bhp_values = bhp_record.get('VALUES')
        elif isinstance(bhp_record.get('VALUES'),numbers.Number):
            bhp_values = [bhp_record.get('VALUES')]

        thp_index = bhp_record['THP_INDEX']-1
        wfr_index = bhp_record['WFR_INDEX']-1
        gfr_index = bhp_record['GFR_INDEX']-1
        alq_index = bhp_record['ALQ_INDEX']-1

        thp_value = thp_values[thp_index]
        wfr_value = wfr_values[wfr_index]
        gfr_value = gfr_values[gfr_index]
        alq_value = alq_values[alq_index]

        bhp_record_values = [thp_value] + [wfr_value] + [gfr_value] + [alq_value] + bhp_values
        bhp_array_values.append(bhp_record_values)

    df_bhp = pd.DataFrame(bhp_array_values)

    indextuples = [('THP', 'DELETE'), ('WFR', 'DELETE'), ('GFR', 'DELETE'), ('ALQ', 'DELETE')]
    for flowvalue in flow_values:
        indextuples.append(('TAB', flowvalue))

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
    df_bhp_stacked.drop('level_0', axis='columns', inplace=True)
    # This column is not meaningful (it is the old index)

    # Delete rows that does not belong to any flow rate (this is
    # possibly a by-product of not doing the stacking in an
    # optimal way)
    df_bhp_stacked = df_bhp_stacked[df_bhp_stacked['level_1'] != 'DELETE']

    # Add correct column name for the flow values that we have stacked
    cols = list(df_bhp_stacked.columns)
    cols[cols.index('level_1')] = 'RATE'
    df_bhp_stacked.columns = cols

    # Add meta-data
    df_bhp_stacked['VFP_TYPE'] = 'VFPPROD'
    df_bhp_stacked['TABLE_NUMBER'] = table
    df_bhp_stacked['DATUM'] = datum
    df_bhp_stacked['UNIT_TYPE'] = units.value
    df_bhp_stacked['RATE_TYPE'] = rate.value
    df_bhp_stacked['WFR_TYPE'] = wfr.value
    df_bhp_stacked['GFR_TYPE'] = gfr.value
    df_bhp_stacked['ALQ_TYPE'] = alq.value
    df_bhp_stacked['TAB_TYPE'] = tab.value

    # Sort the columns in wanted order
    df_bhp_stacked = df_bhp_stacked[['RATE',
                                     'THP',
                                     'WFR',
                                     'GFR',
                                     'ALQ',
                                     'TAB',
                                     'VFP_TYPE',
                                     'TABLE_NUMBER',
                                     'DATUM',
                                     'RATE_TYPE',
                                     'WFR_TYPE',
                                     'GFR_TYPE',
                                     'ALQ_TYPE',
                                     'TAB_TYPE',
                                     'UNIT_TYPE']]

    print(df_bhp_stacked)
    return df_bhp_stacked

"""Return a dataframes of a single VFPINJ table from an Eclipse deck
   Data from the VFPINJ keyword are stacked into a Pandas Dataframe

    Args:
        deck:    Eclipse deck
    """
def vfpinj2df(keyword: DeckKeyword)->pd.DataFrame:
    num_rec = len(keyword)

    # Parse records with basic information and interpolation ranges
    basic_record = parse_opmio_deckrecord(keyword[0],'VFPINJ','records',0)
    flow_record  = parse_opmio_deckrecord(keyword[1],'VFPINJ','records',1)
    thp_record   = parse_opmio_deckrecord(keyword[2],'VFPINJ','records',2)
    
    # Extract interpolation ranges
    flow_values = []
    if isinstance(flow_record.get('FLOW_VALUES'),list):
        flow_values = flow_record.get('FLOW_VALUES')
    elif isinstance(flow_record.get('FLOW_VALUES'),numbers.Number):
        flow_values = [flow_record.get('flow_VALUES')]
    thp_values = []
    if isinstance(thp_record.get('THP_VALUES'),list):
        thp_values = thp_record.get('THP_VALUES')
    elif isinstance(thp_record.get('THP_VALUES'),numbers.Number):
        thp_values = [thp_record.get('THP_VALUES')]

    # Extract basic table information
    table = basic_record['TABLE']
    datum = basic_record['DATUM_DEPTH']
    rate  = VFPINJ_FLO[basic_record['RATE_TYPE']]
    print(basic_record['UNITS'])
    thp = THPTYPE[basic_record['PRESSURE_DEF']]
    if basic_record['PRESSURE_DEF']:
        units = UNITTYPE.DEFAULT
    else:
        units = UNITTYPE[basic_record['UNITS']]
    if basic_record['BODY_DEF']:
        tab = VFPINJ_TABTYPE.BHP
    else:
        tab  = VFPINJ_TABTYPE[basic_record['BODY_DEF']]

    # Extract tabulated values (BHP values)    
    bhp_array_values = []
    for n in range(3,num_rec):
        bhp_record = parse_opmio_deckrecord(keyword[n],'VFPINJ','records',3)
        bhp_values = []
        if isinstance(bhp_record.get('VALUES'),list):
            bhp_values = bhp_record.get('VALUES')
        elif isinstance(bhp_record.get('VALUES'),numbers.Number):
            bhp_values = [bhp_record.get('VALUES')]

        thp_index = bhp_record['THP_INDEX']-1
        thp_value = thp_values[thp_index]

        bhp_record_values = [thp_value] + bhp_values
        bhp_array_values.append(bhp_record_values)

    df_bhp = pd.DataFrame(bhp_array_values)

    indextuples = [('THP', 'DELETE')]

    for flowvalue in flow_values:
        indextuples.append(('TAB', flowvalue))

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
    df_bhp_stacked.drop('level_0', axis='columns', inplace=True)
    # This column is not meaningful (it is the old index)

    # Delete rows that does not belong to any flow rate (this is
    # possibly a by-product of not doing the stacking in an
    # optimal way)
    df_bhp_stacked = df_bhp_stacked[df_bhp_stacked['level_1'] != 'DELETE']

    # Add correct column name for the flow values that we have stacked
    cols = list(df_bhp_stacked.columns)
    cols[cols.index('level_1')] = 'RATE'
    df_bhp_stacked.columns = cols

    # Add meta-data
    df_bhp_stacked['VFP_TYPE'] = 'VFPINJ'
    df_bhp_stacked['TABLE_NUMBER'] = int(table)
    df_bhp_stacked['DATUM'] = float(datum)
    df_bhp_stacked['UNIT_TYPE'] = units.value
    df_bhp_stacked['RATE_TYPE'] = rate.value
    df_bhp_stacked['TAB_TYPE'] = tab.value

    # Sort the columns in wanted order
    df_bhp_stacked = df_bhp_stacked[['RATE',
                                     'THP',
                                     'TAB',
                                     'VFP_TYPE',
                                     'TABLE_NUMBER',
                                     'DATUM',
                                     'RATE_TYPE',
                                     'TAB_TYPE',
                                     'UNIT_TYPE']]

    return df_bhp_stacked

def dfs(deck: Union[EclFiles, 'opm.libopmcommon_python.Deck'], vfptype: Optional[str] = None) -> List[pd.DataFrame]:
    """Produce a list of dataframes of vfp tables from a deck

    Data for the keywords VFPPROD/VFPINJ will be returned as separate item in list

    Args:
        deck:    Eclipse deck
        vfptype: VFP table type, i.e. 'VFPPROD' or 'VFPINJ'. Default VFPPROD and VFPINJ
    """
    if isinstance(deck, EclFiles):
        deck = deck.get_ecldeck()

    vfptype_list = ['VFPPROD','VFPINJ']
    if vfptype:
        vfptype_list = [vfptype]

    dfs_vfp = []
    # The keywords VFPPROD/VFPINJ can be used many times in Eclipse and be introduced in 
    # separate files or a common file. Need to loop to find all instances of keyword
    for keyword in deck:
        if keyword.name in vfptype_list:
            if keyword.name == 'VFPPROD':
                dfs_vfp.append(vfpprod2df(keyword))
            elif keyword.name == 'VFPINJ':
                dfs_vfp.append(vfpinj2df(keyword))

    return dfs_vfp

def df(deck: Union[EclFiles, 'opm.libopmcommon_python.Deck'],vfptype:Optional[str] = None) -> pd.DataFrame:
    """Produce a dataframes of all vfp tables from a deck

    All data for the keywords VFPPROD/VFPINJ will be returned.

    Args:
        deck:    Eclipse deck
        vfptype: VFP table type, i.e. 'VFPPROD' or 'VFPINJ'. Default VFPPROD and VFPINJ
    """
    # Extract all VFPROD/VFPINJ as separate dataframes
    dfs_vfp = dfs(deck,vfptype)
    # Concat all dataframes into one dataframe
    df_vfps = pd.concat(dfs_vfp)
    return df_vfps

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
        "-p",
        "--prettyprint",
        action="store_true",
        help="Pretty-print the VFP dataframes",
    )
    parser.add_argument(
        "-t"
        "--vfptype",
        type=str,
        help="VFP type to extract, 'VFPPROD' or 'VFPINJ'",
        default=None,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser

def vfp_main(args) -> None:
    """Entry-point for module, for command line utility."""
    logger = getLogger_ecl2csv(  # pylint: disable=redefined-outer-name
        __name__, vars(args)
    )
    if not args.vfptype in SUPPORTED_KEYWORDS or not args.vfptype:
        print("vfptype argument {args.vfptype} not supported")
        sys.exit(0)
    if not args.output:
        print("Nothing to do. Set --output")
        sys.exit(0)
    eclfiles = EclFiles(args.DATAFILE)
    dframe = df(eclfiles.get_ecldeck(), vfptype=args.vfptype)
    if args.output:
        write_dframe_stdout_file(dframe, args.output, index=False, caller_logger=logger)


    
    

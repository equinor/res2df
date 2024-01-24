"""Extract the VFPPROD/VFPINJ data from an Eclipse (input) deck as Pandas Dataframes

Data can be extracted from a complete deck or from individual files. Supports
output both in csv format as a pandas DataFrame or in pyarrow and pyarrow.table
"""

import argparse
import logging
import sys
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

from ..common import comment_formatter
from ..common import fill_reverse_parser as common_fill_reverse_parser
from ..common import write_dframe_stdout_file, write_inc_stdout_file
from ..res2csvlogger import getLogger_res2csv
from ..resdatafiles import ResdataFiles
from . import _vfpinj as vfpinj
from . import _vfpprod as vfpprod
from ._vfpdefs import SUPPORTED_KEYWORDS, VFPTYPE

logger = logging.getLogger(__name__)


def basic_data(
    deck: Union[str, ResdataFiles, "opm.libopmcommon_python.Deck"],
    keyword: str = "VFPPROD",
    vfpnumbers_str: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Produce a dictionary with basic data for an Eclipe VFPPROD/VFPINJ.
    Dictionary returned contains items for liftcuve tables as simple datatypes
    Required keys in dictionary for VFPPROD and VFPINJ can be found in
    BASIC_DATA_KEYS in _vfpprod and _vfpinj.

    Args:
        deck:           :term:`.DATA file` or string with :term:`deck`
        keyword:        VFP table type, i.e. 'VFPPROD' or 'VFPINJ'
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds to [0,1,8,9,10,11].
    """

    if isinstance(deck, ResdataFiles):
        deck = deck.get_deck()
    elif isinstance(deck, str):
        deck = ResdataFiles.str2deck(deck)

    if keyword not in SUPPORTED_KEYWORDS:
        raise ValueError(
            f"VFP type {keyword} not supported choose 'VFPPROD'or 'VFPINJ'"
        )

    # The keywords VFPPROD/VFPINJ can be used many times in Eclipse and be introduced in
    # separate files or a common file. Need to loop to find all instances of keyword and
    # store separately
    basic_data_vfps = []
    for deck_keyword in deck:
        if deck_keyword.name == keyword:
            if deck_keyword.name == "VFPPROD":
                basic_data_vfpprod = vfpprod.basic_data(deck_keyword, vfpnumbers_str)
                if basic_data_vfpprod is not None:
                    basic_data_vfps.append(basic_data_vfpprod)
            elif deck_keyword.name == "VFPINJ":
                basic_data_vfpinj = vfpinj.basic_data(deck_keyword, vfpnumbers_str)
                if basic_data_vfpinj is not None:
                    basic_data_vfps.append(basic_data_vfpinj)

    return basic_data_vfps


def basic_data2df(data: Dict[str, Any]) -> pd.DataFrame:
    """Convert basic_data representation of VFPPROD/VFPINF
    (see function basic_data for defintion of data) into
    pandas DataFrame representation

    Args:
        data:  Dictionary with basic data representation of
               VFPPROD or VFPINJ (see basic_data)
    """

    if "VFP_TYPE" in data.keys():
        vfp_type = data["VFP_TYPE"]
        if vfp_type == VFPTYPE.VFPPROD:
            # Check consistency of basic data
            if not vfpprod._check_basic_data(data):
                return pd.DataFrame()

            return vfpprod.basic_data2df(
                tableno=data["TABLE_NUMBER"],
                datum=data["DATUM"],
                rate_type=data["RATE_TYPE"],
                wfr_type=data["WFR_TYPE"],
                gfr_type=data["GFR_TYPE"],
                alq_type=data["ALQ_TYPE"],
                thp_type=data["THP_TYPE"],
                unit_type=data["UNIT_TYPE"],
                tab_type=data["TAB_TYPE"],
                flow_values=data["FLOW_VALUES"],
                thp_values=data["THP_VALUES"],
                wfr_values=data["WFR_VALUES"],
                gfr_values=data["GFR_VALUES"],
                alq_values=data["ALQ_VALUES"],
                thp_indices=data["THP_INDICES"],
                wfr_indices=data["WFR_INDICES"],
                gfr_indices=data["GFR_INDICES"],
                alq_indices=data["ALQ_INDICES"],
                tab_data=data["BHP_TABLE"],
            )
        elif vfp_type == VFPTYPE.VFPINJ:
            # Check consistency of basic data
            if not vfpinj._check_basic_data(data):
                return pd.DataFrame()
            return vfpinj.basic_data2df(
                tableno=data["TABLE_NUMBER"],
                datum=data["DATUM"],
                rate_type=data["RATE_TYPE"],
                thp_type=data["THP_TYPE"],
                unit_type=data["UNIT_TYPE"],
                tab_type=data["TAB_TYPE"],
                flow_values=data["FLOW_VALUES"],
                thp_values=data["THP_VALUES"],
                thp_indices=data["THP_INDICES"],
                tab_data=data["BHP_TABLE"],
            )
        else:
            raise ValueError(f"Unknown VFP_TYPE {vfp_type.value}")

    raise ValueError("VFP_TYPE not found in basic data")


def basic_data2pyarrow(data: Dict[str, Any], /) -> pa.Table:
    """Convert basic_data representation of VFPPROD/VFPINF
    (see function basic_data for defintion of data) into
    pyarrow.Table representation

    Args:
        data:  Dictionary with basic data representation of
               VFPPROD or VFPINJ
    """

    if "VFP_TYPE" in data.keys():
        vfp_type = data["VFP_TYPE"]
        if vfp_type == VFPTYPE.VFPPROD:
            # Check consistency of basic data
            if not vfpprod._check_basic_data(data):
                return pd.DataFrame()

            return vfpprod.basic_data2pyarrow(
                tableno=data["TABLE_NUMBER"],
                datum=data["DATUM"],
                rate_type=data["RATE_TYPE"],
                wfr_type=data["WFR_TYPE"],
                gfr_type=data["GFR_TYPE"],
                alq_type=data["ALQ_TYPE"],
                thp_type=data["THP_TYPE"],
                unit_type=data["UNIT_TYPE"],
                tab_type=data["TAB_TYPE"],
                flow_values=data["FLOW_VALUES"],
                thp_values=data["THP_VALUES"],
                wfr_values=data["WFR_VALUES"],
                gfr_values=data["GFR_VALUES"],
                alq_values=data["ALQ_VALUES"],
                thp_indices=data["THP_INDICES"],
                wfr_indices=data["WFR_INDICES"],
                gfr_indices=data["GFR_INDICES"],
                alq_indices=data["ALQ_INDICES"],
                tab_data=data["BHP_TABLE"],
            )
        elif vfp_type == VFPTYPE.VFPINJ:
            # Check consistency of basic data
            if not vfpinj._check_basic_data(data):
                return pd.DataFrame()
            return vfpinj.basic_data2pyarrow(
                tableno=data["TABLE_NUMBER"],
                datum=data["DATUM"],
                rate_type=data["RATE_TYPE"],
                thp_type=data["THP_TYPE"],
                unit_type=data["UNIT_TYPE"],
                tab_type=data["TAB_TYPE"],
                flow_values=data["FLOW_VALUES"],
                thp_values=data["THP_VALUES"],
                thp_indices=data["THP_INDICES"],
                tab_data=data["BHP_TABLE"],
            )
        else:
            raise ValueError(f"Unknown VFP_TYPE {vfp_type.value}")

    raise ValueError("VFP_TYPE not found in basic data")


def df2basic_data(dframe: pd.DataFrame, /) -> Union[Dict[str, Any], None]:
    """Produce a dictionary with basic data types for a VFPPROD/VFPINJ
    liftcurve table represented as a Pandas DataFrame

    Args:
        dframe:    Dataframe containing complete description of VFPPROD/VFPINJ input
    """

    if "VFP_TYPE" in dframe.columns:
        if len(dframe["VFP_TYPE"].unique()) == 1:
            vfp_type = VFPTYPE[dframe["VFP_TYPE"].unique()[0]]
            if vfp_type == VFPTYPE.VFPPROD:
                return vfpprod.df2basic_data(dframe)
            elif vfp_type == VFPTYPE.VFPINJ:
                return vfpinj.df2basic_data(dframe)
    else:
        raise ValueError("Inconsistent VFP_TYPE definition in dataframe")

    return None


def pyarrow2basic_data(pa_table: pa.Table) -> Union[Dict[str, Any], None]:
    """Produce a dictionary with basic data types for a VFPPROD/VFPINJ
    liftcurve table represented as a pyarrow Table

    Args:
        pa_table:    pyarrow.Table representation of VFPPROD/VFPINJ
    """

    # Check VFP type
    vfp_type = VFPTYPE[pa_table.schema.metadata[b"VFP_TYPE"].decode("utf-8")]
    if vfp_type == VFPTYPE.VFPPROD:
        return vfpprod.pyarrow2basic_data(pa_table)
    elif vfp_type == VFPTYPE.VFPINJ:
        return vfpinj.pyarrow2basic_data(pa_table)
    else:
        raise ValueError("Unknown VFP_TYPE definition")

    return None


def dfs(
    deck: Union[str, ResdataFiles, "opm.libopmcommon_python.Deck"],
    keyword: str = "VFPPROD",
    vfpnumbers_str: Optional[str] = None,
) -> List[pd.DataFrame]:
    """Produce a list of dataframes of vfp tables from a :term:`deck`

    Data for the keyword VFPPROD or VFPINJ will be returned as separate item in list

    Args:
        deck:           :term:`.DATA file` or string with :term:`deck`
        keyword:        VFP table type, i.e. 'VFPPROD' or 'VFPINJ'
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds to [0,1,8,9,10,11].
    """
    if isinstance(deck, ResdataFiles):
        deck = deck.get_deck()
    elif isinstance(deck, str):
        deck = ResdataFiles.str2deck(deck)

    if keyword not in SUPPORTED_KEYWORDS:
        raise ValueError(
            f"VFP type {keyword} not supported choose 'VFPPROD'or 'VFPINJ'"
        )

    # The keywords VFPPROD/VFPINJ can be used many times in Eclipse and be introduced in
    # separate files or a common file. Need to loop to find all instances of keyword and
    # store separately
    dfs_vfp = []
    for deck_keyword in deck:
        if deck_keyword.name == keyword:
            if deck_keyword.name == "VFPPROD":
                df_vfpprod = vfpprod.df(deck_keyword, vfpnumbers_str)
                if df_vfpprod is not None:
                    dfs_vfp.append(df_vfpprod)
            elif deck_keyword.name == "VFPINJ":
                df_vfpinj = vfpinj.df(deck_keyword, vfpnumbers_str)
                if df_vfpinj is not None:
                    dfs_vfp.append(df_vfpinj)

    return dfs_vfp


def pyarrow_tables(
    deck: Union[str, ResdataFiles, "opm.libopmcommon_python.Deck"],
    keyword: str = "VFPPROD",
    vfpnumbers_str: Optional[str] = None,
) -> List[pa.Table]:
    """Produce a list of pyarrow.Table of vfp tables from a :term:`deck`

    Data for the keyword VFPPROD or VFPINJ will be returned as separate item in list

    Args:
        deck:           :term:`.DATA file` or string with :term:`deck`
        keyword:        VFP table type, i.e. 'VFPPROD' or 'VFPINJ'
        vfpnumbers_str: String with list of vfp table numbers to extract.
                        Syntax "[0,1,8:11]" corresponds to [0,1,8,9,10,11].
    """
    if isinstance(deck, ResdataFiles):
        deck = deck.get_deck()
    elif isinstance(deck, str):
        deck = ResdataFiles.str2deck(deck)

    if keyword not in SUPPORTED_KEYWORDS:
        raise ValueError(
            f"VFP type {keyword} not supported choose 'VFPPROD'or 'VFPINJ'"
        )

    # The keywords VFPPROD/VFPINJ can be used many times in Eclipse and be introduced in
    # separate files or a common file. Need to loop to find all instances of keyword and
    # store separately
    pyarrow_tables_vfp = []
    for deck_keyword in deck:
        if deck_keyword.name == keyword:
            if deck_keyword.name == "VFPPROD":
                pa_table_vfpprod = vfpprod.pyarrow(deck_keyword, vfpnumbers_str)
                if pa_table_vfpprod is not None:
                    pyarrow_tables_vfp.append(pa_table_vfpprod)
            elif deck_keyword.name == "VFPINJ":
                pa_table_vfpinj = vfpinj.pyarrow(deck_keyword, vfpnumbers_str)
                if pa_table_vfpinj is not None:
                    pyarrow_tables_vfp.append(pa_table_vfpinj)

    return pyarrow_tables_vfp


def df2ress(
    dframe: pd.DataFrame,
    keyword: str = "VFPPROD",
    comments: Optional[Dict[str, str]] = None,
) -> List[str]:
    """Produce a list of strings defining VFPPROD/VFPINJ Eclipse
    :term:`include file` contents from a dataframe

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
                    vfp_strs.append(vfpprod.df2res(df_vfp, comments["VFPPROD"]))
                elif keyword == "VFPINJ":
                    vfp_strs.append(vfpinj.df2res(df_vfp, comments["VFPINJ"]))
            else:
                if keyword == "VFPPROD":
                    vfp_strs.append(vfpprod.df2res(df_vfp))
                elif keyword == "VFPINJ":
                    vfp_strs.append(vfpinj.df2res(df_vfp))
        else:
            raise ValueError(
                f"VFP number {vfpno} does not have consistent "
                "type defintion in vfp.dfecls"
            )

    return vfp_strs


def df2res(
    dframe: pd.DataFrame,
    keyword: str = "VFPPROD",
    comments: Optional[Dict[str, str]] = None,
    filename: Optional[str] = None,
) -> str:
    """Create a string defining all VFPPROD/VFPINJ Eclipse
    :term:`include file` contents from a dataframe

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

    strs_vfp = df2ress(dframe, keyword=keyword, comments=comments)
    str_vfps = ""

    if comments and "master" in comments.keys():
        str_vfps += comment_formatter(comments["master"])
    for str_vfp in strs_vfp:
        str_vfps += str_vfp
        str_vfps += "\n"

    if filename:
        with open(filename, "w") as fout:
            fout.write(str_vfps)

    return str_vfps


def df(
    deck: Union[str, ResdataFiles, "opm.libopmcommon_python.Deck"],
    keyword: str = "VFPPROD",
    vfpnumbers_str: Optional[str] = None,
) -> pd.DataFrame:
    """Produce a dataframes of all vfp tables from a deck

    All data for the keywords VFPPROD/VFPINJ will be returned.

    Args:
        deck:           :term:`.DATA file` or string wit :term:`deck`
        keyword:        VFP table type, i.e. 'VFPPROD' or 'VFPINJ'
        vfpnumbers_str: str with list of VFP table numbers to extract
    """

    if not keyword:
        logger.warning("No keywords provided to vfp.df. Empty dataframe returned")
        return pd.DataFrame()

    if isinstance(deck, ResdataFiles):
        deck = deck.get_deck()
    elif isinstance(deck, str):
        deck = ResdataFiles.str2deck(deck)

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
    parser.add_argument(
        "DATAFILE", help="Name of the .DATA input file for the reservoir simulator"
    )
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
    """Fill a parser for the operation dataframe -> resdata :term:`include file`"""
    return common_fill_reverse_parser(parser, "VFPPROD, VFPINJ", "vfp.inc")


def vfp_main(args) -> None:
    """Entry-point for module, for command line utility."""
    logger = getLogger_res2csv(  # pylint: disable=redefined-outer-name
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

    resdatafiles = ResdataFiles(args.DATAFILE)
    if args.arrow:
        outputfile = args.output
        outputfile.replace(".arrow", "")
        vfp_arrow_tables = pyarrow_tables(
            resdatafiles.get_deck(), keyword=args.keyword, vfpnumbers_str=vfpnumbers
        )
        for vfp_table in vfp_arrow_tables:
            table_number = int(
                vfp_table.schema.metadata[b"TABLE_NUMBER"].decode("utf-8")
            )
            vfp_filename = f"{outputfile}_{str(table_number)}.arrow"
            write_dframe_stdout_file(
                vfp_table, vfp_filename, index=False, caller_logger=logger
            )
            logger.info(f"Parsed file {args.DATAFILE} for vfp.dfs_arrow")
    else:
        dframe = df(
            resdatafiles.get_deck(), keyword=args.keyword, vfpnumbers_str=vfpnumbers
        )
        if args.output:
            write_dframe_stdout_file(
                dframe, args.output, index=False, caller_logger=logger
            )
            logger.info(f"Parsed file {args.DATAFILE} for vfp.df")


def vfp_reverse_main(args) -> None:
    """Entry-point for module, for command line utility for CSV to Eclipse"""
    logger = getLogger_res2csv(  # pylint: disable=redefined-outer-name
        __name__, vars(args)
    )
    vfp_df = pd.read_csv(args.csvfile)
    logger.info("Parsed {args.csvfile}")
    inc_string = df2res(vfp_df, args.keyword)
    if args.output:
        write_inc_stdout_file(inc_string, args.output)

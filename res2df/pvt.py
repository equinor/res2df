"""
Extract the PVT data from a .DATA file as Pandas Dataframes

Data can be extracted from a complete deck or from individual files.
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

from .common import comment_formatter
from .common import df2res as common_df2res
from .common import fill_reverse_parser as common_fill_reverse_parser
from .common import (
    handle_wanted_keywords,
    keyworddata_to_df,
    write_dframe_stdout_file,
    write_inc_stdout_file,
)
from .inferdims import DIMS_POS, inject_xxxdims_ntxxx
from .res2csvlogger import getLogger_res2csv
from .resdatafiles import ResdataFiles

try:
    # Needed for mypy

    # pylint: disable=unused-import
    import opm.io
except ImportError:
    pass


logger: logging.Logger = logging.getLogger(__name__)

SUPPORTED_KEYWORDS: List[str] = [
    "PVTO",
    "PVDO",
    "PVTG",
    "PVDG",
    "DENSITY",
    "ROCK",
    "PVTW",
]

# The renamers listed here map from opm-common json item names to
# desired column names in produced dataframes. They also to a certain
# extent determine the structure of the dataframe, in particular
# for keywords with arbitrary data amount pr. record (PVTO f.ex)
RENAMERS: Dict[str, Dict[str, Union[str, List[str]]]] = {}

# P_bub (bubble point pressure) is called PRESSURE for ability to merge with
# other pressure data from other frames.
RENAMERS["PVTO"] = {"RS": "RS", "DATA": ["PRESSURE", "VOLUMEFACTOR", "VISCOSITY"]}
RENAMERS["PVDG"] = {"DATA": ["PRESSURE", "VOLUMEFACTOR", "VISCOSITY"]}
RENAMERS["PVDO"] = {"DATA": ["PRESSURE", "VOLUMEFACTOR", "VISCOSITY"]}

# Recheck nomenclature for "OGR" here, is it "vaporized oil-gas ratio" in manual
# which someone also seem to denote r_s (as opposed to R_s for GOR)
# It might make sense to call it RS, but it will cause some confusion with RS from
# PVTO.
RENAMERS["PVTG"] = {
    "GAS_PRESSURE": "PRESSURE",
    "DATA": ["OGR", "VOLUMEFACTOR", "VISCOSITY"],
}
RENAMERS["PVTW"] = {
    "P_REF": "PRESSURE",
    "WATER_VOL_FACTOR": "VOLUMEFACTOR",
    "WATER_COMPRESSIBILITY": "COMPRESSIBILITY",
    "WATER_VISCOSITY": "VISCOSITY",
    "WATER_VISCOSIBILITY": "VISCOSIBILITY",
}
RENAMERS["DENSITY"] = {
    "OIL": "OILDENSITY",
    "WATER": "WATERDENSITY",
    "GAS": "GASDENSITY",
}
RENAMERS["ROCK"] = {"PREF": "PRESSURE", "COMPRESSIBILITY": "COMPRESSIBILITY"}


def pvtw_fromdeck(
    deck: Union[str, "opm.libopmcommon_python.Deck"], ntpvt: Optional[int] = None
) -> pd.DataFrame:
    """Extract PVTW from a :term:`deck`

    Args:
        deck
        ntpvt: Number of PVT regions in :term:`deck`. Will
            be inferred if not present in :term:`deck`.
    """
    if "TABDIMS" not in deck:
        deck = inject_xxxdims_ntxxx("TABDIMS", "NTPVT", deck, ntpvt)
    return keyworddata_to_df(
        deck, "PVTW", renamer=RENAMERS["PVTW"], recordcountername="PVTNUM"
    )


def density_fromdeck(
    deck: Union[str, "opm.libopmcommon_python.Deck"], ntpvt: Optional[int] = None
) -> pd.DataFrame:
    """Extract DENSITY from a :term:`deck`

    Args:
        deck
        ntpvt: Number of PVT regions in :term:`deck`. Will
            be inferred if not present in :term:`deck`.
    """
    if "TABDIMS" not in deck:
        deck = inject_xxxdims_ntxxx("TABDIMS", "NTPVT", deck, ntpvt)
    return keyworddata_to_df(
        deck, "DENSITY", renamer=RENAMERS["DENSITY"], recordcountername="PVTNUM"
    )


def rock_fromdeck(
    deck: Union[str, "opm.libopmcommon_python.Deck"], ntpvt: Optional[int] = None
) -> pd.DataFrame:
    """Extract ROCK from a :term:`deck`

    Args:
        deck
        ntpvt: Number of PVT regions in :term:`deck`. Will
            be inferred if not present in :term:`deck`.
    """
    if "TABDIMS" not in deck:
        deck = inject_xxxdims_ntxxx("TABDIMS", "NTPVT", deck, ntpvt)
    return keyworddata_to_df(
        deck, "ROCK", renamer=RENAMERS["ROCK"], recordcountername="PVTNUM"
    )


def pvto_fromdeck(
    deck: Union[str, "opm.libopmcommon_python.Deck"], ntpvt: Optional[int] = None
) -> pd.DataFrame:
    """Extract PVTO from a :term:`deck`

    Args:
        deck
        ntpvt: Number of PVT regions in :term:`deck`. Will
            be inferred if not present in :term:`deck`.
    """
    if "TABDIMS" not in deck:
        deck = inject_xxxdims_ntxxx("TABDIMS", "NTPVT", deck, ntpvt)
    pvto_df = keyworddata_to_df(
        deck, "PVTO", renamer=RENAMERS["PVTO"], emptyrecordcountername="PVTNUM"
    )
    return pvto_df


def pvdo_fromdeck(
    deck: Union[str, "opm.libopmcommon_python.Deck"], ntpvt: Optional[int] = None
) -> pd.DataFrame:
    """Extract PVDO from a :term:`deck`

    Args:
        deck
        ntpvt: Number of PVT regions in deck. Will
            be inferred if not present in deck.
    """
    if "TABDIMS" not in deck:
        deck = inject_xxxdims_ntxxx("TABDIMS", "NTPVT", deck, ntpvt)
    pvdg_df = keyworddata_to_df(
        deck, "PVDO", renamer=RENAMERS["PVDO"], recordcountername="PVTNUM"
    )
    return pvdg_df


def pvdg_fromdeck(
    deck: Union[str, "opm.libopmcommon_python.Deck"], ntpvt: Optional[int] = None
) -> pd.DataFrame:
    """Extract PVDG from a :term:`deck`

    Args:
        deck
        ntpvt: Number of PVT regions in :term:`deck`. Will
            be inferred if not present in :term:`deck`.
    """
    if "TABDIMS" not in deck:
        deck = inject_xxxdims_ntxxx("TABDIMS", "NTPVT", deck, ntpvt)
    pvdg_df = keyworddata_to_df(
        deck, "PVDG", renamer=RENAMERS["PVDG"], recordcountername="PVTNUM"
    )
    return pvdg_df


def pvtg_fromdeck(
    deck: Union[str, "opm.libopmcommon_python.Deck"], ntpvt: Optional[int] = None
) -> pd.DataFrame:
    """Extract PVTG from a :term:`deck`

    Args:
        deck
        ntpvt: Number of PVT regions in :term:`deck`. Will
            be inferred if not present in :term:`deck`.
    """
    if "TABDIMS" not in deck:
        deck = inject_xxxdims_ntxxx("TABDIMS", "NTPVT", deck, ntpvt)
    pvtg_df = keyworddata_to_df(
        deck, "PVTG", renamer=RENAMERS["PVTG"], emptyrecordcountername="PVTNUM"
    )
    return pvtg_df


def df(
    deck: Union[str, "opm.libopmcommon_python.Deck"],
    keywords: Optional[List[str]] = None,
    ntpvt: Optional[int] = None,
) -> pd.DataFrame:
    """Extract all (most) PVT data from a :term:`deck`.

    If you want to call this function on :term:`include files <include file>`,
    read them in to strings as in this example:

    > pvt_df = pvt.df(open("pvt.inc").read())

    Arguments:
        deck: Incoming data :term:`deck`. Always
            supply as a string if you don't know TABDIMS-NTSFUN.
        keywords: List of keywords for which data is
            wanted. All data will be merged into one dataframe.
        pvtnumcount: Number of PVTNUMs defined in the :term:`deck`, only
            needed if TABDIMS with NTPVT is not found in the :term:`deck`.
            If not supplied (or None) and NTPVT is not defined,
            it will be attempted inferred.

    Return:
        pd.DataFrame
    """
    if isinstance(deck, ResdataFiles):
        deck = deck.get_deck()

    deck = inject_xxxdims_ntxxx("TABDIMS", "NTPVT", deck, ntpvt)
    ntpvt = deck["TABDIMS"][0][DIMS_POS["NTPVT"]].get_int(0)

    wanted_keywords = handle_wanted_keywords(keywords, deck, SUPPORTED_KEYWORDS)

    frames = []
    for keyword in wanted_keywords:
        # Construct the associated function names
        function_name = keyword.lower() + "_fromdeck"
        function = globals()[function_name]
        dframe = function(deck, ntpvt=ntpvt)
        frames.append(dframe.assign(KEYWORD=keyword))
    nonempty_frames = [frame for frame in frames if not frame.empty]
    if nonempty_frames:
        return pd.concat(nonempty_frames, axis=0, sort=False, ignore_index=True)
    return pd.DataFrame()


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parsers for parsing :term:`.DATA file` or
    :term:`include files <include file>` into dataframes

    Arguments:
        parser (ArgumentParser or subparser): parser to fill with arguments
    """
    parser.add_argument(
        "DATAFILE",
        help="Name of the .DATA input file for the reservoir simulator,"
        + " or file with PVT keywords.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file, default pvt.csv. Use '-' for stdout.",
        default="pvt.csv",
    )
    parser.add_argument(
        "-k",
        "--keywords",
        nargs="+",
        help=(
            "List of PVT keywords to include. "
            "If not supplied, all supported keywords will be included."
        ),
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def fill_reverse_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parsers for writing :term:`include files <include file>` from
    dataframes (as CSV files)

    Arguments:
        parser (ArgumentParser or subparser): parser to fill with arguments
    """
    return common_fill_reverse_parser(parser, "PVT", "pvt.inc")


def pvt_main(args) -> None:
    """Entry-point for module, for command line utility for Eclipse to CSV"""
    logger = getLogger_res2csv(  # pylint: disable=redefined-outer-name
        __name__, vars(args)
    )
    resdatafiles = ResdataFiles(args.DATAFILE)
    logger.info("Parsed %s", args.DATAFILE)
    if resdatafiles:
        deck = resdatafiles.get_deck()
    if "TABDIMS" in deck:
        # Things are easier when a full deck with correct TABDIMS
        # is supplied:
        pvt_df = df(deck, keywords=args.keywords)
    else:
        # When TABDIMS is not present, the code will try to infer
        # the number of saturation functions, this is necessarily
        # more error-prone, and it needs a string as input.
        stringdeck = Path(args.DATAFILE).read_text(encoding="utf-8")
        pvt_df = df(stringdeck, keywords=args.keywords)
    if "PVTNUM" in pvt_df and "KEYWORD" in pvt_df:
        pvtnums = str(len(pvt_df["PVTNUM"].unique()))
        keywords = str(pvt_df["KEYWORD"].unique())
    else:
        pvtnums = "-"
        keywords = "-"
    write_dframe_stdout_file(
        pvt_df,
        args.output,
        index=False,
        caller_logger=logger,
        logstr=f"Unique PVTNUMs: {pvtnums}, PVT keywords: {keywords}",
    )


def pvt_reverse_main(args) -> None:
    """Entry-point for module, for command line utility for CSV to simulator
    :term:`deck`"""
    logger = getLogger_res2csv(  # pylint: disable=redefined-outer-name
        __name__, vars(args)
    )
    pvt_df = pd.read_csv(args.csvfile)
    logger.info("Parsed %s", args.csvfile)
    inc_string = df2res(pvt_df, keywords=args.keywords)
    write_inc_stdout_file(inc_string, args.output)


def df2res(
    pvt_df: pd.DataFrame,
    keywords: Optional[Union[str, List[str]]] = None,
    comments: Optional[Dict[str, str]] = None,
    filename: Optional[str] = None,
) -> str:
    """Generate resdata :term:`include file` content from PVT dataframes

    Args:
        pvt_df: Dataframe with PVT data in res2df format.
        keywords: List of keywords to include. Must be
            supported and present in the incoming dataframe.
        comments: Dictionary indexed by keyword with comments to be
            included pr. keyword. If a key named "master" is present
            it will be used as a master comment for the outputted file.
        filename: If supplied, the generated text will also be dumped
            to file.
    """
    return common_df2res(
        pvt_df,
        keywords,
        comments,
        supported=SUPPORTED_KEYWORDS,
        consecutive="PVTNUM",
        filename=filename,
    )


def df2res_rock(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Create string with :term:`include file` contents for ROCK keyword

    Args:
        dframe (pd.DataFrame): Containing ROCK data
        comment (str): Text that will be included as a comment
    """
    if dframe.empty:
        return "-- No data!"
    string = "ROCK\n"
    string += comment_formatter(comment)
    string += "--   {'PRESSURE':^21} {'COMPRESSIBILITY':^21}\n"
    if "KEYWORD" not in dframe:
        # Use everything..
        subset = dframe
    else:
        subset = dframe[dframe["KEYWORD"] == "ROCK"]
    if "PVTNUM" not in subset:
        if len(subset) != 1:
            logger.critical("If PVTNUM is not supplied, only one row should be given")
            return ""
        subset["PVTNUM"] = 1
    subset = subset.set_index("PVTNUM").sort_index()
    for _, row in subset.iterrows():
        string += f"  {row['PRESSURE']:20.7f} {row['COMPRESSIBILITY']:20.7f} /\n"
    return string + "\n"


def df2res_density(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Create string with :term:`include file` contents for DENSITY keyword

    Args:
        dframe: Containing DENSITY data
        comment: Text that will be included as a comment
    """
    if dframe.empty:
        return "-- No data!"
    string = "DENSITY\n"
    string += comment_formatter(comment)
    string += f"--   {'OILDENSITY':^21} {'WATERDENSITY':^21} {'GASDENSITY':^21}\n"
    if "KEYWORD" not in dframe:
        # Use everything..
        subset = dframe
    else:
        subset = dframe[dframe["KEYWORD"] == "DENSITY"]
    if "PVTNUM" not in subset:
        if len(subset) != 1:
            logger.critical("If PVTNUM is not supplied, only one row should be given")
            return ""
        subset["PVTNUM"] = 1
    subset = subset.set_index("PVTNUM").sort_index()
    for _, row in subset.iterrows():
        string += f"  {row['OILDENSITY']:20.7f} {row['WATERDENSITY']:20.7f}"
        string += f" {row['GASDENSITY']:20.7f} /\n"
    return string + "\n"


def df2res_pvtw(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Create string with :term:`include file` contents for PVTW keyword

    PVTW is one line/record with data for a reference pressure
    for each PVTNUM.

    Args:
        dframe: Containing PVTW data
        comment: Text that will be included as a comment
    """
    if dframe.empty:
        return "-- No data!"
    string = "PVTW\n"
    string += comment_formatter(comment)
    string += (
        f"--   {'PRESSURE':^21} {'VOLUMEFACTOR':^21} {'COMPRESSIBILITY':^21} "
        f"{'VISCOSITY':^21} {'VISCOSIBILITY':^21}\n"
    )
    if "KEYWORD" not in dframe:
        # Use everything..
        subset = dframe
    else:
        subset = dframe[dframe["KEYWORD"] == "PVTW"]
    if "PVTNUM" not in subset:
        if len(subset) != 1:
            logger.critical("If PVTNUM is not supplied, only one row should be given")
            return ""
        subset["PVTNUM"] = 1
    subset = subset.set_index("PVTNUM").sort_index()
    for _, row in subset.iterrows():
        string += f"  {row['PRESSURE']:20.7f} {row['VOLUMEFACTOR']:20.7f} "
        string += f"{row['COMPRESSIBILITY']:20.7f} {row['VISCOSITY']:20.7f} "
        string += f"{row['VISCOSIBILITY']:20.7f}/\n"
    return string + "\n"


def df2res_pvtg(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Create string with :term:`include file` contents for PVTG keyword

    Args:
        dframe: Containing PVTG data
        comment: Text that will be included as a comment
    """
    if dframe.empty:
        return "-- No data!"
    string = "PVTG\n"
    string += comment_formatter(comment)
    string += (
        f"-- {'PRESSURE':^22} {'OGR':^22} {'VOLUMEFACTOR':^22} {'VISCOSITY':^22}\n"
    )
    string += f"-- {'*':^22} {'OGR':^22} {'VOLUMEFACTOR':^22} {'VISCOSITY':^22}\n"
    if "KEYWORD" not in dframe:
        # Use everything..
        subset = dframe
    else:
        subset = dframe[dframe["KEYWORD"] == "PVTG"]
    if "PVTNUM" not in subset:
        if len(subset) != 1:
            logger.critical("If PVTNUM is not supplied, only one row should be given")
            return ""
        subset["PVTNUM"] = 1
    subset = subset.set_index("PVTNUM").sort_index()

    def _pvtg_pvtnum(dframe):
        """Create string with :term:`include file` contents for
        PVTG-data with a specific PVTNUM"""
        string = ""
        dframe = dframe.set_index("PRESSURE").sort_index()
        for p_gas in dframe.index.unique():
            string += _pvtg_pvtnum_pg(dframe[dframe.index == p_gas])
        return string + "/\n"

    def _pvtg_pvtnum_pg(dframe):
        """Create string with :term:`include file` contents for
        PVTG-data with a particular gas phase pressure"""
        string = ""
        assert len(dframe.index.unique()) == 1
        p_gas = dframe.index.values[0]
        string += f"{p_gas:20.7f}  "
        for rowidx, row in dframe.reset_index().iterrows():
            if rowidx > 0:
                indent = "\n" + " " * 22
            else:
                indent = ""
            string += (
                indent
                + f"{row['OGR']:20.7f}  {row['VOLUMEFACTOR']:20.7f}  "
                + f"{row['VISCOSITY']:20.7f}"
            )
        string += f" /\n-- End PRESSURE={p_gas}\n"
        return string

    for pvtnum in subset.index.unique():
        string += _pvtg_pvtnum(subset[subset.index == pvtnum])
    return string + "\n"


def df2res_pvdg(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Create string with :term:`include file` contents for PVDG keyword

    This data consists of one table (volumefactor and visosity
    as a function of pressure) pr. PVTNUM.

    Args:
        dframe: Containing PVDG data
        comment: Text that will be included as a comment
    """
    if dframe.empty:
        return "-- No data!"
    string = "PVDG\n"
    string += comment_formatter(comment)
    string += f"--   {'PRESSURE':^21} {'VOLUMEFACTOR':^21} {'VISCOSITY':^21}  \n"
    if "KEYWORD" not in dframe:
        # Use everything..
        subset = dframe
    else:
        subset = dframe[dframe["KEYWORD"] == "PVDG"]
    if "PVTNUM" not in subset:
        if len(subset) != 1:
            logger.critical("If PVTNUM is not supplied, only one row should be given")
            return ""
        subset["PVTNUM"] = 1

    def _pvdg_pvtnum(dframe):
        """Create string with :term:`include file` contents for
        PVDG-data with a specific PVTNUM

        Args:
            dframe (pd.DataFrame): Cropped to only contain the relevant data.

        Returns:
            string
        """
        string = ""
        dframe = dframe.sort_values("PRESSURE")
        for _, row in dframe.iterrows():
            string += f"  {row['PRESSURE']:20.7f} {row['VOLUMEFACTOR']:20.7f} "
            string += f"{row['VISCOSITY']:20.7f}\n"
        return string + "/\n"

    subset = subset.set_index("PVTNUM").sort_index()
    for pvtnum in subset.index.unique():
        string += "-- PVTNUM: {pvtnum}\n"
        string += _pvdg_pvtnum(subset[subset.index == pvtnum])

    return string + "\n"


def df2res_pvdo(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Create string with :term:`include file` contents for PVDO keyword

    Args:
        dframe: Containing PVDO data
        comment: Text that will be included as a comment
    """
    if dframe.empty:
        return "-- No data!"
    string = "PVDO\n"
    string += comment_formatter(comment)
    string += f"--   {'PRESSURE':^21} {'VOLUMEFACTOR':^21} {'VISCOSITY':^21}\n"
    if "KEYWORD" not in dframe:
        # Use everything..
        subset = dframe
    else:
        subset = dframe[dframe["KEYWORD"] == "PVDO"]
    if "PVTNUM" not in subset:
        if len(subset) != 1:
            logger.critical("If PVTNUM is not supplied, only one row should be given")
            return ""
        subset["PVTNUM"] = 1

    def _pvdo_pvtnum(dframe: pd.DataFrame) -> str:
        """Create string with :term:`include file` contents
        for PVDO-data for a specific PVTNUM

        Args:
            dframe (pd.DataFrame): Cropped to only contain the relevant data.

        Returns:
            string
        """
        string = ""
        dframe = dframe.sort_values("PRESSURE")
        for _, row in dframe.iterrows():
            string += f"  {row['PRESSURE']:20.7f} {row['VOLUMEFACTOR']:20.7f} "
            string += f"{row['VISCOSITY']:20.7f}\n"
        return string + "/\n"

    subset = subset.set_index("PVTNUM").sort_index()
    for pvtnum in subset.index.unique():
        string += f"-- PVTNUM: {pvtnum}\n"
        string += _pvdo_pvtnum(subset[subset.index == pvtnum])

    return string + "\n"


def df2res_pvto(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Create string with :term:`include file` contents for PVTO-data from a dataframe

    Args:
        dframe: Containing PVTO data
        comment: Text that will be included as a comment
    """
    if dframe.empty:
        return "-- No data!"
    string = "PVTO\n"
    string += comment_formatter(comment)
    string += "-- {'RS':^22} {'PRESSURE':^22} {'VOLUMEFACTOR':^22} {'VISCOSITY':^22}\n"
    string += "-- {'*':^22} {'PRESSURE':^22} {'VOLUMEFACTOR':^22} {'VISCOSITY':^22}\n"
    if "KEYWORD" not in dframe:
        # Use everything..
        subset = dframe
    else:
        subset = dframe[dframe["KEYWORD"] == "PVTO"]
    if "PVTNUM" not in subset:
        if len(subset) != 1:
            logger.critical("If PVTNUM is not supplied, only one row should be given")
            return ""
        subset["PVTNUM"] = 1
    subset = subset.set_index("PVTNUM").sort_index()

    def _pvto_pvtnum(dframe: pd.DataFrame) -> str:
        """Create string with :term:`include file` contents
        for PVTO-data for a specific PVTNUM"""
        string = ""
        dframe = dframe.set_index("RS").sort_index()
        for rs in dframe.index.unique():
            string += _pvto_pvtnum_rs(dframe[dframe.index == rs])
        return string + "/\n"

    def _pvto_pvtnum_rs(dframe: pd.DataFrame) -> str:
        """Create string with :term:`include file` contents
        for PVTO-data for a particular RS"""
        string = ""
        assert len(dframe.index.unique()) == 1
        rs = dframe.index.values[0]
        string += f"{rs:20.7f}  "
        for rowidx, row in dframe.reset_index().iterrows():
            if rowidx > 0:
                indent = "\n" + " " * 22
            else:
                indent = ""
            string += (
                indent
                + f"{row['PRESSURE']:20.7f}  {row['VOLUMEFACTOR']:20.7f}  "
                + f"{row['VISCOSITY']:20.7f}"
            )
        string += f" /\n-- End RS={rs}\n"
        return string

    for pvtnum in subset.index.unique():
        string += _pvto_pvtnum(subset[subset.index == pvtnum])
    return string + "\n"

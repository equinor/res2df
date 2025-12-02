"""
Extract EQUIL from a :term:`.DATA file` as Pandas DataFrame
"""

import argparse
import logging
from collections.abc import Container
from pathlib import Path
from typing import Final

import opm.io
import pandas as pd

from .common import (
    comment_formatter,
    generic_deck_table,
    handle_wanted_keywords,
    keyworddata_to_df,
    write_dframe_stdout_file,
    write_inc_stdout_file,
)
from .common import df2res as common_df2res
from .common import fill_reverse_parser as common_fill_reverse_parser
from .inferdims import DIMS_POS, inject_xxxdims_ntxxx
from .res2csvlogger import getLogger_res2csv
from .resdatafiles import ResdataFiles

logger = logging.getLogger(__name__)

SUPPORTED_KEYWORDS: Final[list[str]] = ["EQUIL", "PBVD", "PDVD", "RSVD", "RVVD"]
TABLE_RENAMERS: Final[dict[str, dict[str, list[str]]]] = {
    "PBVD": {"DATA": ["Z", "PB"]},
    "PDVD": {"DATA": ["Z", "PD"]},
    "RSVD": {"DATA": ["Z", "RS"]},
    "RVVD": {"DATA": ["Z", "RV"]},
}
PHASE_RENAMERS: Final[dict[str, dict[str, str]]] = {
    "oil-water-gas": {
        "DATUM_DEPTH": "Z",
        "DATUM_PRESSURE": "PRESSURE",
        "OWC": "OWC",
        "PC_OWC": "PCOWC",
        "GOC": "GOC",
        "PC_GOC": "PCGOC",
        "BLACK_OIL_INIT": "INITRS",
        "BLACK_OIL_INIT_WG": "INITRV",
    },
    "gas-water": {
        "DATUM_DEPTH": "Z",
        "DATUM_PRESSURE": "PRESSURE",
        "OWC": "GWC",
        "PC_OWC": "PCGWC",
        "GOC": "IGNORE1",
        "PC_GOC": "IGNORE2",
        "BLACK_OIL_INIT": "IGNORE3",
        "BLACK_OIL_INIT_WG": "IGNORE4",
    },
    "oil-water": {
        "DATUM_DEPTH": "Z",
        "DATUM_PRESSURE": "PRESSURE",
        "OWC": "OWC",
        "PC_OWC": "PCOWC",
        "GOC": "IGNORE1",
        "PC_GOC": "IGNORE2",
        "BLACK_OIL_INIT": "IGNORE3",
        "BLACK_OIL_INIT_WG": "IGNORE4",
    },
    "oil-gas": {
        "DATUM_DEPTH": "Z",
        "DATUM_PRESSURE": "PRESSURE",
        "OWC": "IGNORE1",
        "PC_OWC": "IGNORE2",
        "GOC": "GOC",
        "PC_GOC": "PCGOC",
        "BLACK_OIL_INIT": "IGNORE3",
        "BLACK_OIL_INIT_WG": "IGNORE4",
    },
}


def df(
    deck: "str | ResdataFiles | opm.opmcommon_python.Deck",
    keywords: list[str] | None = None,
    ntequl: int | None = None,
) -> pd.DataFrame:
    """Extract EQUIL related keyword data, EQUIL, RSVD, RVVD
    PBVD and PDVD.

    How each data value in the EQUIL records are to be interpreted
    depends on the phase configuration in the :term:`deck`, which means
    that we need more than the EQUIL section alone to determine the
    dataframe.

    If ntequl is not supplied and EQLDIMS is not in the :term:`deck`, the
    equil data is not well defined in terms of OPM. This means
    that we have to infer the correct number of EQUIL lines from what
    gives us successful parsing from OPM. In those cases, the
    :term:`deck` must be supplied as a string, if not, extra EQUIL lines
    are possibly already removed by the OPM parser in resdatafiles.str2deck().

    Arguments:
        deck: :term:`.DATA file` or string with :term:`deck`. If
           not string, EQLDIMS must be present in the :term:`deck`.
        keywords: Requested keywords for which to extract data.
        ntequl: If not None, should state the NTEQUL in EQLDIMS. If
            None and EQLDIMS is not present, it will be inferred.

    Return:
        pd.DataFrame, at least with columns KEYWORD and EQLNUM
    """
    if isinstance(deck, ResdataFiles):
        deck = deck.get_deck()

    deck = inject_xxxdims_ntxxx("EQLDIMS", "NTEQUL", deck, ntequl)
    ntequl = deck["EQLDIMS"][0][DIMS_POS["NTEQUL"]].get_int(0)

    wanted_keywords = handle_wanted_keywords(keywords, deck, SUPPORTED_KEYWORDS)

    frames = []
    for keyword in wanted_keywords:
        # Construct the associated function names
        function_name = keyword.lower() + "_fromdeck"
        function = globals()[function_name]
        dframe = function(deck, ntequl=ntequl)
        frames.append(dframe.assign(KEYWORD=keyword))
    nonempty_frames = [frame for frame in frames if not frame.empty]
    if nonempty_frames:
        dframe = pd.concat(nonempty_frames, axis=0, sort=False, ignore_index=True)
        logger.info(
            "Extracted keywords %s for %g EQLNUMs",
            dframe["KEYWORD"].unique(),
            len(dframe["EQLNUM"].unique()),
        )
        return dframe
    logger.warning("No equil data found")
    return pd.DataFrame()


def rsvd_fromdeck(
    deck: "str | opm.opmcommon_python.Deck", ntequl: int | None = None
) -> pd.DataFrame:
    """Extract RSVD data from a :term:`deck`

    Args:
        deck
        ntequl: Number of EQLNUM regions in :term:`deck`. Will
            be inferred if not present in :term:`deck`
    """
    if "EQLDIMS" not in deck:
        deck = inject_xxxdims_ntxxx("EQLDIMS", "NTEQUL", deck, ntequl)
    return keyworddata_to_df(
        deck, "RSVD", renamer=TABLE_RENAMERS["RSVD"], recordcountername="EQLNUM"
    )


def rvvd_fromdeck(
    deck: "str | opm.opmcommon_python.Deck", ntequl: int | None = None
) -> pd.DataFrame:
    """Extract RVVD data from a :term:`deck`

    Args:
        deck
        ntequl: Number of EQLNUM regions in :term:`deck`. Will
            be inferred if not present in :term:`deck`
    """
    if "EQLDIMS" not in deck:
        deck = inject_xxxdims_ntxxx("EQLDIMS", "NTEQUL", deck, ntequl)
    return keyworddata_to_df(
        deck, "RVVD", renamer=TABLE_RENAMERS["RVVD"], recordcountername="EQLNUM"
    )


def pbvd_fromdeck(
    deck: "str | opm.opmcommon_python.Deck", ntequl: int | None = None
) -> pd.DataFrame:
    """Extract PBVD data from a :term:`deck`

    Args:
        deck
        ntequl: Number of EQLNUM regions in :term:`deck`. Will
            be inferred if not present in :term:`deck`
    """
    if "EQLDIMS" not in deck:
        deck = inject_xxxdims_ntxxx("EQLDIMS", "NTEQUL", deck, ntequl)
    return keyworddata_to_df(
        deck, "PBVD", renamer=TABLE_RENAMERS["PBVD"], recordcountername="EQLNUM"
    )


def pdvd_fromdeck(
    deck: "str | opm.opmcommon_python.Deck", ntequl: int | None = None
) -> pd.DataFrame:
    """Extract PDVD data from a :term:`deck`

    Args:
        deck
        ntequl: Number of EQLNUM regions in :term:`deck`. Will
            be inferred if not present in :term:`deck`
    """
    if "EQLDIMS" not in deck:
        deck = inject_xxxdims_ntxxx("EQLDIMS", "NTEQUL", deck, ntequl)
    return keyworddata_to_df(
        deck, "PDVD", renamer=TABLE_RENAMERS["PDVD"], recordcountername="EQLNUM"
    )


def phases_from_deck(deck: "str | opm.opmcommon_python.Deck") -> str:
    """Determined the set of phases from a :term:`deck`, as
    a string with values "oil-water-gas", "gas-water", "oil-water",
    or "oil-gas"

    Args:
        deck: A parsed :term:`deck` or :term:`.DATA file` as a string

    Returns:
        String with phase configuration. Empty string if inconclusive.
    """
    if "OIL" in deck and "GAS" in deck and "WATER" in deck:
        return "oil-water-gas"
    if "OIL" not in deck and "GAS" in deck and "WATER" in deck:
        return "gas-water"
    if "OIL" in deck and "GAS" not in deck and "WATER" in deck:
        return "oil-water"
    if "OIL" in deck and "GAS" in deck and "WATER" not in deck:
        return "oil-gas"
    return ""


def phases_from_columns(columns: Container[str]) -> str:
    """Determine the set of phases available in an
    equil dataframe, based on which columns are there.
    Returns "oil-water-gas", "gas-water", "oil-water",
    or "oil-gas"

    By this, we can pick the correct RENAMER to use.

    Args:
        columns: list of strings we can use for the determination

    Returns:
        String with phase configuration. Empty string if inconclusive.
    """
    if "OWC" in columns and "GOC" in columns:
        return "oil-water-gas"
    if "GWC" in columns and "OWC" not in columns and "GOC" not in columns:
        return "gas-water"
    if "OWC" in columns and "GOC" not in columns and "GWC" not in columns:
        return "oil-water"
    if "OWC" not in columns and "GOC" in columns and "GWC" not in columns:
        return "oil-gas"
    return ""


def equil_fromdeck(
    deck: "str | opm.opmcommon_python.Deck", ntequl: int | None = None
) -> pd.DataFrame:
    """Extract EQUIL data from a :term:`deck`

    If the :term:`deck` is supplied as a string object, the number
    of EQLNUM regions will be inferred if needed.

    Args:
        deck
        ntequl: Number of EQLNUM regions in :term:`deck`.
    """
    if "EQLDIMS" not in deck:
        deck = inject_xxxdims_ntxxx("EQLDIMS", "NTEQUL", deck, ntequl)

    phases = phases_from_deck(deck)
    if not phases or phases not in PHASE_RENAMERS:
        raise ValueError(f"Could not determine phase configuration, got '{phases}'")
    columnrenamer = PHASE_RENAMERS[phases]

    dataframe = keyworddata_to_df(
        deck, "EQUIL", renamer=columnrenamer, recordcountername="EQLNUM"
    )

    # The column handling can be made prettier..
    for col in dataframe.columns:
        if "IGNORE" in col:
            del dataframe[col]

    return dataframe


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parsers.

    Arguments:
        parser (argparse.ArgumentParser or argparse.subparser): parser to
            fill with arguments
    """
    parser.add_argument(
        "DATAFILE", help="Name of the .DATA input file for the reservoir simulator"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help=("Name of output csv file. Use '-' for stdout."),
        default="equil.csv",
    )
    parser.add_argument(
        "-k",
        "--keywords",
        nargs="+",
        help=(
            "List of EQUIL/SOLUTION keywords to include. "
            "If not supplied, all supported keywords will be included."
        ),
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def fill_reverse_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Fill a parser for the operation dataframe -> resdata :term:`include file`"""
    return common_fill_reverse_parser(parser, "EQUIL, RSVD++", "solution.inc")


def equil_main(args: argparse.Namespace) -> None:
    """Read from disk and write CSV back to disk"""
    logger = getLogger_res2csv(__name__, vars(args))
    resdatafiles = ResdataFiles(args.DATAFILE)
    if resdatafiles:
        deck = resdatafiles.get_deck()
    if "EQLDIMS" in deck:
        # Things are easier when a full deck with (correct) EQLDIMS
        # is supplied:
        equil_df = df(deck, keywords=args.keywords)
    else:
        # This might be an include file for which we have to infer/guess
        # EQLDIMS. Then we send it to df() as a string
        equil_df = df(Path(args.DATAFILE).read_text(encoding="utf-8"))

    if "EQLNUM" in equil_df and "KEYWORD" in equil_df:
        eqlnums = str(len(equil_df["EQLNUM"].unique()))
        keywords = str(equil_df["KEYWORD"].unique())
    else:
        eqlnums = "-"
        keywords = "-"
    write_dframe_stdout_file(
        equil_df,
        args.output,
        index=False,
        caller_logger=logger,
        logstr=f"Unique EQLNUMs: {eqlnums}, keywords: {keywords}",
    )


def equil_reverse_main(args: argparse.Namespace) -> None:
    """Entry-point for module, for command line utility
    for CSV to reservoir simulator :term:`include files <include file>`
    """
    logger = getLogger_res2csv(__name__, vars(args))
    equil_df = pd.read_csv(args.csvfile)
    logger.info("Parsed %s", args.csvfile)
    inc_string = df2res(equil_df, keywords=args.keywords)
    write_inc_stdout_file(inc_string, args.output)


def df2res(
    equil_df: pd.DataFrame,
    keywords: list[str] | None = None,
    comments: dict[str, str] | None = None,
    withphases: bool = False,
    filename: str | None = None,
) -> str:
    """Generate string contents of :term:`include files <include file>`
    from dataframes with solution (EQUIL, RSVD++) data.

    Args:
        equil_df: Dataframe with res2df format.
        keywords: List of keywords to include. Must be
            supported and present in the incoming dataframe.
        comments: Dictionary indexed by keyword with comments to be
            included pr. keyword. If a key named "master" is present
            it will be used as a master comment for the outputted file.
        withphases: If True, the phase configuration keywords
            will be outputted. This is mostly for testing, and should
            not be necessary in production.
        filename: If supplied, the generated text will also be dumped
            to file.

    """
    string = ""
    if withphases:
        string += (
            phases_from_columns(equil_df.columns).upper().replace("-", "\n") + "\n\n"
        )
    string += common_df2res(
        equil_df,
        keywords=keywords,
        comments=comments,
        supported=SUPPORTED_KEYWORDS,
        consecutive="EQLNUM",
        filename=filename,
    )
    return string


def df2res_equil(dframe: pd.DataFrame, comment: str | None = None) -> str:
    """Create string with :term:`include file` contents for EQUIL keyword

    Args:
        dframe: Containing EQUIL data
        comment: Text that will be included as a comment
    """
    if dframe.empty:
        return "-- No data!"
    string = "EQUIL\n"
    string += comment_formatter(comment)
    # Use everything if KEYWORD not in dframe..
    subset = dframe if "KEYWORD" not in dframe else dframe[dframe["KEYWORD"] == "EQUIL"]
    if "EQLNUM" not in subset:
        if len(subset) != 1:
            logger.critical("If EQLNUM is not supplied, only one row should be given")
            return ""
        subset["EQLNUM"] = 1
    subset = subset.set_index("EQLNUM").sort_index()

    phases = phases_from_columns(subset.columns)

    return generic_deck_table(
        subset,
        "EQUIL",
        renamer=PHASE_RENAMERS[phases],
        comment=comment,
        drop_trailing_columns=False,
    )


def df2res_rsvd(dframe: pd.DataFrame, comment: str | None = None) -> str:
    """Create string with :term:`include file` contents for RSVD keyword

    This data consists of one table (rs as a function
    of depth) for each EQLNUM

    Args:
        dframe: Containing RSVD data
        comment Text that will be included as a comment
    """
    return _df2res_equilfuncs("RSVD", dframe, comment)


def df2res_rvvd(dframe: pd.DataFrame, comment: str | None = None) -> str:
    """Create string with :term:`include file` contents for RVVD keyword

    This data consists of one table (rv as a function
    of depth) for each EQLNUM

    Args:
        dframe: Containing RVVD data
        comment: Text that will be included as a comment
    """
    return _df2res_equilfuncs("RVVD", dframe, comment)


def df2res_pbvd(dframe: pd.DataFrame, comment: str | None = None) -> str:
    """Create string with :term:`include file` contents for PBVD keyword

    Bubble-point versus depth

    This data consists of one table (Pb as a function
    of depth) for each EQLNUM

    Args:
        dframe: Containing PBVD data
        comment: Text that will be included as a comment
    """
    return _df2res_equilfuncs("PBVD", dframe, comment)


def df2res_pdvd(dframe: pd.DataFrame, comment: str | None = None) -> str:
    """Create string with :term:`include file` contents for PDVD keyword.

    Dew-point versus depth.

    This data consists of one table (Pd as a function
    of depth) for each EQLNUM

    Args:
        dframe: Containing PDVD data
        comment: Text that will be included as a comment
    """
    return _df2res_equilfuncs("PDVD", dframe, comment)


def _df2res_equilfuncs(
    keyword: str, dframe: pd.DataFrame, comment: str | None = None
) -> str:
    """Internal function to be used by df2res_<keyword>() functions"""
    if dframe.empty:
        return "-- No data!"
    string = f"{keyword}\n"
    string += comment_formatter(comment)
    col_headers = TABLE_RENAMERS[keyword]["DATA"]

    string += f"--   {'DEPTH':^21} {col_headers[1]:^21} \n"
    # Use everything if KEYWORD not in dframe..
    subset = dframe if "KEYWORD" not in dframe else dframe[dframe["KEYWORD"] == keyword]

    def _df2res_equilfuncs_eqlnum(dframe: pd.DataFrame) -> str:
        """Create string with :term:`include file` contents
        for one equilibriation function table for a specific EQLNUM

        Args:
            dframe (pd.DataFrame): Cropped to only contain data for one EQLNUM

        Returns:
            string
        """
        string = ""
        dframe = dframe.sort_values("Z")
        for _, row in dframe.iterrows():
            string += f"  {row[col_headers[0]]:20.7f} {row[col_headers[1]]:20.7f}\n"
        return string + "/\n"

    subset = subset.set_index("EQLNUM").sort_index()
    for eqlnum in subset.index.unique():
        string += f"-- EQLNUM: {eqlnum}\n"
        string += _df2res_equilfuncs_eqlnum(subset[subset.index == eqlnum])
    return string + "\n"

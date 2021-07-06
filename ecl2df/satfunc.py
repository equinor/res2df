"""
Extract saturation function data (SWOF, SGOF, SWFN, etc.)
from an Eclipse deck as Pandas DataFrame.

Data can be extracted from a full Eclipse deck (`*.DATA`)
or from individual files.

Note that when parsing from individual files, it is
undefined in the syntax how many saturation functions (SATNUMs) are
present. For convenience, it is possible to estimate the count of
SATNUMs, but whenever this is known, it is recommended to either supply
TABDIMS or to supply the satnumcount directly to avoid possible bugs.

"""
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Union, Optional

import pandas as pd

try:
    # pylint: disable=unused-import
    import opm.io
except ImportError:
    pass

from ecl2df import inferdims, common
from .eclfiles import EclFiles
from .common import write_dframe_stdout_file

logger: logging.Logger = logging.getLogger(__name__)

SUPPORTED_KEYWORDS: List[str] = [
    "SWOF",
    "SGOF",
    "SWFN",
    "SGWFN",
    "SOF2",
    "SGFN",
    "SOF3",
    "SLGOF",
]

# RENAMERS are a dictionary of dictionaries, referring to
# how we should rename deck record items, from the JSON
# files in opm.common and into Dataframe column names.
RENAMERS: Dict[str, Dict[str, Union[List[str], str]]] = {}
RENAMERS["SGFN"] = {"DATA": ["SG", "KRG", "PCOG"]}
RENAMERS["SGOF"] = {"DATA": ["SG", "KRG", "KROG", "PCOG"]}
RENAMERS["SGWFN"] = {"DATA": ["SG", "KRG", "KRW", "PCGW"]}
RENAMERS["SLGOF"] = {"DATA": ["SL", "KRG", "KRO", "PCOG"]}
RENAMERS["SOF2"] = {"DATA": ["SO", "KRO"]}
RENAMERS["SOF3"] = {"DATA": ["SO", "KROW", "KROG"]}
RENAMERS["SWFN"] = {"DATA": ["SW", "KRW", "PCOW"]}
RENAMERS["SWOF"] = {"DATA": ["SW", "KRW", "KROW", "PCOW"]}


def xx_inject_satnumcount(deckstr: str, satnumcount: int) -> str:
    """Insert a TABDIMS with NTSFUN into a deck

    This is simple string manipulation, not OPM
    deck manipulation (which might be possible to do).

    Arguments:
        deckstr: A string containing a partial deck (f.ex only
            the SWOF keyword).
        satnumcount: The NTSFUN number to use in TABDIMS
            (this function does not care if it is correct or not)
    Returns:
        New deck with TABDIMS prepended.
    """
    if "TABDIMS" in deckstr:
        logger.warning("Not inserting TABDIMS in a deck where already exists")
        return deckstr
    return "TABDIMS\n " + str(satnumcount) + " /\n\n" + str(deckstr)


def df(
    deck: Union[str, "opm.libopmcommon_python.Deck"],
    keywords: Optional[List[str]] = None,
    ntsfun: Optional[int] = None,
) -> pd.DataFrame:
    """Extract the data in the saturation function keywords as a Pandas
    DataFrames.

    Data for all saturation functions are merged into one dataframe.
    The two first columns in the dataframe are 'KEYWORD' (which can be
    SWOF, SGOF, etc.), and then SATNUM which is an index counter from 1 and
    onwards. Then follows the data for each individual keyword that
    is found in the deck.

    SATNUM data can only be parsed correctly if TABDIMS is present
    and stating how many saturation functions there should be.
    If you have a string with TABDIMS missing, you must supply
    this as a string to this function, and not a parsed deck, as
    the default parser in EclFiles is very permissive (and only
    returning the first function by default).

    Arguments:
        deck: Incoming data deck. Always
            supply as a string if you don't know TABDIMS-NTSFUN.
        keywords: Requested keywords for which to
            to extract data.
        ntsfun: Number of SATNUMs defined in the deck, only
            needed if TABDIMS with NTSFUN is not found in the deck.
            If not supplied (or None) and NTSFUN is not defined,
            it will be attempted inferred.

    Return:
        pd.DataFrame, columns 'KEYWORD', 'SW', 'KRW', 'KROW', 'PC', ..
    """
    if isinstance(deck, EclFiles):
        # NB: If this is done on include files and not on DATA files
        # we can loose data for SATNUM > 1
        deck = deck.get_ecldeck()
    deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    assert "TABDIMS" in deck
    ntsfun = deck["TABDIMS"][0][inferdims.DIMS_POS["NTSFUN"]].get_int(0)

    wanted_keywords = common.handle_wanted_keywords(keywords, deck, SUPPORTED_KEYWORDS)

    frames = []
    for keyword in wanted_keywords:
        # Construct the associated function names
        function_name = keyword.lower() + "_fromdeck"
        function = globals()[function_name]
        dframe = function(deck, ntsfun=ntsfun)
        frames.append(dframe.assign(KEYWORD=keyword))
    nonempty_frames = [frame for frame in frames if not frame.empty]
    if nonempty_frames:
        dframe = pd.concat(nonempty_frames, axis=0, sort=False, ignore_index=True)
        # We want to sort the keywords by the order they appear in
        # SUPPORTED_KEYWORDS (mainly to get WaterOil before GasOil)
        # We do that by converting to a Categorical series:
        dframe["KEYWORD"] = pd.Categorical(dframe["KEYWORD"], SUPPORTED_KEYWORDS)
        dframe.sort_values(["SATNUM", "KEYWORD"], inplace=True)
        dframe["KEYWORD"] = dframe["KEYWORD"].astype(str)
        return dframe
    return pd.DataFrame()


def swof_fromdeck(
    deck: Union[str, "opm.libopmcommon_python.Deck"], ntsfun: Optional[int] = None
) -> pd.DataFrame:
    """Extract SWOF data from a deck

    Args:
        deck
        ntsfun: Number of SATNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "TABDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    return common.ecl_keyworddata_to_df(
        deck, "SWOF", renamer=RENAMERS["SWOF"], recordcountername="SATNUM"
    )


def sgof_fromdeck(
    deck: Union[str, "opm.libopmcommon_python.Deck"], ntsfun: Optional[int] = None
) -> pd.DataFrame:
    """Extract SGOF data from a deck

    Args:
        deck
        ntsfun: Number of SATNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "TABDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    return common.ecl_keyworddata_to_df(
        deck, "SGOF", renamer=RENAMERS["SGOF"], recordcountername="SATNUM"
    )


def swfn_fromdeck(
    deck: Union[str, "opm.libopmcommon_python.Deck"], ntsfun: Optional[int] = None
) -> pd.DataFrame:
    """Extract SWFN data from a deck

    Args:
        deck
        ntsfun: Number of SATNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "TABDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    return common.ecl_keyworddata_to_df(
        deck, "SWFN", renamer=RENAMERS["SWFN"], recordcountername="SATNUM"
    )


def sof2_fromdeck(
    deck: Union[str, "opm.libopmcommon_python.Deck"], ntsfun: Optional[int] = None
) -> pd.DataFrame:
    """Extract SOF2 data from a deck

    Args:
        deck
        ntsfun: Number of SATNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "TABDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    return common.ecl_keyworddata_to_df(
        deck, "SOF2", renamer=RENAMERS["SOF2"], recordcountername="SATNUM"
    )


def sgfn_fromdeck(
    deck: Union[str, "opm.libopmcommon_python.Deck"], ntsfun: Optional[int] = None
) -> pd.DataFrame:
    """Extract SGFN data from a deck

    Args:
        deck
        ntsfun: Number of SATNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "TABDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    return common.ecl_keyworddata_to_df(
        deck, "SGFN", renamer=RENAMERS["SGFN"], recordcountername="SATNUM"
    )


def sgwfn_fromdeck(
    deck: Union[str, "opm.libopmcommon_python.Deck"], ntsfun: Optional[int] = None
) -> pd.DataFrame:
    """Extract SGWFN data from a deck

    Args:
        deck
        ntsfun: Number of SATNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "TABDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    return common.ecl_keyworddata_to_df(
        deck, "SGWFN", renamer=RENAMERS["SGWFN"], recordcountername="SATNUM"
    )


def sof3_fromdeck(
    deck: Union[str, "opm.libopmcommon_python.Deck"], ntsfun: Optional[int] = None
) -> pd.DataFrame:
    """Extract SOF3 data from a deck

    Args:
        deck
        ntsfun: Number of SATNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "TABDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    return common.ecl_keyworddata_to_df(
        deck, "SOF3", renamer=RENAMERS["SOF3"], recordcountername="SATNUM"
    )


def slgof_fromdeck(
    deck: Union[str, "opm.libopmcommon_python.Deck"], ntsfun: Optional[int] = None
) -> pd.DataFrame:
    """Extract SLGOF data from a deck

    Args:
        deck
        ntsfun: Number of SATNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "TABDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("TABDIMS", "NTSFUN", deck, ntsfun)
    return common.ecl_keyworddata_to_df(
        deck, "SLGOF", renamer=RENAMERS["SLGOF"], recordcountername="SATNUM"
    )


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parsers.

    Arguments:
        parser (ArgumentParser or subparser): parser to fill with arguments
    """
    parser.add_argument(
        "DATAFILE", help="Name of Eclipse DATA file or file with saturation functions."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file.",
        default="satfuncs.csv",
    )
    parser.add_argument(
        "-k",
        "--keywords",
        nargs="+",
        help=(
            "List of saturation function keywords to fetch data from. "
            "If not supplied, all supported keywords will be included."
        ),
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def fill_reverse_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Fill a parser for the operation dataframe -> eclipse include file"""
    return common.fill_reverse_parser(parser, "SWOF, SGOF++", "relperm.inc")


def satfunc_main(args) -> None:
    """Entry-point for module, for command line utility"""
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    if "TABDIMS" in deck:
        # Things are easier when a full deck with (correct) TABDIMS
        # is supplied:
        satfunc_df = df(eclfiles, keywords=args.keywords)
    else:
        # This might be an include file for which we have to infer/guess
        # TABDIMS. Then we send it to df() as a string
        satfunc_df = df(Path(args.DATAFILE).read_text(), keywords=args.keywords)
    if not satfunc_df.empty:
        write_dframe_stdout_file(
            satfunc_df,
            args.output,
            index=False,
            caller_logger=logger,
            logstr="Unique SATNUMs: {}, saturation keywords: {}".format(
                str(len(satfunc_df["SATNUM"].unique())),
                str(satfunc_df["KEYWORD"].unique()),
            ),
        )
    else:
        logger.error("Empty saturation functions data, not written to disk!")


def satfunc_reverse_main(args) -> None:
    """For command line utility for CSV to Eclipse"""
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    satfunc_df = pd.read_csv(args.csvfile)
    logger.info("Parsed %s", args.csvfile)
    inc_string = df2ecl(satfunc_df, keywords=args.keywords)
    common.write_inc_stdout_file(inc_string, args.output)


def df2ecl(
    satfunc_df: pd.DataFrame,
    keywords: Optional[List[str]] = None,
    comments: Optional[Dict[str, str]] = None,
    filename: Optional[str] = None,
) -> str:
    """Generate Eclipse include strings from dataframes with
    saturation functions (SWOF, SGOF, ...)

    Args:
        satfunc_df: Dataframe with data on ecl2df format.
        keywords: List of keywords to include. Must be
            supported and present in the incoming dataframe. Keywords
            are printed in the order defined by this list.
        comments: Dictionary indexed by keyword with comments to be
            included pr. keyword. If a key named "master" is present
            it will be used as a master comment for the outputted file.
        filename: If supplied, the generated text will also be dumped
            to file.

    Returns:
        Generated Eclipse include string

    """
    string = ""
    string += common.df2ecl(
        satfunc_df,
        keywords=keywords,
        comments=comments,
        supported=SUPPORTED_KEYWORDS,
        consecutive="SATNUM",
        filename=filename,
    )
    return string


def df2ecl_swof(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Print SWOF data. Used by df2ecl().

    Args:
        dframe: Containing SWOF data
        comment: Text that will be included as a comment
    """
    return _df2ecl_satfuncs("SWOF", dframe, comment)


def df2ecl_sgof(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Print SGOF data. Used by df2ecl().

    Args:
        dframe: Containing SGOF data
        comment: Text that will be included as a comment
    """
    return _df2ecl_satfuncs("SGOF", dframe, comment)


def df2ecl_sgfn(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Print SGFN data. Used by df2ecl().

    Args:
        dframe: Containing SGFN data
        comment: Text that will be included as a comment
    """
    return _df2ecl_satfuncs("SGFN", dframe, comment)


def df2ecl_sgwfn(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Print SGWFN data. Used by df2ecl().

    Args:
        dframe: Containing SGWFN data
        comment: Text that will be included as a comment
    """
    return _df2ecl_satfuncs("SGWFN", dframe, comment)


def df2ecl_swfn(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Print SWFN data. Used by df2ecl().

    Args:
        dframe: Containing SWFN data
        comment: Text that will be included as a comment
    """
    return _df2ecl_satfuncs("SWFN", dframe, comment)


def df2ecl_slgof(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Print SLGOF data. Used by df2ecl().

    Args:
        dframe: Containing SLGOF data
        comment: Text that will be included as a comment
    """
    return _df2ecl_satfuncs("SLGOF", dframe, comment)


def df2ecl_sof2(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Print SOF2 data. Used by df2ecl().

    Args:
        dframe: Containing SOF2 data
        comment: Text that will be included as a comment
    """
    return _df2ecl_satfuncs("SOF2", dframe, comment)


def df2ecl_sof3(dframe: pd.DataFrame, comment: Optional[str] = None) -> str:
    """Print SOF3 data. Used by df2ecl().

    Args:
        dframe: Containing SOF3 data
        comment: Text that will be included as a comment
    """
    return _df2ecl_satfuncs("SOF3", dframe, comment)


def _df2ecl_satfuncs(
    keyword: str, dframe: pd.DataFrame, comment: Optional[str] = None
) -> str:
    if dframe.empty:
        return "-- No data!\n"
    string = "{}\n".format(keyword)
    string += common.comment_formatter(comment)

    if "KEYWORD" not in dframe:
        # Use everything..
        subset = dframe
    else:
        subset = dframe[dframe["KEYWORD"] == keyword]
    if "SATNUM" not in subset:
        subset["SATNUM"] = 1
    subset = subset.set_index("SATNUM").sort_index()

    # Make a function that is to be called for each SATNUM
    def _df2ecl_satfuncs_satnum(keyword, dframe):
        """Print one saturation function for one specific SATNUM"""
        col_headers = RENAMERS[keyword]["DATA"]
        string = (
            "-- "
            + dframe[col_headers]
            .to_string(float_format=" %g", header=True, index=False)
            .strip()
        )
        return string + "\n/\n"

    # Loop over every SATNUM
    for satnum in subset.index.unique():
        string += "-- SATNUM: {}\n".format(satnum)
        string += _df2ecl_satfuncs_satnum(keyword, subset[subset.index == satnum])
    return string + "\n"

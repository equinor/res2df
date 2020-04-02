"""
Extract the PVT data from an Eclipse (input) deck as Pandas Dataframes

Data can be extracted from a full Eclipse deck (*.DATA)
or from individual files.
"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys
import logging

import numpy as np
import pandas as pd

from ecl2df import inferdims
from .eclfiles import EclFiles

from .common import ecl_keyworddata_to_df, comment_formatter

logging.basicConfig()
logger = logging.getLogger(__name__)

SUPPORTED_KEYWORDS = ["PVTO", "PVDO", "PVTG", "PVDG", "DENSITY", "ROCK", "PVTW"]

# The renamers listed here map from opm-common json item names to
# desired column names in produced dataframes. They also to a certain
# extent determine the structure of the dataframe, in particular
# for keywords with arbitrary data amount pr. record (PVTO f.ex)
RENAMERS = {}

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


def inject_ntpvt(deckstr, ntpvt):
    """Insert a TABDIMS with NTPVT into a deck

    This is simple string manipulation, not opm.io
    deck manipulation (which might be possible to do).

    Arguments:
        deckstr (str): A string containing a partial deck (f.ex only
            the DENSITY keyword).
        ntpvt (int): The number for NTPVT to use in TABDIMS
            (this function does not care if it is correct or not)
    Returns:
        str: New deck with TABDIMS prepended.
    """
    if "TABDIMS" in deckstr:
        logger.warning("Not inserting TABDIMS in a deck where already exists")
        return deckstr
    return "TABDIMS\n 1* " + str(ntpvt) + " /\n\n" + str(deckstr)


def inject_tabdims_ntpvt(deck, ntpvt=None):
    """Ensures TABDIMS is present in a deck.

    If ntpvt==None and NTPVT is not in the deck, NTPVT will be inferred
    through trial-and-error parsing of the deck, and then injected
    into the deck.

    Args:
        deck (str or opm.io deck): A data deck. If NTPVT is to be estimated
            this must be a string and not a fully parsed deck.
        nptvt (int): Supply this if NTPVT is known, but not present in the
            deck, this will override any NTPVT guessing. If the deck already
            contains TABDIMS, this will be ignored.

    Returns:
        opm.io Deck object
    """
    if "TABDIMS" not in deck:
        if not isinstance(deck, str):
            logger.critical(
                (
                    "Can't guess NTPVT from a parsed deck without TABDIMS.\n"
                    "Only data for the first PVT region will be returned.\n"
                    "Supply the deck as a string to automatically determine NTPVT"
                )
            )
            ntpvt = 1
        else:
            if ntpvt is None:
                pvtnum_estimate = inferdims.guess_dim(deck, "TABDIMS", 1)
                logger.warning("Guessed NPTVT=%s", str(pvtnum_estimate))
            else:
                pvtnum_estimate = ntpvt
            augmented_strdeck = inferdims.inject_dimcount(
                str(deck), "TABDIMS", inferdims.NTPVT_POS, pvtnum_estimate
            )
            # Overwrite the deck object
            deck = EclFiles.str2deck(augmented_strdeck)
    else:
        logger.warning("Ignoring NTPVT argument, it is already in the deck")
    if isinstance(deck, str):
        # If a string is supplied as a deck, we always return a parsed Deck object
        deck = EclFiles.str2deck(deck)
    return deck


def pvtw_fromdeck(deck, ntpvt=None):
    """Extract PVTW from a deck

    Args:
        deck (str or opm.common Deck)
        ntpvt (int): Number of PVT regions in deck. Will
            be inferred if not present in deck.
    """
    if "TABDIMS" not in deck:
        deck = inject_tabdims_ntpvt(deck, ntpvt=ntpvt)
    return ecl_keyworddata_to_df(
        deck, "PVTW", renamer=RENAMERS["PVTW"], indexname="PVTNUM"
    )


def density_fromdeck(deck, ntpvt=None):
    """Extract DENSITY from a deck

    Args:
        deck (str or opm.common Deck)
        ntpvt (int): Number of PVT regions in deck. Will
            be inferred if not present in deck.
    """
    if "TABDIMS" not in deck:
        deck = inject_tabdims_ntpvt(deck, ntpvt=ntpvt)
    return ecl_keyworddata_to_df(
        deck, "DENSITY", renamer=RENAMERS["DENSITY"], indexname="PVTNUM"
    )


def rock_fromdeck(deck, ntpvt=None):
    """Extract ROCK from a deck

    Args:
        deck (str or opm.common Deck)
        ntpvt (int): Number of PVT regions in deck. Will
            be inferred if not present in deck.
    """
    if "TABDIMS" not in deck:
        deck = inject_tabdims_ntpvt(deck, ntpvt=ntpvt)
    return ecl_keyworddata_to_df(
        deck, "ROCK", renamer=RENAMERS["ROCK"], indexname="PVTNUM"
    )


def pvto_fromdeck(deck, ntpvt=None):
    """Extract PVTO from a deck

    Args:
        deck (str or opm.common Deck)
        ntpvt (int): Number of PVT regions in deck. Will
            be inferred if not present in deck.
    """
    if "TABDIMS" not in deck:
        deck = inject_tabdims_ntpvt(deck, ntpvt=ntpvt)
    pvto_df = ecl_keyworddata_to_df(
        deck, "PVTO", renamer=RENAMERS["PVTO"], emptyrecordcountername="PVTNUM"
    )
    return pvto_df


def pvdo_fromdeck(deck, ntpvt=None):
    """Extract PVDO from a deck

    Args:
        deck (str or opm.common Deck)
        ntpvt (int): Number of PVT regions in deck. Will
            be inferred if not present in deck.
    """
    if "TABDIMS" not in deck:
        deck = inject_tabdims_ntpvt(deck, ntpvt=ntpvt)
    pvdg_df = ecl_keyworddata_to_df(
        deck, "PVDO", renamer=RENAMERS["PVDO"], indexname="PVTNUM"
    )
    return pvdg_df


def pvdg_fromdeck(deck, ntpvt=None):
    """Extract PVDG from a deck

    Args:
        deck (str or opm.common Deck)
        ntpvt (int): Number of PVT regions in deck. Will
            be inferred if not present in deck.
    """
    if "TABDIMS" not in deck:
        deck = inject_tabdims_ntpvt(deck, ntpvt=ntpvt)
    pvdg_df = ecl_keyworddata_to_df(
        deck, "PVDG", renamer=RENAMERS["PVDG"], indexname="PVTNUM"
    )
    return pvdg_df


def pvtg_fromdeck(deck, ntpvt=None):
    """Extract PVTG from a deck

    Args:
        deck (str or opm.common Deck)
        ntpvt (int): Number of PVT regions in deck. Will
            be inferred if not present in deck.
    """
    if "TABDIMS" not in deck:
        deck = inject_tabdims_ntpvt(deck, ntpvt=ntpvt)
    pvtg_df = ecl_keyworddata_to_df(
        deck, "PVTG", renamer=RENAMERS["PVTG"], emptyrecordcountername="PVTNUM"
    )
    return pvtg_df


def df(deck, keywords=None, ntpvt=None):
    """Extract all (most) PVT data from a deck.

    If you want to call this function on Eclipse include files,
    read them in to strings as in this example:

    > pvt_df = pvt.df(open("pvt.inc").read())

    Arguments:
        deck (opm.io deck or str): Incoming data deck. Always
            supply as a string if you don't know TABDIMS-NTSFUN.
        keywords (list of str): List of keywords for which data is
            wanted. All data will be merged into one dataframe.
        pvtnumcount (int): Number of PVTNUMs defined in the deck, only
            needed if TABDIMS with NTPVT is not found in the deck.
            If not supplied (or None) and NTPVT is not defined,
            it will be attempted inferred.

    Return:
        pd.DataFrame
    """
    if not isinstance(keywords, list):
        keywords = [keywords]  # Can still be None
    if isinstance(deck, EclFiles):
        deck = deck.get_ecldeck()
    if "TABDIMS" not in deck:
        deck = inject_tabdims_ntpvt(deck, ntpvt=ntpvt)
    ntpvt = deck["TABDIMS"][0][inferdims.NTPVT_POS].get_int(0)
    if keywords[0] is None and len(keywords) == 1:
        # By default, select all supported PVT keywords:
        keywords = SUPPORTED_KEYWORDS
    else:
        # Warn if some keywords are unsupported:
        not_supported = [
            keyword for keyword in keywords if keyword not in SUPPORTED_KEYWORDS
        ]
        if not_supported:
            logger.warning(
                "Requested keyword(s) not supported by ecl2df.pvt: %s",
                str(not_supported),
            )
        # Reduce to only supported keywords:
        keywords = list(set(keywords) - set(not_supported))
        # Warn if some requested keywords are not in deck:
        not_in_deck = [keyword for keyword in keywords if keyword not in deck]
        if not_in_deck:
            logger.warning(
                "Requested keyword(s) not present in deck: %s", str(not_in_deck)
            )
    keywords_in_deck = [keyword for keyword in keywords if keyword in deck]
    assert isinstance(keywords, list)

    frames = []
    for keyword in keywords_in_deck:
        # Construct the associated function names
        function_name = keyword.lower() + "_fromdeck"
        function = globals()[function_name]
        dframe = function(deck, ntpvt=ntpvt)
        frames.append(dframe.assign(KEYWORD=keyword))
    nonempty_frames = [frame for frame in frames if not frame.empty]
    if nonempty_frames:
        return pd.concat(nonempty_frames, axis=0, sort=False, ignore_index=True)
    return pd.DataFrame()


def fill_parser(parser):
    """Set up sys.argv parsers for parsing Eclipse deck or
    include files into dataframes

    Arguments:
        parser (ArgumentParser or subparser): parser to fill with arguments
    """
    parser.add_argument(
        "DATAFILE", help="Name of Eclipse DATA file or file with PVT keywords."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help=("Name of output csv file, default pvt.csv. ", "Use '-' for stdout."),
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


def fill_reverse_parser(parser):
    """Set up sys.argv parsers for writing Eclipse include files from
    dataframes (as CSV files)

    Arguments:
        parser (ArgumentParser or subparser): parser to fill with arguments
    """
    parser.add_argument(
        "csvfile", help="Name of CSV file with PVT data on ecl2df format"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help=(
            "Name of output Eclipse include file file, default pvt.inc. "
            "Use '-' for stdout."
        ),
        default="pvt.inc",
    )
    parser.add_argument(
        "-k",
        "--keywords",
        nargs="+",
        help=(
            "List of PVT keywords to include. "
            "If not supplied, all supported and found keywords will be included."
        ),
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def pvt_main(args):
    """Entry-point for module, for command line utility for Eclipse to CSV"""
    if args.verbose:
        logger.setLevel(logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    logger.info("Parsed %s", args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    if "TABDIMS" in deck:
        # Things are easier when a full deck with correct TABDIMS
        # is supplied:
        pvt_df = df(deck, keywords=args.keywords)
    else:
        # When TABDIMS is not present, the code will try to infer
        # the number of saturation functions, this is necessarily
        # more error-prone, and it needs a string as input.
        stringdeck = "".join(open(args.DATAFILE).readlines())
        pvt_df = df(stringdeck, keywords=args.keywords)
    if not pvt_df.empty:
        if args.output == "-":
            # Ignore pipe errors when writing to stdout.
            from signal import signal, SIGPIPE, SIG_DFL

            signal(SIGPIPE, SIG_DFL)
            pvt_df.to_csv(sys.stdout, index=False)
        else:
            logger.info(
                "PVTNUM: %d, PVT keywords: %s",
                len(pvt_df["PVTNUM"].unique()),
                str(pvt_df["KEYWORD"].unique()),
            )
            pvt_df.to_csv(args.output, index=False)
            print("Wrote to " + args.output)


def pvt_reverse_main(args):
    """Entry-point for module, for command line utility for CSV to Eclipse"""
    if args.verbose:
        logger.setLevel(logging.INFO)
    pvt_df = pd.read_csv(args.csvfile)
    logger.info("Parsed %s", args.csvfile)
    inc_string = df2ecl(pvt_df, keywords=args.keywords)

    if args.output == "-":
        # Ignore pipe errors when writing to stdout.
        from signal import signal, SIGPIPE, SIG_DFL

        signal(SIGPIPE, SIG_DFL)
        print(inc_string)
    else:
        with open(args.output, "w") as f_handle:
            f_handle.write(inc_string)
        print("Wrote to " + args.output)


# Now comes functionality for the reverse operation, from a dataframe to
# Eclipse include files:


def df2ecl(pvt_df, keywords=None, comments=None):
    """Generate Eclipse include strings from PVT dataframes

    Args:
        pvt_df (pd.DataFrame): Dataframe with PVT data on ecl2df format.
        keywords (list of str): List of keywords to include. Must be
            supported and present in the incoming dataframe.
        comments (dict): Dictionary indexed by keyword with comments to be
            included pr.  keyword.
    """
    # Check consecutive PVTNUM in frame:
    if pvt_df.empty:
        raise ValueError("Empty dataframe")
    if "PVTNUM" in pvt_df:
        if not (
            min(pvt_df["PVTNUM"]) == 1
            and len(pvt_df["PVTNUM"].unique()) == max(pvt_df["PVTNUM"])
        ):
            logger.critical(
                "PVTNUM inconsistent in input dataframe, got the values %s",
                str(pvt_df["PVTNUM"].unique()),
            )
            raise ValueError

    # "KEYWORD" must always be in the dataframe:
    if "KEYWORD" not in pvt_df:
        raise ValueError("KEYWORD must be in the dataframe")

    if comments is None:
        comments = {}
    if not isinstance(keywords, list):
        keywords = [keywords]  # Can still be None
    keywords_in_frame = set(pvt_df["KEYWORD"])
    if keywords[0] is None and len(keywords) == 1:
        # By default, select all supported PVT keywords:
        keywords = SUPPORTED_KEYWORDS
    else:
        # Warn if some keywords are unsupported:
        not_supported = set(keywords) - set(SUPPORTED_KEYWORDS)
        if not_supported:
            logger.warning(
                "Requested keyword(s) not supported by ecl2df.pvt: %s",
                str(not_supported),
            )
        # Reduce to only supported keywords:
        keywords = list(set(keywords) - set(not_supported))
        # Warn if some requested keywords are not in frame:
        not_in_frame = set(keywords) - keywords_in_frame
        if not_in_frame:
            logger.warning(
                "Requested keyword(s) not present in dataframe: %s", str(not_in_frame)
            )
    keywords = keywords_in_frame.intersection(keywords).intersection(
        set(SUPPORTED_KEYWORDS)
    )
    string = ""
    for keyword in keywords:
        # Construct the associated function names
        function_name = "df2ecl_" + keyword.lower()
        function = globals()[function_name]
        if keyword in comments:
            string += function(pvt_df, comments[keyword])
        else:
            string += function(pvt_df)
    return string


def df2ecl_rock(dframe, comment=None):
    """Print ROCK keyword with data

    Args:
        dframe (pd.DataFrame): Containing ROCK data
        comment (str): Text that will be included as a comment
    """
    string = "ROCK\n"
    string += comment_formatter(comment)
    string += "--   {:^21} {:^21}\n".format("PRESSURE", "COMPRESSIBILITY")
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
        string += "  {PRESSURE:20.7f} {COMPRESSIBILITY:20.7f} /\n".format(
            **(row.to_dict())
        )
    return string + "\n"


def df2ecl_density(dframe, comment=None):
    """Print DENSITY keyword with data

    Args:
        dframe (pd.DataFrame): Containing DENSITY data
        comment (str): Text that will be included as a comment
    """
    string = "DENSITY\n"
    string += comment_formatter(comment)
    string += "--   {:^21} {:^21} {:^21}  \n".format(
        "OILDENSITY", "WATERDENSITY", "GASDENSITY"
    )
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
        string += "  {OILDENSITY:20.7f} {WATERDENSITY:20.7f}".format(**(row.to_dict()))
        string += " {GASDENSITY:20.7f} /\n".format(**(row.to_dict()))
    return string + "\n"


def df2ecl_pvtw(dframe, comment=None):
    """Print PVTW keyword with data

    Args:
        dframe (pd.DataFrame): Containing PVTW data
        comment (str): Text that will be included as a comment
    """
    string = "PVTW\n"
    string += comment_formatter(comment)
    string += "--   {:^21} {:^21} {:^21} {:^21} {:^21}  \n".format(
        "PRESSURE", "VOLUMEFACTOR", "COMPRESSIBILITY", "VISCOSITY", "VISCOSIBILITY"
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
        string += "  {PRESSURE:20.7f} {VOLUMEFACTOR:20.7f} ".format(**(row.to_dict()))
        string += "{COMPRESSIBILITY:20.7f} {VISCOSITY:20.7f} ".format(**(row.to_dict()))
        string += "{VISCOSIBILITY:20.7f}/\n".format(**(row.to_dict()))
    return string + "\n"


def df2ecl_pvtg(dframe, comment=None):
    """Print DENSITY keyword with data

    Args:
        dframe (pd.DataFrame): Containing PVTG data
        comment (str): Text that will be included as a comment
    """
    string = "DENSITY\n"
    string += comment_formatter(comment)
    string += "--   {:^21} {:^21} {:^21}  \n".format(
        "OILDENSITY", "WATERDENSITY", "GASDENSITY"
    )
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
        string += "  {OILDENSITY:20.7f} {WATERDENSITY:20.7f} ".format(**(row.to_dict()))
        string += "{GASDENSITY:20.7f} /\n".format(**(row.to_dict()))
    return string + "\n"


def df2ecl_pvdg(dframe, comment=None):
    """Print PVDG keyword with data

    Args:
        dframe (pd.DataFrame): Containing PVDG data
        comment (str): Text that will be included as a comment
    """
    string = "PVDG\n"
    string += comment_formatter(comment)
    string += "--   {:^21} {:^21} {:^21}  \n".format(
        "PRESSURE", "VOLUMEFACTOR", "VISCOSITY"
    )
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
        """Print PVDG-data for a specific PVTNUM

        Args:
            dframe (pd.DataFrame): Cropped to only contain the relevant data.

        Returns:
            string
        """
        string = ""
        dframe = dframe.sort_values("PRESSURE")
        for _, row in dframe.iterrows():
            string += "  {PRESSURE:20.7f} {VOLUMEFACTOR:20.7f} ".format(
                **(row.to_dict())
            )
            string += "{VISCOSITY:20.7f}\n".format(**(row.to_dict()))
        return string + "/\n"

    subset = subset.set_index("PVTNUM").sort_index()
    for pvtnum in subset.index.unique():
        string += "-- PVTNUM: {}\n".format(pvtnum)
        string += _pvdg_pvtnum(subset[subset.index == pvtnum])

    return string + "\n"


def df2ecl_pvdo(dframe, comment=None):
    """Print PVDO keyword with data

    Args:
        dframe (pd.DataFrame): Containing PVDO data
        comment (str): Text that will be included as a comment
    """
    string = "PVDO\n"
    string += comment_formatter(comment)
    string += "--   {:^21} {:^21} {:^21}  \n".format(
        "PRESSURE", "VOLUMEFACTOR", "VISCOSITY"
    )
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

    def _pvdo_pvtnum(dframe):
        """Print PVDO-data for a specific PVTNUM

        Args:
            dframe (pd.DataFrame): Cropped to only contain the relevant data.

        Returns:
            string
        """
        string = ""
        dframe = dframe.sort_values("PRESSURE")
        for _, row in dframe.iterrows():
            string += "  {PRESSURE:20.7f} {VOLUMEFACTOR:20.7f} ".format(
                **(row.to_dict())
            )
            string += "{VISCOSITY:20.7f}\n".format(**(row.to_dict()))
        return string + "/\n"

    subset = subset.set_index("PVTNUM").sort_index()
    for pvtnum in subset.index.unique():
        string += "-- PVTNUM: {}\n".format(pvtnum)
        string += _pvdo_pvtnum(subset[subset.index == pvtnum])

    return string + "\n"


def df2ecl_pvto(dframe, comment=None):
    """Print PVTO-data from a dataframe

    Args:
        dframe (pd.DataFrame): Containing PVTO data
        comment (str): Text that will be included as a comment
    """
    string = "PVTO\n"
    string += comment_formatter(comment)
    string += "-- {:^22} {:^22} {:^22} {:^22}\n".format(
        "RS", "PRESSURE", "VOLUMEFACTOR", "VISCOSITY"
    )
    string += "-- {:^22} {:^22} {:^22} {:^22}\n".format(
        "*", "PRESSURE", "VOLUMEFACTOR", "VISCOSITY"
    )
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

    def _pvto_pvtnum(dframe):
        """Print PVTO-data for a specific PVTNUM"""
        string = ""
        dframe = dframe.set_index("RS").sort_index()
        for rs in dframe.index.unique():
            string += _pvto_pvtnum_rs(dframe[dframe.index == rs])
        return string + "/\n"

    def _pvto_pvtnum_rs(dframe):
        """Print PVTO-data for a particular RS"""
        string = ""
        assert len(dframe.index.unique()) == 1
        rs = dframe.index.values[0]
        string += "{:20.7f}  ".format(rs)
        for rowidx, row in dframe.reset_index().iterrows():
            if rowidx > 0:
                indent = "\n" + " " * 22
            else:
                indent = ""
            string += (
                indent
                + "{PRESSURE:20.7f}  {VOLUMEFACTOR:20.7f}  {VISCOSITY:20.7f}".format(
                    **(row.to_dict())
                )
            )
        string += " /\n-- End RS={}\n".format(rs)
        return string

    for pvtnum in subset.index.unique():
        string += _pvto_pvtnum(subset[subset.index == pvtnum])
    return string + "\n"

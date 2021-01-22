"""
Extract EQUIL from an Eclipse deck as Pandas DataFrame

"""

import logging
import pandas as pd

from ecl2df import inferdims, common
from .eclfiles import EclFiles

logger = logging.getLogger(__name__)

SUPPORTED_KEYWORDS = ["EQUIL", "PBVD", "PDVD", "RSVD", "RVVD"]
RENAMERS = {}
RENAMERS["PBVD"] = {"DATA": ["Z", "PB"]}
RENAMERS["PDVD"] = {"DATA": ["Z", "PD"]}
RENAMERS["RSVD"] = {"DATA": ["Z", "RS"]}
RENAMERS["RVVD"] = {"DATA": ["Z", "RV"]}
RENAMERS["oil-water-gas"] = {
    "DATUM_DEPTH": "Z",
    "DATUM_PRESSURE": "PRESSURE",
    "OWC": "OWC",
    "PC_OWC": "PCOWC",
    "GOC": "GOC",
    "PC_GOC": "PCGOC",
    "BLACK_OIL_INIT": "INITRS",
    "BLACK_OIL_INIT_WG": "INITRV",
    "OIP_INIT": "ACCURACY",
}
RENAMERS["gas-water"] = {
    "DATUM_DEPTH": "Z",
    "DATUM_PRESSURE": "PRESSURE",
    "OWC": "GWC",
    "PC_OWC": "PCGWC",
    "GOC": "IGNORE1",
    "PC_GOC": "IGNORE2",
    "BLACK_OIL_INIT": "IGNORE3",
    "BLACK_OIL_INIT_WG": "IGNORE4",
    "OIP_INIT": "ACCURACY",
}
RENAMERS["oil-water"] = {
    "DATUM_DEPTH": "Z",
    "DATUM_PRESSURE": "PRESSURE",
    "OWC": "OWC",
    "PC_OWC": "PCOWC",
    "GOC": "IGNORE1",
    "PC_GOC": "IGNORE2",
    "BLACK_OIL_INIT": "IGNORE3",
    "BLACK_OIL_INIT_WG": "IGNORE4",
    "OIP_INIT": "ACCURACY",
}
RENAMERS["oil-gas"] = {
    "DATUM_DEPTH": "Z",
    "DATUM_PRESSURE": "PRESSURE",
    "OWC": "IGNORE1",
    "PC_OWC": "IGNORE2",
    "GOC": "GOC",
    "PC_GOC": "PCGOC",
    "BLACK_OIL_INIT": "IGNORE3",
    "BLACK_OIL_INIT_WG": "IGNORE4",
    "OIP_INIT": "ACCURACY",
}


def df(deck, keywords=None, ntequl=None):
    """Extract EQUIL related keyword data, EQUIL, RSVD, RVVD
    PBVD and PDVD.

    How each data value in the EQUIL records are to be interpreted
    depends on the phase configuration in the deck, which means
    that we need more than the EQUIL section alone to determine the
    dataframe.

    If ntequl is not supplied and EQLDIMS is not in the deck, the
    equil data is not well defined in terms of OPM. This means
    that we have to infer the correct number of EQUIL lines from what
    gives us successful parsing from OPM. In those cases, the
    deck must be supplied as a string, if not, extra EQUIL lines
    are possibly already removed by the OPM parser in eclfiles.str2deck().

    Arguments:
        deck (opm.io deck or str): Eclipse deck or string with deck. If
           not string, EQLDIMS must be present in the deck.
        keywords (list of str): Requested keywords for which to extract
            data.
        ntequl (int): If not None, should state the NTEQUL in EQLDIMS. If
            None and EQLDIMS is not present, it will be inferred.

    Return:
        pd.DataFrame, at least with columns KEYWORD and EQLNUM
    """
    if isinstance(deck, EclFiles):
        deck = deck.get_ecldeck()

    deck = inferdims.inject_xxxdims_ntxxx("EQLDIMS", "NTEQUL", deck, ntequl)
    ntequl = deck["EQLDIMS"][0][inferdims.DIMS_POS["NTEQUL"]].get_int(0)

    keywords = common.handle_wanted_keywords(keywords, deck, SUPPORTED_KEYWORDS)

    frames = []
    for keyword in keywords:
        # Construct the associated function names
        function_name = keyword.lower() + "_fromdeck"
        function = globals()[function_name]
        dframe = function(deck, ntequl=ntequl)
        frames.append(dframe.assign(KEYWORD=keyword))
    nonempty_frames = [frame for frame in frames if not frame.empty]
    if nonempty_frames:
        return pd.concat(nonempty_frames, axis=0, sort=False, ignore_index=True)
    return pd.DataFrame()


def rsvd_fromdeck(deck, ntequl=None):
    """Extract RSVD data from a deck

    Args:
        deck (str or opm.common Deck)
        ntequl (int): Number of EQLNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "EQLDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("EQLDIMS", "NTEQUL", deck, ntequl)
    return common.ecl_keyworddata_to_df(
        deck, "RSVD", renamer=RENAMERS["RSVD"], recordcountername="EQLNUM"
    )


def rvvd_fromdeck(deck, ntequl=None):
    """Extract RVVD data from a deck

    Args:
        deck (str or opm.common Deck)
        ntequl (int): Number of EQLNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "EQLDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("EQLDIMS", "NTEQUL", deck, ntequl)
    return common.ecl_keyworddata_to_df(
        deck, "RVVD", renamer=RENAMERS["RVVD"], recordcountername="EQLNUM"
    )


def pbvd_fromdeck(deck, ntequl=None):
    """Extract PBVD data from a deck

    Args:
        deck (str or opm.common Deck)
        ntequl (int): Number of EQLNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "EQLDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("EQLDIMS", "NTEQUL", deck, ntequl)
    return common.ecl_keyworddata_to_df(
        deck, "PBVD", renamer=RENAMERS["PBVD"], recordcountername="EQLNUM"
    )


def pdvd_fromdeck(deck, ntequl=None):
    """Extract PDVD data from a deck

    Args:
        deck (str or opm.common Deck)
        ntequl (int): Number of EQLNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "EQLDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("EQLDIMS", "NTEQUL", deck, ntequl)
    return common.ecl_keyworddata_to_df(
        deck, "PDVD", renamer=RENAMERS["PDVD"], recordcountername="EQLNUM"
    )


def phases_from_deck(deck):
    """Determined the set of phases from a deck, as
    a string with values "oil-water-gas", "gas-water", "oil-water",
    or "oil-gas"

    Args:
        deck (opm.common deck): A parsed deck (or any container
        which can answer questions like "OIL" in deck)

    Returns:
        str. Empty string if inconclusive.
    """
    if "OIL" in deck and "GAS" in deck and "WATER" in deck:
        return "oil-water-gas"
    if "OIL" not in deck and "GAS" in deck and "WATER" in deck:
        return "gas-water"
    if "OIL" in deck and "GAS" not in deck and "WATER" in deck:
        return "oil-water"
    if "OIL" in deck and "GAS" in deck and "WATER" not in deck:
        return "oil-gas"
    print("HELP!")
    print(deck)
    return ""


def phases_from_columns(columns):
    """Determine the set of phases available in an
    equil dataframe, based on which columns are there.
    Returns "oil-water-gas", "gas-water", "oil-water",
    or "oil-gas"

    By this, we can pick the correct RENAMER to use.

    Args:
        columns (list of str): list of strings we can use for
            the determination

    Returns:
        str with phase configuration. Empty string if inconclusive.
    """
    if "OWC" in columns and "GOC" in columns:
        return "oil-water-gas"
    if "GWC" in columns:
        return "gas-water"
    if "OWC" in columns and "GOC" not in columns:
        return "oil-water"
    if "OWC" not in columns and "GOC" in columns:
        return "oil-gas"
    return ""


def equil_fromdeck(deck, ntequl=None):
    """Extract EQUIL data from a deck

    Args:
        deck (str or opm.common Deck)
        ntequl (int): Number of EQLNUM regions in deck. Will
            be inferred if not present in deck
    """
    if "EQLDIMS" not in deck:
        deck = inferdims.inject_xxxdims_ntxxx("EQLDIMS", "NTEQUL", deck, ntequl)

    phasecount = sum(["OIL" in deck, "GAS" in deck, "WATER" in deck])
    phases = phases_from_deck(deck)
    if not phases or phases not in RENAMERS:
        raise ValueError(
            "Could not determine phase configuration, got '{}'".format(phases)
        )
    columnrenamer = RENAMERS[phases_from_deck(deck)]
    if phasecount == 1:
        columnrenamer = {"DATUM_DEPTH": "DATUM", "DATUM_PRESSURE": "PRESSURE"}
    if not columnrenamer:
        raise ValueError("Unsupported phase configuration")

    dataframe = common.ecl_keyworddata_to_df(
        deck, "EQUIL", renamer=columnrenamer, recordcountername="EQLNUM"
    )

    # The column handling can be made prettier..
    for col in dataframe.columns:
        if "IGNORE" in col:
            del dataframe[col]

    return dataframe


def fill_parser(parser):
    """Set up sys.argv parsers.

    Arguments:
        parser (argparse.ArgumentParser or argparse.subparser): parser to
            fill with arguments
    """
    parser.add_argument("DATAFILE", help="Name of Eclipse DATA file.")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help=("Name of output csv file. " "Use '-' for stdout."),
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


def fill_reverse_parser(parser):
    """Fill a parser for the operation dataframe -> eclipse include file"""
    return common.fill_reverse_parser(parser, "EQUIL, RSVD++", "solution.inc")


def equil_main(args):
    """Read from disk and write CSV back to disk"""
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    if eclfiles:
        deck = eclfiles.get_ecldeck()
    if "EQLDIMS" in deck:
        # Things are easier when a full deck with (correct) EQLDIMS
        # is supplied:
        equil_df = df(deck, keywords=args.keywords)
    else:
        # This might be an include file for which we have to infer/guess
        # EQLDIMS. Then we send it to df() as a string
        equil_df = df("".join(open(args.DATAFILE).readlines()))
    if not equil_df.empty:
        common.write_dframe_stdout_file(
            equil_df,
            args.output,
            index=False,
            caller_logger=logger,
            logstr=(
                "Unique EQLNUMs: {}, keywords: {}".format(
                    str(len(equil_df["EQLNUM"].unique())),
                    str(equil_df["KEYWORD"].unique()),
                )
            ),
        )
    else:
        logger.error("Empty EQUIL-data, not written to disk!")


def equil_reverse_main(args):
    """Entry-point for module, for command line utility for CSV to Eclipse"""
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    equil_df = pd.read_csv(args.csvfile)
    logger.info("Parsed %s", args.csvfile)
    inc_string = df2ecl(equil_df, keywords=args.keywords)
    common.write_inc_stdout_file(inc_string, args.output)


def df2ecl(equil_df, keywords=None, comments=None, withphases=False, filename=None):
    """Generate Eclipse include strings from dataframes with
    solution (EQUIL, RSVD++) data.

    Args:
        equil_df (pd.DataFrame): Dataframe with data on ecl2df format.
        keywords (list of str): List of keywords to include. Must be
            supported and present in the incoming dataframe.
        comments (dict): Dictionary indexed by keyword with comments to be
            included pr. keyword. If a key named "master" is present
            it will be used as a master comment for the outputted file.
        withphases (boolean): If True, the phase configuration keywords
            will be outputted. This is mostly for testing, and should
            not be necessary in production.
        filename (str): If supplied, the generated text will also be dumped
            to file.

    """
    string = ""
    if withphases:
        string += (
            phases_from_columns(equil_df.columns).upper().replace("-", "\n") + "\n\n"
        )
    string += common.df2ecl(
        equil_df,
        keywords=keywords,
        comments=comments,
        supported=SUPPORTED_KEYWORDS,
        consecutive="EQLNUM",
        filename=filename,
    )
    return string


def df2ecl_equil(dframe, comment=None):
    """Print EQUIL keyword with data

    Args:
        dframe (pd.DataFrame): Containing EQUIL data
        comment (str): Text that will be included as a comment
    """
    if dframe.empty:
        return "-- No data!"
    string = "EQUIL\n"
    string += common.comment_formatter(comment)

    if "KEYWORD" not in dframe:
        # Use everything..
        subset = dframe
    else:
        subset = dframe[dframe["KEYWORD"] == "EQUIL"]
    if "EQLNUM" not in subset:
        if len(subset) != 1:
            logger.critical("If EQLNUM is not supplied, only one row should be given")
            return ""
        subset["EQLNUM"] = 1
    subset = subset.set_index("EQLNUM").sort_index()

    phases = phases_from_columns(subset.columns)

    # Make a copy as we are going to modify it in order to have Pandas
    # make a pretty txt table:
    equildf = subset.copy()
    # Column names are pr. ec2ldf standard, redo to opm.common in order
    # to use sorting from that:
    inv_renamer = {value: key for key, value in RENAMERS[phases].items()}
    # print(inv_renamer)
    equildf.rename(inv_renamer, axis="columns", inplace=True)
    col_headers = [item["name"] for item in common.OPMKEYWORDS["EQUIL"]["items"]]
    for colname in col_headers:
        # Add those that are missing, as Eclipse defaults
        if colname not in equildf:
            equildf[colname] = "1*"
    # Reorder columns:
    equildf = equildf[col_headers]

    # It is critical for opm.common, maybe also E100 to have integers printed
    # as integers, for correct parsing. Ensure integer types where
    # the json says integer:
    integer_cols = [
        item["name"]
        for item in common.OPMKEYWORDS["EQUIL"]["items"]
        if item["value_type"] == "INT"
    ]
    for int_col in integer_cols:
        # But allow these columns to contain "1*"
        if set(equildf[int_col]) != {"1*"}:
            equildf[int_col] = equildf[int_col].astype(int)

    # Now rename again to have prettier column names:
    equildf.rename(RENAMERS[phases], axis="columns", inplace=True)
    # Add a final column with the end-slash, invisible header:
    equildf[" "] = "/"
    string += "-- " + equildf.to_string(header=True, index=False)
    return string + "\n\n"


def df2ecl_rsvd(dframe, comment=None):
    """Print RSVD keyword with data

    This data consists of one table (rs as a function
    of depth) for each EQLNUM

    Args:
        dframe (pd.DataFrame): Containing RSVD data
        comment (str): Text that will be included as a comment

    Returns:
        string
    """
    return _df2ecl_equilfuncs("RSVD", dframe, comment)


def df2ecl_rvvd(dframe, comment=None):
    """Print RVVD keyword with data

    This data consists of one table (rv as a function
    of depth) for each EQLNUM

    Args:
        dframe (pd.DataFrame): Containing RVVD data
        comment (str): Text that will be included as a comment

    Returns:
        string
    """
    return _df2ecl_equilfuncs("RVVD", dframe, comment)


def df2ecl_pbvd(dframe, comment=None):
    """Print PBVD keyword with data

    Bubble-point versus depth

    This data consists of one table (Pb as a function
    of depth) for each EQLNUM

    Args:
        dframe (pd.DataFrame): Containing PBVD data
        comment (str): Text that will be included as a comment

    Returns:
        string
    """
    return _df2ecl_equilfuncs("PBVD", dframe, comment)


def df2ecl_pdvd(dframe, comment=None):
    """Print PDVD keyword with data.

    Dew-point versus depth.

    This data consists of one table (Pd as a function
    of depth) for each EQLNUM

    Args:
        dframe (pd.DataFrame): Containing PDVD data
        comment (str): Text that will be included as a comment

    Returns:
        string
    """
    return _df2ecl_equilfuncs("PDVD", dframe, comment)


def _df2ecl_equilfuncs(keyword, dframe, comment=None):
    """Internal function to be used by df2ecl_<keyword>() functions"""
    if dframe.empty:
        return "-- No data!"
    string = "{}\n".format(keyword)
    string += common.comment_formatter(comment)
    col_headers = RENAMERS[keyword]["DATA"]

    string += "--   {:^21} {:^21} \n".format("DEPTH", col_headers[1])
    if "KEYWORD" not in dframe:
        # Use everything..
        subset = dframe
    else:
        subset = dframe[dframe["KEYWORD"] == keyword]
    if "EQLNUM" not in subset:
        subset["EQLNUM"] = 1

    def _df2ecl_equilfuncs_eqlnum(dframe):
        """Print one equilibriation function table for a specific
        EQLNUM

        Args:
            dframe (pd.DataFrame): Cropped to only contain data for one EQLNUM

        Returns:
            string
        """
        string = ""
        dframe = dframe.sort_values("Z")
        for _, row in dframe.iterrows():
            string += "  {:20.7f} {:20.7f}\n".format(
                row[col_headers[0]], row[col_headers[1]]
            )
        return string + "/\n"

    subset = subset.set_index("EQLNUM").sort_index()
    for eqlnum in subset.index.unique():
        string += "-- EQLNUM: {}\n".format(eqlnum)
        string += _df2ecl_equilfuncs_eqlnum(subset[subset.index == eqlnum])
    return string + "\n"

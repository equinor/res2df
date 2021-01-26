"""Common functions for ecl2df modules"""

import sys
import json
import signal
import inspect
import logging
import datetime
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

# This import is seemingly not used, but necessary for some attributes
# to be included in DeckItem objects.
from opm.io.deck import DeckKeyword  # noqa

from ecl2df import __version__

# Parse named JSON files, this exposes a dict of dictionary describing the contents
# of supported Eclipse keyword data
OPMKEYWORDS = {}
for keyw in [
    "COMPDAT",
    "COMPSEGS",
    "DENSITY",
    "EQLDIMS",
    "EQUIL",
    "FAULTS",
    "GRUPNET",
    "GRUPTREE",
    "PBVD",
    "PDVD",
    "PVDG",
    "PVDO",
    "PVTG",
    "PVTO",
    "PVTW",
    "ROCK",
    "RSVD",
    "RVVD",
    "SGFN",
    "SGWFN",
    "SGOF",
    "SLGOF",
    "SOF2",
    "SOF3",
    "SWFN",
    "SWOF",
    "TABDIMS",
    "WCONHIST",
    "WCONINJE",
    "WCONINJH",
    "WCONPROD",
    "WELOPEN",
    "WELSEGS",
    "WELSPECS",
    "WSEGAICD",
    "WSEGSICD",
    "WSEGVALV",
]:
    OPMKEYWORDS[keyw] = json.loads(
        (Path(__file__).parent / "opmkeywords" / keyw).read_text()
    )


# This is a magic filename that means read/write from/to stdout
# This makes it impossible to write to a file called "-" on disk
# but that would anyway create a lot of other problems in the shell.
MAGIC_STDOUT = "-"

logger = logging.getLogger(__name__)


def write_dframe_stdout_file(
    dframe, output, index=False, caller_logger=None, logstr=None
):
    """Write a dataframe to either stdout or a file

    If output is the magic string "-", output is written
    to stdout.

    Arguments:
        dframe (pd.DataFrame): Dataframe to write
        output (str): Filename or "-"
        index (bool): Passed to to_csv()
        caller_logger (logging): Used if not stdout
        logstr (str): Logged if not stdout.
    """
    if output == MAGIC_STDOUT:
        # Ignore pipe errors when writing to stdout:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
        dframe.to_csv(sys.stdout, index=index)
    else:
        if caller_logger and not logstr:
            caller_logger.info("Writing to file %s", str(output))
        elif caller_logger and logstr:
            caller_logger.info(logstr)
        dframe.to_csv(output, index=index)


def write_inc_stdout_file(string, outputfilename):
    """Write a string (typically an include file string) to stdout
    or to a named file"""
    if outputfilename == MAGIC_STDOUT:
        # Ignore pipe errors when writing to stdout:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
        print(string)
    else:
        Path(outputfilename).write_text(string)
        print(f"Wrote to {outputfilename}")


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


def ecl_keyworddata_to_df(
    deck, keyword, renamer=None, recordcountername=None, emptyrecordcountername=None
):
    """Extract data associated to an Eclipse keyword into a tabular form.

    Two modes of enueration of tables in the keyworddata is supported, you
    will have to find out which one fits your particular keyword. Activate
    by setting recordcountername or emptyrecordcountername to some string, which
    will be the name of your enumeration, e.g. PVTNUM, EQLNUM or SATNUM.

    Arguments:
        deck (opm.common.Deck): Parsed deck
        keyword (str): Name of the keyword for which to extract data.
        renamer (dict): Mapping of names present in OPM json files for the
            keyword to desired column names in returned dataframe
        recordcountername (str): If present, an extra column is added with this name
            with consecutive rows enumerated from 1. Use this to assign
            EQLNUM or similar when this should be consecutive pr. row (not
            the case for all keywords).
        emptyrecordcountername (str): If supplied, an index is added to every parsed
            row based on how many empty records is encountered. For PVTO f.ex,
            this gives the PVTNUM indexing.
    """
    records = []  # list of dicts or dataframes

    record_counter = 1
    emptyrecord_counter = 1
    for deckrecord in deck[keyword]:
        if str(deckrecord).strip() == "/":
            # For some keywords, at least PVTO, an empty record like
            # this signifies that we jump to the next table, and
            # for PVTO, this counter variable will be used as PVTNUM
            emptyrecord_counter += 1
            continue
        else:
            recdict = parse_opmio_deckrecord(deckrecord, keyword, renamer=renamer)
        if emptyrecordcountername is not None:
            recdict[emptyrecordcountername] = emptyrecord_counter
        if recordcountername is not None:
            recdict[recordcountername] = record_counter
        # Now some keywords have an arbitrary amount of data for a record, f.ex.
        # PVTO, where multiple undersaturated lines can be added. We want
        # to unroll this data. We detect this situation by the item name "DATA" in
        # the json files, and that its value is of list type:
        if "DATA" in recdict and isinstance(recdict["DATA"], list):
            # If DATA is sometimes used for something else in the jsons, redo this.
            data_dim = len(renamer["DATA"])  # The renamers must be in sync with json!
            data_chunks = int(len(recdict["DATA"]) / data_dim)
            try:
                data_reshaped = np.reshape(recdict["DATA"], (data_chunks, data_dim))
            except ValueError as err:
                raise ValueError(
                    (
                        f"Wrong number count for keyword {keyword}. \n"
                        "Either your keyword is wrong, or your data is wrong"
                    )
                ) from err
            data_df = pd.DataFrame(columns=renamer["DATA"], data=data_reshaped)
            # Assign the remaining items from the parsed dict to the dataframe:
            for key, value in recdict.items():
                if key != "DATA":
                    data_df[key] = recdict[key]
            records.append(data_df)
            record_counter += 1
        else:
            records.append(recdict)
            record_counter += 1
    if isinstance(records[0], pd.DataFrame):
        dframe = pd.concat(records)
    else:  # records contain lists.
        dframe = pd.DataFrame(data=records)
    return dframe.reset_index(drop=True)


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
            the keys in returned dict. For items with name DATA, the dict
            value is assumed to be a list of strings to be mapped to
            each subitem.
    Returns:
        dict
    """
    if keyword not in OPMKEYWORDS:
        raise ValueError(f"Keyword {keyword} not supported by common.py")

    rec_dict = {}

    if recordindex is None:  # Beware, 0 is different from None here.
        itemlist = OPMKEYWORDS[keyword][itemlistname]
    else:
        itemlist = OPMKEYWORDS[keyword][itemlistname][recordindex]

    # Loop over the items in the "items" section of the json keyword description.
    # Usually these items refer to one number/value in the deck record ("one line")
    # but for some keywords there are more values, like for PVTO
    for item_idx, jsonitem in enumerate(itemlist):
        item_name = jsonitem["name"]
        if not record[item_idx].defaulted:
            if len(record[item_idx]) == 1:
                # The DeckItem attribute .value is only present if there is an
                # explicit statement "from opm.io.deck import DeckKeyword"
                # in this file.
                rec_dict[item_name] = record[item_idx].value
            else:
                rec_dict[item_name] = record[item_idx].get_raw_data_list()
                # (the caller is responsible for unrolling this list with
                # correct naming of elements)
        else:
            rec_dict[item_name] = jsonitem.get("default", None)

    if renamer:
        renamed_dict = {}
        for key in rec_dict:
            if key in renamer and not isinstance(renamer[key], list):
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


def comment_formatter(multiline, prefix="-- "):
    """Prepends comment characters to every line in input

    If nothing is supplied, an empty string is returned.

    Args:
        multiline (str): String that can contain newlines
        prefix (str): Comment characters to prepend every line with
            Default is the Eclipse comment syntax '-- '

    Returns:
        string, with newlines preserved, and where each line
            starts with the given prefix. Always ends with a newline.
    """
    if multiline is None or not multiline.strip():
        return ""
    return (
        "\n".join([prefix + line.strip() for line in multiline.splitlines()]).strip()
        + "\n"
    )


def handle_wanted_keywords(wanted, deck, supported, modulename=""):
    """Handle three list of keywords, wanted, available and supported

    Args:
        keywords (list of str): None, or list of strings of user-requested keywords
        deck (opm.common Deck): Used to query which data is available
        supported (list of str): Keywords that are supported by the module
        modulename (str): Name of the module calling this function, used in logging
    """
    if not isinstance(wanted, list):
        wanted = [wanted]
    if wanted[0] is None and len(wanted) == 1:
        # By default, select all supported keywords:
        keywords = supported
    else:
        # Warn if some keywords are unsupported:
        not_supported = set(wanted) - set(supported)
        if not_supported:
            logger.warning(
                "Requested keyword(s) not supported by ecl2df.%s: %s",
                modulename,
                str(not_supported),
            )
        # Reduce to only supported keywords:
        keywords = list(set(wanted) - set(not_supported))
        # Warn if some requested keywords are not in deck:
        keywords_in_deck = [keyword for keyword in keywords if keyword in deck]
        not_in_deck = set(keywords) - set(keywords_in_deck)
        if not_in_deck:
            logger.warning(
                "Requested keyword(s) not present in deck: %s", str(not_in_deck)
            )
    # Reduce again to only present keywords, but without warning:
    keywords = [keyword for keyword in keywords if keyword in deck]

    return keywords


def fill_reverse_parser(parser, modulename, defaultoutputfile):
    """A standardized submodule parser for the command line utility
    to produce Eclipse include files from a CSV file.

    Arguments:
        parser (ArgumentParser or subparser): parser to fill with arguments
        modulename (str): Will be included in the help text
        defaultoutputfile (str): Default output filename
    """
    parser.add_argument(
        "csvfile", help="Name of CSV file with " + modulename + " data on ecl2df format"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help=(
            "Name of output Eclipse include file file, default "
            + defaultoutputfile
            + ". "
            "Use '-' for stdout."
        ),
        default=defaultoutputfile,
    )
    parser.add_argument(
        "-k",
        "--keywords",
        nargs="+",
        help=(
            "List of " + modulename + " keywords to include. "
            "If not supplied, all supported and found keywords will be included."
        ),
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def df2ecl(
    dataframe,
    keywords=None,
    comments=None,
    supported=None,
    consecutive=None,
    filename=None,
):
    """Generate Eclipse include strings from dataframes in ecl2df format

    Args:
        dataframe (pd.DataFrame): Dataframe with Eclipse data on ecl2df format.
        keywords (list of str): List of keywords to include. Will be reduced
            to the set of keywords available in dataframe and to those supported
        comments (dict): Dictionary indexed by keyword with comments to be
            included pr.  keyword. If a key named "master" is present
            it will be used as a master comment for the outputted file.
        supported (list): List of strings of keywords which are
            supported in this invocation of this function.
        consecutive (str): Column name for which we require the
            numbers to be consecutive. Typically PVTNUM, EQLNUM, SATNUM.
        filename (str): If supplied, the generated text will also be dumped
            to file.

    Returns:
        string that can be used as an include file for Eclipse.
    """
    from_module = inspect.stack()[1]
    calling_module = inspect.getmodule(from_module[0])
    if dataframe.empty:
        raise ValueError("Empty dataframe")
    if consecutive is not None and consecutive in dataframe:
        if not (
            min(dataframe[consecutive]) == 1
            and len(dataframe[consecutive].unique()) == max(dataframe[consecutive])
        ):
            logger.critical(
                "%s inconsistent in input dataframe, got the values %s",
                consecutive,
                str(dataframe[consecutive].unique()),
            )
            raise ValueError

    # "KEYWORD" must always be in the dataframe:
    if "KEYWORD" not in dataframe:
        raise ValueError("KEYWORD must be in the dataframe")

    if comments is None:
        comments = {}
    if not isinstance(keywords, list):
        keywords = [keywords]  # Can still be None
    keywords_in_frame = set(dataframe["KEYWORD"])
    if keywords[0] is None and len(keywords) == 1:
        # By default, select all supported PVT keywords:
        keywords = supported
    else:
        # Warn if some keywords are unsupported:
        not_supported = set(keywords) - set(supported)
        if not_supported:
            logger.warning(
                "Requested keyword(s) not supported by %s: %s",
                calling_module.__name__,
                str(not_supported),
            )
        # Warn if some requested keywords are not in frame:
        not_in_frame = set(keywords) - keywords_in_frame
        if not_in_frame:
            logger.warning(
                "Requested keyword(s) not present in dataframe: %s", str(not_in_frame)
            )
    keywords = [
        keyword
        for keyword in keywords  # user supplied list defines the print order
        if keyword in supported and keyword in keywords_in_frame
    ]
    if not keywords:
        # Nothing to do

        return ""
    string = ""
    ecl2df_header = (
        "Output file printed by "
        + calling_module.__name__
        + " "
        + __version__
        + "\n"
        + " at "
        + str(datetime.datetime.now())
    )
    string += comment_formatter(ecl2df_header)
    string += "\n"
    if "master" in comments:
        string += comment_formatter(comments["master"])
    for keyword in keywords:
        # Construct the associated function names
        function_name = "df2ecl_" + keyword.lower()
        function = getattr(calling_module, function_name)
        if keyword in comments:
            string += function(dataframe, comments[keyword])
        else:
            string += function(dataframe)

    if filename is not None:
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        Path(filename).write_text(string, encoding="utf-8")
    return string


def runlength_eclcompress(string, sep="  "):
    """Compress a string of space-separated elements so that

       2 2 2 2 2 3 3 4

    becomes

       5*2 2*3 4

    which is the format supported by Eclipse. The input
    string must be splittable with split(). Any newlines
    will be replaced by a space prior to split().

    See https:///en.wikipedia.org/wiki/Run-length_encoding

    Args:
        string (str): String of space-separated elements to compress
        sep (str): Separator string used in output. Separator string in
            input is not conserved, but it must be compatible with
            str.split()
    Returns:
        string, shorter or equal-length to the input.
    """
    compresseddata = []
    stringlist = string.replace("\n", " ").split()
    for _, group in itertools.groupby(stringlist):
        equalvalues = list(group)
        if len(equalvalues) > 1:
            compresseddata += [str(len(equalvalues)) + "*" + str(equalvalues[0])]
        else:
            compresseddata += [sep.join(equalvalues)]
    return sep.join(compresseddata)


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

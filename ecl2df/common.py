"""Common functions for ecl2df modules"""

import argparse
import datetime
import inspect
import itertools
import json
import logging
import re
import shlex
import signal
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import numpy as np
import pandas as pd
import pyarrow

try:
    # pylint: disable=unused-import
    import opm.io.deck  # lgtm [py/import-and-import-from]

    # This import is seemingly not used, but necessary for some attributes
    # to be included in DeckItem objects.
    from opm.io.deck import DeckKeyword  # noqa
except ImportError:
    # Allow parts of ecl2df to work without OPM:
    pass

from ecl2df import __version__

from .constants import MAGIC_STDOUT

# Parse named JSON files, this exposes a dict of dictionary describing the contents
# of supported Eclipse keyword data
OPMKEYWORDS: Dict[str, dict] = {}
for keyw in [
    "BRANPROP",
    "COMPDAT",
    "COMPLUMP",
    "COMPSEGS",
    "DENSITY",
    "EQLDIMS",
    "EQUIL",
    "FAULTS",
    "GRUPNET",
    "GRUPTREE",
    "NODEPROP",
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
    "WLIST",
    "WSEGAICD",
    "WSEGSICD",
    "WSEGVALV",
]:
    OPMKEYWORDS[keyw] = json.loads(
        (Path(__file__).parent / "opmkeywords" / keyw).read_text()
    )


SVG_COLOR_NAMES = [
    color.lower()
    for color in (
        (Path(__file__).parent / "svg_color_keyword_names.txt")
        .read_text(encoding="utf-8")
        .splitlines()
    )
]

logger: logging.Logger = logging.getLogger(__name__)


def write_dframe_stdout_file(
    dframe: Union[pd.DataFrame, pyarrow.Table],
    output: str,
    index: bool = False,
    caller_logger: Optional[logging.Logger] = None,
    logstr: Optional[str] = None,
) -> None:
    """Write a dataframe to either stdout or a file

    If output is the magic string "-", output is written
    to stdout.

    Arguments:
        dframe: Dataframe to write
        output: Filename or "-"
        index: Passed to to_csv()
        caller_logger: Used if not stdout
        logstr: Logged if not stdout.
    """
    if output == MAGIC_STDOUT:
        # Ignore pipe errors when writing to stdout:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
        if isinstance(dframe, pd.DataFrame):
            dframe.to_csv(sys.stdout, index=index)
        else:
            raise SystemExit("Not possible to write arrow format to stdout")
    else:
        if caller_logger and isinstance(dframe, pd.DataFrame) and dframe.empty:
            caller_logger.warning("Empty dataframe being written to disk")
        if caller_logger and not logstr:
            caller_logger.info("Writing to file %s", str(output))
        elif caller_logger and logstr:
            caller_logger.info(logstr)
        if isinstance(dframe, pd.DataFrame):
            dframe.to_csv(output, index=index)
        else:
            pyarrow.feather.write_feather(dframe, dest=output)


def write_inc_stdout_file(string: str, outputfilename: str) -> None:
    """Write a string (typically an include file string) to stdout
    or to a named file"""
    if outputfilename == MAGIC_STDOUT:
        # Ignore pipe errors when writing to stdout:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
        print(string)
    else:
        Path(outputfilename).write_text(string, encoding="utf-8")
        print(f"Wrote to {outputfilename}")


def parse_ecl_month(eclmonth: str) -> int:
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
    deck,
    keyword: str,
    renamer: Optional[Dict[str, Union[str, List[str]]]] = None,
    recordcountername: Optional[str] = None,
    emptyrecordcountername: Optional[str] = None,
) -> pd.DataFrame:
    """Extract data associated to an Eclipse keyword into a tabular form.

    Two modes of enumeration of tables in the keyworddata is supported, you
    will have to find out which one fits your particular keyword. Activate
    by setting recordcountername or emptyrecordcountername to some string, which
    will be the name of your enumeration, e.g. PVTNUM, EQLNUM or SATNUM.

    Arguments:
        deck: Parsed deck
        keyword: Name of the keyword for which to extract data.
        renamer: Mapping of names present in OPM json files for the
            keyword to desired column names in returned dataframe
        recordcountername: If present, an extra column is added with this name
            with consecutive rows enumerated from 1. Use this to assign
            EQLNUM or similar when this should be consecutive pr. row (not
            the case for all keywords).
        emptyrecordcountername: If supplied, an index is added to every parsed
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
            assert renamer is not None
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
                    data_df[key] = value
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
    record: "opm.libopmcommon_python.DeckRecord",
    keyword: str,
    itemlistname: str = "items",
    recordindex: Optional[int] = None,
    renamer: Optional[Union[Dict[str, str], Dict[str, Union[str, List[str]]]]] = None,
) -> Dict[str, Any]:
    """
    Parse an opm.io.DeckRecord belonging to a certain keyword

    Args:
        record: Record be parsed
        keyword: Which Eclipse keyword this belongs to
        itemlistname: The key in the json dict that describes the items,
            typically 'items' or 'records'
        recordindex: For keywords where itemlistname is 'records', this is a
            list index to the "record".
            Beware, there are multiple concepts here for what we call a record.
        renamer: If supplied, this dictionary will be used to remap
            the keys in returned dict. For items with name DATA, the dict
            value is assumed to be a list of strings to be mapped to
            each subitem.
    """
    if keyword not in OPMKEYWORDS:
        raise ValueError(f"Keyword {keyword} not supported by common.py")

    rec_dict: Dict[str, Any] = {}

    if recordindex is None:  # Beware, 0 is different from None here.
        itemlist = OPMKEYWORDS[keyword][itemlistname]
    else:
        itemlist = OPMKEYWORDS[keyword][itemlistname][recordindex]

    # Loop over the items in the "items" section of the json keyword description.
    # Usually these items refer to one number/value in the deck record ("one line")
    # but for some keywords there are more values, like for PVTO
    for item_idx, jsonitem in enumerate(itemlist):
        item_name = jsonitem["name"]
        try:
            defaulted = record[item_idx].defaulted
        except IndexError:
            # Workaround for missing default in json for WLIST item WELLS (empty string)
            defaulted = True
        if not defaulted:
            if len(record[item_idx]) == 1:
                # The DeckItem attribute .value is only present if there is an
                # explicit statement "from opm.io.deck import DeckKeyword"
                # in this file.
                rec_dict[item_name] = record[item_idx].value
            else:
                try:
                    rec_dict[item_name] = record[item_idx].get_raw_data_list()
                except ValueError:
                    # Will get here for string lists:
                    rec_dict[item_name] = record[item_idx].get_data_list()
                # (the caller is responsible for unrolling this list with
                # correct naming of elements)

                # When we parse a list, some values in it can be defaulted, for
                # which the default values are not provided in the JSON. Return
                # these defaulted values as NaN's for the calling code to fix.
                for idx in range(len(record[item_idx])):
                    # This code is using a private attribute of an
                    # OPM DeckItem. A better solution has not yet
                    # been found in the OPM API. See also
                    # https://github.com/OPM/opm-common/issues/2598
                    if record[item_idx].__defaulted(idx):
                        rec_dict[item_name][idx] = np.nan
        else:
            rec_dict[item_name] = jsonitem.get("default", None)

    if renamer:
        renamed_dict: Dict[str, Any] = {}
        for key, value in rec_dict.items():
            if key in renamer and not isinstance(renamer[key], list):
                renamed_dict[renamer[key]] = value  # type: ignore
            else:
                renamed_dict[key] = value
        return renamed_dict
    return rec_dict


def parse_opmio_date_rec(record: "opm.io.DeckRecord") -> datetime.date:
    """Parse a opm.io.DeckRecord under a DATES or START keyword in a deck."""
    day = record[0].get_int(0)
    month = record[1].get_str(0)
    year = record[2].get_int(0)
    return datetime.date(year=year, month=parse_ecl_month(month), day=day)


def parse_opmio_tstep_rec(record: "opm.io.DeckRecord") -> List[Union[float, int]]:
    """Parse a record with TSTEP data

    Return:
        list of floats or ints
    """
    return record[0].get_raw_data_list()


def merge_zones(
    df: pd.DataFrame, zonedict: dict, zoneheader: str = "ZONE", kname: str = "K1"
) -> pd.DataFrame:
    """Merge in a column with zone names, from a dictionary mapping
    k-index to zone name. If the zonemap is not covering all
    zones, cells will be filled with NaN.

    Args:
        df: Dataframe where we should augment a column
        zonedict: Dictionary with integer keys pointing to strings
            with zone names.
        zoneheader: Name of the result column merged in,
            default: ZONE
        kname: Column header in your dataframe that maps to dictionary keys.
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

    df[zoneheader] = df[kname].map(zonedict)
    return df


def comment_formatter(multiline: Optional[str], prefix: str = "-- ") -> str:
    """Prepends comment characters to every line in input

    If nothing is supplied, an empty string is returned.

    Args:
        multiline: String that can contain newlines
        prefix: Comment characters to prepend every line with
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


def handle_wanted_keywords(
    wanted: Optional[List[str]],
    deck: "opm.io.Deck",
    supported: List[str],
    modulename: str = "",
) -> List[str]:
    """Handle three list of keywords, wanted, available and supported

    Args:
        keywords: None, or list of strings of user-requested keywords
        deck: Used to query which data is available
        supported: Keywords that are supported by the module
        modulename: Name of the module calling this function, used in logging
    """
    if isinstance(wanted, str):
        wanted = [wanted]
    if wanted is None or (wanted[0] is None and len(wanted) == 1):
        # By default, select all supported keywords:
        keywords = supported
    else:
        # Warn if some keywords are unsupported:
        not_supported: Set[str] = set(wanted) - set(supported)
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


def fill_reverse_parser(
    parser: argparse.ArgumentParser, modulename: str, defaultoutputfile: str
):
    """A standardized submodule parser for the command line utility
    to produce Eclipse include files from a CSV file.

    Arguments:
        parser: parser to fill with arguments
        modulename: Will be included in the help text
        defaultoutputfile: Default output filename
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
    dataframe: pd.DataFrame,
    keywords: Optional[Union[str, List[str], List[Optional[str]]]] = None,
    comments: Optional[Dict[str, str]] = None,
    supported: Optional[List[str]] = None,
    consecutive: Optional[str] = None,
    filename: Optional[str] = None,
) -> str:
    """Generate Eclipse include strings from dataframes in ecl2df format

    Args:
        dataframe: Dataframe with Eclipse data on ecl2df format.
        keywords: List of keywords to include. Will be reduced
            to the set of keywords available in dataframe and to those supported
        comments: Dictionary indexed by keyword with comments to be
            included pr. keyword. If a key named "master" is present
            it will be used as a master comment for the outputted file.
        supported: List of strings of keywords which are
            supported in this invocation of this function.
        consecutive: Column name for which we require the
            numbers to be consecutive. Typically PVTNUM, EQLNUM, SATNUM.
        filename: If supplied, the generated text will also be dumped
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
    if keywords is None or isinstance(keywords, str):
        keywords = [keywords]
    keywords_in_frame = set(dataframe["KEYWORD"])
    if keywords[0] is None and len(keywords) == 1:
        assert supported is not None
        keywords = supported
    else:
        # Warn if some keywords are unsupported:
        assert keywords is not None
        assert supported is not None
        not_supported: Set[Optional[str]] = set(keywords) - set(supported)
        if not_supported:
            logger.warning(
                "Requested keyword(s) not supported by %s: %s",
                calling_module.__name__,  # type: ignore
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
        + calling_module.__name__  # type: ignore
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


def runlength_eclcompress(string: str, sep: str = "  ") -> str:
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


def stack_on_colnames(
    dframe: pd.DataFrame,
    sep: str = "@",
    stackcolname: str = "DATE",
    inplace: bool = True,
) -> pd.DataFrame:
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
        dframe: A dataframe to stack
        sep: The separator that is used in dframe.columns to define
            the multilevel column names.
        stackcolname: Used as column name for the second level
            of the column multiindex
    """
    if not inplace:
        dframe = dframe.copy()
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


def is_color(input_string: str) -> bool:
    """Checks if the input string is a valid color.
    That is six-digit hexadecimal, three-digit hexadecimal or
    given as an SVG color keyword name
    """
    if input_string.lower() in SVG_COLOR_NAMES:
        return True

    regex = "^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
    return bool(re.match(regex, input_string))


def parse_lyrfile(filename: str) -> Optional[List[Dict[str, Any]]]:
    """Return a list of dicts representation of the lyr file.

    The lyr file contains data of the following format,
    where the color code is optional::

      'ZoneA' 1-4     #FFE5F7
      'ZoneB' 5       red

    Description of the lyr format:
    https://resinsight.org/3d-main-window/formations/#formation-names-description-files-_lyr_

    The output has the following format::

        [
            {
                "name": "ZoneA",
                "from_layer": 1,
                "to_layer": 4,
                "color": "#FFE5F7"
            },
            {
                "name": "ZoneB",
                "span": 5,
                "color": "red"
            }
        ]

    Args:
        filename: Absolute path to a lyr file

    Returns:
        A list of dictionaries representing the information in the lyr file.

    """  # noqa

    zonelines = Path(filename).read_text(encoding="utf-8").splitlines()

    # Remove comments, support both "--" and "#":
    zonelines = [line.split("--")[0].strip() for line in zonelines]
    zonelines = [line for line in zonelines if line and not line.startswith("#")]

    lyrlist: List[Dict[str, Any]] = []
    for line in zonelines:
        try:
            linesplit = shlex.split(line)
            zonedict: Dict[str, Any] = {"name": linesplit[0]}
            zone_color = linesplit.pop(-1) if is_color(linesplit[-1]) else None
            if zone_color is not None:
                zonedict["color"] = zone_color

            numbers = " ".join(linesplit[1:]).split("-")
            if len(numbers) == 2:
                from_layer, to_layer = int(numbers[0]), int(numbers[1])
                if from_layer <= to_layer:
                    zonedict["from_layer"] = from_layer
                    zonedict["to_layer"] = to_layer
                else:
                    logger.error("From_layer higher than to_layer")
                    raise ValueError()
            elif len(numbers) == 1:
                zonedict["span"] = int(numbers[0])
            else:
                raise ValueError()
            lyrlist.append(zonedict)
        except ValueError:
            logger.error("Could not parse lyr file %s", filename)
            logger.error("Failed on content: %s", line)
            return None
    return lyrlist


def convert_lyrlist_to_zonemap(lyrlist: List[Dict[str, Any]]) -> Dict[int, str]:
    """Returns a layer to zone map as a dictionary

    Args:
        lyrlist: list of dicts coming from parse_lyrfile()
    Returns:
        Layer to zone mapping {1: "zoneA", 2: "zoneB"}
    """
    if lyrlist is None:
        return None
    zonemap = {}
    for idx, zonedict in enumerate(lyrlist):
        if "span" in zonedict:
            from_layer = lyrlist[idx - 1]["to_layer"] + 1 if idx > 0 else 1
            to_layer = from_layer + zonedict["span"]
        else:
            from_layer = zonedict["from_layer"]
            to_layer = zonedict["to_layer"]
        zonemap.update(dict.fromkeys(range(from_layer, to_layer + 1), zonedict["name"]))
    return zonemap


def get_wells_matching_template(template: str, wells: list):
    """Returns the wells in the list that is matching the template
    containing wilcard characters. The wildcard charachters supported
    are * to match zero or more charachters and ? to match a single
    non-empty character. Any wildcards in the beginning of the template
    must be preceded with a \\.

    Well name templates starting with ? might be allowed in Eclipse
    in some contexts, but not in all and will not be permitted here to
    avoid confusion.

    Args:
        template: well name template with wildcard characters
        wells: list of wells to match against the template

    Returns:
        List of matched wells
    """
    if template.startswith("*") or template.startswith("?"):
        raise ValueError(
            "Well template not allowed to start with a wildcard character: "
            f"Must be preceded with a \\: {template}"
        )
    if template.startswith("\\"):
        # Note that the two \\ are actually read as one and
        # this will return True for f.ex '\*P1'
        template = template[1:]
    regex = template.replace("*", ".*").replace("?", ".")
    return [well for well in wells if bool(re.match(regex, well))]

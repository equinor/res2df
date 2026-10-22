"""Extract FIP region reports from PRT file"""

import argparse
import datetime
import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd

from datetime import date

from .common import parse_month, write_dframe_stdout_file
from .res2csvlogger import getLogger_res2csv
from .resdatafiles import ResdataFiles

logger = logging.getLogger(__name__)

REGION_REPORT_COLUMNS: list[str] = [
    "DATE",
    "FIPNAME",
    "REGION",
    "DATATYPE",
    "TO_REGION",
    "STOIIP_OIL",
    "ASSOCIATEDOIL_GAS",
    "STOIIP_TOTAL",
    "WIIP_TOTAL",
    "GIIP_GAS",
    "ASSOCIATEDGAS_OIL",
    "GIIP_TOTAL",
    # "PORV_TOTAL",
    # "HCPV_OIL",
    # "WATPV_TOTAL",
    # "HCPV_GAS",
    # "HCPV_TOTAL",
]


def report_block_lineparser(line: str) -> tuple:
    """
    Parses single lines within region reports, splits data into a tuple.

    Does not support many different phase configurations yet.
    """

    def float_or_nan(string: str) -> float:
        try:
            return float(string)
        except ValueError:
            return np.nan

    allowed_line_starts = [":CURRENTLY", ":OUTFLOW", ":MATERIAL", ":ORIGINALLY"]
    if not any(line.strip().upper().startswith(x) for x in allowed_line_starts):
        return ()

    colonsections = line.split(":")
    to_index: int | None
    if "OUTFLOW TO REGION" in line:
        to_index = int(colonsections[1].split()[3])
        row_name = "OUTFLOW TO REGION"
    else:
        to_index = None
        row_name = " ".join(colonsections[1].strip().upper().split())

    # Oil section:
    liquid_oil: float | None = None
    vapour_oil: float | None = None
    total_oil: float | None = None
    if len(colonsections[2].split()) == 3:
        (liquid_oil, vapour_oil, total_oil) = map(
            float_or_nan, colonsections[2].split()
        )
    elif len(colonsections[2].split()) == 2:
        (liquid_oil, total_oil) = map(float_or_nan, colonsections[2].split())
    elif len(colonsections[2].split()) == 1:
        total_oil = float_or_nan(colonsections[2])

    total_water = float_or_nan(colonsections[3])

    # Gas section:
    free_gas = None
    dissolved_gas = None
    total_gas = None
    if len(colonsections[4].split()) == 1:
        total_gas = float_or_nan(colonsections[4])
    elif len(colonsections[4].split()) == 2:
        (free_gas, total_gas) = map(float_or_nan, colonsections[4].split())
    else:
        (free_gas, dissolved_gas, total_gas) = map(
            float_or_nan, colonsections[4].split()
        )
    return (
        row_name,
        to_index,
        liquid_oil,
        vapour_oil,
        total_oil,
        total_water,
        free_gas,
        dissolved_gas,
        total_gas,
    )


def df(
    prtfile: str | ResdataFiles, fipname: str = "FIPNUM", porv: bool = False
) -> pd.DataFrame:
    """
    Parses a PRT file from and finds FIPXXXX REGION REPORT blocks and
    organizes those numbers into a dataframe

    Each row in the dataframe represents one parsed line in the PRT file, with
    DATE and region index added.

    Args:
        prtfile: filename (PRT) or a ResdataFiles object
        fipname: The name of the regport regions, FIPNUM, FIPZON or whatever
            Max length of the string is 8, the first three characters must be FIP,
            and the next 3 characters must be unique for a given :term:`.DATA file`.
    """
    if isinstance(prtfile, ResdataFiles):
        prtfile = prtfile.get_prtfilename()
    if not fipname.startswith("FIP"):
        raise ValueError("fipname must start with FIP")
    if len(fipname) > 8:
        raise ValueError("fipname can be at most 8 characters")

    # List of rows in final dataframe
    fip_records = []
    porv_records = []

    # State variables while parsing line by line:
    in_fip_report_block = False
    in_porv_report_block = False
    region_index = None
    date = None

    ecl_datematcher = re.compile(r"\s\sREPORT\s+\d+\s+(\d+)\s+(\w+)\s+(\d+)")
    opm_datematcher = re.compile(r"Starting time step.*? date = (\d+)-(\w+)-(\d+)\s*")

    # When case insensitive, this one works with both Eclipse100 and OPM:
    fipreportblockmatcher = re.compile(
        ".+" + fipname + r"\s+REPORT\s+REGION\s+(\d+)", re.IGNORECASE
    )
    porvreportblockmatcher = re.compile(r"^\s*:\s*RESERVOIR VOLUMES.*$")

    with Path(prtfile).open(encoding="utf-8") as prt_fh:
        logger.info(
            "Parsing file %s for blocks starting with %s REPORT REGION",
            prtfile,
            fipname,
        )
        for line in prt_fh:
            matcheddate = re.match(ecl_datematcher, line)
            if matcheddate is None:
                matcheddate = re.match(opm_datematcher, line)
            if matcheddate is not None:
                newdate = datetime.date(
                    year=int(matcheddate.group(3)),
                    month=parse_month(matcheddate.group(2).upper()),
                    day=int(matcheddate.group(1)),
                )
                if newdate != date:
                    date = newdate
                    logger.debug("Found date: %s", date)
                continue

            matchedfipreportblock = re.match(fipreportblockmatcher, line)
            matchedporvreportblock = re.match(porvreportblockmatcher, line)

            # FIP report
            if matchedfipreportblock:
                in_fip_report_block = True
                region_index = int(matchedfipreportblock.group(1))
                logger.debug("  Region report for region %s", region_index)
                continue
            if line.startswith(" ============================"):
                in_fip_report_block = False
                continue

            if in_fip_report_block:
                interesting_strings = ["IN PLACE", "OUTFLOW", "MATERIAL"]
                if not sum(string in line.upper() for string in interesting_strings):
                    # Skip if we are not on an interesting line.
                    continue

                # The colons in the report block are not reliably included
                # (differs by Eclipse version), even in the same PRT file. We
                # insert them in fixed positions and hope for the best (if the
                # ASCII table is actually dynamic with respect to content, this
                # will fail)
                line = line.strip()
                if line[0] != ":":
                    line = ":" + line
                # There should another colon somewhere between 25 - 27
                # (depend on OPM/Eclipse version)
                if ":" not in line[25:27] and len(line) > 26:
                    linechars = list(line)
                    linechars[26] = ":"
                    line = "".join(linechars)

                fip_records.append(
                    [date, fipname, region_index, *list(report_block_lineparser(line))]
                )

            if porv:
                # Reservoir pore volumes report block
                if matchedporvreportblock:
                    in_porv_report_block = True
                    # region_index = int(matchedfipreportblock.group(1))
                    # logger.debug("  Region report for region %s", region_index)
                    # continue
                if line.startswith(" ============================"):
                    in_porv_report_block = False
                    continue

                if in_porv_report_block:
                    # Extract lines with only numbers in between colons
                    line_split = [
                        part.strip() for part in line.split(":") if part.strip()
                    ]
                    if len(line_split) != 6:
                        continue
                    try:
                        int(line_split[0])
                    except ValueError:
                        # Not the line we are looking for.
                        continue

                    porv_records.append(
                        {
                            "DATE": date,
                            "FIPNAME": fipname,
                            "REGION": int(line_split[0]),
                            "PORV_TOTAL": float(line_split[1]),
                            "HCPV_OIL": float(line_split[2]),
                            "WATPV_TOTAL": float(line_split[3]),
                            "HCPV_GAS": float(line_split[4]),
                            "HCPV_TOTAL": float(line_split[5]),
                        }
                    )

    df_fip = pd.DataFrame(data=fip_records, columns=REGION_REPORT_COLUMNS)

    if porv:
        df_porv = pd.DataFrame(data=porv_records)
        df_fip = df_fip.merge(df_porv, how="outer", on=["DATE", "FIPNAME", "REGION"])

    return df_fip


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Fill parser with command line arguments"""
    parser.add_argument("PRTFILE", type=str, help="PRT file (or .DATA file)")
    parser.add_argument(
        "--fipname",
        type=str,
        help="Region parameter name of interest",
        default="FIPNUM",
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Output CSV filename", default="outflow.csv"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    parser.add_argument("--debug", action="store_true", help="Debug mode for logging")
    return parser


def fipreports_main(args: argparse.Namespace) -> None:
    """Command line API"""
    logger = getLogger_res2csv(__name__, vars(args))
    if args.PRTFILE.endswith(".PRT"):
        prtfile = args.PRTFILE
    else:
        prtfile = ResdataFiles(args.PRTFILE).get_prtfilename()
    dframe = df(prtfile, args.fipname)
    write_dframe_stdout_file(dframe, args.output, index=False, caller_logger=logger)


def _find_report_date_in_prt(line: str, find_initial: bool = False) -> date | None:
    """For a line in PRT file, search for a pattern to find a report date.
    Return the corresponding date.

    Args:
        line (str): Line from the PRT file.

    Returns:
        datetime.date: The report date wanted.
    """

    # To find a report date in PRT file, use regular expressions compiled upfront, as
    # global constants

    date_matcher = DATE_MATCHER

    if find_initial:
        # Different pattern for Eclipse and Flow, try Eclipse syntax first
        date_matcher = DATE_MATCHER_ECL

    date_object = None
    if date_matcher.search(line) is not None:
        line_split = line.split("*")
        date_string = line_split[0].rstrip().split("  ")[-1]
        # Handle Eclipse dumping out July as JLY instead of JUL
        date_string = date_string.replace("JLY", "JUL")
        date_object = datetime.datetime.strptime(date_string, "%d %b %Y").date()

    if find_initial and date_object is None:
        # Try Flow syntax
        date_matcher = DATE_MATCHER_FLOW
        if date_matcher.search(line) is not None:
            line_split = line.split("=")
            date_string = line_split[-1].strip()
            date_object = datetime.datetime.strptime(date_string, "%d-%b-%Y").date()
            logger.debug("This is an OPM Flow PRT file\n")
    elif find_initial and date_object is not None:
        logger.debug("This is an Eclipse PRT file\n")

    return date_object


def _currently_in_place_from_prt(
    prt_file: str, fipname: str = "FIPNUM", date_str: str | None = None
) -> tuple[pd.DataFrame, np.ndarray, str]:
    """Extracts currently-in-place volumes from a PRT file

    This function uses res2df.fipreports, and slices its
    output for the purpose here.

    Args:
        prt_file (str): Path to a PRT to parse
        fipname (str): FIPNUM, FIPZON or similar.
        date_str (str): If None or "first", the first date will be used. If not None,
                    "first" or "last", it should be an ISO-formatted date string
                    to extract (YYYY-MM-DD).

    Returns:
        pd.DataFrame: The dataframe with in-place volumes.
        np.ndarray: Array of available dates with BALANCE reports.
        str: The selected date as a string.
    """
    inplace_df = df(prt_file, fipname=fipname)

    # Avoid date_str as None, use empty string instead
    if date_str is None:
        date_str = ""

    if inplace_df.empty:
        logger.warning("The PRT file %s has no volume report for %s", prt_file, fipname)
        # Then there will be no RESERVOIR VOLUME report either
        return inplace_df, np.array([]), date_str

    available_dates = inplace_df.sort_values("DATE")["DATE"].unique()

    # Available dates as list of strings:
    available_dates_str = [
        date_obj.strftime("%Y-%m-%d") for date_obj in available_dates
    ]
    logger.info(f" Available dates with BALANCE report are:\n{available_dates_str}")

    if date_str in {"", "first"}:
        date = available_dates[0]
        date_str = date.strftime("%Y-%m-%d")  # update date_str to the date found
    elif date_str == "last":
        date = available_dates[-1]
        date_str = date.strftime("%Y-%m-%d")  # update date_str to the date found
    else:
        date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

        if date not in available_dates:
            logger.warning(
                f" The user specified date {date_str} is not available "
                f"with volume report in the PRT file.\n"
                f"Available dates with volume report are:\n{available_dates_str}",
            )
            # Should return an empty dataframe with the same columns,
            # and not volumes for first date in PRT file
            empty_df = pd.DataFrame(columns=inplace_df.columns)
            return empty_df, np.array([]), date_str

    # Filter to requested date:
    inplace_df = inplace_df[inplace_df["DATE"] == date]

    # Filter dataframe to only volumes pr. region, not inter-region flows:
    inplace_df = inplace_df[inplace_df["DATATYPE"] == "CURRENTLY IN PLACE"]

    # Cleanup dataframe:
    inplace_df = inplace_df.drop(
        ["DATATYPE", "TO_REGION", "FIPNAME", "DATE"], axis="columns"
    ).set_index("REGION")
    inplace_df.index.name = fipname  # Use "FIPNUM" if not handled by Webviz

    logger.info("Extracted CURRENTLY IN PLACE from %s at date %s", prt_file, date_str)

    # Find the initial date from the PRT file, to compare with date for report extracted
    initial_date_object = None
    find_initial = True
    with Path(prt_file).open(encoding="utf8") as f_handle:
        for line in f_handle:
            initial_date_object = _find_report_date_in_prt(line, find_initial)

            if initial_date_object is not None:
                logger.info(
                    f"Initial date is {initial_date_object}, report date is {date_str}"
                )
                break

    if initial_date_object is not None and (date > initial_date_object):
        logger.warning(
            "The volume report extracted is not at initial time. \n The volume "
            "report is from %s, which is later than start of simulation (%s).",
            date_str,
            initial_date_object,
        )
    elif initial_date_object is None:
        logger.warning(
            "Cannot determine if volume report is at initial time.",
        )

    return inplace_df, available_dates, date_str


def _reservoir_volumes_from_prt(
    prt_file: str,
    dates_bal_report: np.ndarray,
    fipname: str = "FIPNUM",
    date_str: str = "",
) -> pd.DataFrame:
    """Extracts numbers from the table "RESERVOIR VOLUMES" in an Eclipse PRT
    file, example table is::

                                                          ===================================
                                                          :  RESERVOIR VOLUMES      RM3     :
      :---------:---------------:---------------:---------------:---------------:---------------:
      : REGION  :  TOTAL PORE   :  PORE VOLUME  :  PORE VOLUME  : PORE VOLUME   :  PORE VOLUME  :
      :         :   VOLUME      :  CONTAINING   :  CONTAINING   : CONTAINING    :  CONTAINING   :
      :         :               :     OIL       :    WATER      :    GAS        :  HYDRO-CARBON :
      :---------:---------------:---------------:---------------:---------------:---------------:
      :   FIELD :     399202846.:      45224669.:     353978177.:             0.:      45224669.:
      :       1 :      78802733.:      17000359.:      61802374.:             0.:      17000359.:
      :       2 :      79481140.:             0.:      79481140.:             0.:             0.:
      :       3 :      75757104.:      17096867.:      58660238.:             0.:      17096867.:
      :       4 :      74929403.:             0.:      74929403.:             0.:             0.:
      :       5 :      50120783.:      11127443.:      38993340.:             0.:      11127443.:
      :       6 :      40111683.:             0.:      40111683.:             0.:             0.:
      ===========================================================================================

    If no BALANCE report, there will be no RESERVOIR VOLUME report in the PRT file.

    Args:
        prt_file (str): PRT filename.
        dates_bal_report (np.ndarray): Available dates with BALANCE report in the PRT file.
        fipname (str): Name of FIP-parameter, defaults to FIPNUM.
        date_str (str): The requested date to extract volume report from PRT file from.

    Returns:
        pd.DataFrame: The dataframe with reservoir volumes.
    """  # noqa: E501

    records = []
    start_matcher = re.compile(r"^\s*:\s*RESERVOIR VOLUMES.*$")

    table_found = (
        False  # State determining if current line is in our interesting table or not.
    )
    # The Reservoir Volume table is not tagged with the "FIPNAME", but will appear
    # after the in-place volume table (see the "BALANCE" report) in the PRT file.
    fipname_found = fipname == "FIPNUM"  # found the correct fipname, True for FIPNUM

    # Must pick the reservoir volume table corresponding to the date of interest
    date_found = False

    # In case empty numpy array (no dates provided as input to function):
    if dates_bal_report.size == 0:
        logger.error(
            "No dates with BALANCE report in the PRT file %s", prt_file, stacklevel=2
        )
        return pd.DataFrame()

    # Get the relevant date in ISO-format, as datetime.date object
    if date_str in {"", "first"}:
        # Use the first date with BAL report also for res.vol
        wanted_date = dates_bal_report[0]
    elif date_str == "last":
        wanted_date = dates_bal_report[-1]
    else:
        wanted_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

    # Eclipse, Flow: Look for "  REPORT " at start of line (Eclipse: up to REPORT 999)
    with Path(prt_file).open(encoding="utf8") as f_handle:
        for line in f_handle:
            # Search PRT file for the date requested:
            date_object = _find_report_date_in_prt(line)

            if date_object == wanted_date:
                date_found = True
            if isinstance(date_object, date) and date_object > wanted_date:
                # Next report step (i.e. no Reservoir Volume Report) -> stop search
                break

            # PRT file will have the BAL<nnn> report after the BALANCE report
            if date_found and line.startswith("  " + "BAL" + fipname[3:6]):
                fipname_found = True
                continue
            if date_found and fipname_found and start_matcher.search(line) is not None:
                table_found = True
                continue
            if table_found and line.strip().startswith("======================="):
                # PRT table is finished.
                break
            if table_found:
                # Extract lines with only numbers in between colons
                line_split = [part.strip() for part in line.split(":") if part.strip()]
                if len(line_split) != 6:
                    continue
                try:
                    int(line_split[0])
                except ValueError:
                    # Not the line we are looking for.
                    continue
                records.append(
                    {
                        fipname: int(line_split[0]),
                        "PORV_TOTAL": float(line_split[1]),
                        "HCPV_OIL": float(line_split[2]),
                        "WATPV_TOTAL": float(line_split[3]),
                        "HCPV_GAS": float(line_split[4]),
                        "HCPV_TOTAL": float(line_split[5]),
                    }
                )

    if not records:
        logger.warning(
            "No RESERVOIR VOLUMES table found in PRT file %s at requested date %s",
            prt_file,
            wanted_date,
        )
        logger.warning(
            "Include RPTSOL with FIP=2 (or 3) and 'FIPRESV' in Eclipse DATA file"
        )
        return pd.DataFrame()

    return pd.DataFrame(records).set_index(fipname)

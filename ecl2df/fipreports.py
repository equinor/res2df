# pylint: disable=c0301
"""Extract FIP region reports from Eclipse PRT file"""

import argparse
import datetime
import logging
import re
from typing import List, Optional, Union

import numpy as np
import pandas as pd

from ecl2df import EclFiles, getLogger_ecl2csv
from ecl2df.common import parse_ecl_month, write_dframe_stdout_file

logger = logging.getLogger(__name__)

REGION_REPORT_COLUMNS: List[str] = [
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
        return tuple()

    colonsections = line.split(":")
    to_index: Optional[int]
    if "OUTFLOW TO REGION" in line:
        to_index = int(colonsections[1].split()[3])
        row_name = "OUTFLOW TO REGION"
    else:
        to_index = None
        row_name = " ".join(colonsections[1].strip().upper().split())

    # Oil section:
    liquid_oil: Optional[float] = None
    vapour_oil: Optional[float] = None
    total_oil: Optional[float] = None
    if len(colonsections[2].split()) == 3:
        (liquid_oil, vapour_oil, total_oil) = map(
            float_or_nan, colonsections[2].split()
        )
    elif len(colonsections[2].split()) == 1:
        total_oil = float_or_nan(colonsections[2])
    else:
        (liquid_oil, total_oil) = map(float_or_nan, colonsections[2].split())

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


def df(prtfile: Union[str, EclFiles], fipname: str = "FIPNUM") -> pd.DataFrame:
    """
    Parses a PRT file from Eclipse and finds FIPXXXX REGION REPORT blocks and
    organizes those numbers into a dataframe

    Each row in the dataframe represents one parsed line in the PRT file, with
    DATE and region index added.

    Args:
        prtfile: filename (PRT) or an EclFiles object
        fipname: The name of the regport regions, FIPNUM, FIPZON or whatever
            Max length of the string is 8, the first three characters must be FIP,
            and the next 3 characters must be unique for a given Eclipse deck.
    """
    if isinstance(prtfile, EclFiles):
        prtfile = prtfile.get_prtfilename()
    if not fipname.startswith("FIP"):
        raise ValueError("fipname must start with FIP")
    if len(fipname) > 8:
        raise ValueError("fipname can be at most 8 characters")

    # List of rows in final dataframe
    records = []

    # State variables while parsing line by line:
    in_report_block = False
    region_index = None
    date = None

    ecl_datematcher = re.compile(r"\s\sREPORT\s+\d+\s+(\d+)\s+(\w+)\s+(\d+)")
    opm_datematcher = re.compile(r"Starting time step.*? date = (\d+)-(\w+)-(\d+)\s*")

    # When case insensitive, this one works with both Eclipse100 and OPM:
    reportblockmatcher = re.compile(
        ".+" + fipname + r"\s+REPORT\s+REGION\s+(\d+)", re.IGNORECASE
    )

    # Flag for whether we are supposedly parsing a PRT file made by OPM flow:
    opm = False

    with open(prtfile, encoding="utf-8") as prt_fh:
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
                    opm = True
            if matcheddate is not None:
                newdate = datetime.date(
                    year=int(matcheddate.group(3)),
                    month=parse_ecl_month(matcheddate.group(2).upper()),
                    day=int(matcheddate.group(1)),
                )
                if newdate != date:
                    date = newdate
                    logger.debug("Found date: %s", str(date))
                continue
            matchedreportblock = re.match(reportblockmatcher, line)
            if matchedreportblock:
                in_report_block = True
                region_index = int(matchedreportblock.group(1))
                logger.debug("  Region report for region %s", str(region_index))
                continue
            if line.startswith(" ============================"):
                in_report_block = False
                continue

            if in_report_block:
                interesting_strings = ["IN PLACE", "OUTFLOW", "MATERIAL"]
                if not sum([string in line.upper() for string in interesting_strings]):
                    # Skip if we are not on an interesting line.
                    continue

                if opm is False:
                    # The colons in the report block are not reliably included
                    # (differs by Eclipse version), even in the same PRT file. We
                    # insert them in fixed positions and hope for the best (if the
                    # ASCII table is actually dynamic with respect to content, this
                    # will fail)
                    linechars = list(line)
                    linechars[1] = ":"
                    linechars[27] = ":"
                    line = "".join(linechars)

                records.append(
                    [date, fipname, region_index] + list(report_block_lineparser(line))
                )
    return pd.DataFrame(data=records, columns=REGION_REPORT_COLUMNS)


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Fill parser with command line arguments"""
    parser.add_argument("PRTFILE", type=str, help="Eclipse PRT file (or DATA file)")
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


def fipreports_main(args) -> None:
    """Command line API"""
    logger = getLogger_ecl2csv(  # pylint: disable=redefined-outer-name
        __name__, vars(args)
    )
    if args.PRTFILE.endswith(".PRT"):
        prtfile = args.PRTFILE
    else:
        prtfile = EclFiles(args.PRTFILE).get_prtfilename()
    dframe = df(prtfile, args.fipname)
    write_dframe_stdout_file(dframe, args.output, index=False, caller_logger=logger)

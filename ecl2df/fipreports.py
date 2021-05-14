# pylint: disable=c0301
"""Extract FIP region reports from Eclipse PRT file"""

import re
import logging
import argparse
import datetime
from typing import Union, List, Optional

import pandas as pd

from ecl2df import EclFiles
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

    allowed_line_starts = [" :CURRENTLY", " :OUTFLOW", " :MATERIAL", " :ORIGINALLY"]
    if not any([line.startswith(x) for x in allowed_line_starts]):
        return tuple()

    colonsections = line.split(":")
    to_index: Optional[int]
    if "OUTFLOW TO REGION" in line:
        to_index = int(colonsections[1].split()[3])
        row_name = "OUTFLOW TO REGION"
    else:
        to_index = None
        row_name = colonsections[1].strip()

    # Oil section:
    liquid_oil: Optional[float]
    vapour_oil: Optional[float]
    total_oil: Optional[float]
    if len(colonsections[2].split()) == 3:
        # yes we have:
        (liquid_oil, vapour_oil, total_oil) = map(float, colonsections[2].split())
    elif len(colonsections[2].split()) == 1:
        total_oil = float(colonsections[2])
        (liquid_oil, vapour_oil) = (None, None)
    else:
        (liquid_oil, total_oil) = map(float, colonsections[2].split())
        vapour_oil = None
    total_water = float(colonsections[3])

    # Gas section:
    if len(colonsections[4].split()) == 1:
        total_gas = float(colonsections[4])
        (free_gas, dissolved_gas) = (None, None)
    else:
        (free_gas, dissolved_gas, total_gas) = map(float, colonsections[4].split())
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

    datematcher = re.compile(r"\s\sREPORT\s+(\d+)\s+(\d+)\s+(\w+)\s+(\d+)")
    reportblockmatcher = re.compile(".+" + fipname + r"\s+REPORT\s+REGION\s+(\d+)")

    with open(prtfile) as prt_fh:
        logger.info(
            "Parsing file %s for blocks starting with %s REPORT REGION",
            prtfile,
            fipname,
        )
        for line in prt_fh:
            matcheddate = re.match(datematcher, line)
            if matcheddate:
                newdate = datetime.date(
                    year=int(matcheddate.group(4)),
                    month=parse_ecl_month(matcheddate.group(3)),
                    day=int(matcheddate.group(2)),
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
                if not sum([string in line for string in interesting_strings]):
                    # Skip if we are not on an interesting line.
                    continue
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
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    if args.PRTFILE.endswith(".PRT"):
        prtfile = args.PRTFILE
    else:
        prtfile = EclFiles(args.PRTFILE).get_prtfilename()
    dframe = df(prtfile, args.fipname)
    write_dframe_stdout_file(dframe, args.output, index=False, caller_logger=logger)

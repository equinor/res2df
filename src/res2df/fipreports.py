"""Extract FIP region reports from PRT file"""

import argparse
import datetime
import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd

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
        liquid_oil, vapour_oil, total_oil = map(float_or_nan, colonsections[2].split())
    elif len(colonsections[2].split()) == 2:
        liquid_oil, total_oil = map(float_or_nan, colonsections[2].split())
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
        free_gas, total_gas = map(float_or_nan, colonsections[4].split())
    else:
        free_gas, dissolved_gas, total_gas = map(float_or_nan, colonsections[4].split())
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
    last_seen_region = None
    in_porv_report_block = False
    region_index = None
    date = None

    ecl_datematcher = re.compile(r"\s\sREPORT\s+\d+\s+(\d+)\s+(\w+)\s+(\d+)")
    opm_datematcher = re.compile(r"Starting time step.*? date = (\d+)-(\w+)-(\d+)\s*")

    # When case insensitive, this one works with both Eclipse100 and OPM:
    # Match provided fipname
    fipnamereportblockmatcher = re.compile(
        ".+" + fipname + r"\s+REPORT\s+REGION\s+(\d+)", re.IGNORECASE
    )
    # Match any fipreport block. Group 1 = the FIP name
    fipreportblockmatcher = re.compile(
        r".+(FIP[^\s:]{0,5})\s+REPORT\s+REGION\s+(\d+)",
        re.IGNORECASE,
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

            matchedfipnamereportblock = re.match(fipnamereportblockmatcher, line)
            matchedfipreportblockmatcher = re.match(fipreportblockmatcher, line)
            matchedporvreportblock = re.match(porvreportblockmatcher, line)

            if matchedfipreportblockmatcher:
                last_seen_region = matchedfipreportblockmatcher.group(1)

            # FIP report
            if matchedfipnamereportblock:
                in_fip_report_block = True
                region_index = int(matchedfipnamereportblock.group(1))
                logger.debug("  Region report for region %s", region_index)
                continue
            if line.startswith(" ============================"):
                in_fip_report_block = False
                in_porv_report_block = False
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
                if (
                    matchedporvreportblock
                    and last_seen_region is not None
                    and last_seen_region.upper() == fipname.upper()
                ):
                    in_porv_report_block = True
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
        if len(porv_records) > 0:
            df_porv = pd.DataFrame(data=porv_records)
            df_fip = df_fip.merge(
                df_porv, how="outer", on=["DATE", "FIPNAME", "REGION"]
            )
        else:
            logger.warning(
                "No RESERVOIR VOLUMES tables found in PRT file."
                "Include RPTSOL or RPTSCHED with FIP=2 (or 3) and "
                "FIPRESV in the DATA file.",
            )

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
